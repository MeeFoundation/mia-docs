# Tasks: subset-rbsr

Scope: capability-filtered reconciliation enforcing Invariant 2 — a serving node reveals only records the peer is read-authorized for. Includes a minimal single-link read capability (precursor to UWill), and keeps capability-scoped peers outside the gossip swarm. Modifies pdn-store. The reconcile-trigger live path is a separate change (`reconcile-trigger`).

## 1. Read capability (data-layer)

- [ ] 1.1 Minimal read-capability type: `{ issuer, audience, record set }`, single grant (no chain)
- [ ] 1.2 Issuance: an issuer grants an audience read on a set of records
- [ ] 1.3 Per-record evaluation from presented capabilities; own-identity → authorized without a capability

## 2. Egress filter (pdn-store)

- [ ] 2.1 Session-scoped filtering adapter implementing `ranger::Store` over a record source plus the peer's rights frozen at session setup; reconciliation reads records only through it (D6 — verify no read path bypasses the trait; if one exists, fall back to materialized views for scoped sessions)
- [ ] 2.2 Filter coverage is uniform by construction — fingerprints, split boundaries, offers, and item transmissions all derive from the adapter's iterators; add the existence-hiding test for the transcript property
- [ ] 2.3 fs sessions read through a redb snapshot (`snapshot_owned`): snapshot opens at session setup and closes at `SyncFinished`; verify the two redb items from D6 (read transactions pin pages — keep lifetimes within session bounds; `snapshot()` commits an open write transaction — check the write-batching interaction)
- [ ] 2.4 Optional, when a profile demands it: materialized per-audience view keyed by the rights set, invalidated incrementally by the audience-resolution index (D6)

## 3. Wiring (data-layer)

- [ ] 3.1 Peer presents read capabilities at session setup; serving node builds the per-peer filter from them
- [ ] 3.2 `SyncNode` reconciliation uses the filter; same-identity peers get the unfiltered (full) view

## 4. Scoped peers outside the swarm (pdn-store)

- [ ] 4.1 Scoped access does not join the replica's gossip swarm: the scoped import/session path skips gossip subscription, while same-identity devices keep full-record gossip

The reconcile-trigger live path (resolve covered peers, send, coalesce, triggered-peer-reconciles) is the `reconcile-trigger` change.

## 5. Tests

- [ ] 5.1 New read-restriction scenario (the old `sync_two_nodes` was removed by multi-identity-node): issuer grants a peer read on a subset; assert the subset arrives and a withheld record never does (existence hidden). Use real read capabilities, not the naive `Connections` set
- [ ] 5.2 Same-identity suites (`sync_two_devices`, `device_linking`, `multi_identity`, `three_devices`) still replicate in full under the filter
- [ ] 5.3 Flake check on the new/changed scenarios; lints + full suite (`just precommit-check`)

## 6. Docs & archive

- [ ] 6.1 On archive: place `data-layer-read-capabilities` and `data-layer-subset-reconciliation` into `components/data-layer/`; reread the swarm glossary entry (`architecture/language/swarm.md`) — after D5 its "fresh writes are broadcast to swarm neighbors" phrasing describes fully-authorized swarms only
