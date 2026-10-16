# Mobile host

## ADDED Requirements

### Requirement: A test build serves the laptop host's surface on the phone's loopback, and what ships does not
The facade SHALL have an observation feature, off in every build a device installs, that enables the runtime's test-only feature and exports exactly 2 further calls: one that starts an HTTP server on the facade's runtime, on the node directory and the port it is given, bound to the loopback address and to no other; and one that hands that server a device sample, which the server answers unread. The server SHALL answer the laptop host's debug routes and observation routes ([laptop host](../../pdn-node-http/host/spec.md)) against the node that is up, through the laptop host's own router, so a record it streams is the bytes the laptop host writes for the same event. It SHALL also answer 3 routes of its own: a reset, which stops the node, deletes the node directory, brings a node up on it at a reconcile interval of 10 seconds and at the pod interval and the connectivity the request names, creates one identity, and answers the identity, the node id and the build profile, `release` or `debug`; the device samples it was handed, from a sequence number the request names, a request from a sequence number releasing the samples up to it, so the phone's memory does not carry what was read; and the device's wall clock in microseconds. A reset naming a pod interval of 0 SHALL be refused as malformed before it stops anything, so it changes nothing. The server SHALL outlive a reset, and while no node is up a route that needs one SHALL answer that it is unavailable. The feature SHALL compile in the release configuration a release is built in. Without the feature, the facade SHALL contain neither call nor the server, and remain the surface the requirements above state.

**Example:** the test surface on the phone's `127.0.0.1:3011`, driven through a usbmux tunnel; route names are illustrative, as the laptop host's spec leaves them unpinned.

| request | answer |
|---|---|
| reset, pod interval 300, `direct` | the new identity, the node id, `release` |
| reset, pod interval 0 | refused as malformed; the node up before it, or none, stays so |
| the observed join route, on an invite code | the pod id in a header, then a line per record from `seq` 0, as the laptop host streams it |
| the event route of a pod the identity holds no store of | refused through the laptop host's error table |
| the samples route, after sample 41 | the samples from 42 on |
| any node route between a reset's stop and its bring-up | unavailable |

#### Scenario: The test surface yields the runtime's records
- **WHEN** 2 nodes, each a handle of a facade built with observation serving its test surface, are members of one pod, one places a record, and the other's event route is open
- **THEN** that stream yields an `insert_remote` line for the record's key naming the record store, the line parses as the record the runtime's JSON form defines, and the other's listing route holds the record `counted` with its payload

#### Scenario: An observed join through the surface yields the joiner's first session
- **WHEN** a node behind its test surface joins, through the observed join route, a pod in which another node placed a record
- **THEN** the response names the pod and yields, from `seq` 0, an `insert_remote` line for that record before the record-store `sync_finished` line of the session that carried it

#### Scenario: A non-member and a consumed invite are refused
- **WHEN** the test surface of a node whose identity is a member of no pod is asked for that pod's event stream and its listing, and for an observed join on an invite code already consumed
- **THEN** each request is refused through the laptop host's error table, no stream opens and no pod is joined

#### Scenario: The surface answers on the loopback address alone
- **WHEN** the test surface is started on a port and a connection to that port is made at the device's local network address, and another at the loopback address
- **THEN** the first is refused and the second is answered

#### Scenario: A reset starts from an empty directory, and a pod interval of 0 is refused
- **WHEN** a reset naming a pod interval of 0 is made before any node is up, and later a reset follows a run in which the node created a pod
- **THEN** the first is refused as malformed and no node is up after it; the second brings up a node reporting a node id and an identity it did not report before, holding no pod

#### Scenario: What ships has no test surface
- **WHEN** the artifacts a device installs are built
- **THEN** the facade is compiled without its observation feature, and its exported surface names neither call

### Requirement: The facade names its runtime's threads
The facade SHALL name every thread of its asynchronous runtime, worker and blocking alike, with the fixed prefix `pdn-node`, in every build, so a sampler in the same process can tell the node's threads from the application's. The name SHALL change nothing else the facade does.

**Example:** the threads of the application's process during a catch-up, as a sampler lists them.

| thread name | whose work |
|---|---|
| `pdn-node` (several) | the facade's runtime: sessions, the node's tasks, the observation's numbering, and in the test build the test surface's server |
| `sync-actor` (one per hosted identity) | the store's actor |
| the JavaScript thread, the main thread, others | the application: its screens, the agent and its sampler |

#### Scenario: The node's threads carry the prefix
- **WHEN** a node is brought up through the facade, in a test build or in what ships
- **THEN** every thread its asynchronous runtime starts is named with the prefix `pdn-node`
