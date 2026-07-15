# Design: sync-node-extra-protocols

## Context

`SyncNode::spawn` binds the endpoint, spawns gossip and the docs engine, and builds the protocol router in one closed move: three built-in handlers (blob transfer, gossip, document sync), each accepted under its application-layer protocol negotiation (ALPN) identifier, and nothing else. The endpoint never leaves the assembly — the only trace of it on the public surface is `node_id()`. ADR-0011 commits pairing to a fourth protocol on the same endpoint and names this exact gap in its Consequences: the assembly "must gain a way to register an externally supplied protocol handler". The pairing change cannot be written until this surface exists; the demo plan runs them as consecutive steps. The pdn-node-runtime change prepared the runtime half (decision D5: the runtime owns node assembly in one place, so threading a handler through is a parameter addition) and left the `data-layer` half — this change — open.

In iroh 1.0 the router's protocol map is fixed when the router spawns: `RouterBuilder::accept` collects handlers keyed by ALPN, `spawn` derives the endpoint's accepted-ALPN set from them, and no public mutation exists afterwards. Handlers are values implementing iroh's `ProtocolHandler` trait; the builder takes anything convertible to its boxed dynamic form, so heterogeneous handlers pass as a plain collection. Dialing out needs no registration at all — an outgoing connection names its ALPN at connect time — but it does need the endpoint handle, which is also where a node reads its own wire address from.

## Goals / Non-Goals

**Goals:**

- A spawn-time registration point on `SyncNode` where the ADR-0011 pairing handler joins the built-in protocols on the one router — kept protocol-agnostic (an (ALPN, handler) pair) so data-layer does not own pairing's semantics, not to be a general extension facility.
- ALPN uniqueness enforced before anything binds: no shadowing of the built-in stack, no ambiguous handlers.
- A supplied handler's panic contained to its own connection, never the node.
- A dial handle exposed for the dial side and the node's own address — enough for the pairing initiator to reach a peer and for an invite payload to carry where to dial.
- The registration point reachable from `pdn-node` without a direct iroh dependency, via `data-layer` re-exports.

**Non-Goals:**

- Any actual protocol: no pairing handler, no invite payload, no pairing secret (the pairing change, per ADR-0011).
- Runtime (`pdn-node`) API changes — the runtime keeps calling the no-extras spawn until it has a handler to pass.
- Post-spawn registration or deregistration of protocols.
- Changes to the built-in protocols, the reconcile pass, or the pdn-store fork.

## Decisions

### D1. Registration happens at spawn, not after

Extras are passed into the spawn call and registered while the router is built. This follows the grain of iroh 1.0 — the protocol map is fixed at router spawn, and the endpoint's accepted-ALPN set is derived from it — and keeps `SyncNode` the single owner of assembly: there is never a half-assembled node whose protocol set is still changing. Alternative — a post-spawn `register` method — rejected: iroh offers no public insertion into a spawned router, so it would mean reimplementing the accept loop or holding the router half-built behind a lock, real complexity for a need nobody has (the pairing handler is known at node construction). Alternative — handing the endpoint or a router builder out and letting the caller assemble — rejected: ownership inversion; the caller would become responsible for accepting the built-in stack and for shutdown, and the assembly would no longer live in one place.

A consequence callers must design around: a handler is constructed *before* the node it serves exists. Anything it needs from the running node — the endpoint, store handles, runtime state — must arrive through shared state the handler captures (an `Arc`'d interior it shares with its constructor, late-bound where necessary). iroh's trait already requires handlers to be `Send + Sync + 'static` values, so this imposes nothing new; it is recorded here because the pairing change will hit it first.

### D2. The extras parameter is iroh-shaped, re-exported through `data-layer`

The extras-taking spawn form accepts a collection of (ALPN bytes, boxed dynamic handler) pairs — exactly what iroh's `RouterBuilder::accept` consumes, with no wrapper types in between. A protocol handler is inherently an iroh concept (its argument is an iroh connection); wrapping it would rename, not abstract. `data-layer` re-exports the types the surface needs — the handler traits, the error type handlers return, the connection and address types — the same way it already re-exports `AuthorId` and `DocTicket` from pdn-store, so `pdn-node` (which has no direct iroh dependency today) implements its pairing handler against `data-layer`'s surface and the iroh version stays pinned in one place. The genericity is a consequence of that layering — data-layer stays protocol-agnostic so pairing's semantics live in pdn-node — not an invitation to register arbitrary protocols; the pairing handler is the one consumer in view (device linking later reuses the same ceremony, not a different protocol). The existing `spawn()` remains as the no-handler form and delegates to the new one; every current caller compiles unchanged.

### D3. ALPN collisions are refused before binding

The extras' ALPNs are checked against the built-in set (document sync, gossip, blob transfer) and against each other before the endpoint binds; a collision fails the spawn with nothing started. Registering an extra under the document-sync ALPN would silently replace the sync stack — a node that looks alive and never syncs — so last-wins is not an acceptable semantics here. Checking before bind (a pure data check) keeps the failure clean: no endpoint, no tasks, nothing to unwind. Alternative — allow overriding built-ins as a power feature — rejected: no consumer, and the failure mode it enables is exactly the silent one the lint posture of this codebase exists to prevent.

### D4. The dial side is a narrow handle, not the raw endpoint

`SyncNode` exposes a `DialHandle` — a narrow facade over the node's endpoint offering exactly the dial side the pairing initiator needs: `connect(addr, alpn)`, the node's own address, and its wire id. The raw endpoint is not handed out.

An earlier draft exposed the raw endpoint handle, reasoning that its types are iroh's anyway so a wrapper hides nothing, guarded by a documented contract that the node owns the endpoint's lifecycle. Review rejected that: iroh's `Endpoint` is a cheaply-cloned handle onto one shared `Arc` inner, and `close()` and `set_alpns()` take `&self` and are public — so a consumer calling `endpoint().close()` (as iroh's own dial examples do) or `endpoint().set_alpns(...)` (a plausible-looking way to register post-spawn) silently kills or hijacks the accept loop for the whole node while local reads and writes keep answering — the exact "looks alive, never syncs" failure the ALPN-uniqueness check exists to prevent. A doc contract does not stop that; the facade does, by not offering the methods. Its return types are still iroh's (`Connection`, `EndpointAddr`, `EndpointId`), so it hides no vocabulary — only the lifecycle power — and each future dial-side need is one method added to the facade deliberately, not a standing hazard.

### D5. The scenario test carries its own protocol

The change is validated by a test-only echo protocol in `data-layer`'s scenario tests — a stand-in for the future pairing handler: node A spawns with the echo handler under a test ALPN, node B dials it through B's dial handle, bytes round-trip, and the same pair of nodes still converges a replica over the ordinary ticket flow — proving coexistence, not just dispatch. The paired refusals: dialing an ALPN the target never registered fails and no handler runs (the tightest unauthorized party for an assembly-level surface — there are no capability semantics here to test); spawning with a reserved or duplicate ALPN fails with no node started. A further test drives a handler that panics mid-accept and asserts the same node still converges a replica (D6's containment), with a negative control — the guard removed — confirming the node dies without it. Alternative — waiting for the pairing change to exercise the point — rejected: the mechanism would land untested and the flaky-test practice requires stressing the affected scenarios now, in isolation from the feature built on top.

### D6. Extra handlers are panic-isolated

A panic in a supplied handler's `accept` would, unguarded, be fatal to the whole node: iroh's router run loop treats a panicking handler task as terminal — it breaks the accept loop, shuts every protocol down, and closes the endpoint. That is the "looks alive, never syncs" outcome the ALPN-uniqueness check refuses, reached by another path — and a supplied handler is exactly the code not bound by this workspace's no-panic lints. So each handler is wrapped at registration in a guard whose `accept` runs the inner handler inside `catch_unwind`: a caught panic fails only that one connection (iroh logs the returned error) and the node keeps serving. The spawn form's contract still asks handlers not to panic — the guard cannot help a `panic = "abort"` build — but containment is the default, by construction. Alternative — document the contract only — rejected: it leaves the whole node one external bug away from silent death, where the guard is ~20 lines and adds no dependency (`catch_unwind` comes from `futures-lite`, already used).

## Risks / Trade-offs

- **[Endpoint lifecycle power]** The raw endpoint's `close()` / `set_alpns()` could silently kill or hijack the node's accept loop if handed to a consumer. → The dial side is a narrow `DialHandle` facade (D4) that does not offer those methods; the node keeps sole ownership of the endpoint's lifecycle by construction, not by a doc note.
- **[Pairing registration point lands before its consumer]** Speculative-surface risk, the same one D5 of pdn-node-runtime used to defer this. → No longer speculative: ADR-0011 is written, the pairing change is the next step of the demo plan and is blocked on exactly this; the echo test is a real consumer from day one.
- **[Boxed-dynamic handlers erase types]** Registration mistakes surface at runtime, not compile time. → The only runtime-checked property is ALPN uniqueness, and it fails the spawn loudly; handler behavior stays typed inside each handler.
- **[Unregistered-ALPN refusal shape]** The deny test asserts on how iroh surfaces an ALPN mismatch (a failed dial), which is protocol-negotiation behavior, not ours. → Assert that the dial fails and no connection is established, not any particular error text; that survives iroh upgrades.

## Migration Plan

Purely additive to `crates/data-layer`: add the handler-taking spawn form (existing `spawn()` delegates), the uniqueness check, the per-handler panic guard, the dial-handle accessor, and the re-exports; land the echo scenario test with its paired refusals and the panic-containment test; stress the new and adjacent scenario tests per the flaky-tests practice. No other crate changes; the runtime adopts the new form only when the pairing change gives it a handler. Rollback is deleting the additions — nothing outside the new test consumes them yet.

## Open Questions

None blocking this change. ADR-0011's open questions (invite payload encoding, secret entropy and lifetime, where the pairing handler lives inside the runtime, failure handling mid-dialogue) belong to the pairing change that consumes this surface.
