# Tasks: subset-rbsr

Scope: capability-filtered reconciliation enforcing Invariant 2 — a serving node reveals only records the peer is read-authorized for. Includes a minimal single-link read capability (precursor to UWill). Modifies pdn-store.

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

## 4. Tests

- [ ] 4.1 `sync_two_nodes` → read-restriction: issuer grants a peer read on a subset; assert the subset arrives and a withheld record never does (existence hidden). Use real read capabilities, not the naive `Connections` set
- [ ] 4.2 `connections_two_devices` and `device_linking` (same-identity) still replicate in full under the filter
- [ ] 4.3 Flake check on the new/changed scenario; lints + full suite (`just precommit-check`)

## 5. Docs & archive

- [ ] 5.1 On archive: place `data-layer-read-capabilities` and `data-layer-subset-reconciliation` into `components/data-layer/`
