---
status: accepted
date: 2026-10-14
---
# Own a variant of iroh-docs whose every session the embedder judges

## Context and Problem Statement

A pod's two stores are iroh-docs replicas shared by the devices of its members, and what a session on them may serve and take depends on who is asking. A current member's device is served the store whole. A former member's device is served its departure's past alone, and takes nothing placed after its departure. A node no statement of a current member lists is sent nothing on the membership store and taken that member's device statements alone. A device whose own identity departed takes its own chain and the events that chain rests on, and nothing else. None of this is a property of the replica: it is read from the membership store's own entries, by the membership view, at the moment the session starts. The question is where that judgement runs, given that iroh-docs, as published, has no place for it.

Facts verified against iroh-docs 0.100, the release the variant starts from:

1. Ingest funnels through one chokepoint: `validate_entry` in `src/sync.rs`, which checks the namespace and author signatures, the namespace id and a timestamp no more than 10 minutes in the future, and nothing else. Beneath it, the set-reconciliation engine's `process_message` in `src/ranger.rs` takes a per-entry callback that runs before the entry is stored, and an entry the callback refuses is never stored. iroh-docs hardwires that callback to `validate_entry` and does not expose it.
2. Reconciliation converges two peers to the union of the whole replica. Every fingerprint covers every entry in its range, so there is no per-entry read control: whatever a replica holds, a peer that reconciles with it learns.
3. A ticket is a bearer token with no expiry and no revocation. Every device of every member holds a write ticket to a pod's stores, and with it the stores' namespace key, so a former member's device keeps both, and the namespace signature on an entry cannot tell a current member's device from a former one's.
4. iroh-docs is small: a multi-writer key-value store over iroh's set reconciliation, with gossip for live notice and iroh-blobs for payloads.

## Decision Drivers

* Refuse before persisting and withhold before revealing: an entry the session must not take is never stored, and an entry it must not serve is never fingerprinted, offered or sent.
* No fork of iroh itself — the endpoint, the transport, the gossip — and no sync protocol of our own: iroh-docs remains the thing that syncs.
* The store stays ignorant of pods: the membership vocabulary and the identity vocabulary live above it, so the store can be rebased onto upstream releases without carrying them.
* A refusal looks the same whatever its reason, so a caller learns nothing from it about what the replica holds.
* One judgement per session, decided once and applied to the whole session, so a membership change during a session cannot widen what it serves.

## Considered Options

* **iroh-docs verbatim, with a gate after the fact**: sync everything into an untrusted copy and promote what passes
* **A replica per audience**: re-create a pod's stores at every membership change, and keep a store of its own for every former member's past
* **Our own variant of iroh-docs whose every session the embedder judges** ← chosen

## Decision Outcome

Chosen option: **our own variant of iroh-docs whose every session the embedder judges**, because it is the only option that both refuses before persisting and withholds before revealing, at a cost of hooks placed where iroh-docs already validates and reconciles.

The variant is the workspace crate `pdn-store`. It carries upstream's version number, is never published, and records every upstream commit since the fork point with a verdict on each. iroh itself is not forked.

**The judgement.** The node is assembled with a session access provider, and the store asks it, for every session and on both roles — the dial and the accept — for one of two answers: a refusal, or an egress predicate together with an ingest verdict. The egress predicate says which entries the session may reveal. The ingest verdict says, for every entry the peer offers, whether to accept it or to drop it in silence. The two are independent, so what ingest drops neither widens nor narrows what egress reveals. The store compares the identities a session names as opaque bytes and applies the predicates it is handed; what they mean is the data layer's.

**Hidden, not merely undelivered.** Every range fingerprint, split boundary, offer and item a session sends is computed over the entries its egress predicate admits, and over nothing else. The transcript a peer observes depends only on those entries, so neither a withheld entry nor the fact that it exists reaches the peer.

**Dropped in silence.** A dropped entry is refused before it persists and is not remembered. The sender keeps its own copy and offers the entry again in its next session, and nothing about the drop is signalled to it.

**Decided once, against a frozen view.** A session's access is decided at setup and holds for the session, and the session serves a snapshot taken at that setup. An accept asks the provider before it opens the snapshot, and the answer names the replicas it read at their write counts; if any of them was written before the snapshot opened, the provider is asked again before the first message is served. A dial asks once its connection stands and its snapshot is open, never when the dial is asked for, since a connect can wait for as long as the peer is down.

**A uniform refusal.** A refused session ends with the same frame a replica the node does not host produces, so a caller cannot tell a refusal from an absence.

**Tickets are transport bootstrap only.** A ticket says that a node may reach and write a store, never that it is authorized: authority is membership, which the provider reads from the store's own entries for every session.

**Example:** Alice's phone a1 serves the membership store of "Family" to Carol's phone c1; Alice removed Carol at Carol's sequence 2, and Dave joined afterwards; `<x>` stands for the 64 hex characters of the identity x.

| key | the egress predicate, on what a1 holds | the ingest verdict, on what c1 offers |
|---|---|---|
| `member/<carol>/1/joined/<bob>/1` | revealed: in Carol's departure's past | accepted: in that past |
| `member/<carol>/2/removed/<alice>/3` | revealed: the departure itself | accepted |
| `member/<dave>/1/joined/<alice>/4` | withheld | dropped |

### Consequences

* Good — prevention, not cleanup: an entry a session must not take never persists, and there is no untrusted copy to collect, no window between "synced" and "trusted", and no second copy of every entry.
* Good — a former member's device, holding a valid write ticket and the namespace key, still cannot place an entry past its departure into a member's replica, because the verdict, not the signature, decides.
* Good — the store knows no pod: the membership view, the device statements and the departure's past are computed in the data layer, so an upstream release touching neither the ranger nor the session setup is taken as it is.
* Bad — we own a variant of iroh-docs and track upstream by hand; an upstream patch to the ranger, the sync session or the live actor's dialing is adapted rather than taken.
* Bad — a dropped entry costs its sender one offer in every later session with that peer, since the sender is told nothing and keeps offering it.
* Neutral — confidentiality is unchanged: an entry is readable by every device a session serves it to, and payload encryption is not built.

## Validation

The store's own tests pin the mechanics: `an_egress_predicate_delivers_only_what_it_admits`, `a_withheld_entry_leaves_the_transcript_of_its_absence` and `an_ingest_drop_leaves_egress_unchanged` in `crates/pdn-store/src/sync.rs`. The data layer's scenario tests pin the judgement on a pod's stores: `a_member_device_is_served_and_a_ticket_holder_is_not` and `every_refusal_is_the_frame_an_unhosted_replica_produces` in `crates/data-layer/tests/pod_sessions.rs`, and `a_dial_decided_before_a_removal_takes_nothing_placed_after_it` and `an_accept_decided_before_a_removal_takes_nothing_placed_after_it` in `crates/data-layer/tests/pod_tombstone.rs`. The compliance criterion is that no entry the verdict drops is stored, and no entry the predicate withholds is observable in the peer's transcript.

## Pros and Cons of the Options

### iroh-docs verbatim, with a gate after the fact

* Good — no modification of iroh-docs.
* Bad — no prevention: the untrusted copy can be filled by any ticket holder, and needs quotas and collection.
* Bad — no read control at all: reconciliation reveals the whole replica, so a former member's device learns every event after its departure.

### A replica per audience

* Good — iroh-docs unmodified, and every store served whole.
* Bad — every removal re-creates both stores and copies their content to every remaining member's devices.
* Bad — a former member's past needs a store of its own, written by the members, for every departure.
* Bad — a device offline during the change holds a store nobody serves any more, and has to be told where the new one is.

### Our own variant whose every session the embedder judges (chosen)

* Good — refusal before persisting and withholding before revealing, at the places iroh-docs already validates and reconciles.
* Good — the store stays ignorant of pods.
* Bad — a variant to maintain and to rebase.

## More Information

Beyond the judgement, the variant carries the dial controls a pod's pass uses — dialing a store with chosen peers alone, ordering a record store's dial after its membership store's, stating whom each peer of a store is dialed as, naming the identity on the other side of a finished session — and the rule that an entry affects only its own key. Each divergence is listed with its reason beside the crate, in `crates/pdn-store/CLAUDE.md`, and its behaviour is specified where it is consumed: what a session serves and admits in [reconciliation sessions](../../components/mee-pdn/data-layer/reconciliation-sessions/spec.md), which caller a pod's store serves and how its pass dials in [pod stores](../../components/mee-pdn/data-layer/pod-store/spec.md).

Related: [ADR-0013](0013-identity-isolation-on-one-node.md) (the identity a session names, which the provider judges by); Invariant 2 (`../../components/mee-pdn/invariants.md`).

External references: iroh-docs 0.100 — the ingest chokepoint `validate_entry` in `src/sync.rs`, the per-entry pre-persist callback of `process_message` in `src/ranger.rs`, not exposed publicly; share tickets are non-expiring bearer tokens.
