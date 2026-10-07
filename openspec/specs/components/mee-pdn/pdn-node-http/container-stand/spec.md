# Container stand

## Purpose

The out-of-process stand the demos run on: every node is the [HTTP host](../host/spec.md) binary in its own container, driven from the test host over HTTP alone while the nodes reach each other over the [runtime core](../../pdn-node/core/spec.md)'s own protocols. It exists to prove what an in-process suite cannot — that a node packaged as a binary comes up, that the address it publishes in a ceremony payload is one a peer on another container dials, and that a device which goes away takes its process with it.

## Requirements

### Requirement: The stand runs each node as its own process in its own container
The stand SHALL run every node as a separate process in a separate container, all attached to one container network per scenario. No scenario SHALL place two nodes in one process.

**Example:** what `the_whole_scenario_runs_across_containers` creates; `<pid>` is its test process's id.

| kind | name | runs |
|---|---|---|
| network | `pdn-stand-<pid>-0` | |
| container | `pdn-stand-<pid>-0-inviter` | one `pdn-node-http` process |
| container | `pdn-stand-<pid>-0-scanner` | one `pdn-node-http` process |
| container | `pdn-stand-<pid>-0-outsider` | one `pdn-node-http` process |
| test ends | the containers are removed, and the network with the last of them, passed or failed | |

#### Scenario: Nodes are separate processes
- **WHEN** a scenario spawns 3 nodes
- **THEN** each runs in its own container, and stopping one leaves the others running

#### Scenario: A scenario's network is its own
- **WHEN** a scenario ends, whether it passes or fails
- **THEN** its network is removed and its containers are gone

### Requirement: The image serves the host binary and nothing else
The image SHALL contain the HTTP host binary, run it as a non-root user, and listen for HTTP on all interfaces. It SHALL leave the runtime's endpoint bind unconfigured, so the endpoint binds every interface and publishes the container's own address, and SHALL leave the runtime's reachability at its default of direct paths only, so the address it publishes is a direct one, no relay stands between two containers, and a peer that reaches it reached it directly. It SHALL name the directory the runtime stores its state in, writable by the user the binary runs as, and SHALL declare no volume of its own — what is mounted over that directory is the caller's decision, so an image-declared volume is never created behind a caller's back.

**Example:** the image `pdn-node-http:dev`, as `ops/Dockerfile` builds it.

| aspect | as the image sets it |
|---|---|
| entrypoint | `/usr/local/bin/pdn-node-http`, run as the non-root user `pdn` |
| HTTP | `PDN_HOST=0.0.0.0`, `PDN_PORT=3011`: every interface of the container |
| endpoint | `PDN_BIND_ADDR` unset: every interface, the container's own address published, relays off |
| state | `PDN_DATA_DIR=/var/lib/pdn`, owned by `pdn`, mode 700, no `VOLUME` over it |
| debug | `PDN_DEBUG` unset: `/debug/` absent until the caller passes `PDN_DEBUG=1` |

#### Scenario: A container answers liveness
- **WHEN** a container starts from the image
- **THEN** `GET /live` answers 200 on the published port

#### Scenario: A peer dials the address a payload carries
- **WHEN** a node on one container consumes an invite payload minted on another
- **THEN** the dial reaches the minting node over the container network, with no relay and no discovery configured

#### Scenario: The debug surface follows its flag inside the image too
- **WHEN** a container starts without the debug flag set
- **THEN** requests under `/debug/` return 404 and `GET /live` still answers 200

#### Scenario: The state directory is writable by the running user
- **WHEN** a container starts from the image with nothing mounted over its state directory
- **THEN** the runtime provisions that directory and serves, without running as a privileged user

### Requirement: HTTP is the control plane from the test host and travels nowhere else
Each container's HTTP port SHALL be published to the test host, and the runtime's endpoint port SHALL NOT be. A scenario SHALL address every container itself and SHALL NOT give one container another's URL, so establishment, linking, reconciliation, and gossip run over the runtime's own protocols.

**Example:** each hop of a stand scenario, and what crosses it.

| hop | over | in the stand |
|---|---|---|
| test host → container port 3011 | HTTP, on a host port the daemon picks | every request of a scenario |
| test host → container endpoint | nothing | the endpoint port is never published |
| `inviter` → test host → `scanner` | the invite payload | body of `POST …/invite`'s response, then of `POST …/establish` |
| container → container | the runtime's protocols | establishment, linking, reconciliation, gossip |
| container → container | HTTP | never: no container is handed another's URL |

#### Scenario: A ceremony payload travels through the caller
- **WHEN** an invite payload minted on one container is consumed on another
- **THEN** the payload passes through the scenario, and neither container issues an HTTP request

#### Scenario: Replication crosses no HTTP
- **WHEN** a grantee converges on an entry written on another container
- **THEN** the only HTTP requests are the scenario's own, and the entry arrives over the runtime's protocols

### Requirement: The stand runs the whole scenario with its paired denials
The stand SHALL run, across containers, identity creation, connection establishment, a scoped grant, a write, the grantee's read, and the grant's withdrawal. In the same scenario it SHALL assert the tightest denials: a container with no connection and no grant is refused, and the claims the grant withholds are absent from the grantee's view after a second replication wave is shown to have happened.

**Example:** Alice (issuer) on node `inviter`, Bob on `scanner`, Carol (outsider) on `outsider`.

| step | action | outcome |
|---|---|---|
| 1 | Alice writes `contact/email` "alice@example.org" and `notes/diary` "dear diary" | |
| 2 | Alice grants Bob read on `contact/email` | Bob's repeated read ends at `200 "alice@example.org"` |
| 3 | Carol reads `contact/email` under Alice | 409, no entry |
| 4 | Alice writes `contact/email` "alice@new.example.org" | Bob reads it: a second wave has run |
| 5 | Bob lists Alice's entries | `contact/email` alone; `notes/diary` reads 404 |
| 6 | Alice withdraws the grant | Bob's read turns 409; Alice still reads her entry |

#### Scenario: A grantee reads what the grant names
- **WHEN** a scoped grant is published toward a connected peer and an entry inside it is written
- **THEN** the peer's container reads that entry by repeating the read

#### Scenario: An outsider is refused
- **WHEN** a third container with no connection and no grant reads the same entry
- **THEN** the response is a client error and no entry is returned

#### Scenario: Withheld claims stay withheld
- **WHEN** the issuer writes a claim outside the grant and a later entry inside it arrives at the grantee
- **THEN** the withheld claim is absent from the grantee's view

#### Scenario: Withdrawal closes the access it opened
- **WHEN** the grant is withdrawn
- **THEN** the peer's container stops reading the granted namespace

### Requirement: The stand runs device linking across containers
The stand SHALL bring a second container into an existing identity through the linking ceremony and SHALL show the joined device reading an entry written before it joined.

**Example:** Alice (issuer) on node `first`; nodes `second` and `bystander`; `<alice>` is her identity in hex.

| step | action | outcome |
|---|---|---|
| 1 | `first`: Alice writes `contact/email` "written before the link" | |
| 2 | `first`: `POST /debug/identities/<alice>/linking-invite` | answers the linking payload |
| 3 | `second`: `POST /debug/link?timeout_secs=60` with it | 204; `GET /debug/identities` lists Alice |
| 4 | `second`: reads `contact/email` under Alice | "written before the link" |
| 5 | `bystander`: `POST /debug/link` with the same payload | 403, and it hosts nothing |

#### Scenario: A device joins and catches up
- **WHEN** a linking payload minted on the first container is consumed on a second
- **THEN** the second container reports the identity as hosted and reads an entry written before the link

### Requirement: A stopped device does not stop the connection
The stand SHALL show a granted peer still converging after the device that published the grant is stopped, with a sibling device of the same identity serving the namespace.

**Example:** Alice on nodes `alice-publisher` and `alice-sibling`, Bob (read grant on `contact/email`) on `audience`.

```
1  alice-sibling joins Alice by linking; alice-publisher establishes with Bob and publishes the grant
2  Bob reads "published from the first device"; alice-sibling reads it and holds the grant record
3  alice-publisher is stopped, and the daemon reports it not running
4  alice-sibling writes "served by the sibling"
5  Bob reads "served by the sibling", from a device whose address he was never given
6  Carol (outsider) on outsider still gets 409
```

#### Scenario: The publishing device is stopped
- **WHEN** an identity on 2 containers publishes a grant from the first, and that container is stopped
- **THEN** the peer converges on an entry written by the surviving container

### Requirement: Convergence is waited for at the runtime's own cadence
A scenario SHALL wait for convergence by repeating a read, bounded by a budget above the runtime's periodic reconciliation interval. No route, environment variable, or harness call SHALL force a reconciliation or shorten the runtime's cadence.

**Example:** Bob waits to read `contact/email` under Alice; `<alice>` and `<bob>` are their identities in hex.

| part | what it does |
|---|---|
| the runtime reconciles | every 10 s, its default, which nothing on the stand shortens |
| the scenario reads | every 100 ms: 409 until the namespace is bound, 404 until the entry arrives, then 200 |
| its budget | 2 min, 12 reconciliation intervals |
| on expiry | `"contact/email under <alice> never read back as expected for <bob>"`, the last answer, the node's log tail |

#### Scenario: A wait ends when the value arrives
- **WHEN** a scenario waits for a value written on another container
- **THEN** it repeats the read until the value appears or its budget expires, and a failed wait names what it waited for

### Requirement: The stand is where the HTTP surface is tested
Every test that drives the HTTP surface of a running node — a request through the host's router to a runtime behind it — SHALL run against nodes on the stand. A property that cannot be reached from outside a node's process — one that holds the runtime's own state lock — MAY be tested in the test's own process, and SHALL build its runtime itself rather than through the stand's harness. A unit test of one of the host's own functions — the error table, the request parsers, the configuration read from the environment, the admission function on a router of its own, the runtime budget on a future that never resolves — MAY run in the test process too, since it starts no runtime and drives no node's surface.

**Example:** the host's test files, what each asserts, and what it runs against.

| test file | asserts | against |
|---|---|---|
| `tests/stand.rs` | the scenarios across nodes | nodes started from the image |
| `tests/stand_denials.rs` | the refusals, beside what they deny | nodes started from the image |
| `tests/stand_restart.rs` | stop, kill, and a full state directory | nodes started from the image |
| `tests/stand_surface.rs` | the debug gate, its routes, the body ceiling | nodes started from the image |
| `tests/readiness.rs` | `/live` 200 and `/ready` 500, the lock held | a runtime it spawns in its own process |
| `tests/admission.rs` | 1 of 17 requests shed with 503, the lock held | a runtime it spawns in its own process |
| `src/lib.rs`, unit tests | admission sheds with 503; the budget ends in 500 | the function alone, with no runtime |
| `src/error.rs`, `parse.rs`, … | the status each error maps to; 400 when malformed | the function alone, with no runtime |

#### Scenario: A surface property is asserted against the image
- **WHEN** the debug gate, the routes it gates, or the body ceiling is asserted
- **THEN** the assertion runs against a node started from the image

#### Scenario: The runtime's own behaviour is not re-proven here
- **WHEN** a scenario asserts establishment, a grant, replication or linking
- **THEN** it runs on the stand, and the runtime's own suite proves the same behaviour without HTTP

#### Scenario: A function of the host is tested alone
- **WHEN** a test asserts the error table, a request parser, the configuration read from the environment, the admission function, or the runtime budget by itself
- **THEN** it runs in the test process and starts no runtime

### Requirement: The suite states what it needs and stays out of the default run
The suite SHALL NOT run as part of the workspace's default test run, nor be selected by the flaky hunt's default selection. It SHALL be reachable through a recipe that builds the image first, SHALL run in the pipeline on every proposed change, and its parallelism SHALL be bounded to what the container daemon can start at once. Its tests SHALL state that they need a daemon and a built image.

**Example:** each stand test: `#[ignore = "needs a container daemon and the pdn-node-http:dev image (just test-docker)"]`.

| command | what runs |
|---|---|
| `just test` | skipped, no image built |
| `just stress` | skipped: its default selection, `-E 'kind(test)'`, runs no ignored test |
| `just test-docker` | `just build-image`, then nextest with `-E 'binary(~stand)' --run-ignored all`; a daemon reporting 8 CPUs: `--profile cap-8`, at most 8 stand tests at once |
| the pipeline's stand job | on every pull request: the image built, then the same nextest run |

#### Scenario: A machine without a daemon still passes
- **WHEN** the default test run or the flaky hunt runs with no selection given
- **THEN** none of the stand's tests run, no image is built, and they are reported skipped

#### Scenario: The recipe builds before it runs
- **WHEN** the container-suite recipe runs
- **THEN** it builds the image and then runs the suite against it

#### Scenario: The pipeline runs the suite
- **WHEN** a change is proposed
- **THEN** the pipeline builds the image and runs the suite against it

### Requirement: The image carries the workspace as it resolves
The image SHALL be built from the workspace alone — its manifests, its lock file, and its crates, the store among them — and no input outside version control SHALL reach the build: a cargo configuration file beside the workspace is not carried, and no stage of the build reaches for a checkout beside it.

**Example:** the build context, as `.dockerignore` lets it through (`just check-context` lists it).

| path | in the build context |
|---|---|
| `Cargo.toml`, `Cargo.lock`, `crates/` | carried, `crates/pdn-store` among them |
| `target/`, `.git`, `.env`, `CLAUDE*.md` | left out, at any depth |
| `.cargo/config.toml` | left out: whatever the file does not name is excluded |
| `rust-toolchain.toml` | left out: the base image `rust:1.98-bookworm` picks the compiler |
| `mia-docs/`, `ops/`, `scripts/` | left out |

#### Scenario: A store edit reaches the image
- **WHEN** a source file under `crates/pdn-store` is edited and the image is rebuilt
- **THEN** the containers run that edit, and no step of the build refuses the resolution or reaches outside the build context

#### Scenario: A cargo configuration beside the workspace stays out
- **WHEN** a `.cargo/config.toml` exists beside the workspace and the build context is listed
- **THEN** the listing carries no `.cargo` entry

### Requirement: The live demos run on the stand's image
Each demo — the connections demo and the pods demo — SHALL run the same image the suite runs, with every node on one container network and each node's HTTP port published on loopback of the demo host. Each node SHALL have a volume of its own for its state. A demo SHALL remove its nodes, its network and those volumes on every exit, the failing one included, and it SHALL drive the nodes over HTTP alone, so what passes between nodes is the runtimes' own traffic.

**Example:** `just demo-connections` and `just demo-pods`, each with a compose file and a project of its own, every node on network `demo` with `PDN_DEBUG=1`.

```
just demo-connections    ops/compose-connections.yml, project pdn-demo-connections, 7 nodes
  alice-phone      127.0.0.1:3011 → 3011    volume alice-phone-state over /var/lib/pdn
  …
  bob-laptop       127.0.0.1:3015 → 3011    volume bob-laptop-state; stopped and started mid-show, same node id
  …
  carol-laptop     127.0.0.1:3017 → 3011    volume carol-laptop-state
just demo-pods           ops/compose-pods.yml, project pdn-demo-pods, 6 nodes
  alice-phone      127.0.0.1:3021 → 3011    volume alice-phone-state; stopped and started mid-show with alice-laptop, same node id
  …
  dave-phone       127.0.0.1:3026 → 3011    volume dave-phone-state
on every exit            docker compose -f ops/compose-<demo>.yml down --remove-orphans --volumes
```

#### Scenario: A demo brings up the nodes it names
- **WHEN** a demo recipe runs
- **THEN** it builds the image, brings up every node its compose file names, and waits for each of them to answer liveness before the first step

#### Scenario: A run never meets the previous run's state
- **WHEN** a demo exits, whether it finishes or fails
- **THEN** its containers, its network and its volumes are removed

#### Scenario: A demo publishes on loopback
- **WHEN** a node of a demo publishes its HTTP port
- **THEN** the port is bound to loopback, because the debug surface is unauthenticated and mints live ceremony secrets

#### Scenario: The connections show survives a node restarting
- **WHEN** the connections demo stops one node mid-show and starts it again
- **THEN** that node comes back as the same node, its connection still stands, and nothing is established a second time

#### Scenario: The pods show carries on without its creator's devices
- **WHEN** the pods demo stops every device of the pod's creator mid-show and starts them again later
- **THEN** while they are down a newcomer joins on another member's invite and reads what was placed before, and an edit reaches every online member device; started again, they come back as the same nodes and read what happened without them; and an owner's removal stops what reaches the removed member

### Requirement: The stand restarts a node and asserts what came back
The stand SHALL stop a node's container and start it again with its state directory intact, and SHALL assert that the node came back as itself: the same node id, the identity still hosted, the connection still listed, and an entry written before the stop still readable; a write made on it after the restart reaching its peer with no ceremony repeated; and the grant still readable on the peer's node. The stand SHALL also kill a node's container — no grace, no shutdown path — and start it again, asserting the same recovery, because a process that ends without warning is the ordinary end of a process, and recovery that differs by the manner of stopping depends on a goodbye a kill does not provide. One kill SHALL land in the middle of a stream of writes: every write acknowledged before the stores' settle window — the bounded delay after which an acknowledged write has committed, since the replica store and the blob store each commit after the acknowledgement, on a timer — SHALL be readable after the restart, and a write the kill cut inside that window, acknowledged or not, SHALL be absent or whole — never a torn value and never a read error. The assertion SHALL be paired, in the same scenario, with the tightest denial: a node started from the same image on an empty state directory holds none of it. Without that arm the scenario passes just as well against a node that quietly re-created everything.

**Example:** a kill mid-stream, the indices as one run cuts them; settle window 2 s (the replica store commits within 500 ms).

| writes | acknowledgement | read back |
|---|---|---|
| `PUT stream/0000 … stream/0041` | acknowledged over 2 s before the kill | after the restart each reads whole, "value-0000" … |
| `PUT stream/0042 … stream/0049` | acknowledged in the last 2 s | each 404, or whole |
| `PUT stream/0050` | cut by the kill, never acknowledged | 404, or whole |
| none of them | a torn value, or a status besides 200 and 404 | |

#### Scenario: A restarted node is the same node
- **WHEN** a node holding an identity, a connection and a grant is stopped and started again on its own state directory
- **THEN** it reports the same node id, hosts the same identity, lists the same connection, and reads an entry written before the stop, and its peer still reads the grant it received

#### Scenario: A killed node comes back the same way
- **WHEN** a node holding an identity, a connection and a grant is killed without grace and started again on its own state directory
- **THEN** it reports the same node id, hosts the same identity, lists the same connection, and reads an entry acknowledged before the stores' settle window, and its peer still reads the grant it received

#### Scenario: A kill mid-stream loses nothing settled
- **WHEN** entries are being written to a node in a stream and its container is killed without grace mid-stream, then started again
- **THEN** every entry whose write was acknowledged before the stores' settle window is readable with its payload, and an entry the kill cut inside that window — acknowledged or not — is either absent or read whole, never partial

#### Scenario: A node on an empty directory holds nothing
- **WHEN** a node is started from the same image on an empty state directory
- **THEN** it reports a node id of its own, hosts no identity, and refuses reads addressed to the identity the restarted node hosts

#### Scenario: A peer converges with the restarted node without a new ceremony
- **WHEN** the restarted node writes an entry after coming back
- **THEN** its counterparty converges on that entry, with no invite minted and no linking performed after the restart

### Requirement: The stand shows a storage failure arriving as a failure
The stand SHALL run one node whose state directory is a filesystem with a bounded size, write until the store refuses, and assert that the refusal reaches the caller as a failed request rather than as a success. A node that reports a write it did not store is the failure mode a full disk produces on a device, and it is invisible on an in-memory node.

**Example:** Alice on a node whose `/var/lib/pdn` is a 16 MiB tmpfs; the refusal's index as one run meets it.

| request | answer |
|---|---|
| `PUT fill/0000 … fill/0040`, 256 KiB each | 204: distinct payloads, since equal bytes are one blob |
| `PUT fill/0041` | an error status: the store refused |
| `GET fill/0041` | anything but 200 with that payload |

#### Scenario: Writing past the bound is refused, not absorbed
- **WHEN** entries are written to a node whose state directory has no free space left
- **THEN** a write fails with an error response, and a read of that path does not report the value as stored

### Requirement: The stand asserts that two identities on one node keep separate audiences

The stand SHALL run two identities on one container as issuers, each connected to a peer of its own on another container and granting that peer read on a claim at the same path, holding a different value under each identity. In the same scenario it SHALL assert that the shared node hosts both identities and lists each one's own peer, and not the other's, among its connections; that each peer reads the value of the identity that granted it; and that neither peer, nor a container with no connection and no grant, reads the other identity's namespace. The refusals SHALL be read on the peers' containers, each hosting one identity; whether one of the two identities reads the other's data on the node they share is not asserted here. Asserting it from outside the process is the point: the property is what the node serves and answers over its surface, not what its internal calls happen to do.

**Example:** two identities of Alice on node `alice`: at work and at leisure; Bob on `bob`, Carol on `carol`, an outsider on `outsider`.

| step | action | outcome |
|---|---|---|
| 1 | at work establishes with Bob, at leisure with Carol | |
| 2 | at work writes `contact/email` "alice@acme.example", at leisure "alice@bridgeclub.example" | |
| 3 | each grants its peer read on `contact/email` | Bob reads "alice@acme.example", Carol "alice@bridgeclub.example" |
| 4 | `alice` lists the connections of each identity | at work: Bob, not Carol; at leisure: Carol, not Bob |
| 5 | Bob reads `contact/email` under at leisure | 409 |
| 6 | Carol reads it under at work | 409 |
| 7 | the outsider reads it under either | 409 |

#### Scenario: Each peer reads what its own identity granted

- **WHEN** two identities on one container each grant their own peer read on a claim at the same path, and each peer reads the identity that granted it
- **THEN** each read returns the value that identity wrote

#### Scenario: The shared node keeps each identity's connection to itself

- **WHEN** the shared node is asked which identities it hosts and whom each one is connected to
- **THEN** it reports both identities, and each identity's connections list its own peer and not the other's

#### Scenario: Neither peer reads the other identity's namespace

- **WHEN** each peer reads the identity that granted the other peer
- **THEN** both reads are refused, and neither returns an entry

#### Scenario: An outsider reads neither

- **WHEN** a container holding no connection and no grant reads both identities' namespaces
- **THEN** both reads are refused

### Requirement: The stand runs a pod across three containers with its paired denials

The stand SHALL run, across three containers, a [pod](../../../../architecture/language/pod.md)'s creation, an invitation by its creator and one by an invited member, a claim and a mergeable-document placed by the creator, and an operation on that document appended by another member; it SHALL promote a member to owner, remove a member through that owner, and restart a member's node. In the same scenario it SHALL assert the tightest denials: a plain member's promotion of itself and its removal of a member are refused while an owner's promotion and removal go through; a consumed invite secret is refused; a removed member stops receiving records after the remaining members are shown to receive a later one; and a pod left before a restart stays left. What a modified node does — a forged entry, an entry outside the key layout — is not reachable over HTTP, and the data layer's own tests hold it.

**Example:** the scenario across containers A, B and C, hosting Alice, Bob and Carol, every step a request over HTTP.

| step | A | B | C |
|---|---|---|---|
| 1 | creates "Family" and invites B | joins and invites C | joins; B's invite presented again is a client error |
| 2 | places a claim and a note | | appends an operation to A's note |
| 3 | | reads the claim and both operations | promotes itself and removes B: two 403s |
| 4 | promotes B: B is an owner on every container | removes C | |
| 5 | places two records, one after the other | reads both | reads neither within the budget |
| 6 | places a record while B's container is stopped | starts again on its state directory, lists the pod and reads the record | |
| 7 | creates a second pod and invites B | joins it, leaves it and restarts: lists no such pod, and requests addressing it are 409 | |

#### Scenario: Any member invites, and the pod reaches all three

- **WHEN** container A creates a pod and invites B, B joins and invites C, and C joins
- **THEN** all three list the same members, and a second join presenting B's consumed invite is refused with a client error

#### Scenario: A record and an edit reach every member

- **WHEN** A places a claim and a mergeable-document, and C appends an operation to A's document
- **THEN** B reads the claim and both A's and C's operations by repeating the read

#### Scenario: A plain member's owner-only acts are refused

- **WHEN** C, no owner, promotes itself and removes B, and A then promotes B
- **THEN** C's two requests are client errors, C stays a plain member and B's membership is unchanged, while B reads as an owner on every container

#### Scenario: A removed member stops receiving

- **WHEN** A promotes B, B removes C, and A places two records one after the other
- **THEN** B reads both, and C reads neither within the budget once B has read the second

#### Scenario: A member's node comes back with its pod

- **WHEN** B's container is stopped, A places a record, and B's container starts again on its state directory
- **THEN** B lists the pod and reads the record placed meanwhile, with no invite minted after the restart

#### Scenario: A pod left before a restart stays left

- **WHEN** B joins a second pod, leaves it, and its container restarts on its state directory
- **THEN** B lists no such pod, and requests addressing it are refused with a client error
