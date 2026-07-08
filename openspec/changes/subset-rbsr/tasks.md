# Tasks: subset-rbsr

Scope: capability-filtered reconciliation enforcing Invariant 2 — a serving node reveals only records the peer is read-authorized for. Includes a minimal single-link read capability (precursor to UWill) and the directed-notification live path (D5). Modifies pdn-store.

## 1. Read capability (data-layer)

- [ ] 1.1 Minimal read-capability type: `{ issuer, audience, record set }`, single grant (no chain)
- [ ] 1.2 Issuance: an issuer grants an audience read on a set of records
- [ ] 1.3 Per-record evaluation from presented capabilities; own-identity → authorized without a capability

## 2. Egress filter (pdn-store)

- [ ] 2.1 Add a reconciliation-time, per-peer filter (distinct from the ingest `validate_entry` hook) in the `ranger` / reconciliation path
- [ ] 2.2 Apply the filter uniformly to fingerprints, split boundaries, offers, and item transmissions (consistency — partial application leaks)
- [ ] 2.3 Records not covered by the peer's presented capabilities never enter any message

## 3. Wiring (data-layer)

- [ ] 3.1 Peer presents read capabilities at session setup; serving node builds the per-peer filter from them
- [ ] 3.2 `SyncNode` reconciliation uses the filter; same-identity peers get the unfiltered (full) view

## 4. Live path (D5: directed notifications)

- [ ] 4.1 Scoped access does not join the replica's gossip swarm: the scoped import/session path skips gossip subscription, while same-identity devices keep full-record gossip
- [ ] 4.2 Directed notifications: on a write, resolve the scoped peers whose capabilities cover the written record (reusing the capability index) and send each a content-free notification over its direct connection
- [ ] 4.3 Coalescing: consecutive covered writes collapse into one pending notification per peer until that peer reconciles; a missed notification is left to reconciliation-on-contact
- [ ] 4.4 A notified peer triggers a capability-filtered reconciliation and receives exactly the covered records

## 5. Tests

- [ ] 5.1 New read-restriction scenario (the old `sync_two_nodes` was removed by multi-identity-node): issuer grants a peer read on a subset; assert the subset arrives and a withheld record never does (existence hidden). Use real read capabilities, not the naive `Connections` set
- [ ] 5.2 Same-identity suites (`sync_two_devices`, `device_linking`, `multi_identity`, `three_devices`) still replicate in full under the filter
- [ ] 5.3 Worked-example scenario (one issuer, many records, scoped peers): an unshared write notifies no scoped peer; a covered write notifies exactly the covering peer, which fetches it through filtered reconciliation; nothing reaches scoped peers over gossip
- [ ] 5.4 Flake check on the new/changed scenarios; lints + full suite (`just precommit-check`)

## 6. Docs & archive

- [ ] 6.1 On archive: place `data-layer-read-capabilities` and `data-layer-subset-reconciliation` into `components/data-layer/`; reread the swarm glossary entry (`architecture/language/swarm.md`) — after D5 its "fresh writes are broadcast to swarm neighbors" phrasing describes fully-authorized swarms only
