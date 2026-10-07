# Invariants

Cross-cutting rules the system upholds. **Referenced by number only** — write "Invariant 1" in code, specs, and discussion, never a name. The list is **append-only**: numbers are never reused or renumbered, and an invariant that stops holding is marked withdrawn in place rather than deleted.

## Invariant 1

A Mee Identity's private metadata store — the one device-internal directory, carrying its device set, its tickets, and its connections records — is reachable only by that identity's own devices, and a device's copy of it holds that identity's data only.

The enforcing mechanism is the store ticket, not a behavioural agreement between nodes: syncing or writing the replica requires its ticket, and an identity hands that ticket only to its own devices — over the device-linking dialogue's encrypted channel, after the one-time linking secret is verified and burned; it is never carried in a QR. (Today the ticket is a bearer token: whoever holds it has access. Identity-bound, revocable access lands with UWill.)

## Invariant 2

A node obtains a claim only if it holds a read capability covering that claim at the moment of transfer — so a node's replica never contains claims it was not authorized to read.

The invariant governs **acquisition, not retention**, and its enforcement bounds delivery rather than being a behavioural promise from every node:

- **Delivery is capability-filtered at egress.** During reconciliation an honest serving node reveals — fingerprints, offers, sends — only claims the receiving peer can present a read capability for: the read-side counterpart of the ADR-0008 ingest gate. A node can only serve what it holds, and holds only what this rule let it acquire, so no node — honest or not — can deliver claims it never received. An under-authorized node cannot *obtain* the data; a node authorized for a claim can of course still leak that claim.
- **Revocation is not recall.** A revoked capability blocks further delivery, but deletion of already-delivered data cannot be guaranteed — nothing compels a modified node to forget claims it received while authorized. The invariant promises access is gated *before* delivery, not that delivered data can be retracted.
- **Inside a [pod](../../architecture/language/pod.md), membership is the read authorization.** A pod has no audience narrower than its members, so a member's devices are served both of its stores whole and no filter runs within them. Acquisition is gated by membership instead: once a member's departure reaches a serving device, that device refuses the departed member's devices the record store from the next session ([pod stores](data-layer/pod-store/spec.md)), and what they obtained while a member stays with them.
- **Payload bytes are held back only as far as their hash is.** Every gate above judges entries. A claim's payload bytes travel by hash over blob transfer, which serves any caller naming a hash the node's one blob store holds (ADR-0013), and a device that has fetched a payload announces its hash to its neighbors in the store's topic — a kicked member's device that stays in the swarm of a pod's record store among them. The [threat model](threat-model.md#payload-bytes-by-hash) records this under "Payload bytes by hash".

## Invariant 3

A connection metadata store is written only by its issuing identity's devices, read only by those devices and by the connection counterparty's devices — and to every other party it does not observably exist.

The enforcing mechanism is ticket routing, as in Invariant 1: the store's write ticket circulates only through the issuing identity's private-metadata directory, and its read ticket travels only inside the establishment dialogue and, from there, through the two identities' directories. In pdn-store a replica's namespace identifier is itself the read capability, so the store's existence is hidden exactly because that identifier travels nowhere else. Invariants 1 and 2 do not cover this store: Invariant 1's audience is an identity's own devices alone, Invariant 2 governs claims under read capabilities, and the metadata store is deliberately read whole by the counterparty under a ticket. (Today the ticket is a bearer token: whoever holds it has access. Identity-bound, revocable access lands with UWill.)
