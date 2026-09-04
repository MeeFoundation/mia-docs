# Proposal: sync-node-extra-protocols

## Why

ADR-0011 decided that connection establishment (pairing) runs as its own protocol on its own application-layer protocol negotiation (ALPN) identifier — a raw bidirectional iroh dialogue on the same endpoint that already carries document sync, gossip, and blob transfer. Today that endpoint is unreachable from outside `data-layer`: `SyncNode::spawn` builds its protocol router entirely internally with a fixed handler set, and nothing exposes the endpoint for dialing a peer or reading the node's own address. ADR-0011 records this as a known consequence ("it must gain a way to register an externally supplied protocol handler"); until it exists, the pairing handshake cannot be assembled at all. This change builds exactly that assembly surface — the socket, not the protocol that will plug into it.

## What Changes

- **`SyncNode` can host the pairing protocol at spawn.** So the ADR-0011 pairing handler can ride the node's endpoint, the assembly gains a spawn form taking (ALPN, handler) pairs, registered on the protocol router alongside the built-in stack (document sync, gossip, blob transfer). A connection arriving on a registered ALPN is dispatched to its handler as a raw bidirectional connection — not a sync session. The parameter is a plain (ALPN, handler) pair rather than a pairing-specific type only because data-layer must not own pairing's semantics (those live in pdn-node) — this is not a general protocol-extension facility. The existing no-extras `spawn()` keeps working unchanged.
- **ALPN uniqueness is enforced at spawn.** An extra protocol claiming a built-in ALPN (document sync, gossip, or blob transfer), or two extras claiming the same ALPN, is refused: spawn fails and no node starts. Silently shadowing the sync stack must be impossible.
- **The node exposes a dial handle.** Runtime code gets a narrow handle onto the node's endpoint (`DialHandle`): the dial side of a dialogue (connect to a peer's address under a chosen ALPN) and the node's own wire address and id (what a future invite payload carries). It is deliberately not the raw endpoint — closing or reconfiguring the socket stays the node's own job, enforced by the handle's shape rather than a doc note. One endpoint per node — extra protocols share the node's wire identity; the handle's id is the node's `NodeId`.
- **A panicking extra handler cannot take down the node.** Each externally supplied handler is wrapped so a panic in its `accept` is caught and fails only that one connection, while the built-in stack keeps serving. iroh's router treats a panicking handler task as fatal to the whole node, so this containment is explicit; the spawn form's contract still asks handlers not to panic (a `panic = "abort"` build cannot be caught).
- **No protocol behavior lands.** No pairing logic, no invite payload, no pairing secret — the ADR-0011 handshake arrives as its own change and registers through this surface.

## Out of Scope (deferred)

- **The pairing protocol itself** — the handler, the invite payload and its encoding, the atomic verify-and-burn of the pairing secret, the `ConnectionMetadataStore` ticket exchange (ADR-0011; requires the connection metadata store proposal).
- **Runtime (`pdn-node`) surface** — the runtime keeps calling the no-extras spawn. Threading a real handler through `Runtime::spawn` is a parameter addition made by the pairing change when it has a handler to thread (design decision D5 of the pdn-node-runtime change); adding the pass-through now would be speculative surface with no consumer.
- **Device linking over the pairing dialogue** — re-basing `link_device` onto the same ceremony is a separate, later change.
- **Any change to the built-in protocols** — sync, gossip, blob transfer, and the periodic reconcile pass are untouched; blob-egress gating remains the open question it already is.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree.

| Capability (delta)        | Archive destination                                   |
| ------------------------- | ----------------------------------------------------- |
| `data-layer-node-assembly` | `openspec/specs/components/mee-pdn/data-layer/node-assembly.md` |

### New Capabilities

- `data-layer-node-assembly`: the node assembly as the registration point ADR-0011 needs — letting the pairing protocol (a raw dialogue that establishes a connection between two identities) ride the node's one endpoint next to the built-in stack, without data-layer owning its semantics. Covers the spawn-time registration point keyed by ALPN, ALPN uniqueness against the built-in stack, panic-isolation of the supplied handler, and a dial handle onto the endpoint for reaching a peer and reading the node's own address. Kept protocol-agnostic (an opaque handler) because pairing's semantics live above in pdn-node, not to offer general protocol extensibility. The existing `components/mee-pdn/data-layer/` specs describe the stores and flows riding the assembly; this one describes the assembly itself.

### Modified Capabilities

_None._ The store specs (`data-store`, `connections-store`, `private-metadata-store`, `device-linking`, `multi-identity`) and the `pdn-node` specs are untouched: the change adds no store, no addressing, no service surface, and no access-model change — admission to replicas remains ticket possession, and the pairing registration point carries no capability semantics of its own.

## Impact

- **`crates/data-layer`**: `SyncNode` gains the handler-taking spawn form and a dial-handle accessor; the internal router assembly checks ALPN uniqueness and wraps each supplied handler in a panic guard before registering it. Purely additive — no existing signature changes, all current callers compile unchanged.
- **`crates/pdn-node` / `crates/pdn-node-http`**: untouched (the runtime's no-extras spawn keeps working; see Out of Scope).
- **pdn-store fork**: untouched — the pairing registration point lives in `data-layer`'s assembly, exactly the placement ADR-0011 argues for (pairing must not entangle the sync engine).
- **Dependencies**: none added; the handler and endpoint types are iroh's, which `data-layer` already depends on and re-exports peers of (`AuthorId`, `DocTicket`), and the panic guard's `catch_unwind` comes from `futures-lite`, already a dependency.
- **Tests**: a new `data-layer` scenario test stands in for the pairing handler with a test-only echo protocol, end to end — spawn with a handler, dial from a second node via the exposed dial handle, bytes round-trip while document sync between the same two nodes still converges; paired refusals per the access-control-tests practice (dial on an ALPN the node did not register; spawn with a reserved or duplicate ALPN); and a handler that panics mid-accept is contained — its connection fails while the same node keeps converging a replica (with a negative control confirming the node dies without the guard). A flaky-test stress pass closes the change per the flaky-tests practice.
