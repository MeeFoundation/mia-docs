---
status: accepted
date: 2026-07-15
---
# Establish connections over a raw iroh dialogue: pairing is its own protocol, not pdn-store sync

## Context and Problem Statement

Two identities that have never met need to become [connected](../language/connection.md): exchange who they are (PdnId), how to reach each other (node addresses), and the initial access everything afterwards rides on — tickets to the metadata replicas through which capability grants and data-store tickets will later travel. Every ongoing channel in the stack — reconciliation, gossip, blob fetch — presupposes a shared replica and a ticket for it. Connection establishment is the step that *creates* that shared state, so it cannot presuppose it.

The concrete flow being designed is in-person pairing: the inviter's device displays a QR code, the scanner's device completes the procedure, and afterwards both identities see the connection from all of their devices. Two properties constrain the design. First, the QR is semi-public — shown on a screen, photographable — so nothing bearer-grade can ride in it; and at display time the counterparty is unknown, so nothing can be scoped to them either. Second, the invitation must be single-use: a one-time pairing secret verified and burned atomically, closing replay and the double-scan race. The question: over what channel does the pairing dialogue run?

Facts about the stack:

1. A node's iroh endpoint already multiplexes several protocols by application-layer protocol negotiation (ALPN) identifier — blob transfer, gossip, document sync are three handlers on one router (`data-layer`'s node assembly). Registering one more protocol handler on the same endpoint is the mechanism iroh provides for exactly this.
2. pdn-store tickets are bearer tokens bundling the replica capability (read or write) with node addresses (`src/ticket.rs`); whoever holds one can import the replica and sync it. This is why tickets must not appear in the QR.
3. Reconciliation is convergent and retryable: it has no request/response step and no "verify, then act exactly once" semantics — any ticket holder can re-run it at any time. An atomic check-and-burn of a one-time secret cannot be expressed as replica convergence.

## Decision Drivers

* Pairing distributes the *first* tickets between identities that share nothing yet; the mechanism must not itself require a shared replica or ticket — no bootstrap circularity.
* Nothing bearer-grade in the QR: a photograph must not grant durable access, and grants cannot be scoped before the counterparty is known.
* The one-time pairing secret needs an atomic verify-and-burn before any state change — request/response semantics with one authoritative side.
* Keep the pdn-store fork minimal ([ADR-0008](0008-iroh-without-willow.md)): pairing is not set reconciliation and does not belong in the sync engine.
* Leave the road open: the same dialogue must later carry the KERI proof of control over the presented PdnId, fit UWill-style capability-first authorization ([ADR-0007](0007-uwill.md)), and not preclude offline/pending invitations built later.

## Considered Options

* **A dedicated pairing protocol on its own ALPN: one raw bidirectional iroh connection per establishment** ← chosen
* **A bootstrap replica: the QR carries a ticket to a meeting replica, the exchange converges via pdn-store sync**
* **QR-only exchange: everything rides in the QR, no network dialogue at all**
* **Extend the pdn-store sync protocol with pairing messages**

## Decision Outcome

Chosen option: **a dedicated pairing protocol on its own ALPN**, because it is the only option that requires no pre-shared state, keeps bearer material out of the QR, and gives the secret's verify-and-burn one atomic home — while leaving pdn-store untouched.

The shape (names are working titles; the store-level realization is specified in the [connection metadata store spec](../../components/data-layer/connection-metadata-store.md)):

* **The QR carries**: the inviter device's node address (endpoint public key plus every address the endpoint publishes about itself: direct socket addresses, and a relay URL on a runtime that binds relays — reachability is a spawn-time choice, and a QR minted by the suites and by the container stand, which take the direct-paths-only one, carries direct addresses alone; on a runtime that also binds address lookup the public key resolves to a current address on its own, so addresses that have gone stale between minting and scanning are not fatal there), a one-time short-lived pairing secret (random, not a counter), the inviter's PdnId, and a format version. It carries **no** tickets and **no** identity proof.
* **The dialogue**: the scanner's endpoint dials the address over the pairing ALPN — a raw bidirectional QUIC stream, not a document-sync session. The scanner presents the pairing secret, its PdnId, its own node address, and a read ticket to the metadata replica it issues for the counterparty; the inviter **atomically verifies and burns** the secret — present and unburned → burn and continue, anything else → refuse — *before* creating or writing any state, then answers with the read ticket to its own metadata replica. The secret also burns on timeout, whichever comes first.
* **After the dialogue**: each side records the connection among its private-metadata directory's connections records and imports the counterpart's ticket. Everything later — capability grants, data-store tickets, further sharing, revocation — travels *inside* the exchanged metadata replicas over ordinary pdn-store sync, and reaches both identities' other devices through device replication. The raw channel is used once per establishment; it is not a data path.
* **Deferred**: the KERI proof of control over the presented PdnId is a marked step of this same dialogue, not built yet; until it lands the exchange is bearer-level (secret plus tickets), consistent with the interim posture of [ADR-0008](0008-iroh-without-willow.md).

### Consequences

* Good — no pre-shared state: the dialogue is what creates shared state, so the bootstrap circularity disappears.
* Good — a photographed QR expires with the secret; replay and double-scan close at one atomic point; a handshake that fails after the burn is repeated with a fresh invite, and re-running establishment is safe (re-creating one's own metadata replica is idempotent).
* Good — pdn-store stays untouched: pairing is runtime code behind its own ALPN, so upstream tracking of the fork is unaffected.
* Good — the dialogue has a natural slot for the KERI proof, and the format version in the QR gives the protocol room to evolve.
* Bad — both peers must be online simultaneously; inviting an offline party (pending connections) needs separate machinery later, which this decision leaves possible but does not build.
* Bad — a second protocol surface to design, version, and secure, next to the sync protocol.
* Bad — `data-layer`'s node assembly currently builds its protocol router internally (blobs, gossip, docs); it must gain a way to register an externally supplied protocol handler.
* Neutral — an observer of the QR learns the inviter's PdnId (a linkability leak, accepted for now).
* Neutral — the connection model above is unchanged: a connection is mutual knowledge plus exchanged metadata replicas; access to data remains a separate, capability-gated act.

## Validation

An in-process integration test drives the full establishment: invite → dial by the scanned address → secret verified and burned → tickets exchanged → both identities see the connection from all their devices (the device-replicated stores converge). Adversarial cases per the [access-control-tests practice](../../code-practices/access-control-tests.md), each paired with its allowed counterpart: a replayed or second presentation of the same secret is refused; presentation after expiry is refused; a caller without the secret obtains nothing — and refused attempts leave **no** observable state on the inviter (no replica created, no ticket issued, no connections record written in the directory), which is the atomicity property itself.

Re-establishment, the recovery path the Consequences claim: a fresh invite between identities that already share establishment state — a completed connection, or the residue of a handshake that died after the burn — converges rather than duplicates. One connections entry per side, each side's own metadata replica reused through its directory (tickets from different attempts address the same namespace), whichever side mints the fresh invite — including the direction-swapped retry.

## Pros and Cons of the Options

### Dedicated pairing ALPN (chosen)

* Good — zero pre-shared state; one-time semantics are natural on a request/response stream.
* Good — the QR stays free of bearer rights; the fork stays minimal.
* Bad — a new protocol surface; both-online only.

### Bootstrap replica (ticket in the QR)

* Good — reuses the sync machinery end to end.
* Bad — the QR itself becomes a bearer ticket: a photograph grants access, and the grant cannot be scoped because the counterparty is unknown at issue time.
* Bad — no atomic one-time step: reconciliation is convergent and retryable, a second scanner converges just as well; "burn" has no home.
* Bad — durable replica state (create, ticket, clean up) for a transient dialogue, and establishment starts depending on reconciliation timing.

### QR-only exchange (no dialogue)

* Good — no protocol at all.
* Bad — one-directional: the scanner's half (its PdnId, address, ticket) has no way back, so symmetric establishment is impossible.
* Bad — everything in the QR is bearer and photographable — including exactly what must not leak.
* Bad — no reachability confirmation and no burn semantics.

### Extend the sync protocol with pairing messages

* Good — one ALPN fewer.
* Bad — entangles the fork with a dialogue that has nothing to do with set reconciliation, deepening divergence from upstream against [ADR-0008](0008-iroh-without-willow.md)'s minimalism; pairing logic belongs to the runtime, not the store.

## More Information

Open questions, none blocking this decision: exact QR encoding and size budget; the later shape of pending/offline invitations; the exact contents of the KERI proof step; the QR linkability leak: whether the inviter's PdnId needs to be in the QR at all (it could travel inside the encrypted dialogue instead), and whether pairing should later present a per-relationship identifier rather than the long-lived PdnId — KERI makes minting per-context autonomic identifiers cheap, which is the hoped-for path, not yet a design.

Resolved by the connection-establishment change: secret entropy and lifetime (32 random bytes from the operating-system generator; 120-second default lifetime with an invite-time override; expiry checked lazily at presentation); mid-dialogue failure handling (a handshake that dies after the burn is retried with a fresh invite and converges — see Validation's re-establishment case); where the protocol handler lives and the `data-layer` API (the handler is pdn-node runtime code, registered at `Runtime::spawn` through `data-layer`'s spawn-time protocol slot, with a narrow dial handle for the dial side).

Related ADRs: [ADR-0007](0007-uwill.md) (the capability model the exchanged grants grow into), [ADR-0008](0008-iroh-without-willow.md) (fork minimalism; the metadata channel the exchanged tickets open), [ADR-0009](0009-per-issuer-namespace.md) (the per-issuer replicas the grants point into), [ADR-0010](0010-subset-rbsr.md) (the reconciliation-time egress filter that enforces the read grants the metadata replicas carry), [ADR-0012](0012-linking-over-raw-iroh.md) (device linking rebased onto this dialogue shape: dedicated ALPN, verify-and-burn, commit-precedes-reply).

External references: iroh protocol multiplexing — one endpoint, multiple ALPN-keyed handlers on a router (`Router::builder(endpoint).accept(alpn, handler)`); pdn-store `DocTicket { capability, nodes }` — a bearer token carrying the replica capability and node addresses (`src/ticket.rs`).
