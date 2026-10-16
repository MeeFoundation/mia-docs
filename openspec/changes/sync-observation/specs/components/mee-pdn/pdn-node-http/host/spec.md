# HTTP host

## MODIFIED Requirements

### Requirement: Debug requests have aggregate bounds
The host SHALL accept at most 16 concurrent requests under `/debug/` and at most 16 MiB per entry body. `GET /live` and `GET /ready` stay outside that admission, so a burst of debug traffic cannot shed the probes an orchestrator acts on. It SHALL return HTTP 503 when concurrency admission is full and HTTP 413 for an oversized body. HTTP 500 responses SHALL use stable generic public text while retaining the full cause chain only in server logs.

A request's admission SHALL end when its response headers are sent, so a streamed response holds none of the 16. A host built with the observation feature SHALL keep at most 32 event streams open at once and SHALL answer HTTP 503 to a subscription beyond them, without opening it. An observed join SHALL count as an event stream from its request on, and one beyond the bound SHALL be answered HTTP 503 without joining.

**Example:** Alice hosted on the node; `<alice>` is her identity in hex. The last 4 rows are a host built with the observation feature.

| request | what the host does |
|---|---|
| `PUT /debug/data/<alice>/<alice>/contact/email`, 16,777,216-byte body | passes the router to the data service |
| the same `PUT` with 16,777,217 bytes | 413, no handler runs |
| `GET /live` while 16 requests under `/debug/` are in flight | 200: the probes are outside the admission |
| an event stream on one pod, open for the run | 1 of the 32 streams; none of the 16 request permits once its headers are sent |
| a record placed while that stream is open | 1 of the 16 permits, released with its response |
| a 33rd event stream | 503, nothing subscribed |
| an observed join while 32 streams are open | 503, no join and nothing subscribed |

#### Scenario: Overload is shed
- **WHEN** 16 requests are already admitted
- **THEN** an additional request receives HTTP 503 without entering its handler

#### Scenario: Open streams leave the request bound free
- **WHEN** event streams are open on a host built with observation
- **THEN** 16 further requests are still admitted at once

#### Scenario: A stream beyond the bound is refused
- **WHEN** 32 event streams are open
- **THEN** a further subscription receives HTTP 503 and opens no subscription

### Requirement: The debug surface is absent by default
Debug endpoints are demo scaffolding, not platform API. The host SHALL NOT serve any route under `/debug/` unless `PDN_DEBUG` is set to `1` or `true` at startup; unset, `0` and `false` leave the surface absent. Any other value — `TRUE`, `yes`, `1` with a leading space, the empty string — SHALL stop the start with an error naming the accepted values, serving neither liveness nor the debug surface: a mistyped flag read as off would look, from outside, like a renamed route. When enabled, route names, paths, and payload shapes are deliberately unspecified and may change without a spec change; the properties required of the surface as a whole are the requirements below.

**Example:** `PDN_DEBUG` at start, and what `GET /debug/status` answers.

| `PDN_DEBUG` at start | what `GET /debug/status` answers |
|---|---|
| unset, `0` or `false` | 404, as for a route the host never had |
| `1` or `true` | 200, `"node <node id>"`, then `"profile release"` or `"profile debug"`, then `"observation on"` or `"observation off"`, then a `"hosts <identity>"` line per hosted identity |
| `yes`, `TRUE` or empty | nothing: the host exits with `PDN_DEBUG must be one of 1, true, 0, false, or unset — got "yes"` |

#### Scenario: Debug routes off without the flag
- **WHEN** the host starts without `PDN_DEBUG` set
- **THEN** requests under `/debug/` return HTTP 404

#### Scenario: An unrecognized flag value stops the start
- **WHEN** the host starts with `PDN_DEBUG` set to a value other than `1`, `true`, `0` or `false`
- **THEN** the process exits with an error naming the accepted values, serving neither liveness nor the debug surface

### Requirement: The surface offers no path the runtime's own callers lack
The surface SHALL NOT expose namespace ticket handover, forced reconciliation, state reset, or direct store access, and SHALL NOT return a namespace ticket when reading a grant.

A host built with the observation feature SHALL add exactly 3 observation routes, each delegating to one of the runtime's test-only observation calls: a subscription to one hosted identity's stores of one pod, the observed join of one hosted identity on an invite, and the record listing of that identity's record store ([observation](../../pdn-node/observation/spec.md)), with its payloads unless the request asks for none. The observed join takes the invite the product's join route takes and runs the product's join dialogue. None of the 3 forces a reconciliation, hands over or accepts a namespace ticket, resets state, or reaches a store other than through its call.

**Example:** what waiting for a record placed elsewhere can use.

| build | wait mechanisms |
|---|---|
| without observation | repeating the read |
| with observation | repeating the read, or watching the event subscription; neither starts a session the node would not start |

#### Scenario: A granted namespace arrives with no ticket crossing the surface
- **WHEN** a connected peer publishes a grant and the grantee reads the entry over HTTP
- **THEN** the entry eventually reads back without any route handing over or accepting a namespace ticket

#### Scenario: Convergence is waited for, not forced
- **WHEN** a caller waits for a value written on another node
- **THEN** repeating the read, and in a build with observation watching the event subscription, are the only wait mechanisms available, and no route starts a session

## ADDED Requirements

### Requirement: Observation routes exist only in an observation build with the debug surface on
The host SHALL serve the observation routes only when it was built with its observation feature and started with the debug surface enabled. A host built without the feature SHALL NOT contain them, and the feature SHALL be off in the default build. The event route SHALL answer one record per line, each written as the runtime yields it, over one response that stays open until the runtime stops or the host receives its stop signal; a store's `closed` record does not end it. The observed join route SHALL answer once the runtime's observed join has answered: a join refused or failed before its import answers as the product's join route answers it, and a join that imported the pod answers HTTP 200 with the pod id in a response header and a body that is the event route's for that subscription, record for record and line for line. The listing route SHALL answer the record listing as one JSON document.

**Example:**

| build | `PDN_DEBUG` | observation routes |
|---|---|---|
| default | `1` | absent: HTTP 404 |
| `observation` | unset | absent: HTTP 404, as the whole debug surface |
| `observation` | `1` | served |

#### Scenario: A default build has no observation routes
- **WHEN** a host built without the observation feature starts with the debug surface enabled
- **THEN** requests to the observation routes return HTTP 404, and the other debug routes answer

#### Scenario: An observation build without the debug flag has no observation routes
- **WHEN** a host built with the observation feature starts without `PDN_DEBUG`
- **THEN** requests to the observation routes return HTTP 404

#### Scenario: A record crossing is observed on both sides
- **WHEN** 2 hosts built with observation are members of one pod, each with its event route open, and the first places a record
- **THEN** the first's route yields an `insert_local` of the record, the second's yields an `insert_remote` of it from the first's node with the same entry timestamp and, after it, a record-store `sync_finished` whose session id and counts match a `sync_finished` on the first's route

#### Scenario: An observed join streams the joiner's catch-up from its first insert
- **WHEN** a host built with observation joins, through the observed join route, a pod whose members hold records
- **THEN** the response names the pod, and its lines hold an `insert_remote` of every record the pod held, each before the record-store `sync_finished` of the session that carried it, counting from `seq` 0 with no gap

#### Scenario: A refused observed join streams nothing
- **WHEN** a host built with observation asks the observed join route to join on an invite already consumed
- **THEN** it answers the refusal the product's join route answers, opens no stream, and holds none of the 32

#### Scenario: A removed member's host observes its record stream close
- **WHEN** a third host built with observation, a member of that pod, is removed by an owner and folds the removal
- **THEN** its event route yields `closed` for the record store and stays open, and no `insert_remote` of a record placed after that reaches it

#### Scenario: A stop signal ends open streams
- **WHEN** the host receives its stop signal while event streams are open
- **THEN** the streams end, and the host's graceful drain is not held up by them

### Requirement: The host reads its pod interval from the environment
The host SHALL read `PDN_POD_RECONCILE_INTERVAL_SECS` at startup and bring the runtime up with that many seconds as the interval of its pass over each pod store. Unset, the runtime's default SHALL apply. A value that is not a positive whole number SHALL stop the start with an error naming the variable, before the runtime is spawned.

**Example:**

| `PDN_POD_RECONCILE_INTERVAL_SECS` | outcome |
|---|---|
| unset | the runtime's default of 300 seconds |
| `30` | a pass over each pod store every 30 seconds |
| `0`, `-5`, `30s` or empty | the process exits naming the variable, serving nothing |

#### Scenario: A configured interval is the node's
- **WHEN** the host starts with `PDN_POD_RECONCILE_INTERVAL_SECS=30`
- **THEN** the runtime's pass over each pod store runs every 30 seconds instead of every 300

#### Scenario: An invalid interval stops the start
- **WHEN** the host starts with `PDN_POD_RECONCILE_INTERVAL_SECS=0`
- **THEN** the process exits with an error naming the variable, serving neither liveness nor the debug surface

### Requirement: An observation build is a release build, and the host says which build it is
The host built with the observation feature SHALL compile in the release profile, and the workspace's checks SHALL compile it there. The status route SHALL state the build profile — `release` when debug assertions are compiled out, `debug` otherwise — and whether the observation feature is compiled in, so a caller can refuse to measure a build it did not mean to.

**Example:**

| built with | status lines after the node line |
|---|---|
| `cargo build --release -p pdn-node-http --features observation` | `profile release`, `observation on` |
| `cargo build -p pdn-node-http --features observation` | `profile debug`, `observation on` |
| the stand's image | `profile release`, `observation off` |

#### Scenario: A release observation build reports itself
- **WHEN** the host built in the release profile with the observation feature starts with the debug surface enabled
- **THEN** its status states `profile release` and `observation on`

#### Scenario: A debug build reports itself as one
- **WHEN** the host built in the debug profile starts with the debug surface enabled
- **THEN** its status states `profile debug`
