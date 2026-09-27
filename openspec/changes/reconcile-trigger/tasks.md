# Tasks: reconcile-trigger

Scope: the live path for capability-scoped peers — a directed, content-free trigger on a covered write, coalesced per peer, best-effort, prompting a filtered reconciliation. Depends on subset-rbsr (filter, read capability, scoped-peers-outside-swarm). Correctness and confidentiality are subset-rbsr's.

## 1. Trigger

- [ ] 1.1 On a write, resolve the scoped peers whose grants cover the written claim from the grant records in the issuer's connection metadata stores and the device sets their counterparties publish — the records `AccessBook::classify_issued` builds each session's egress filter from; nothing indexes them by claim — and send each a content-free trigger over a connection dialed for it, addressed to the node and the identity holding the replica there: a node holding one namespace for two identities receives one trigger per covering identity
- [ ] 1.2 Coalescing: consecutive covered writes collapse into one pending trigger per peer until that peer reconciles; a missed trigger is left to reconciliation-on-contact
- [ ] 1.3 A triggered peer runs a capability-filtered reconciliation and receives exactly the covered claims
- [ ] 1.4 The co-located trigger is the existing write announcement (`CoLocatedRequest::Announce`, `reconcile_with_co_located` in `crates/data-layer/src/node.rs`): on a data namespace narrow its targets to the issuer and the identities whose grant covers the written claim, keeping every holder for a directory and a connection metadata store; no co-located trigger leaves the node
- [ ] 1.5 Keep a co-located announcement pending across its pair's session: replace the drop in `announcements_in_flight` with a pending mark per pair, and make the replay of an announced session that found its pair running (`resync_requested`) reach that pair — `sync_with_peer` resolves the node's own id to the replica's default identity when no contact or running session names another, which on the issuer's own namespace is the writer

## 2. Transport & policy

- [ ] 2.1 Choose the transport (docs ALPN frame vs dedicated protocol), how it names the addressed identity, and the retry policy (how long before giving up to reconciliation-on-contact) — the design open questions

## 3. Tests

- [ ] 3.1 Worked-example scenario (one issuer, many claims, scoped peers): an unshared write triggers no scoped peer; a covered write triggers exactly the covering peer, which fetches it through filtered reconciliation; nothing reaches scoped peers over gossip
- [ ] 3.2 Coalescing: a burst of covered writes leaves one pending trigger per peer until it reconciles
- [ ] 3.3 Two identities of one node, granted a different claim each of one issuer: a write covered by one triggers that identity's replica and not the other's
- [ ] 3.4 An issuer writes a claim a co-located identity holding its namespace is not granted: no in-process session opens for that pair before the interval elapses (`SyncNode::in_process_sessions`); fails against the announcement to every holder the node makes today
- [ ] 3.5 A write landing while its pair's previous announced session is being set up or running reaches the co-located identity before the next pass; fails with either the `announcements_in_flight` drop or the default-identity replay restored
- [ ] 3.6 Flake check on the new scenarios; lints + full suite (`just precommit-check`)

## 4. Docs & archive

- [ ] 4.1 The comments on `announcements_in_flight` and on `SyncReason::Announced` state the pending mark, not the drop and the replay they describe today
- [ ] 4.2 On archive: the reconcile-trigger delta lands at `components/mee-pdn/data-layer/reconcile-trigger/spec.md`, given a title in the tree's style and a real `## Purpose`; the in-process-sessions delta merges into `components/mee-pdn/data-layer/in-process-sessions/spec.md`
