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

The rule: a trait where a second non-degenerate implementation is plausible, concrete otherwise; borderline leans to the trait. Identity is a trait — the current implementation mints placeholder identifiers, and a KERI-backed service is a live future second implementation. Sync is a trait — a test mock standing in for the network is the second implementation, and it keeps host tests hermetic — and the services later changes add follow the same shape. One production implementation of each backs them all with the same `data-layer` stack.

### D3. The runtime owns the hosted-identity set

`data-layer` deliberately keeps no list of hosted identities — store handles stay with the caller. The runtime is that caller: it holds each hosted identity's private metadata store handle and author, keyed by `PdnId`, and the sync service reports exactly this set plus the node id. Identity creation mints the identity key pair and derives the `PdnId` from its public key, a stand-in for the KERI identifier of ADR-0003; the identity service trait is the replacement point for it. Alternative — pushing the hosted-identity set into `SyncNode` — rejected: the multi-identity change already considered and rejected node-side identity state as a resource with no consumer; the consumer now exists and it is the runtime, so the state lives here.

### D5. No protocol-handler registration point yet, but nothing that precludes it

`SyncNode::spawn` builds its protocol router internally (blobs, gossip, docs), and a ceremony needs it to accept an externally supplied handler for its own ALPN. That registration point belongs to the change that brings the first ceremony, together with its `data-layer` API; this change adds nothing to `SyncNode`. What it does guarantee is the runtime side: the runtime owns node assembly in one place (spawn-time construction, single owner of the `SyncNode`), so threading a handler through at spawn will be a parameter addition, not a restructuring. Alternative — adding the registration hook now, unused — rejected: speculative surface, with where the handler lives and the API's shape still open.

### D6. Debug surface off by default, `/live` always on

The HTTP host serves `/live` unconditionally — the container harness and the demo stand probe it. Debug endpoints are demo scaffolding: gated behind `PDN_DEBUG=1`, absent by default, and their shape is deliberately unspecified so demo scripts can evolve them without spec churn. The spec pins only the gate: off means absent.

## Risks / Trade-offs

- **[Runtime spec shadows data-layer specs]** Service-level scenarios re-tread store behavior. → The runtime spec pins delegation and isolation contracts (what the glue must preserve), not store semantics; store behavior stays specified in `components/mee-pdn/data-layer/`.
- **[Traits with a single implementation]** Dead seams if the second implementation never comes. → The rule is applied per service with a named second implementation (KERI, test mock); hosts test against mocks immediately, so the seam is exercised from day one.
- **[Stand-in identity minting leaks into products]** A `PdnId` derived from an identity key that never rotates, standing in for the KERI identifier of ADR-0003. → Confined to the identity service implementation; the trait is the replacement point, and proof-of-control is marked deferred in the linking dialogue (ADR-0012).

## Migration Plan

New crates: add `crates/pdn-node` and `crates/pdn-node-http` to the workspace, implement services over `data-layer` as-is, land the in-process scenario test and the `/live` smoke test. Rollback is removing the crates.
