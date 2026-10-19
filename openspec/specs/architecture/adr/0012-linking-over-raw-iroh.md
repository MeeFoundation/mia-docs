---
status: accepted
date: 2026-09-04
---
# Link devices over a raw iroh dialogue: the bootstrap ticket rides the reply, not the QR

## Context and Problem Statement

A new device joins an identity by obtaining the identity's private metadata store (PMS) — the one device-internal replica carrying the device set, the identity key and the typed tickets to the stores of the identity's pods (Invariant 1). Until this decision, linking was ticket-first: the QR carried the PMS's **write ticket** (the "seed"), the new device imported the PMS and then leaned on reconciliation twice — once to discover the next store's ticket through the PMS's entries, and once to push its own device registration back until it demonstrably reached an existing device. Both waits were retry loops born from debugged flakes (`code-practices/flaky-tests.md` records the second as the measured cure for a ~1.2%-per-act flake), and the QR was a durable bearer credential: a pdn-store ticket never expires, so a photographed seed granted write access to the whole PMS forever.

The alternative shape is a raw dialogue on a dedicated ALPN: a one-time secret atomically verified-and-burned before any state change, uniform refusals, commit-precedes-reply, and a spawn-time protocol slot in the node assembly that takes any number of handlers. The question: does device linking move onto that shape, and if so, what exactly rides the dialogue?

Facts that constrain the design:

1. A pdn-store ticket is a bearer token with unlimited lifetime; nothing bearer-grade may sit in a QR.
2. Reconciliation is convergent and retryable, with no "verify, then act exactly once" semantics — and, structurally, a wait on reconciliation in a ceremony's critical path is a wait on machinery whose timing the ceremony does not control.
3. Ticket payloads are blobs: a ticket read through PMS entries is payload-waiting (records land before bytes), so any in-ceremony PMS read reintroduces a discovery wait.
4. The inviter's device holds the PMS locally — every device of an identity does, by induction over creation and linking — so it can mint a fresh write ticket to it without any read through PMS entries.

## Decision Drivers

* No bearer material in the QR: a photographed payload must expire with its secret.
* No reconciliation wait in the linking critical path: the ceremony is one request/response exchange; the only wait left is the newcomer's own bounded catch-up against a peer that just answered.
* An atomic verify-and-burn for the one-time linking secret, with uniform refusals — the access boundary the seed model never had.
* The registration must not depend on cross-node delivery: the race behind the confirmed-registration loop should be removed, not re-cured.
* A linked device must come up with the identity's full store set: its PMS, through which everything else the identity holds is reached.
* Keep the pdn-store fork untouched; share one machinery between the ceremonies (pending-invite set, framing, protocol slot) rather than growing a parallel stack.

## Considered Options

* **A dedicated linking protocol on its own ALPN: verify-and-burn, inviter-side registration, the bootstrap ticket in the encrypted reply** ← chosen
* **Keep the seed QR: PMS write ticket in the QR, bootstrap by reconciliation** (the shape being replaced)
* **A message variant on another ceremony's ALPN** instead of a protocol of its own

## Decision Outcome

Chosen option: **a dedicated linking protocol on its own ALPN**, because it is the only option that removes both reconciliation waits and the bearer QR at once, gives the linking secret an atomic home, and hands the newcomer the full store set with no discovery step.

The shape (the ceremony is specified in [device-linking/spec.md](../../components/mee-pdn/pdn-node/device-linking/spec.md)):

* **The linking payload carries**: a format version, the inviting device's node address, a one-time short-lived secret, and the identity's `PdnId`. It carries **no** tickets and **no** identity proof — nothing in it grants durable access.
* **The dialogue**: the new device dials the payload's address on the linking ALPN — separate from every other ceremony's, because the stakes differ (a whole-PMS write ticket versus a pod's two store tickets) and separate protocols version their wire formats independently. It presents the format version and the secret; the inviter **atomically verifies and burns** the secret before any state change. Refusals are uniform: wrong, expired, burned, malformed, and unknown-version all get the same silent close, and a refused attempt leaves no observable state. A wrong secret burns nothing.
* **Inviter-side registration**: after the burn, the inviter writes the newcomer's timestamped pending-device record into its own PMS replica, taking the node id from the connection's authenticated peer identity — never from a claimed field; the request carries none. The registration is a local write on a device that already holds the PMS, so no cross-node delivery sits in the linking critical path. Pending records confer no device access and expire after 24 hours unless the newcomer confirms.
* **The ticket in the reply**: the inviter answers — commit preceding the reply — with a fresh write ticket to the PMS, minted from the local replica (no PMS reads, so no payload wait). The newcomer imports it and waits, bounded by the caller's timeout, for the first successful PMS sync session started after the import — one wait against the peer that just answered, not a retry loop; the node's periodic reconcile pass is the re-dial cadence within that budget. On any failure after the import the newcomer forgets the PMS replica and the identity's half of the node, so a failed link leaves no residue.
* **Everything else**: the identity key and the tickets to the stores of the identity's pods reach the newcomer through the PMS, after the ceremony; the linking critical path reads none of them.
* **What the dialogue does not establish**: the identity is asserted, not proven — the exchange is bearer-level, resting on the transport peer and the one-time secret. Both devices are online for it, and the device set only grows: an invite redeemed while the inviting device is offline, device removal, and revocation sit outside this decision.

### Consequences

* Good — no reconciliation in the critical path: both waits of the seed flow are structurally gone (discovery: nothing left to discover; registration: written where it must exist), and the one remaining wait is the newcomer's own catch-up with a live, just-answering peer.
* Good — the linking access boundary exists and is testable: a photographed payload expires with its secret; replay, expiry, and wrong-secret probes are refused uniformly and leave no observable state — the boundary the bearer QR never had.
* Good — a linked device comes up with the full store set: its PMS, through which it reaches every pod its identity holds.
* Good — one device-internal replica per identity: "the PMS synced but another of the identity's own stores silently didn't" is unrepresentable.
* Bad — the PMS write ticket now transits the network; accepted because it crosses an end-to-end encrypted QUIC channel to a peer that proved possession of a one-time secret — strictly narrower exposure than the same ticket in plaintext on a screen with unlimited lifetime.
* Bad — a ceremony surface of its own to version and secure, next to a pod's join; mitigated by one machinery shared between them (pending-invite set, length-prefixed postcard framing, state-slot discipline).
* Neutral — a reply lost after the registration leaves a pending device record: it confers nothing, since session classification consults the confirmed set alone, and it converges on the next fresh invite — the lost-reply posture a pod's join shares. The newcomer promotes its own record once the tickets are in hand, a write only the PMS's write ticket permits.
* Good — cancellation rollback remains supervised and retains its identity reservation until cleanup completes; shutdown waits for tracked cleanup within a 10-second budget, so an older attempt cannot dismantle a successful retry.
* Neutral — storage and ticket failures after the one-time secret burns remain uniform refusals to the peer, but emit typed local diagnostics for the operator.
* Neutral — an observer of the payload learns the identity's `PdnId` (a linkability leak, accepted for now).

## Validation

The linking scenario tests drive the ceremony end to end: create on one runtime, link on another — the newcomer is registered on the inviting device with no sync wait, `link` returns only once the PMS demonstrably caught up, and the newcomer comes up with the full store set (a record either runtime writes into the PMS becomes readable on the other). The refusal pairs, per the [access-control-tests practice](../../code-practices/access-control-tests.md), each next to their allowed counterpart and probed for no observable state: a replayed secret after a completed link, an expired secret, a wrong secret that burns nothing (the live one still links), an unknown payload version refused before dialing, linking into an already-hosted identity refused before dialing (the secret survives for another runtime to use), a linking invite for an unhosted identity. The chain through a linked device: a third device links from an invite minted on a linked device — the induction behind minting from local replicas. The rollback: a link whose PMS cannot catch up within the timeout leaves the dialing runtime hosting neither replica, with the identity's operations refusing as unknown rather than failing as storage errors. Lost-reply convergence, and what it does not confer: a dialer that never reads the reply leaves a pending registration that is in no device set, and a fresh invite links the same device cleanly. The data layer's own scenario holds the other half — a device registered as pending is served nothing of the identity's pods.

## Pros and Cons of the Options

### Dedicated linking ALPN, tickets in the reply (chosen)

* Good — kills both waits and the bearer QR in one shape; atomic one-time semantics on a request/response stream; full store set handed over.
* Good — machinery shared with a pod's join; the fork stays untouched.
* Bad — a second protocol surface; both-online only.

### The seed QR (ticket in the QR, bootstrap by reconciliation)

* Good — no new protocol; the QR alone suffices in principle.
* Bad — the QR is a durable bearer write credential to the whole PMS: a photograph grants access forever.
* Bad — two reconciliation waits in the critical path, each a retry loop over machinery the ceremony does not control — the flake source the confirmation loop was built to cure.
* Bad — no access boundary: nothing is verified, nothing burns, a replayed seed is indistinguishable from a legitimate one.

### A message variant on another ceremony's ALPN

* Good — one ALPN fewer; the same handler serves both ceremonies.
* Bad — entangles two dialogues with different stakes (a whole-PMS write ticket versus a pod's two store tickets) in one wire format, so neither can evolve without versioning the other.
* Bad — one handler must branch on intent before verify-and-burn, widening the pre-burn surface of both ceremonies.

## More Information

The dialogue carries no proof of control over the identity: such a proof arrives with a root identifier that can carry one ([ADR-0003](0003-mee-identity-represents-keri-autonomic-namespace.md)), and the dialogue is the exchange that would carry it.

A pod's join applies this shape to a pod ([ADR-0015](0015-pod-join-over-raw-iroh.md)): a one-time secret on a dedicated ALPN, verified and burned before any state changes. A linked device receives the identity key through the PMS, which is what lets it publish the identity's device list into every pod the identity belongs to.

Open questions, none blocking this decision: human-readable device labels in the registration (cheap to add behind the payload's format version); the QR encoding of the linking payload (a host concern); device removal and revocation (the device set only grows for now); whether linking should later present a per-relationship identifier instead of the long-lived `PdnId` — the hoped-for KERI path.

Related ADRs: [ADR-0015](0015-pod-join-over-raw-iroh.md) (a pod's join, on the same shape and machinery), [ADR-0003](0003-mee-identity-represents-keri-autonomic-namespace.md) (the proof of control this dialogue would carry), [ADR-0013](0013-identity-isolation-on-one-node.md) (several identities on one node, each linked on its own).
