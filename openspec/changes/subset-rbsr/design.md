# Design: subset-rbsr

## Context

Invariant 2 says a node receives a record only if it holds a read capability for it. Today reconciliation delivers every record to any peer that syncs — no per-record read control: the old ingest gate was removed by multi-identity-node, nodes host several identities, and access is bounded by ticket possession alone. This change enforces Invariant 2 by filtering what a serving node reveals during reconciliation, driven by the receiving peer's read capabilities — the read-side counterpart of the ADR-0008 ingest hook (the fork's `validate_entry`, available and uninstalled), and the first enforcement to land on that ungated baseline.

## Goals / Non-Goals

**Goals:**

- A serving node reveals only records the peer is read-authorized for; unauthorized records' content and existence stay hidden.
- A minimal, testable read-capability mechanism driving the filter.

**Non-Goals:**

- Full UWill (chains, revocation, token encoding) — ADR-0007.
- Efficiency — a filtered session may scan every record in the replica; accepted.

## Decisions

### D1. Filter at reconciliation time, applied consistently

The filter lives in `pdn-store` at reconciliation time (the `ranger` path), as a per-peer predicate over which records participate. It is new — the existing `validate_entry` hook is ingest-only. It MUST be applied uniformly: range fingerprints, split boundaries, offers, and item transmissions all computed over the filtered view. Partial application leaks — a fingerprint computed over the full set in a shared range would betray unauthorized neighbours.

### D2. Confidentiality = consistent filtering

Because every value the serving node sends is computed over the peer's authorized subset, the peer's transcript depends only on that subset. The peer's session is indistinguishable from reconciling with a node holding exactly that subset — so it learns neither content nor existence of the withheld records. No PIO/ZK needed; this is "don't send it," enforced at the serving node.

### D3. Minimal read capability — the single-link precursor to UWill

The capability the filter consumes is a single grant `{ issuer, audience, records }`, presented by the peer, evaluated per record. No delegation chain, no revocation crypto, no token encoding — the degenerate single-link form that UWill's chain validation later supersedes (ADR-0007). Placement: the minimal type lives in `data-layer` for now; the domain issuance surface (`pdn-layer` `Capability`, then UWill) supersedes it later.

### D4. The replica's own devices are fully authorized

A device of the identity a replica belongs to is read-authorized for all of that replica's records (composes with Invariant 1), so the filter admits everything for such a peer with no capability presented, and reconciliation between an identity's devices (connections store, private metadata store, data store) stays full. On a multi-identity node this is judged per replica, not per node: a node hosting several identities is a fully authorized peer only for the replicas of the identities it is linked into, and a capability-scoped peer for anything else it holds. How a peer proves being a device of the identity — today by holding the replica's ticket (bearer), identity-bound proof with UWill — is the same authentication question as for presented capabilities (see Open Questions).

### D5. Scoped peers are outside the swarm

The reconciliation filter alone does not enforce Invariant 2: live sync broadcasts full records (`Op::Put(SignedEntry)`) and author-heads digests (`SyncReport`) to every swarm member. A broadcast cannot be filtered per recipient. The sender controls only its few active gossip neighbors (HyParView partial view — five by default); every further delivery is a relay performed by a swarm member outside the sender's control. A relaying member must hold what it forwards — Plumtree pushes full messages to eager peers and answers `Graft` requests with full content, and even the lazy path's `IHave` digests leak record existence — so a capability-scoped relay would either obtain records it is not authorized for (the exact transfer Invariant 2 forbids) or refuse to relay and tear the delivery tree, breaking delivery for fully authorized peers behind it. Filtering at every hop instead would require every member to know every neighbor's rights for every record — distributing the access matrix, itself sensitive metadata, to the whole swarm. In short: a broadcast presumes members are interchangeable with respect to the topic's content, per-record authorization breaks that premise, and membership is the only level at which gossip can be "filtered" without breaking the protocol.

Therefore the swarm consists of fully authorized members only — today an identity's own devices (D4), whose full-record gossip is unchanged — and capability-scoped peers never join it. Their only data path is the filtered reconciliation, which they initiate, and which remains the single enforcement point and the sole carrier of correctness. A scoped peer that never reconciles simply never sees updates; reconciliation-on-contact is the baseline. Making that path prompt — a directed, content-free trigger to exactly the peers a written record covers, coalesced per peer — is the separate `reconcile-trigger` change, a latency optimization on which correctness does not depend. D2's transcript property extends to that liveness path: a scoped peer is prompted only about records it can read, so no side channel opens (the load profiles make the cost and the side channel concrete).

### D6. The filter is a session-scoped filtered store: snapshots for stability, views for speed

Three independent layers.

**Form.** A filtering adapter implementing `ranger::Store<SignedEntry>`, constructed at session setup from a record source and the peer's rights, frozen for the session (rights changing mid-session would make the filtered view drift between rounds). The reconciliation engine is not modified and cannot read past the adapter — the trait is its only door to records. Range fingerprints are filtered by construction: pdn-store computes them by iterating `get_range` (no cached aggregates — the fs store carries the upstream's own "TODO: optimize"), so filtering the iterators filters the fingerprints. This is the structural alternative to sprinkling a predicate through the reconciliation logic, where one missed call site would leak record existence through a fingerprint.

**Source.** On the fs backend the record source is a redb read transaction (`snapshot_owned` — already in the store's API, currently unused by reconciliation, which reads the current transaction): every session sees the data as of its start, fingerprints stay consistent across rounds, and MVCC makes this free of copying. The memory backend has no snapshot primitive and keeps the live store, with the same tolerance to mid-session drift the unfiltered engine has today (reconciliation is anti-entropy; drift heals next session). A snapshot buys consistency, not speed — iterating a snapshot costs the same as iterating the live store.

**Views, optional.** Where a profile makes per-fingerprint rescans expensive, a pre-filtered view is materialized and keyed by **audience** — the set of rights, not the peer: the SMB example's sessions fall into two audiences regardless of member count, and the sparse example's audiences are single-record. The audience-resolution a covered write performs — the same index the reconcile trigger reuses (`reconcile-trigger` change) — doubles as the view's incremental invalidation. If implementation uncovers a reconciliation read path that bypasses `ranger::Store`, scoped sessions fall back to materialized views wholesale.

Two redb properties are verification items for implementation, not settled facts: long-lived read transactions pin old pages (so sessions must hold snapshots strictly within session bounds), and the store's `snapshot()` commits any open write transaction (its interaction with write batching needs checking).

### D7. When scoped peers reconcile — before access and on an interval

Since scoped peers pull, something has to trigger the pull. The baseline trigger — and, until `reconcile-trigger` lands, the only one — is self-initiated: a scoped peer reconciles a replica **before it reads from it**, and **on an interval** (hourly to start). That is what reconciliation-on-contact means concretely, and it suffices for correctness — a peer sees an update at the latest on its next read or interval tick. The cross-node push that prompts an out-of-schedule reconcile the moment a covered write lands is the deferred `reconcile-trigger` change; it lowers latency, never changes what a reconcile delivers. (The timer and the before-read hook live in the node runtime that drives reconciliation; subset-rbsr fixes the policy, not the scheduler.)

## Risks / Trade-offs

- **[Consistency discipline]** The filter must touch fingerprints + boundaries + offers + sends uniformly; any path over the unfiltered set leaks. Test the existence-hiding property explicitly.
- **[Side channels]** Timing and message sizes can leak the replica's total record count (the server scans every record to filter). Minor; note, don't block.
- **[Efficiency]** A filtered session may cost time linear in the number of records rather than logarithmic — accepted; performance is not a goal here.
