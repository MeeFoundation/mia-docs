# pdn-node: HTTP host

The HTTP host for the demo stand: a thin binary embedding the runtime core and serving it over HTTP. One process, one embedded runtime. The HTTP surface is a host over the core, not the platform API — other hosts (mobile, wasm) embed the same core later.

## ADDED Requirements

### Requirement: The host serves liveness unconditionally
The host SHALL expose `GET /live` returning success while the embedded runtime is running, with no flag or configuration required. Container harnesses and the demo stand probe it.

#### Scenario: Liveness while running
- **WHEN** the host process is up with its embedded runtime
- **THEN** `GET /live` returns HTTP 200

### Requirement: The debug surface is absent by default
Debug endpoints are demo scaffolding, not platform API. The host SHALL NOT serve any route under `/debug/` unless `PDN_DEBUG=1` is set at startup; when enabled, their shape is deliberately unspecified and may change without a spec change.

#### Scenario: Debug routes off without the flag
- **WHEN** the host starts without `PDN_DEBUG` set
- **THEN** requests under `/debug/` return HTTP 404
