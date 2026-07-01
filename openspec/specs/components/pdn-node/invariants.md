# Invariants

Cross-cutting rules the system upholds. **Referenced by number only** — write "Invariant 1" in code, specs, and discussion, never a name. The list is **append-only**: numbers are never reused or renumbered, and an invariant that stops holding is marked withdrawn in place rather than deleted.

## Invariant 1

A Mee Identity's connections store and private metadata store are reachable only by that identity's own devices, and a device's copies of them hold that identity's data only.

Two mechanisms enforce this — it is not a behavioural agreement between nodes:

- **The store ticket gates access.** Syncing or writing either replica requires its ticket, and an identity hands that ticket only to its own devices — at linking, over the private-metadata directory. (Today the ticket is a bearer token: whoever holds it has access. Identity-bound, revocable access lands with UWill.)
- **The `SelfOwned` ingest policy keeps them single-identity.** On every incoming entry, a node admits it into a connections or private-metadata replica only if that replica is its own identity's — decided from the binding's identity alone, reading no stored state. Another identity's private store is never ingested. This runs in code on the ingest path, per entry.

## Invariant 2

A node obtains a data record only if it holds a read capability covering that record at the moment of transfer — so a node's replica never contains records it was not authorized to read.

The invariant governs **acquisition, not retention**, and its enforcement bounds delivery rather than being a behavioural promise from every node:

- **Delivery is capability-filtered at egress.** During reconciliation an honest serving node reveals — fingerprints, offers, sends — only records the receiving peer can present a read capability for: the read-side counterpart of the ADR-0008 ingest gate. A node can only serve what it holds, and holds only what this rule let it acquire, so no node — honest or not — can deliver records it never received. An under-authorized node cannot *obtain* the data; a node authorized for a record can of course still leak that record.
- **Revocation is not recall.** A revoked capability blocks further delivery, but deletion of already-delivered data cannot be guaranteed — nothing compels a modified node to forget records it received while authorized. The invariant promises access is gated *before* delivery, not that delivered data can be retracted.
