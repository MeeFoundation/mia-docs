# HTTP host

## Purpose

The HTTP host for the demo stand: a thin binary embedding the [runtime core](../../pdn-node/core/spec.md) and serving it over HTTP. One process, one embedded runtime. The HTTP surface is a host over the core, not the platform API — other hosts (mobile, wasm) embed the same core later. What this host is packaged into, and the scenarios driven across containers through it, are the [container stand](../container-stand/spec.md)'s.

## Requirements

### Requirement: The host reads where its state lives from the environment, and requires it
The host SHALL read the runtime's storage location from `PDN_DATA_DIR` at startup and pass that directory to the runtime it embeds. The host SHALL NOT offer an in-memory mode and SHALL NOT carry a path of its own: unset, the start stops with an error naming the variable, because a host that starts without a directory promises persistence it does not provide. A directory the runtime cannot use — unwritable, or held by another running node — SHALL stop the start with an error naming it, and SHALL NOT be answered by starting in memory instead: a host that silently forgets where its state was is indistinguishable, from outside, from one that lost it.

**Example:** `PDN_DATA_DIR` at start, and what the host does.

| `PDN_DATA_DIR` at start | what the host does |
|---|---|
| `/var/lib/pdn`, empty | creates `identities/`, `blobs/`, `lock` and `node.key` there, then serves |
| `/var/lib/pdn`, kept from an earlier run | reads `node.key` back: the same node id, the same hosted identities |
| unset, or set to `""` | exits with `"PDN_DATA_DIR is not set — …"`, serving nothing |
| `/var/lib/pdn`, held by a running node | exits with `"storage directory /var/lib/pdn is held by another running node"` |

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

**Example:** a host started with `PDN_DATA_DIR` alone: no `PDN_DEBUG`, `PDN_HOST` or `PDN_PORT`.

```
request:     GET http://127.0.0.1:3011/live
response:    200, body "ok"
```

#### Scenario: Liveness while running
- **WHEN** the host process is up with its embedded runtime
- **THEN** `GET /live` returns HTTP 200

### Requirement: Readiness is bounded separately
The host SHALL expose `GET /ready` as a bounded check of the runtime: its coarse state lock answers within the budget, and its replica store answers a read. The store read is the half that can say no after a full filesystem: the store then refuses every operation until the process restarts, while the in-memory bookkeeping stays intact, so a readiness drawn from the bookkeeping alone would keep reporting a node that serves nothing. `GET /live` SHALL NOT wait for either.

**Example:** Alice hosted on a node whose 16 MiB state directory filled, asked once the replica store has failed.

| request | answer |
|---|---|
| `GET /debug/identities` | 200, lists Alice: the in-memory bookkeeping is intact |
| `GET /ready` | `500 "internal server error"`: the replica store refuses its read |
| `GET /live` | `200 "ok"` |

#### Scenario: Lock contention affects readiness only
- **WHEN** the coarse state lock remains held beyond 2 seconds
- **THEN** `/live` returns HTTP 200 and `/ready` returns non-success within its budget

#### Scenario: A store that stopped answering fails readiness
- **WHEN** the replica store refuses its operations after the state directory filled
- **THEN** `/ready` returns non-success while `/live` returns HTTP 200

### Requirement: Debug requests have aggregate bounds
The host SHALL accept at most 16 concurrent requests under `/debug/` and at most 16 MiB per entry body. `GET /live` and `GET /ready` stay outside that admission, so a burst of debug traffic cannot shed the probes an orchestrator acts on. It SHALL return HTTP 503 when concurrency admission is full and HTTP 413 for an oversized body. HTTP 500 responses SHALL use stable generic public text while retaining the full cause chain only in server logs.

**Example:** Alice hosted on the node; `<alice>` is her identity in hex.

| request | what the host does |
|---|---|
| `PUT /debug/data/<alice>/<alice>/contact/email`, 16,777,216-byte body | passes the router to the data service |
| the same `PUT` with 16,777,217 bytes | 413, no handler runs |
| `GET /live` while 16 requests under `/debug/` are in flight | 200: the probes are outside the admission |

#### Scenario: Overload is shed
- **WHEN** 16 requests are already admitted
- **THEN** an additional request receives HTTP 503 without entering its handler

### Requirement: The debug surface is absent by default
Debug endpoints are demo scaffolding, not platform API. The host SHALL NOT serve any route under `/debug/` unless `PDN_DEBUG` is set to `1` or `true` at startup; unset, `0` and `false` leave the surface absent. Any other value — `TRUE`, `yes`, `1` with a leading space, the empty string — SHALL stop the start with an error naming the accepted values, serving neither liveness nor the debug surface: a mistyped flag read as off would look, from outside, like a renamed route. When enabled, route names, paths, and payload shapes are deliberately unspecified and may change without a spec change; the properties required of the surface as a whole are the requirements below.

**Example:** `PDN_DEBUG` at start, and what `GET /debug/status` answers.

| `PDN_DEBUG` at start | what `GET /debug/status` answers |
|---|---|
| unset, `0` or `false` | 404, as for a route the host never had |
| `1` or `true` | 200, `"node <node id>"`, then a `"hosts <identity>"` line per hosted identity |
| `yes`, `TRUE` or empty | nothing: the host exits with `PDN_DEBUG must be one of 1, true, 0, false, or unset — got "yes"` |

#### Scenario: Debug routes off without the flag
- **WHEN** the host starts without `PDN_DEBUG` set
- **THEN** requests under `/debug/` return HTTP 404

#### Scenario: An unrecognized flag value stops the start
- **WHEN** the host starts with `PDN_DEBUG` set to a value other than `1`, `true`, `0` or `false`
- **THEN** the process exits with an error naming the accepted values, serving neither liveness nor the debug surface

### Requirement: The debug surface covers the embedded runtime's operations
When enabled, the debug surface SHALL make identity creation and linking, connection establishment, grants, entry operations, [cells](../../../../architecture/language/cell.md), node status, and hosted identities reachable over HTTP. An entry operation SHALL name the identity performing it as well as the issuer addressed, and a cells operation the identity performing it as well as the cell, so a caller reaches exactly what that identity holds. Each route SHALL delegate to a runtime service call and add no orchestration of its own. The cells routes SHALL cover every operation of the cells service, one route each: creating and listing cells and listing a cell's members; inviting and joining; the membership acts; placing records, appending operations, reading and listing records; and listing the entries outside the key layout.

**Example:** two requests to the host on Alice's tablet a3, which hosts Alice-leisure, a member of the cell `9cbcbe4da7cc35a44360d64e45621957`, and Alice-work, no member; `<alice-leisure>`, `<alice-work>`: 64 lowercase hex chars of each `PdnId`.

| request | answer |
|---|---|
| `GET /debug/identities/<alice-leisure>/cells/9cbcbe4da7cc35a44360d64e45621957/records` | the records Alice-leisure's replica holds, from one `list_records` call |
| `GET /debug/identities/<alice-work>/cells/9cbcbe4da7cc35a44360d64e45621957/records` | 409: Alice-work is no member, whoever else the tablet hosts |

#### Scenario: A whole scenario runs over HTTP alone
- **WHEN** 2 hosts are driven only over HTTP through identity creation, establishment, a grant, a write, and a grantee read
- **THEN** the grantee reads the granted entry without an in-process call into either runtime

#### Scenario: A device joins over HTTP
- **WHEN** a linking payload is minted on 1 host and consumed on a second
- **THEN** the second host reports the identity as hosted and reads entries written before the link

#### Scenario: A read as a co-located identity is refused
- **WHEN** a host hosting two identities is asked, over HTTP, to read an issuer one identity holds under a grant, naming the other identity
- **THEN** the response is a client error and no entry is returned

#### Scenario: A cell scenario runs over HTTP alone
- **WHEN** 3 hosts are driven only over HTTP through creating a cell, two invitations, a record placed by one member and an operation appended to it by another
- **THEN** every member reads the record and the operation without an in-process call into any runtime

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

**Example:** what passes between 2 hosts, by the ALPN (protocol name) each connection opens under.

| traffic | ALPN |
|---|---|
| establishment | `/pdn/pairing/0` |
| linking | `/pdn/linking/0` |
| reconciliation | `/iroh-sync/1` |
| gossip | `/iroh-gossip/1` |
| entry payloads | `/iroh-bytes/4` |
| HTTP | nothing: no route addresses another host, and the host carries no HTTP client |

#### Scenario: Nodes exchange no HTTP
- **WHEN** a caller drives 2 hosts through establishment, a grant, and replication
- **THEN** HTTP remains the external control plane and all inter-node traffic uses runtime protocols

### Requirement: A refused operation is reported as a refusal
The host SHALL report a runtime refusal with its allow-listed client-error status and SHALL NOT report it as success. A refusal SHALL remain distinguishable from an absent route and an internal or transport failure.

**Example:** cells requests on Alice's tablet a3, which hosts Alice-leisure, the owner of `9cbcbe4da7cc35a44360d64e45621957`, and Alice-work, a plain member of `f942dfc21acd0218d48f61f714ddfff3` and no member of `9cbcbe4da7cc35a44360d64e45621957`; `<alice-leisure>`, `<alice-work>`, `<bob>`: 64 lowercase hex chars of each `PdnId`; `<absent>`: an id the cell does not hold.

| request | answer |
|---|---|
| `POST /debug/identities/<alice-work>/cells/f942dfc21acd0218d48f61f714ddfff3/acts`, `Kick(<bob>)` | 403; Bob stays a member |
| `GET /debug/identities/<alice-work>/cells/9cbcbe4da7cc35a44360d64e45621957/members` | 409 |
| `GET /debug/identities/<alice-leisure>/cells/9cbcbe4da7cc35a44360d64e45621957/records/<bob>/claim/<absent>` | 404 |

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

#### Scenario: A cell the identity is no member of is refused, not absent
- **WHEN** a request addresses a cell the identity is no member of
- **THEN** the response is a client error other than 404

#### Scenario: A refusal by role is reported as a refusal
- **WHEN** a plain member kicks another member of the cell
- **THEN** the response is a client error and every member still lists the other member

#### Scenario: An absent record is reported as absent
- **WHEN** a member reads a record the cell does not hold
- **THEN** the response is HTTP 404

### Requirement: The debug surface exposes live ceremony secrets and stays bound accordingly
Invite and linking payloads cross the unauthenticated debug surface in the clear. The host SHALL bind loopback unless a wider address is configured explicitly, and no namespace ticket SHALL cross the surface.

**Example:** `PDN_HOST` and `PDN_PORT` at start, and where the host listens.

| `PDN_HOST` and `PDN_PORT` at start | where the host listens |
|---|---|
| both unset | `127.0.0.1:3011` |
| `PDN_PORT=9000` | `127.0.0.1:9000` |
| `PDN_HOST=0.0.0.0`, `PDN_PORT=3011` | `0.0.0.0:3011`, as the stand's image sets them |
| `PDN_HOST=localhost` | nowhere: the start fails with `"PDN_HOST is not an IP address"` |

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
The host SHALL log the full internal cause chain for an unrecognized failure and SHALL return `internal server error` for HTTP 500. A client error for a runtime error the host's error table maps SHALL carry the outermost message of that error as the runtime returns it, and SHALL NOT carry the causes beneath it: where the runtime raises a refusal over a lower failure — a refused establishment or linking arrives as the connection closing under a read — the refusal is that outermost message and the read failure stays out, while a refusal the runtime wrapped in further context would keep the refusal's status and carry that context's text. A client error the host raises itself names what was absent or malformed, the parser's complaint included; a rejection by the router itself — a query it cannot decode, a body past the ceiling — carries the router's own text.

**Example:** a nested failure the error table does not name, then refusals it does.

```
client:        500, body "internal server error"
server log:    ERROR pdn_node_http::error: unmapped host error: failed to open the identity directory: private storage path /secret/node.db
client:        409, body "identity not hosted on this runtime: <identity in hex>"
client:        403, body "linking refused by the inviter", for a payload refused by closing the connection: the failed read beneath stays out
client:        403, body "linking into the identity", for a refusal wrapped in that context: the outermost message, not the refusal's
```

#### Scenario: Internal cause is not disclosed
- **WHEN** a handler returns nested internal context mapped to HTTP 500
- **THEN** the client receives stable generic text and the server log retains the complete chain

#### Scenario: A refusal carries its outermost message alone
- **WHEN** the runtime returns a refusal the error table maps, with a cause beneath its outermost message
- **THEN** the client receives the refusal's status with the outermost message as its body, and nothing of the cause beneath it

#### Scenario: Oversized entry is refused
- **WHEN** an entry body exceeds 16 MiB
- **THEN** the host returns HTTP 413 without invoking the data service
