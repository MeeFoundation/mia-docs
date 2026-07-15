# Tasks: sync-node-extra-protocols

## 1. The pairing registration point (`SyncNode`)

- [x] 1.1 Handler-taking spawn form: accepts (ALPN, boxed dynamic handler) pairs and registers them on the router next to blobs/gossip/docs; ALPN uniqueness checked against the built-in set and among the supplied handlers *before* the endpoint binds, collision fails the spawn with nothing started; existing `spawn()` delegates with no handlers (all current callers compile unchanged)
- [x] 1.2 Dial handle on `SyncNode` (`DialHandle`): a narrow facade exposing connect / own address / wire id; the endpoint's lifecycle controls (close, set_alpns) are not reachable through it, so the node stays sole owner of lifecycle — shutdown remains `SyncNode::shutdown` (D4)
- [x] 1.3 Re-export the handler types from `data-layer` (handler traits, the accept error type, connection/address types), so `pdn-node` later implements its pairing handler with no direct iroh dependency (D2)
- [x] 1.4 Assembly docs reflect the pairing slot: `node.rs` module/struct docs mention the supplied protocol and the exposed dial handle (today they describe a closed three-protocol stack)
- [x] 1.5 Panic-isolate the supplied handler: each is wrapped so a panic in `accept` is caught (`catch_unwind` from `futures-lite`) and fails only that connection, never the node; the spawn form's doc states the panic contract (containment, and the `panic = "abort"` caveat) (D6)

## 2. Scenario tests (each allowed case paired with its refusal, per the access-control-tests practice)

- [x] 2.1 Echo round-trip and coexistence (scenarios "An extra protocol answers on its ALPN", "The built-in stack is unaffected by extras", "Dialing out rides the node's own identity"): test-only echo handler (standing in for the pairing handler) under a test ALPN on node A; node B dials through its exposed dial handle — bytes round-trip on the raw stream, the handler observes B's node id as the remote identity; the same pair then converges a replica over the ordinary ticket flow
- [x] 2.2 Paired refusal — unregistered ALPN (scenario "A node that did not register the ALPN refuses it"): dialing an ALPN the target never registered fails, no connection is established, and the handler records no invocation
- [x] 2.3 Spawn refusals (scenarios "A built-in ALPN is refused at spawn", "A duplicate supplied ALPN is refused at spawn"): a supplied handler claiming the document-sync ALPN fails the spawn; two supplied handlers sharing an ALPN fail the spawn; nothing is left bound in either case (the check precedes the endpoint bind, and every built-in ALPN is covered, not just document sync)
- [x] 2.4 Dial-handle identity (scenario "The dial handle carries the node's wire identity"): the dial handle's identifier equals `node_id()`
- [x] 2.5 Panic containment (scenario "A panicking handler does not take down the node"): a handler that panics mid-accept fails its connection while the same node still converges a replica over the ticket flow; a negative control (guard removed) confirms the node dies without it

## 3. Wrap-up

- [x] 3.1 CLAUDE.md `data-layer` row mentions the pairing registration point (supplied protocol handler at spawn + exposed dial handle; the ADR-0011 slot)
- [x] 3.2 `just precommit-check` green across the workspace
- [x] 3.3 Flaky-test stress pass per the flaky-tests practice (`just stress`): the new scenario test plus the existing sync/linking scenarios, counted loop; any failure is a defect of this change, diagnosed in isolation — roster restricted per the practice: pool A = `extra_protocols` ×300 (0 failures; bounds the rate at ~1%, 95% confidence), pool B = the data-layer + pdn-node + http scenario binaries riding the shared spawn path ×20 (0 failures); logs in `target/stress/20260715-030646-extra-protocols/`. Re-stressed after the dial-handle facade (D4) and panic guard (D6) landed: `extra_protocols` ×100, 0 failures; the panic-containment test's negative control (guard removed) fails as expected, confirming the test has teeth
- [x] 3.4 `openspec validate --all --strict` passes for the change
