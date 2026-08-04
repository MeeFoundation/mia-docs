# Tasks: http-host-surface

Start after `product-path-gaps` is merged: the error table below downcasts two marker errors it adds, and the scenario tests expect a granted namespace that converges from any reachable device of its issuer. Nothing here edits `pdn-node` — if a handler seems to need something the runtime does not offer, that is a finding to raise, not a runtime edit to make in passing.

## 1. Shapes and error mapping (`pdn-node-http`)

- [x] 1.1 Dependencies: `serde` and `serde_json`, axum's `json` feature; no `data-layer` dependency (the runtime re-exports what the shapes need)
- [x] 1.2 Request and response shapes: identity list, connection list, entry listing (`EntryInfo`), grant publication (issuer plus `GrantedClaim` list), grant read as capability only — issuer, claims, commands, no ticket (D4); ceremony payloads passed through opaquely, the host never naming their fields (D3)
- [x] 1.3 Error mapping: the closed downcast table of D9 — refusals (`EstablishmentRefused`, `LinkingRefused`, `WriteNotGranted`, `DelegationUnsupported`) → 403, unhosted identity or issuer → 409, unsupported payload version and malformed input → 400, absent entry → 404, anything unrecognized → 500 — each carrying the error's own text. The two the host decides itself rather than by downcast, both 400 so neither lands on the pessimistic default: an empty entry payload, which the engine keeps no entry for, and an unknown query parameter, refused rather than ignored (D9)
- [x] 1.4 Unit tests for the mapping: each listed error maps to its status and no other; an unmapped error is 500 — the table is the thing a deny test rests on, so it is tested directly, not only through the routes

## 2. Routes (`pdn-node-http`)

- [x] 2.1 Identity: `POST /debug/identities` (create), `GET /debug/identities` (hosted), `POST /debug/identities/{identity}/linking-invite` with an optional lifetime, `POST /debug/link` with the timeout as a query parameter and a default (D1, D7)
- [x] 2.2 Connections: `POST /debug/identities/{identity}/invite` with an optional lifetime, `POST /debug/identities/{identity}/establish`, `GET /debug/identities/{identity}/connections` (D1, D7)
- [x] 2.3 Grants: `POST` and `GET /debug/identities/{identity}/grants/{peer}` (publish, read), `DELETE /debug/identities/{identity}/grants/{peer}/{issuer}` (withdraw); reads report what is there now and never wait (D4, D8)
- [x] 2.4 Data: `PUT` and `GET /debug/data/{issuer}/{*path}` with the raw body as the payload both ways, `GET /debug/data/{issuer}` with an optional prefix for listing; an absent entry is 404 (D2, D8)
- [x] 2.5 No route for the out-of-band ticket handover, none that forces reconciliation, resets state, or reaches a store outside a service call — the absence is the requirement, so it is stated in the router's own docs where the next person would otherwise add one; likewise no handler addressing another host: the crate keeps zero HTTP-client dependencies, and inter-node traffic stays on the runtime's protocols (D4, D5, D11)
- [x] 2.6 `/live` and `/debug/status` unchanged; the debug gate still decides the whole `/debug/` subtree in one place (D10)
- [x] 2.7 Bind resolution moved out of `main` into a testable function (host and port from the environment, loopback when unset) and unit-tested for the loopback default and an explicit wider bind
- [x] 2.8 The binary's stop path: the graceful shutdown answers SIGTERM as well as an interrupt, because a container stop sends the former and the graceful path would otherwise never run where it matters; the runtime's shutdown is then required rather than attempted, so sole ownership failing is an error and not a silent skip that holds process exit

## 3. Host scenario tests (`pdn-node-http`)

- [x] 3.1 Two in-process runtimes, each behind its own router, driven only over HTTP: create identities, invite, establish, publish a grant, write an entry, read it back through the grantee — the spec's whole-scenario proof, with no direct service call in the test body, no ticket anywhere in it, and waiting done by repeating the read. Then the grant's counterpart: withdraw it and wait for the grantee's read to answer the unknown-issuer refusal, with the issuer's own entry still readable — the surface's one access-narrowing act, and the route no positive assertion would otherwise reach. The listing's prefix and a minted lifetime are exercised in the same place, so no query parameter of the surface goes unread
- [x] 3.2 A device joins over HTTP: linking payload minted on one host and consumed on a second, which then lists the identity as hosted and reads entries written before the link
- [x] 3.3 Paired denials per [access-control-tests](../../specs/code-practices/access-control-tests.md), each asserted as a client error with its own status: an unhosted identity; a replayed invite payload; a write outside the grant's write set, with the prior value still readable afterwards; a grant naming a foreign issuer; an empty entry payload and a mistyped query parameter, each beside the well-formed request it is the near miss of
- [x] 3.4 The gate keeps its existing assertion — every new route is absent without `PDN_DEBUG=1`, not merely unauthorized

## 4. Docs and spec tree (manual, not deltas)

- [x] 4.1 Crate docs of `pdn-node-http`: the debug surface is scaffolding covering the runtime's operations, it carries live ceremony secrets, it authorizes nothing, and route names are free to change; the host is off the product path — product hosts embed the runtime, and nodes talk only the runtime's protocols, never HTTP (D11)
- [x] 4.2 CLAUDE.md crate row for `pdn-node-http`: the surface covers the runtime's services behind `PDN_DEBUG=1`, `/live` always on, defaults unchanged
- [x] 4.3 Sweep the spec tree and the active changes for statements this change invalidates — anything reading that the debug surface has no requirements beyond its gate

## 5. Gates

- [x] 5.1 `just check` and `just test` green
- [x] 5.2 Stress pass per [flaky-tests](../../specs/code-practices/flaky-tests.md): the new host scenario tests under `--stress-count`, sized by the rule of three; any failure diagnosed as a defect of this change before anything is built on top
  - Wide sweep green: `just test`, 122/122, re-run after the withdrawal, prefix, empty-payload and query-parameter assertions joined the suite.
  - Deep pass green: `just stress --stress-count 300 -p pdn-node-http` — 300 of 300 iterations, 5,700 test executions, no failure and nothing even reported slow, on the suite as it stands with those assertions in it. Three hundred consecutive iterations bound the per-iteration failure rate at roughly one percent with 95% confidence.
  - One defect found and fixed on the way: the gate tests leaked their runtime — `Arc::try_unwrap` cannot succeed while the router holds the other reference, so `shutdown` never ran and the endpoint plus a created identity's armer held process exit for minutes under load. The router is now dropped first and the shutdown is required, not attempted. Reproduced at iteration 264 of 300; the fixed test then ran 400 of 400 green in isolation.
  - One dependency-level abort recorded, not this change's code: `debug_assert!(max_size >= min_size)` in `noq-proto`'s packet builder (iroh's QUIC), reached from the connection driver on a dial — one occurrence in roughly 1,400 test executions on a machine running at a two-hundred-fold slowdown, on the dial path every scenario suite in the workspace shares. It did not recur in the 5,700 executions of the clean pass, and the assertion lives in debug builds only, which is what the test runner uses. Worth knowing when a dial-path suite aborts under a starved runner.
- [x] 5.3 `openspec validate --all --strict` before archiving. The delta's relative links are written for the archive destination, not for the delta's own directory — `code-practices` two levels up, sibling component specs by bare file name — as every landed component spec has them
