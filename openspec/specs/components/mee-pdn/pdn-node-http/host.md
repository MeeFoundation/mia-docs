# HTTP host

## Purpose

The HTTP host for the demo stand: a thin binary embedding the [runtime core](../pdn-node/core.md) and serving it over HTTP. One process, one embedded runtime. The HTTP surface is a host over the core, not the platform API — other hosts (mobile, wasm) embed the same core later. What this host is packaged into, and the scenarios driven across containers through it, are the [container stand](container-stand.md)'s.

## Requirements

### Requirement: The host reads where its state lives from the environment, and requires it
The host SHALL read the runtime's storage location from `PDN_DATA_DIR` at startup and pass that directory to the runtime it embeds. The host SHALL NOT offer an in-memory mode and SHALL NOT carry a path of its own: unset, the start stops with an error naming the variable, because a host that starts without a directory promises persistence it does not provide. A directory the runtime cannot use — unwritable, or held by another running node — SHALL stop the start with an error naming it, and SHALL NOT be answered by starting in memory instead: a host that silently forgets where its state was is indistinguishable, from outside, from one that lost it.

#### Scenario: The configured directory is used
- **WHEN** the host starts with `PDN_DATA_DIR` set to a writable directory
- **THEN** the runtime stores its state there, and a host started again on the same directory serves the same node id and the same hosted identities

#### Scenario: An unset variable stops the start
- **WHEN** the host starts with `PDN_DATA_DIR` unset
- **THEN** the process exits with an error naming the variable, serving neither liveness nor the debug surface

#### Scenario: An unusable directory stops the start
- **WHEN** the host starts with `PDN_DATA_DIR` naming a directory it cannot use
- **THEN** the process exits with an error naming the directory, serving neither liveness nor the debug surface

### Requirement: The host serves liveness unconditionally
The host SHALL expose `GET /live` returning success while the embedded runtime is running, with no flag or configuration required. Container harnesses and the demo stand probe it.

#### Scenario: Liveness while running
- **WHEN** the host process is up with its embedded runtime
- **THEN** `GET /live` returns HTTP 200

### Requirement: Readiness is bounded separately
The host SHALL expose `GET /ready` as a bounded check of the runtime's coarse state lock. `GET /live` SHALL NOT wait for that lock.

#### Scenario: Lock contention affects readiness only
- **WHEN** the coarse state lock remains held beyond 2 seconds
- **THEN** `/live` returns HTTP 200 and `/ready` returns non-success within its budget

### Requirement: Debug requests have aggregate bounds
The host SHALL accept at most 16 concurrent requests and at most 16 MiB per entry body. It SHALL return HTTP 503 when concurrency admission is full and HTTP 413 for an oversized body. HTTP 500 responses SHALL use stable generic public text while retaining the full cause chain only in server logs.

#### Scenario: Overload is shed
- **WHEN** 16 requests are already admitted
- **THEN** an additional request receives HTTP 503 without entering its handler

### Requirement: The debug surface is absent by default
Debug endpoints are demo scaffolding, not platform API. The host SHALL NOT serve any route under `/debug/` unless `PDN_DEBUG=1` is set at startup. When enabled, route names, paths, and payload shapes are deliberately unspecified and may change without a spec change; the properties required of the surface as a whole are the requirements below.

#### Scenario: Debug routes off without the flag
- **WHEN** the host starts without `PDN_DEBUG` set
- **THEN** requests under `/debug/` return HTTP 404

### Requirement: The debug surface covers the embedded runtime's operations
When enabled, the debug surface SHALL make identity creation and linking, connection establishment, grants, entry operations, node status, and hosted identities reachable over HTTP. Each route SHALL delegate to a runtime service call and add no orchestration of its own.

#### Scenario: A whole scenario runs over HTTP alone
- **WHEN** 2 hosts are driven only over HTTP through identity creation, establishment, a grant, a write, and a grantee read
- **THEN** the grantee reads the granted entry without an in-process call into either runtime

#### Scenario: A device joins over HTTP
- **WHEN** a linking payload is minted on 1 host and consumed on a second
- **THEN** the second host reports the identity as hosted and reads entries written before the link

### Requirement: The surface offers no path the runtime's own callers lack
The surface SHALL NOT expose namespace ticket handover, forced reconciliation, state reset, or direct store access, and SHALL NOT return a namespace ticket when reading a grant.

#### Scenario: A granted namespace arrives with no ticket crossing the surface
- **WHEN** a connected peer publishes a grant and the grantee reads the entry over HTTP
- **THEN** the entry eventually reads back without any route handing over or accepting a namespace ticket

#### Scenario: Convergence is waited for, not forced
- **WHEN** a caller waits for a value written on another node
- **THEN** repeating the read is the only available wait mechanism

### Requirement: The container scenario runs on the product path
Every route SHALL act on its own host's embedded runtime. Hosts SHALL NOT address each other over HTTP; establishment, linking, reconciliation, and gossip SHALL use the runtime's iroh protocols.

#### Scenario: Nodes exchange no HTTP
- **WHEN** a caller drives 2 hosts through establishment, a grant, and replication
- **THEN** HTTP remains the external control plane and all inter-node traffic uses runtime protocols

### Requirement: A refused operation is reported as a refusal
The host SHALL report a runtime refusal with its allow-listed client-error status and SHALL NOT report it as success. A refusal SHALL remain distinguishable from an absent route and an internal or transport failure.

#### Scenario: An unhosted identity is refused, not absent
- **WHEN** a request addresses an identity the runtime does not host
- **THEN** the response is a client error other than 404

#### Scenario: An absent entry is reported as absent
- **WHEN** a request reads a missing entry under a hosted issuer
- **THEN** the response is HTTP 404

#### Scenario: A write outside the grant's write set is refused
- **WHEN** a grantee writes a read-only claim
- **THEN** the response is a client error and the previous value remains

#### Scenario: A burnt invite secret is refused
- **WHEN** a consumed invite payload is presented again
- **THEN** the response is a client error and no second connection is recorded

### Requirement: The debug surface exposes live ceremony secrets and stays bound accordingly
Invite and linking payloads cross the unauthenticated debug surface in the clear. The host SHALL bind loopback unless a wider address is configured explicitly, and no namespace ticket SHALL cross the surface.

#### Scenario: Default bind is loopback
- **WHEN** no bind address is configured
- **THEN** the host listens on loopback only

#### Scenario: A wider bind is explicit
- **WHEN** a bind address is configured
- **THEN** the host listens on exactly that address

### Requirement: The host stays off the product path
Product hosts SHALL embed the runtime in-process. The runtime SHALL declare no HTTP server or client of its own, and the host dependency SHALL point toward the runtime only.

#### Scenario: The runtime serves no HTTP of its own
- **WHEN** the runtime crate is built without the host
- **THEN** it opens no HTTP listener and no workspace crate besides the host depends on the host

### Requirement: Internal failures stay server-side
The host SHALL log the full internal cause chain for an unrecognized failure and SHALL return `internal server error` for HTTP 500. Client-error responses SHALL expose only allow-listed public messages.

#### Scenario: Internal cause is not disclosed
- **WHEN** a handler returns nested internal context mapped to HTTP 500
- **THEN** the client receives stable generic text and the server log retains the complete chain

#### Scenario: Oversized entry is refused
- **WHEN** an entry body exceeds 16 MiB
- **THEN** the host returns HTTP 413 without invoking the data service
