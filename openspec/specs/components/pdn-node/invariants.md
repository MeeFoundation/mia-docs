# Invariants

Cross-cutting rules the system upholds. **Referenced by number only** — write "Invariant 1" in code, specs, and discussion, never a name. The list is **append-only**: numbers are never reused or renumbered, and an invariant that stops holding is marked withdrawn in place rather than deleted.

## Invariant 1

A PDN identity's connections store and private metadata store are reachable only by that identity's own devices, and a device's copies of them hold that identity's data only.

Two mechanisms enforce this — it is not a behavioural agreement between nodes:

- **The store ticket gates access.** Syncing or writing either replica requires its ticket, and an identity hands that ticket only to its own devices — at linking, over the private-metadata directory. (Today the ticket is a bearer token: whoever holds it has access. Identity-bound, revocable access lands with UWill.)
- **The `SelfOwned` ingest policy keeps them single-identity.** On every incoming entry, a node admits it into a connections or private-metadata replica only if that replica is its own identity's — decided from the binding's identity alone, reading no stored state. Another identity's private store is never ingested. This runs in code on the ingest path, per entry.
