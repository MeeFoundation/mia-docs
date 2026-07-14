# Design: pdn-node-runtime

## Context

`data-layer` provides working primitives — `SyncNode` (endpoint + gossip + blobs + docs), `ConnectionsStore`, `PrivateMetadataStore`, `provision_identity` / `link_device` — but their only consumer is the crate's own test suite; the multi-identity change even records that store handles are meant to stay "with the caller (today the tests, later the pdn-node runtime)". This change creates that runtime. An earlier prototype (v3-single-device: a `Node` trait with associated service types, a demo impl, and an axum HTTP binary with `/live` plus flag-gated debug endpoints) is the studied form; its sync stack and identity placeholders predate the current architecture, so the form is reused where it fits and nothing is carried over for recognizability's sake. The runtime will eventually glue `pdn-layer` too (the domain model and `PdnOp`); this slice glues only `data-layer`. Pairing over a dedicated ALPN (ADR-0011) is designed but not built; its handler will have to join the same endpoint the runtime assembles.

## Goals / Non-Goals

**Goals:**

- An embeddable `pdn-node` core: identity / connections / data / sync services as thin glue over `data-layer`, hosting any number of identities in one runtime.
- A `pdn-node-http` host for the demo stand: `/live` health, debug scaffolding off by default.
- A runtime assembly shape that will admit the pairing protocol handler (ADR-0011) without re-architecture.
- Scenario coverage driving the services end to end in-process, with the paired deny cases the access-control-tests practice requires.

**Non-Goals:**

- Connection establishment (ADR-0011), `ConnectionMetadataStore`, and capability grants — the connections service only records and lists.
- On-disk persistence; the runtime rides the in-memory `SyncNode`.
- Implementing the `DataLayer` trait or typed runtime errors — the runtime drives `SyncNode`'s `anyhow` surface (extended with `list` by this change); the trait switch is its own change.
- Mobile/wasm facades (uniffi / jni / wasm) — kept possible by the library-first form, not built.
- `pdn-layer` integration (`PdnOp`, claims, capability semantics) — a later change.

## Decisions

### D1. Two crates, hosts depend on the core directly

`pdn-node` is the embeddable core library; `pdn-node-http` is one host over it. The v3-single-device split into an api-trait crate plus impl crate plus demo binary collapses to two: a separate api crate would let alternative cores implement the same traits, but there is no second core in sight, and hosts binding to `pdn-node` directly is one less indirection. Alternative — a single crate with a feature-gated HTTP host — rejected: host dependencies (axum, tokio server machinery) would sit in every embedder's dependency tree behind a feature flag, and the "core stays host-free" property becomes a discipline instead of a structure.

### D2. Services are traits with one production implementation

The rule: a trait where a second non-degenerate implementation is plausible, concrete otherwise; borderline leans to the trait. Identity is a trait — the current implementation mints placeholder identifiers, and a KERI-backed service is a live future second implementation. Data and sync are traits — a test mock standing in for the network is the second implementation, and it keeps host tests hermetic. Connections follows the same shape for uniformity of the service surface (its future second implementation arrives with pairing, which replaces manual recording as the producer of connections). One production implementation of each backs them all with the same `data-layer` stack.

### D3. The runtime owns the hosted-identity set

`data-layer` deliberately keeps no list of hosted identities — store handles stay with the caller. The runtime is that caller: it holds each hosted identity's `IdentityStores` (private metadata + connections handles) and its data-namespace registration, keyed by `PdnId`, and the sync service reports exactly this set plus the node id. Identity creation mints a fresh placeholder `PdnId` (random identifier, no key material) — honest about KERI not being integrated; the identity service trait is where the real thing lands. Alternative — pushing the hosted-identity set into `SyncNode` — rejected: the multi-identity change already considered and rejected node-side identity state as a resource with no consumer; the consumer now exists and it is the runtime, so the state lives here.

### D4. Data namespace tickets are shared and imported through the data service

The interim access model (ADR-0008) is ticket possession, and the current cross-node data path is exactly "share the namespace ticket, the peer imports and syncs it whole". The data service exposes that as operations: share a hosted namespace as a ticket, import a peer's namespace from a ticket, write, read, and list entries by issuer and path. This is not freezing a test workaround into a contract — it is the current access model made operable, and it is explicitly interim: capability-scoped sharing (subset-rbsr egress, grants carried in the connection metadata store) replaces whole-store tickets in later changes, at which point the spec requirement changes with the mechanism. One guard-rail holds regardless of that evolution: `import` registers the replica and persists the foreign ticket nowhere else — in particular never into the identity's own device-replicated stores (private metadata store included), where a copy would outlive revocation: the issuing peer cannot reach it, device sync spreads it to every device, and a restart or a freshly linked device would re-import from it after the grant is gone. The durable home for foreign-store tickets is the counterpart's connection metadata store once it lands (the identity's own data-store ticket in the private metadata store is the legitimate bootstrap exception); local runtime state — the registry, later any on-disk manifest of it — is a cache the bootstrap orchestration cleans. Alternative — keeping ticket handover out of the runtime and leaving it to test code — rejected: the demo stand needs two runtimes exchanging data without reaching into `data-layer` internals.

### D5. No protocol-handler registration point yet, but nothing that precludes it

`SyncNode::spawn` builds its protocol router internally (blobs, gossip, docs), and ADR-0011 records that it must eventually accept an externally supplied handler for the pairing ALPN. That registration point belongs to the pairing change together with its `data-layer` API; this change adds nothing to `SyncNode`. What it does guarantee is the runtime side: the runtime owns node assembly in one place (spawn-time construction, single owner of the `SyncNode`), so threading a handler through at spawn will be a parameter addition, not a restructuring. Alternative — adding the registration hook now, unused — rejected: speculative surface, and ADR-0011's open questions (where the handler lives, the API shape) are explicitly unresolved.

### D6. Debug surface off by default, `/live` always on

The HTTP host serves `/live` unconditionally — the container harness and the demo stand probe it. Debug endpoints are demo scaffolding: gated behind `PDN_DEBUG=1`, absent by default, and their shape is deliberately unspecified so demo scripts can evolve them without spec churn. The spec pins only the gate: off means absent.

### D7. Entry listing is an additive `SyncNode` method shaped after the trait

The data service includes listing — without enumeration a service cannot show what a namespace holds, and scenario tests need to assert exact contents, not just probe paths they already know. `SyncNode` has no enumeration and its doc handles are crate-private, so the runtime cannot build listing above the existing surface; instead `SyncNode` gains a `list` returning entry metadata (`EntryInfo`: issuer, path, payload length) for a hosted issuer, optionally filtered by a path prefix matching whole components — the same shape as `DataLayer::list_entries`, so switching the runtime onto the trait later stays mechanical. Listing is record-level, consistent with record-first reads: an entry appears once its record is stored, payload fetched or not. Alternative — exposing doc handles and querying from the runtime — rejected: it leaks pdn-store types through the runtime and bypasses the registry's issuer addressing. Alternative — deferring listing to the `DataLayer`-trait change — rejected: the service surface needs it now, and the addition is small and purely additive.

## Risks / Trade-offs

- **[Whole-store ticket sharing in the service surface]** Exposing share/import invites treating it as the sharing model. → It is the documented interim model (ADR-0008 posture); the spec requirement names it interim, and the subset-rbsr / connection-metadata changes replace the mechanism and the requirement together.
- **[Runtime spec shadows data-layer specs]** Service-level scenarios re-tread store behavior. → The runtime spec pins delegation and isolation contracts (what the glue must preserve), not store semantics; store behavior stays specified in `components/data-layer/`.
- **[Traits with a single implementation]** Dead seams if the second implementation never comes. → The rule is applied per service with a named second implementation (KERI, test mock); hosts test against mocks immediately, so the seam is exercised from day one.
- **[Placeholder identity minting leaks into products]** A random `PdnId` with no key material behind it. → Confined to the identity service implementation; the trait is the replacement seam, and proof-of-control is already marked deferred in ADR-0011's dialogue.

## Migration Plan

New crates plus one additive `data-layer` method: add `crates/pdn-node` and `crates/pdn-node-http` to the workspace, give `SyncNode` its `list` (additive — nothing existing changes shape), implement services over `data-layer` otherwise as-is, land the in-process scenario test and the `/live` smoke test. Rollback is removing the crates and the unused `list`.
