---
status: proposed
date: 2026-07-16
---
# Link devices over a raw iroh dialogue: the bootstrap tickets ride the reply, not the QR

## Context and Problem Statement

A new device joins an identity by obtaining the identity's private-metadata directory — the one device-internal replica carrying the device set, the typed tickets, and the connections records (Invariant 1) — and the identity's data namespace. Until this decision, linking was ticket-first: the QR carried the directory's **write ticket** (the "seed"), the new device imported the directory and then leaned on reconciliation twice — once to discover the next store's ticket through the directory's entries, and once to push its own device registration back until it demonstrably reached an existing device. Both waits were retry loops born from debugged flakes (`code-practices/flaky-tests.md` records the second as the measured cure for a ~1.2%-per-act flake), and the QR was a durable bearer credential: a pdn-store ticket never expires, so a photographed seed granted write access to the whole directory forever.

Establishment ([ADR-0011](0011-pairing-over-raw-iroh.md)) already built the alternative shape on this codebase: a raw dialogue on a dedicated ALPN, a one-time secret atomically verified-and-burned before any state change, uniform refusals, commit-precedes-reply, and a spawn-time protocol slot in the node assembly that takes any number of handlers. The question: does device linking move onto that shape, and if so, what exactly rides the dialogue?

Facts that constrain the design:

1. A pdn-store ticket is a bearer token with unlimited lifetime; nothing bearer-grade may sit in a QR (the same driver as ADR-0011).
2. Reconciliation is convergent and retryable, with no "verify, then act exactly once" semantics — and, structurally, a wait on reconciliation in a ceremony's critical path is a wait on machinery whose timing the ceremony does not control.
3. Ticket payloads are blobs: a ticket read through directory entries is payload-waiting (records land before bytes), so any in-ceremony directory read reintroduces a discovery wait.
4. The inviter's device holds the directory and the data namespace locally — every device of an identity does, by induction over creation and linking — so it can mint fresh write tickets for both without any read through directory entries.

## Decision Drivers

* No bearer material in the QR: a photographed payload must expire with its secret.
* No reconciliation wait in the linking critical path: the ceremony is one request/response exchange; the only wait left is the newcomer's own bounded catch-up against a peer that just answered.
* An atomic verify-and-burn for the one-time linking secret, with uniform refusals — the access boundary the seed model never had.
* The registration must not depend on cross-node delivery: the race behind the confirmed-registration loop should be removed, not re-cured.
* A linked device must come up with the identity's full store set — directory and data namespace — resolving ADR-0009's deferred "discovery at linking" note.
* Keep the pdn-store fork untouched; reuse establishment's machinery (pending-invite set, framing, protocol slot) rather than growing a parallel stack.

## Considered Options

* **A dedicated linking protocol on its own ALPN: verify-and-burn, inviter-side registration, both bootstrap tickets in the encrypted reply** ← chosen
* **Keep the seed QR: directory write ticket in the QR, bootstrap by reconciliation** (the shape being replaced)
* **A message variant on the pairing ALPN** instead of a second protocol
* **The dialogue hands over the directory ticket only; the data namespace is discovered through the directory's `tickets/data` entry**

## Decision Outcome

Chosen option: **a dedicated linking protocol on its own ALPN**, because it is the only option that removes both reconciliation waits and the bearer QR at once, gives the linking secret the same atomic home pairing's has, and hands the newcomer the full store set with no discovery step.

The shape (the ceremony is specified in [device-linking.md](../../components/pdn-node/device-linking.md)):

* **The linking payload carries**: a format version, the inviting device's node address, a one-time short-lived secret, and the identity's `PdnId`. It carries **no** tickets and **no** identity proof — nothing in it grants durable access.
* **The dialogue**: the new device dials the payload's address on the linking ALPN — separate from the pairing ALPN, because the stakes differ (a whole-directory write ticket versus per-connection read tickets) and separate protocols version their wire formats independently. It presents the format version and the secret; the inviter **atomically verifies and burns** the secret before any state change. Refusals are uniform: wrong, expired, burned, malformed, and unknown-version all get the same silent close, and a refused attempt leaves no observable state. A wrong secret burns nothing.
* **Inviter-side registration**: after the burn, the inviter writes the newcomer's timestamped pending-device record into its own directory replica, taking the node id from the connection's authenticated peer identity — never from a claimed field; the request carries none. The registration is a local write on a device that already holds the directory, so no cross-node delivery sits in the linking critical path. Pending records confer no device access and expire after 24 hours unless the newcomer confirms.
* **Tickets in the reply**: the inviter answers — commit preceding the reply — with fresh write tickets to the directory and to the identity's data namespace, both minted from local replicas (no directory reads, so no payload wait). The newcomer imports both and waits, bounded by the caller's timeout, for the first successful directory sync session started after the import — one wait against the peer that just answered, not a retry loop; the node's periodic reconcile pass is the re-dial cadence within that budget. On any failure after the import the newcomer forgets both replicas — the data namespace unregistered from its issuer, not merely dropped — so a failed link leaves no residue.
* **The durable record**: creation still publishes the data-namespace ticket in the directory under the `data` kind — the flat bootstrap model's record for everything outside the ceremony; the linking critical path never reads it.
* **Deferred**: the KERI proof of control over the identity is a marked step of this dialogue, exactly as in pairing; both devices must be online; pending linking invites, device removal, and revocation are future work.

### Consequences

* Good — no reconciliation in the critical path: both waits of the seed flow are structurally gone (discovery: nothing left to discover; registration: written where it must exist), and the one remaining wait is the newcomer's own catch-up with a live, just-answering peer.
* Good — the linking access boundary exists and is testable: a photographed payload expires with its secret; replay, expiry, and wrong-secret probes are refused uniformly and leave no observable state — the boundary the bearer QR never had.
* Good — a linked device comes up with the full store set; manual out-of-band handover of same-identity data tickets disappears, resolving ADR-0009's deferral.
* Good — one device-internal replica per identity (the connections store folded into the directory in the same change): "the directory synced but the connections store silently didn't" is unrepresentable.
* Bad — the directory write ticket now transits the network; accepted because it crosses an end-to-end encrypted QUIC channel to a peer that proved possession of a one-time secret — strictly narrower exposure than the same ticket in plaintext on a screen with unlimited lifetime.
* Bad — a second ceremony surface to version and secure, next to pairing; mitigated by reusing pairing's machinery (pending-invite set, length-prefixed postcard framing, state-slot discipline).
* Neutral — a reply lost after the registration leaves a pending device record: it confers nothing, since session classification consults the confirmed set alone, and it converges on the next fresh invite — the same lost-reply posture as re-establishment. The newcomer promotes its own record once the tickets are in hand, a write only the directory's write ticket permits.
* Good — cancellation rollback remains supervised and retains its identity reservation until cleanup completes; shutdown waits for tracked cleanup within a 10-second budget, so an older attempt cannot dismantle a successful retry.
* Neutral — storage and ticket failures after the one-time secret burns remain uniform refusals to the peer, but emit typed local diagnostics for the operator.
* Neutral — an observer of the payload learns the identity's `PdnId` (the same linkability leak as pairing's QR, accepted for now).

## Validation

The linking scenario tests drive the ceremony end to end: create on one runtime, link on another — the newcomer is registered on the inviting device with no sync wait, `link` returns only once the directory demonstrably caught up, and the newcomer comes up with the full store set (entries written under the identity on either runtime become readable on the other). The refusal pairs, per the [access-control-tests practice](../../code-practices/access-control-tests.md), each next to their allowed counterpart and probed for no observable state: a replayed secret after a completed link, an expired secret, a wrong secret that burns nothing (the live one still links), an unknown payload version refused before dialing, linking into an already-hosted identity refused before dialing (the secret survives for another runtime to use), a linking invite for an unhosted identity. The non-founder chain: a third device links from an invite minted on a non-founder device — the induction behind minting from local replicas. The rollback: a link whose directory cannot catch up within the timeout leaves the dialing runtime hosting neither replica, with the identity's operations refusing as unknown rather than failing as storage errors. Lost-reply convergence, and what it does not confer: a dialer that never reads the reply leaves a pending registration that is in no device set, and a fresh invite links the same device cleanly. The data layer's own scenario holds the other half — a device registered as pending, holding a grant on one claim, receives exactly that claim and nothing more.

## Pros and Cons of the Options

### Dedicated linking ALPN, tickets in the reply (chosen)

* Good — kills both waits and the bearer QR in one shape; atomic one-time semantics on a request/response stream; full store set handed over.
* Good — machinery shared with pairing; the fork stays untouched.
* Bad — a second protocol surface; both-online only.

### The seed QR (ticket in the QR, bootstrap by reconciliation)

* Good — no new protocol; the QR alone suffices in principle.
* Bad — the QR is a durable bearer write credential to the whole directory: a photograph grants access forever.
* Bad — two reconciliation waits in the critical path, each a retry loop over machinery the ceremony does not control — the flake source the confirmation loop was built to cure.
* Bad — no access boundary: nothing is verified, nothing burns, a replayed seed is indistinguishable from a legitimate one.

### A message variant on the pairing ALPN

* Good — one ALPN fewer; the same handler serves both ceremonies.
* Bad — entangles two dialogues with different stakes (whole-directory write ticket versus per-connection read tickets) in one wire format, so neither can evolve without versioning the other.
* Bad — one handler must branch on intent before verify-and-burn, widening the pre-burn surface of both ceremonies.

### Directory-only data discovery (reply carries the directory ticket alone)

* Good — a smaller reply; the directory stays the single bootstrap artifact.
* Bad — without a reactive cascade nothing imports the data namespace, and with an in-ceremony wait on `tickets/data` it is the discovery loop again — ticket reads are payload-waiting by design.
* Bad — the full-store-set induction breaks: a non-founder device could answer a linking invite with a directory ticket but no data ticket it is guaranteed to hold.

## More Information

Open questions, none blocking this decision: human-readable device labels in the registration (cheap to add behind the payload's format version); the QR encoding of the linking payload (a host concern); device removal and revocation (the device set only grows for now); whether linking should later present a per-relationship identifier instead of the long-lived `PdnId` — the same hoped-for KERI path as pairing's.

Related ADRs: [ADR-0011](0011-pairing-over-raw-iroh.md) (the ceremony shape this decision reuses: dedicated ALPN, verify-and-burn, commit-precedes-reply, the assembly's protocol slot), [ADR-0008](0008-iroh-without-willow.md) (the interim bearer posture the deferred KERI step keeps), [ADR-0009](0009-per-issuer-namespace.md) (the per-issuer data namespace whose linking-time discovery this decision resolves), [ADR-0007](0007-uwill.md) (the capability model that later replaces bearer tickets).
