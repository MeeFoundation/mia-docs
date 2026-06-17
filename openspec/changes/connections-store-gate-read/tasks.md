# Tasks: connections-store-gate-read

Scope: the connections store and its replication between two devices of one
identity. No fork change; no gate-reads-the-store (deferred). The existing
`sync_two_nodes` test and in-memory Tier-1 policy stay intact.

## 1. Registry: typed bindings (crates/data-layer)

- [x] 1.1 Introduce `Binding { Data(NamespaceId), Connections { owner: PdnId } }`; registry resolves iroh ns → `Binding`; `SyncNode::create_namespace`/`import_namespace` bind `Data`
- [x] 1.2 Carry the resolved binding in `IngestCtx { binding: Option<Binding> }`; bridge resolves it from `entry.namespace()` (no fork change, no store read)

## 2. Policies: device axiom

- [x] 2.1 `SelfOwned { me }` policy — admits `Connections { owner == me }` and `Data(ns)` with `ns.issued_by == me`, reading no store; rejects everything else
- [x] 2.2 `AnyOf([..])` first-accept combinator (composition seam for when data gating is added later)
- [x] 2.3 Doc comments: `SelfOwned` is an axiom (own-identity state is self-trusted), runs within the existing seam, reads nothing

## 3. ConnectionsStore module (crates/data-layer)

- [x] 3.1 `ConnectionsStore::create(node)` / `import(node, ticket)` / `share_ticket()` — bind the replica as `Connections { owner }`
- [x] 3.2 `connect(peer)` (marker entry at `connections/<pdnid-hex>`), `disconnect(peer)` (tombstone via `del`)
- [x] 3.3 Async reads for UI/tests: `is_connected(peer)`, `list()` via normal doc queries

## 4. Test: two devices of Alice (crates/data-layer)

- [x] 4.1 `connections_two_devices`: phone + laptop, same PdnId, each running `SelfOwned { me: alice }`; phone creates the store, laptop imports via ticket
- [x] 4.2 Assertions: `connect(P)` on phone → laptop's store eventually shows `P` live; `disconnect(P)` on phone → laptop eventually shows `P` not live. Wait on connection visibility explicitly (no fixed sleep)
- [x] 4.3 Leave `sync_two_nodes` (in-memory Tier-1 data gating) untouched
- [x] 4.4 Lints + full suite: `just precommit-check`
- [x] 4.5 Flake check: run the new test in a loop (single invocations, ≥8); if flaky and reruns pass, diagnose and fix the timing source

## 5. Documentation

- [x] 5.1 Update workspace CLAUDE.md crate table: `data-layer` now hosts the connections store + device axiom
- [ ] 5.2 On archive: place the two capability specs into `components/data-layer/` per the proposal's mapping table, following the flat `components/pdn-node/uwill.md` convention
