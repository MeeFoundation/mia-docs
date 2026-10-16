## REMOVED Requirements

### Requirement: The debug surface covers the embedded runtime's operations

**Reason**: Two of its scenarios run on connection establishment, grants and the entry routes, which this change removes; the requirement returns as "The debug surface covers identities, linking and pods".

**Migration**: None: the pods routes carry the same properties.

### Requirement: The surface offers no path the runtime's own callers lack

**Reason**: Its first scenario is a grant's namespace arriving without a ticket, and grants are removed by this change; the requirement returns as "The surface hands over no store ticket".

**Migration**: None: the pods routes carry the same properties.

### Requirement: A refused operation is reported as a refusal

**Reason**: Two of its scenarios are an entry absent under an issuer and a write outside a grant's write set, both removed by this change; the requirement returns as "A refusal is reported as a refusal", over the pods routes.

**Migration**: None: the pods routes carry the same properties.

## MODIFIED Requirements

### Requirement: The container scenario runs on the product path
Every route SHALL act on its own host's embedded runtime. Hosts SHALL NOT address each other over HTTP; linking, a pod's join, reconciliation, and gossip SHALL use the runtime's iroh protocols.

**Example:** what passes between 2 hosts, by the ALPN (protocol name) each connection opens under.

| traffic | ALPN |
|---|---|
| linking | `/pdn/linking/0` |
| a pod's join | `/pdn/pod-join/0` |
| reconciliation | `/iroh-sync/1` |
| gossip | `/iroh-gossip/1` |
| record payloads | `/iroh-bytes/4` |
| HTTP | nothing: no route addresses another host, and the host carries no HTTP client |

#### Scenario: Nodes exchange no HTTP
- **WHEN** a caller drives 2 hosts through a pod's join and replication
- **THEN** HTTP remains the external control plane and all inter-node traffic uses runtime protocols

### Requirement: Internal failures stay server-side
The host SHALL log the full internal cause chain for an unrecognized failure and SHALL return `internal server error` for HTTP 500. A client error for a runtime error the host's error table maps SHALL carry the outermost message of that error as the runtime returns it, and SHALL NOT carry the causes beneath it: where the runtime raises a refusal over a lower failure — a refused linking or join arrives as the connection closing under a read — the refusal is that outermost message and the read failure stays out, while a refusal the runtime wrapped in further context would keep the refusal's status and carry that context's text. A client error the host raises itself names what was absent or malformed, the parser's complaint included; a rejection by the router itself — a query it cannot decode, a body past the ceiling — carries the router's own text.

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
- **WHEN** a record body exceeds 16 MiB
- **THEN** the host returns HTTP 413 without invoking the pods service

### Requirement: Readiness is bounded separately
The host SHALL expose `GET /ready` as a bounded check of the runtime: its coarse state lock answers within the budget, its replica store answers a read, and its blob store answers a lookup. The two stores are the half that can say no after a full filesystem, each on its own: a placement into a pod fails at the blob store first, whose metadata actor then stops and fails every later payload read while the replica store still answers, and a commit the replica store meets on the full disk fails the replica store. Either refuses every operation until the process restarts, while the in-memory bookkeeping stays intact, so a readiness drawn from the bookkeeping alone, or from one store alone, would keep reporting a node that serves nothing. `GET /live` SHALL NOT wait for any of them.

**Example:** Alice hosted on a node whose 16 MiB state directory filled with the claims she placed, asked once the blob store has failed.

| request | answer |
|---|---|
| `GET /debug/identities` | 200, lists Alice: the in-memory bookkeeping is intact |
| `GET /ready` | `500 "internal server error"`: the blob store refuses its lookup |
| `GET /live` | `200 "ok"` |

#### Scenario: Lock contention affects readiness only
- **WHEN** the coarse state lock remains held beyond 2 seconds
- **THEN** `/live` returns HTTP 200 and `/ready` returns non-success within its budget

#### Scenario: A store that stopped answering fails readiness
- **WHEN** the replica store or the blob store refuses its operations after the state directory filled
- **THEN** `/ready` returns non-success while `/live` returns HTTP 200

## ADDED Requirements

### Requirement: The debug surface covers identities, linking and pods
When enabled, the debug surface SHALL make identity creation and linking, [pods](../../../../architecture/language/pod.md), node status, and hosted identities reachable over HTTP. A pods operation SHALL name the identity performing it as well as the pod, so a caller reaches exactly what that identity holds. Each route SHALL delegate to a runtime service call and add no orchestration of its own. The pods routes SHALL cover every operation of the pods service, one route each: creating and listing pods and listing a pod's members; inviting and joining; the membership acts; placing records, appending operations, reading and listing records; and listing the entries outside the key layout.

**Example:** two requests to the host on Alice's tablet a3, which hosts Alice-leisure, a member of the pod `ad58a3faa04cdc5576c8dc5823a347c6`, and Alice-work, no member; `<alice-leisure>`, `<alice-work>`: 64 lowercase hex chars of each `PdnId`.

| request | answer |
|---|---|
| `GET /debug/identities/<alice-leisure>/pods/ad58a3faa04cdc5576c8dc5823a347c6/records` | the records Alice-leisure's replica holds, from one `list_records` call |
| `GET /debug/identities/<alice-work>/pods/ad58a3faa04cdc5576c8dc5823a347c6/records` | 409: Alice-work is no member, whoever else the tablet hosts |

#### Scenario: A device joins over HTTP
- **WHEN** a linking payload is minted on 1 host and consumed on a second
- **THEN** the second host reports the identity as hosted and reads a record the identity placed before the link

#### Scenario: A read as a co-located identity that is no member is refused
- **WHEN** a host hosting two identities is asked, over HTTP, to read a pod one identity is a member of, naming the other identity
- **THEN** the response is a client error and no record is returned

#### Scenario: A pod scenario runs over HTTP alone
- **WHEN** 3 hosts are driven only over HTTP through creating a pod, two invitations, a record placed by one member and an operation appended to it by another
- **THEN** every member reads the record and the operation without an in-process call into any runtime

### Requirement: The surface hands over no store ticket
The surface SHALL NOT expose a store ticket handover, forced reconciliation, state reset, or direct store access: a pod invite carries a one-time secret and no ticket, and every store a node holds arrives through the runtime's own ceremonies.

#### Scenario: A joined pod arrives with no ticket crossing the surface
- **WHEN** a member mints a pod invite and a newcomer joins with it over HTTP
- **THEN** the newcomer reads the pod's records without any route handing over or accepting a store ticket

#### Scenario: Convergence is waited for, not forced
- **WHEN** a caller waits for a value written on another node
- **THEN** repeating the read is the only available wait mechanism

### Requirement: A refusal is reported as a refusal
The host SHALL report a runtime refusal with its allow-listed client-error status and SHALL NOT report it as success. A refusal SHALL remain distinguishable from an absent route and an internal or transport failure.

**Example:** pods requests on Alice's tablet a3, which hosts Alice-leisure, the owner of `ad58a3faa04cdc5576c8dc5823a347c6`, and Alice-work, a plain member of `f942dfc21acd0218d48f61f714ddfff3` and no member of `ad58a3faa04cdc5576c8dc5823a347c6`; `<alice-leisure>`, `<alice-work>`, `<bob>`: 64 lowercase hex chars of each `PdnId`; `<absent>`: an id the pod does not hold.

| request | answer |
|---|---|
| `POST /debug/identities/<alice-work>/pods/f942dfc21acd0218d48f61f714ddfff3/acts`, `Remove(<bob>)` | 403; Bob stays a member |
| `GET /debug/identities/<alice-work>/pods/ad58a3faa04cdc5576c8dc5823a347c6/members` | 409 |
| `GET /debug/identities/<alice-leisure>/pods/ad58a3faa04cdc5576c8dc5823a347c6/records/<bob>/claim/<absent>` | 404 |

#### Scenario: An unhosted identity is refused, not absent
- **WHEN** a request addresses an identity the runtime does not host
- **THEN** the response is a client error other than 404

#### Scenario: A burnt invite secret is refused
- **WHEN** a consumed pod invite payload is presented again
- **THEN** the response is a client error and no second joined event is written

#### Scenario: A pod the identity is no member of is refused, not absent
- **WHEN** a request addresses a pod the identity is no member of
- **THEN** the response is a client error other than 404

#### Scenario: A refusal by role is reported as a refusal
- **WHEN** a plain member removes another member of the pod
- **THEN** the response is a client error and every member still lists the other member

#### Scenario: An absent record is reported as absent
- **WHEN** a member reads a record the pod does not hold
- **THEN** the response is HTTP 404
