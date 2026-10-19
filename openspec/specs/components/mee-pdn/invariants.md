# Invariants

Cross-cutting rules the system upholds. **Referenced by number only** — write "Invariant 1" in code, specs, and discussion, never a name. The list is **append-only**: numbers are never reused or renumbered, and an invariant that stops holding is marked withdrawn in place rather than deleted.

## Invariant 1

A Mee Identity's private metadata store — the one device-internal private metadata store (PMS), carrying its device set, its identity key and its tickets — is reachable only by that identity's own devices, and a device's copy of it holds that identity's data only.

The enforcing mechanism is the store ticket, not a behavioural agreement between nodes: syncing or writing the replica requires its ticket, and an identity hands that ticket only to its own devices — over the device-linking dialogue's encrypted channel, after the one-time linking secret is verified and burned; it is never carried in a QR. The ticket is a bearer token: whoever holds it has access.

## Invariant 2

A node obtains an entry of a [pod](../../architecture/language/pod.md)'s store only while it is a device of a current member of that pod, with two exceptions: a former member's device obtains the membership store's entries of its departure's past and nothing else, and a node a store's ticket names is sent the device statements of the identity whose replica lists nobody yet, and nothing else, whichever member that node's identity is by then — so a node's replica holds no other entry it was not authorized to read.

The invariant governs **acquisition, not retention**, and its enforcement bounds delivery rather than being a behavioural promise from every node:

- **Delivery is judged at egress.** During reconciliation an honest serving node reveals — fingerprints, offers, sends — only the entries the session may reveal: both stores whole to a current member's device, the membership store over its departure's past to a former member's device, and nothing to any other node, save that a dial from a replica whose membership view lists nobody yet sends its callee — unchecked, a node the store's ticket names — the device statements of the replica's own identity, so a device whose siblings are gone before any member device took its statement reaches a member device ([reconciliation sessions](data-layer/reconciliation-sessions/spec.md), [pod stores](data-layer/pod-store/spec.md), ADR-0014). As the code stands, the access book sends those statements on any dial whose membership view counts no current member, a view that lists only former members included, and on a dial toward a callee naming a current member whose devices the view lists none of (`Unserved::Unresolved` in the data layer's `access.rs`); the callee is whoever the dial reaches, not only a node a ticket names. A node can only serve what it holds, and holds only what this rule let it acquire, so no node — honest or not — can deliver entries it never received. A node that is no member's device cannot *obtain* a pod's entries; a member can of course still leak what it holds.
- **Removal is not recall.** Once a member's departure reaches a serving device, that device refuses the departed member's devices the record store from the next session, but deletion of what they obtained while a member cannot be guaranteed — nothing compels a modified node to forget entries it received. The invariant promises access is judged *before* delivery, not that delivered data comes back.
- **Payload bytes are held back only as far as their hash is.** Every judgement above is on entries. A record's payload bytes travel by hash over blob transfer, which serves any caller naming a hash the node's one blob store holds (ADR-0013), and a device that has fetched a payload announces its hash to its neighbors in the store's topic — a removed member's device that stays in the swarm of a pod's record store among them. The [threat model](threat-model.md#payload-bytes-by-hash) records this under "Payload bytes by hash".

## Invariant 3

Withdrawn.
