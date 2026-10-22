# HTTP host

## MODIFIED Requirements

### Requirement: Debug requests have aggregate bounds
The host SHALL accept at most 16 concurrent requests under `/debug/` and at most 16 MiB per request body. `GET /live` and `GET /ready` stay outside that admission, so a burst of debug traffic cannot shed the probes an orchestrator acts on. It SHALL return HTTP 503 when concurrency admission is full and HTTP 413 for an oversized body. HTTP 500 responses SHALL use stable generic public text while retaining the full cause chain only in server logs.

A request's admission SHALL end when its response headers are sent, so a streamed response holds none of the 16. A host built with the observation feature SHALL keep at most 32 event streams open at once and SHALL answer HTTP 503 to a subscription beyond them, without opening it. An observed join SHALL count as an event stream from its request on, and one beyond the bound SHALL be answered HTTP 503 without joining.

**Example:** Alice hosted on the node with a pod "Family"; `<alice>` and `<family>` are their ids in hex. The last 4 rows are a host built with the observation feature.

| request | what the host does |
|---|---|
| `POST /debug/identities/<alice>/pods/<family>/records?kind=claim`, 16,777,216-byte body | passes the router to the pods service |
| the same `POST` with 16,777,217 bytes | 413, no handler runs |
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

### Requirement: The surface hands over no store ticket
The surface SHALL NOT expose a store ticket handover, forced reconciliation, state reset, or direct store access: a pod invite carries a one-time secret and no ticket, and every store a node holds arrives through the runtime's own ceremonies.

#### Scenario: A joined pod arrives with no ticket crossing the surface
- **WHEN** a member mints a pod invite and a newcomer joins with it over HTTP
- **THEN** the newcomer reads the pod's records without any route handing over or accepting a store ticket

#### Scenario: Convergence is waited for, not forced
- **WHEN** a caller waits for a value written on another node
- **THEN** repeating the read is the only available wait mechanism, and in a build with observation watching the event subscription is the other; no route starts a session

### Requirement: The host stays off the product path
Product hosts SHALL embed the runtime in-process. The runtime SHALL declare no HTTP server or client of its own, and the host dependency SHALL point toward the runtime only. No crate of a build that ships SHALL depend on the host: the one workspace crate that names it is the mobile facade, through an optional dependency its `observation` feature enables, and no build a device installs enables that feature.

**Example:** what `cargo tree -e normal -i pdn-node-http` prints, inverted on the host.

| built | crates depending on the host |
|---|---|
| the workspace, no feature | the host alone |
| `pdn-mobile` with `observation` | `pdn-mobile`, the facade's test build |

#### Scenario: The runtime serves no HTTP of its own
- **WHEN** the runtime crate is built without the host
- **THEN** it opens no HTTP listener, and no workspace crate of a build that ships depends on the host — only the mobile facade's test build, with its `observation` feature, links it

## ADDED Requirements

### Requirement: The observation routes are the one exception to what the surface lacks
A host built with the observation feature SHALL add exactly 3 observation routes, each delegating to one of the runtime's test-only observation calls: a subscription to one hosted identity's stores of one pod, the observed join of one hosted identity on an invite, and the record listing of that identity's record store ([observation](../../pdn-node/observation/spec.md)), with its payloads unless the request asks for none. The observed join takes the invite the product's join route takes and runs the product's join dialogue. None of the 3 forces a reconciliation, hands over or accepts a store ticket, resets state, or reaches a store other than through its call.

**Example:** what waiting for a record placed elsewhere can use.

| build | wait mechanisms |
|---|---|
| without observation | repeating the read |
| with observation | repeating the read, or watching the event subscription; neither starts a session the node would not start |

#### Scenario: An observation build offers no route the runtime's callers lack
- **WHEN** a host built with observation serves its debug surface
- **THEN** its routes beyond the product's are the 3 observation routes, each answering what the runtime's observation call answers, and none hands over a store ticket, forces a reconciliation or resets state

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
- **THEN** its event route yields `closed` for the record store and stays open, and a record placed after that is absent or refused on its record route while the remaining member reads it

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

### Requirement: The host reads its connectivity from the environment
The host SHALL read `PDN_CONNECTIVITY` at startup, in every build, and bring the runtime up with the connectivity it names: `direct`, direct paths alone, which unset also means; `relays`, direct paths and relays; `product`, relays and address lookup, the connectivity a device's host runs with. Any other value SHALL stop the start with an error naming the accepted values, serving neither liveness nor the debug surface. Every value past `direct` routes through infrastructure this project does not run, and on a relay both ends' node ids are visible to whoever runs it, so a host reaches it only when told to.

**Example:** `PDN_CONNECTIVITY` at start, and what the node dials through.

| `PDN_CONNECTIVITY` at start | the node's connectivity |
|---|---|
| unset or `direct` | direct paths: the container stand, and the sync tests' laptop nodes |
| `relays` | direct paths and relays |
| `product` | relays and address lookup: the pods demo, whose peers are devices that move between networks |
| `relay`, `Direct` or empty | nothing: the host exits with `PDN_CONNECTIVITY must be one of direct, relays, product, or unset — got "relay"` |

#### Scenario: An unset connectivity is direct paths
- **WHEN** the host starts without `PDN_CONNECTIVITY` set
- **THEN** the runtime is brought up on direct paths alone, as with `PDN_CONNECTIVITY=direct`

#### Scenario: An unrecognized connectivity stops the start
- **WHEN** the host starts with `PDN_CONNECTIVITY` set to a value other than `direct`, `relays` or `product`
- **THEN** the process exits with an error naming the accepted values, serving neither liveness nor the debug surface

### Requirement: The debug surface opens to a browser's page of any origin only when asked
The host SHALL read `PDN_ANY_ORIGIN` at startup, in every build, with the closed set `PDN_DEBUG` takes: `1` or `true` turn it on, unset, `0` and `false` leave it off, and any other value SHALL stop the start with an error naming the accepted values. On, and only where the debug surface is served, every answer under `/debug/` SHALL carry the cross-origin headers that let a page of any origin read it — `access-control-allow-origin: *`, the allowed methods and the `content-type` header — and a preflight `OPTIONS` under `/debug/` SHALL be answered HTTP 204 with those headers before any handler. Off, the host SHALL send none of those headers, so a page of another origin in a browser on the machine cannot read what the subtree answers, though it can still send a request a browser sends without a preflight, whose answer it cannot read. Whatever the flag, the host SHALL answer HTTP 421 to a request under `/debug/` whose `Host` header names anything but an IP literal or `localhost`, with or without a port, so a page made same-origin by DNS rebinding is kept out. `GET /live` and `GET /ready` SHALL never carry the headers. The flag exists for the demo's browser screens, which a browser loads from a file and so from no origin; it opens the subtree's live ceremony secrets to every page open in a browser on that machine, and a host that serves the subtree to a browser it does not trust is the demo's to avoid.

**Example:** the pods demo, `PDN_DEBUG=1` and `PDN_ANY_ORIGIN=1` on every node, the nodes published on the demo host's loopback; a page of any site open in a browser on that machine.

| the page does | what it gets |
|---|---|
| `fetch("http://127.0.0.1:3021/debug/identities")` | the answer, readable: the hosted identities, and from them the pods and their live linking and pod invites |
| a `POST` of an act under Alice's pod route, with a JSON body | a preflight answered 204, then the act performed under Alice's name |
| the same with `PDN_ANY_ORIGIN` unset | the `GET`'s answer carries no `access-control-allow-origin`, so the browser withholds it from the page; the `POST` is never sent, its preflight carrying no header the browser accepts |
| `fetch("http://127.0.0.1:3021/live")` with the flag on | no cross-origin header: the probes stay outside |
| `fetch("http://evil.example:3021/debug/status")`, the name rebound to `127.0.0.1` | HTTP 421, whatever the flag |

#### Scenario: The subtree opens to any origin only when asked
- **WHEN** one host starts with `PDN_DEBUG=1` and `PDN_ANY_ORIGIN=1` and another with `PDN_DEBUG=1` alone
- **THEN** every answer under `/debug/` of the first carries `access-control-allow-origin: *` and an `OPTIONS` under `/debug/` is answered HTTP 204, while no answer of the second carries the header, and neither host's `/live` does

#### Scenario: A request naming another host is refused
- **WHEN** a host serving the debug surface is asked for `/debug/status` with `Host: localhost`, and then with `Host: evil.example:3011`
- **THEN** the first is answered and the second is refused HTTP 421

#### Scenario: An unrecognized flag value stops the start
- **WHEN** the host starts with `PDN_ANY_ORIGIN` set to a value other than `1`, `true`, `0` or `false`
- **THEN** the process exits with an error naming the accepted values, serving neither liveness nor the debug surface

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
