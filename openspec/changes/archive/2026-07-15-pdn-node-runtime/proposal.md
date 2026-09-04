# Proposal: pdn-node-runtime

## Why

The layers exist but nothing glues them: `data-layer` provides the store set, linking, and the assembled `SyncNode`, yet only tests drive them — there is no runtime a host (the demo stand today, desktop and mobile apps later) can embed. This change creates the smallest real `pdn-node`: a gluing core library plus a thin HTTP host, deliberately narrow so that pairing (ADR-0011), persistence, and richer introspection each arrive as their own follow-up change.

## What Changes

- **New crate `pdn-node` — the embeddable runtime core.** A library gluing the existing `data-layer` primitives into a service surface; each embedded runtime is one running node (a host embeds one, in-process tests embed several to stand up several nodes): **identity** (create an identity on its first device via `provision_identity`; add a device via `link_device` with the identity's seed), **connections** (record and list an identity's connections over `ConnectionsStore`), **data** (write, read, and list entries in an identity's data namespace over `SyncNode`), **sync** (report the node id and which identities the runtime hosts). One runtime hosts any number of identities (per `data-layer` multi-identity), each added by an explicit act.
- **No new sync or authorization mechanics.** The core is glue: every operation delegates to a `data-layer` primitive, and access to a replica remains bounded by possession of its ticket — the interim posture of ADR-0008, unchanged by this change.
- **New crate `pdn-node-http` — a thin HTTP host for the demo stand.** It embeds the core and exposes `/live` (health, always on). Debug endpoints are demo scaffolding behind an environment flag: not part of the spec, free to change or disappear without a spec change.
- **Library-first form ("not always a server").** The core has no host or HTTP dependencies; hosts depend on `pdn-node` directly (no separate api-trait crate). Service interfaces are traits where a second implementation is plausible (a future KERI-backed identity service; test mocks for sync/data) — see design.md.
- **The node assembly must not preclude an additional protocol handler.** Pairing (ADR-0011) will need to register its own ALPN handler on the same endpoint; this change keeps the runtime's assembly shape compatible with that, while the registration point itself lands with the pairing change.

## Out of Scope (deferred)

- **Connection establishment** — the pairing dialogue over its own ALPN, `ConnectionMetadataStore`, ticket exchange, invite/connect flows (ADR-0011). The connections service here only records and lists what the establishment procedure will later produce.
- **On-disk persistence** — the current `SyncNode` is in-memory; the redb + fs-blob variant and the "where does data live" config are a separate change.
- **The `DataLayer` trait contract** — the runtime drives `SyncNode` directly; implementing the entries-only `DataLayer` trait (typed errors) and switching the runtime onto it is its own change. Entry listing is not deferred with it: `SyncNode` gains a `list` in this change, shaped after the trait's `list_entries` so the later switch stays mechanical.
- **Mobile / wasm hosts** — no uniffi/jni/wasm now; the embeddable core form is what keeps them possible.
- **Sync introspection beyond node id + hosted identities** — transfer progress, per-replica status, and live events come later (with reconcile triggering and subset-rbsr work).

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree, following the `components/mee-pdn/pdn-layer/uwill.md` convention.

| Capability (delta)   | Archive destination                          |
| -------------------- | -------------------------------------------- |
| `pdn-node-core`      | `openspec/specs/components/mee-pdn/pdn-node/core.md` |
| `pdn-node-http-host` | `openspec/specs/components/mee-pdn/pdn-node-http/host.md` |
| `data-layer-data-store` | `openspec/specs/components/mee-pdn/data-layer/data-store.md` |

### New Capabilities

- `pdn-node-core`: the embeddable runtime core — service surface (identity / connections / data / sync) as glue over `data-layer`, multi-identity hosting, library-first form with no host dependencies.
- `pdn-node-http-host`: the HTTP host — embeds the core, `/live` health; debug surface explicitly out of spec.

### Modified Capabilities

- `data-layer-data-store`: the data store gains entry listing — an issuer-addressed enumeration returning entry metadata (`EntryInfo`), optionally filtered by path prefix. The one `data-layer` surface addition of this change; existing `components/mee-pdn/pdn-node/` specs (invariants, namespace-addressing, uwill) and the remaining `components/mee-pdn/data-layer/` specs are untouched — the runtime adds no store, no addressing, and no capability semantics.

## Impact

- **New crates** `crates/pdn-node` (depends on `data-layer`, `pdn-types`) and `crates/pdn-node-http` (depends on `pdn-node`; axum) join the workspace. Dependency direction is one-way: core knows nothing of hosts.
- **`crates/data-layer`**: one additive method — `SyncNode` gains `list` (entry metadata by issuer, optional path-prefix filter; shaped after `DataLayer::list_entries`) with its own paired-deny test; the runtime consumes `SyncNode`, `ConnectionsStore`, `PrivateMetadataStore`, `provision_identity` / `link_device` otherwise as they are.
- **`crates/pdn-layer`**: unaffected — the domain model and `PdnOp` join the runtime in a later change.
- **pdn-store fork**: untouched.
- **Tests**: an in-process scenario test drives the runtime services end to end (create identity, link a second device, record a connection, write and list data, observe both on the linked device); an HTTP smoke test covers `/live`.
- **justfile / CI**: the new crates ride the existing workspace recipes (`just build` / `test` / `check`); a Dockerfile and container recipes arrive with the container test-harness change, not here.
