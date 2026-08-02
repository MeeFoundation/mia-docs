# Tasks: http-host-surface

Start after `product-path-gaps` is merged: the error table below downcasts two marker errors it adds, and the scenario tests expect a granted namespace that converges from any reachable device of its issuer. Nothing here edits `pdn-node` — if a handler seems to need something the runtime does not offer, that is a finding to raise, not a runtime edit to make in passing.

## 1. Shapes and error mapping (`pdn-node-http`)

- [ ] 1.1 Dependencies: `serde` and `serde_json`, axum's `json` feature; no `data-layer` dependency (the runtime re-exports what the shapes need)
- [ ] 1.2 Request and response shapes: identity list, connection list, entry listing (`EntryInfo`), grant publication (issuer plus `GrantedClaim` list), grant read as capability only — issuer, claims, commands, no ticket (D4); ceremony payloads passed through opaquely, the host never naming their fields (D3)
- [ ] 1.3 Error mapping: the closed downcast table of D9 — refusals (`EstablishmentRefused`, `LinkingRefused`, `WriteNotGranted`, `DelegationUnsupported`) → 403, unhosted identity or issuer → 409, unsupported payload version and malformed input → 400, absent entry → 404, anything unrecognized → 500 — each carrying the error's own text
- [ ] 1.4 Unit tests for the mapping: each listed error maps to its status and no other; an unmapped error is 500 — the table is the thing a deny test rests on, so it is tested directly, not only through the routes

## 2. Routes (`pdn-node-http`)

- [ ] 2.1 Identity: `POST /debug/identities` (create), `GET /debug/identities` (hosted), `POST /debug/identities/{identity}/linking-invite` with an optional lifetime, `POST /debug/link` with the timeout as a query parameter and a default (D1, D7)
- [ ] 2.2 Connections: `POST /debug/identities/{identity}/invite` with an optional lifetime, `POST /debug/identities/{identity}/establish`, `GET /debug/identities/{identity}/connections` (D1, D7)
- [ ] 2.3 Grants: `POST` and `GET /debug/identities/{identity}/grants/{peer}` (publish, read), `DELETE /debug/identities/{identity}/grants/{peer}/{issuer}` (withdraw); reads report what is there now and never wait (D4, D8)
- [ ] 2.4 Data: `PUT` and `GET /debug/data/{issuer}/{*path}` with the raw body as the payload both ways, `GET /debug/data/{issuer}` with an optional prefix for listing; an absent entry is 404 (D2, D8)
- [ ] 2.5 No route for the out-of-band ticket handover, none that forces reconciliation, resets state, or reaches a store outside a service call — the absence is the requirement, so it is stated in the router's own docs where the next person would otherwise add one; likewise no handler addressing another host: the crate keeps zero HTTP-client dependencies, and inter-node traffic stays on the runtime's protocols (D4, D5, D11)
- [ ] 2.6 `/live` and `/debug/status` unchanged; the debug gate still decides the whole `/debug/` subtree in one place (D10)
- [ ] 2.7 Bind resolution moved out of `main` into a testable function (host and port from the environment, loopback when unset) and unit-tested for the loopback default and an explicit wider bind

## 3. Host scenario tests (`pdn-node-http`)

- [ ] 3.1 Two in-process runtimes, each behind its own router, driven only over HTTP: create identities, invite, establish, publish a grant, write an entry, read it back through the grantee — the spec's whole-scenario proof, with no direct service call in the test body, no ticket anywhere in it, and waiting done by repeating the read
- [ ] 3.2 A device joins over HTTP: linking payload minted on one host and consumed on a second, which then lists the identity as hosted and reads entries written before the link
- [ ] 3.3 Paired denials per [access-control-tests](../../specs/code-practices/access-control-tests.md), each asserted as a client error with its own status: an unhosted identity; a replayed invite payload; a write outside the grant's write set, with the prior value still readable afterwards; a grant naming a foreign issuer
- [ ] 3.4 The gate keeps its existing assertion — every new route is absent without `PDN_DEBUG=1`, not merely unauthorized

## 4. Docs and spec tree (manual, not deltas)

- [ ] 4.1 Crate docs of `pdn-node-http`: the debug surface is scaffolding covering the runtime's operations, it carries live ceremony secrets, it authorizes nothing, and route names are free to change; the host is off the product path — product hosts embed the runtime, and nodes talk only the runtime's protocols, never HTTP (D11)
- [ ] 4.2 CLAUDE.md crate row for `pdn-node-http`: the surface covers the runtime's services behind `PDN_DEBUG=1`, `/live` always on, defaults unchanged
- [ ] 4.3 Sweep the spec tree and the active changes for statements this change invalidates — anything reading that the debug surface has no requirements beyond its gate

## 5. Gates

- [ ] 5.1 `just check` and `just test` green
- [ ] 5.2 Stress pass per [flaky-tests](../../specs/code-practices/flaky-tests.md): the new host scenario tests under `--stress-count`, sized by the rule of three; any failure diagnosed as a defect of this change before anything is built on top
- [ ] 5.3 `openspec validate --all --strict` before archiving
