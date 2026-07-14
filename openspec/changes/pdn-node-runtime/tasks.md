# Tasks: pdn-node-runtime

## 1. Workspace scaffolding

- [ ] 1.1 Add `crates/pdn-node` (library) to the workspace: deps on `data-layer`, `pdn-types`, tokio, anyhow; workspace lints inherited
- [ ] 1.2 Add `crates/pdn-node-http` (binary) to the workspace: deps on `pdn-node`, axum, tokio; no direct `data-layer` dependency
- [ ] 1.3 `just check` passes with the empty skeletons (fmt, clippy strict lints, check)

## 2. Data-layer: entry listing (`SyncNode::list`)

- [ ] 2.1 `SyncNode::list(issuer, path_prefix)` returning entry metadata (`EntryInfo`), shaped after `DataLayer::list_entries`: no payload bytes, optional path-prefix filter matching whole components, record-level (an entry lists once its record is stored); unknown issuer → `UnknownIssuer`
- [ ] 2.2 data-layer tests: listing yields exactly the written paths as metadata; prefix filter matches whole components (`contacts` matches `contacts/a`, not `contactsx/c`); paired deny — listing an issuer with no data store on this node fails with `UnknownIssuer`

## 3. Runtime core (`pdn-node`)

- [ ] 3.1 Runtime type owning the `SyncNode` and the hosted-identity set (`PdnId` → `IdentityStores` + data-namespace registration): spawn and shutdown, single owner of node assembly (D5: one place a future pairing handler threads through)
- [ ] 3.2 Identity service (trait + production impl): create — mint placeholder `PdnId`, `provision_identity`, create the data namespace; link — `link_device` with the identity's seed and a timeout
- [ ] 3.3 Connections service (trait + production impl): record and list, delegating to the hosted identity's `ConnectionsStore`
- [ ] 3.4 Data service (trait + production impl): write/read/list by issuer and path, share a hosted namespace as a ticket, import a namespace from a ticket
- [ ] 3.5 Sync service (trait + production impl): node id + hosted identities

## 4. Core scenario tests (each allowed case paired with its deny, per the access-control-tests practice)

- [ ] 4.1 In-process embedding: one test drives identity, connections, data, and sync services with no host attached
- [ ] 4.2 Create on runtime A, link runtime B by seed: B reports the identity among its hosted identities, connections store converges; paired deny — linking identity X imports nothing of identity Y, operations addressed to an unhosted identity are refused as unknown
- [ ] 4.3 Connections: recorded on device A → listed on linked device B; disjoint lists for two identities hosted on one runtime
- [ ] 4.4 Data: local write/read; listing yields exactly the written paths; whole-store ticket handover A→B syncs entries; paired deny — read/write/list under an issuer neither created nor imported fails with the unknown-issuer error
- [ ] 4.5 Hosted identities: none on a fresh runtime, exactly the created + linked ones afterwards, node id stable throughout

## 5. HTTP host (`pdn-node-http`)

- [ ] 5.1 axum binary embedding one runtime core; `GET /live` served unconditionally
- [ ] 5.2 `PDN_DEBUG=1` gate: without the flag no `/debug/` route exists (404); scaffolding routes live only behind it, shape unpinned
- [ ] 5.3 Host smoke tests: `/live` returns 200 while running; `/debug/` returns 404 without the flag

## 6. Wrap-up

- [ ] 6.1 Crate docs: `lib.rs`/`main.rs` doc-comments state the glue-only role and the interim ticket-possession posture; CLAUDE.md crates table gains `pdn-node` and `pdn-node-http` rows
- [ ] 6.2 `just precommit-check` green across the workspace
- [ ] 6.3 `openspec validate --all --strict` passes for the change
