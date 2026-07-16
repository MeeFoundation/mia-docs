# Invariants

Cross-cutting rules the system upholds. **Referenced by number only** — write "Invariant 1" in code, specs, and discussion, never a name. The list is **append-only**: numbers are never reused or renumbered, and an invariant that stops holding is marked withdrawn in place rather than deleted.

## Invariant 1

A Mee Identity's connections store and private metadata store are reachable only by that identity's own devices, and a device's copies of them hold that identity's data only.

The enforcing mechanism is the store ticket, not a behavioural agreement between nodes: syncing or writing either replica requires its ticket, and an identity hands that ticket only to its own devices — at linking, over the private-metadata directory. (Today the ticket is a bearer token: whoever holds it has access. Identity-bound, revocable access lands with UWill.)

## Invariant 2

A node obtains a claim only if it holds a read capability covering that claim at the moment of transfer — so a node's replica never contains claims it was not authorized to read.

The invariant governs **acquisition, not retention**, and its enforcement bounds delivery rather than being a behavioural promise from every node:

- **Delivery is capability-filtered at egress.** During reconciliation an honest serving node reveals — fingerprints, offers, sends — only claims the receiving peer can present a read capability for: the read-side counterpart of the ADR-0008 ingest gate. A node can only serve what it holds, and holds only what this rule let it acquire, so no node — honest or not — can deliver claims it never received. An under-authorized node cannot *obtain* the data; a node authorized for a claim can of course still leak that claim.
- **Revocation is not recall.** A revoked capability blocks further delivery, but deletion of already-delivered data cannot be guaranteed — nothing compels a modified node to forget claims it received while authorized. The invariant promises access is gated *before* delivery, not that delivered data can be retracted.

## Invariant 3

A connection metadata store is written only by its issuing identity's devices, read only by those devices and by the connection counterparty's devices — and to every other party it does not observably exist.

The enforcing mechanism is ticket routing, as in Invariant 1: the store's write ticket circulates only through the issuing identity's private-metadata directory, and its read ticket travels only inside the establishment dialogue and, from there, through the two identities' directories. In pdn-store a replica's namespace identifier is itself the read capability, so the store's existence is hidden exactly because that identifier travels nowhere else. Invariants 1 and 2 do not cover this store: Invariant 1's audience is an identity's own devices alone, Invariant 2 governs claims under read capabilities, and the metadata store is deliberately read whole by the counterparty under a ticket. (Today the ticket is a bearer token: whoever holds it has access. Identity-bound, revocable access lands with UWill.)
