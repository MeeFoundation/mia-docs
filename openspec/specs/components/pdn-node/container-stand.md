# Container stand

## Purpose

The out-of-process stand the demo runs on: every node is the [HTTP host](http-host.md) binary in its own container, driven from the test host over HTTP alone while the nodes reach each other over the [runtime core](core.md)'s own protocols. It exists to prove what an in-process suite cannot — that a node packaged as a binary comes up, that the address it publishes in a ceremony payload is one a peer on another container dials, and that a device which goes away takes its process with it.

## Requirements

### Requirement: The stand runs each node as its own process in its own container
The stand SHALL run every node as a separate process in a separate container, all attached to one container network per scenario. No scenario SHALL place two nodes in one process.

#### Scenario: Nodes are separate processes
- **WHEN** a scenario spawns 3 nodes
- **THEN** each runs in its own container, and stopping one leaves the others running

#### Scenario: A scenario's network is its own
- **WHEN** a scenario ends, whether it passes or fails
- **THEN** its network is removed and its containers are gone

### Requirement: The image serves the host binary and nothing else
The image SHALL contain the HTTP host binary, run it as a non-root user, and listen for HTTP on all interfaces. It SHALL leave the runtime's endpoint bind unconfigured, so the endpoint binds every interface and publishes the container's own address, and SHALL leave the runtime's relay use at its default of off, so the address it publishes is a direct one and a peer that reaches it reached it directly. It SHALL name the directory the runtime stores its state in, writable by the user the binary runs as, and SHALL declare no volume of its own — what is mounted over that directory is the caller's decision, so an image-declared volume is never created behind a caller's back.

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

#### Scenario: A ceremony payload travels through the caller
- **WHEN** an invite payload minted on one container is consumed on another
- **THEN** the payload passes through the scenario, and neither container issues an HTTP request

#### Scenario: Replication crosses no HTTP
- **WHEN** a grantee converges on an entry written on another container
- **THEN** the only HTTP requests are the scenario's own, and the entry arrives over the runtime's protocols

### Requirement: The stand runs the whole scenario with its paired denials
The stand SHALL run, across containers, identity creation, connection establishment, a scoped grant, a write, the grantee's read, and the grant's withdrawal. In the same scenario it SHALL assert the tightest denials: a container with no connection and no grant is refused, and the claims the grant withholds are absent from the grantee's view after a second replication wave is shown to have happened.

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

#### Scenario: A device joins and catches up
- **WHEN** a linking payload minted on the first container is consumed on a second
- **THEN** the second container reports the identity as hosted and reads an entry written before the link

### Requirement: A stopped device does not stop the connection
The stand SHALL show a granted peer still converging after the device that published the grant is stopped, with a sibling device of the same identity serving the namespace.

#### Scenario: The publishing device is stopped
- **WHEN** an identity on 2 containers publishes a grant from the first, and that container is stopped
- **THEN** the peer converges on an entry written by the surviving container

### Requirement: Convergence is waited for at the runtime's own cadence
A scenario SHALL wait for convergence by repeating a read, bounded by a budget above the runtime's periodic reconciliation interval. No route, environment variable, or harness call SHALL force a reconciliation or shorten the runtime's cadence.

#### Scenario: A wait ends when the value arrives
- **WHEN** a scenario waits for a value written on another container
- **THEN** it repeats the read until the value appears or its budget expires, and a failed wait names what it waited for

### Requirement: The stand is where the HTTP surface is tested
Every test of the HTTP surface SHALL run against nodes on the stand. A property that cannot be reached from outside a node's process — one that holds the runtime's own state lock — MAY be tested in the test's own process, and SHALL build its runtime itself rather than through the stand's harness.

#### Scenario: A surface property is asserted against the image
- **WHEN** the debug gate, the routes it gates, or the body ceiling is asserted
- **THEN** the assertion runs against a node started from the image

#### Scenario: The runtime's own behaviour is not re-proven here
- **WHEN** a scenario asserts establishment, a grant, replication or linking
- **THEN** it runs on the stand, and the runtime's own suite proves the same behaviour without HTTP

### Requirement: The suite states what it needs and stays out of the default run
The suite SHALL NOT run as part of the workspace's default test run, nor be selected by the flaky hunt's default selection. It SHALL be reachable through a recipe that builds the image first, SHALL run in the pipeline on every proposed change, and its parallelism SHALL be bounded to what the container daemon can start at once. Its tests SHALL state that they need a daemon and a built image.

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

#### Scenario: A store edit reaches the image
- **WHEN** a source file under `crates/pdn-store` is edited and the image is rebuilt
- **THEN** the containers run that edit, and no step of the build refuses the resolution or reaches outside the build context

#### Scenario: A cargo configuration beside the workspace stays out
- **WHEN** a `.cargo/config.toml` exists beside the workspace and the build context is listed
- **THEN** the listing carries no `.cargo` entry

### Requirement: The live demo runs on the stand's image
The demo SHALL run the same image the suite runs, with every node on one container network and each node's HTTP port published on loopback of the demo host. Each node SHALL have a volume of its own for its state. The demo SHALL remove its nodes, its network and those volumes on every exit, the failing one included, and it SHALL drive the nodes over HTTP alone, so what passes between nodes is the runtimes' own traffic.

#### Scenario: The demo brings up the nodes it names
- **WHEN** the demo recipe runs
- **THEN** it builds the image, brings up every node its compose file names, and waits for each of them to answer liveness before the first step

#### Scenario: A run never meets the previous run's state
- **WHEN** the demo exits, whether it finishes or fails
- **THEN** its containers, its network and its volumes are removed

#### Scenario: The demo publishes on loopback
- **WHEN** a node of the demo publishes its HTTP port
- **THEN** the port is bound to loopback, because the debug surface is unauthenticated and mints live ceremony secrets

#### Scenario: The show survives a node restarting
- **WHEN** the demo stops one node mid-show and starts it again
- **THEN** that node comes back as the same node, its connection still stands, and nothing is established a second time

### Requirement: The stand restarts a node and asserts what came back
The stand SHALL stop a node's container and start it again with its state directory intact, and SHALL assert that the node came back as itself: the same node id, the identity still hosted, the connection still listed, the grant still readable, and an entry written before the stop still readable — with no ceremony repeated. The stand SHALL also kill a node's container — no grace, no shutdown path — and start it again, asserting the same recovery, because a process that ends without warning is the ordinary end of a process, and recovery that differs by the manner of stopping depends on a goodbye a kill does not provide. One kill SHALL land in the middle of a stream of writes: every write acknowledged before the stores' settle window — the bounded delay after which an acknowledged write has committed, since the replica store and the blob store each commit after the acknowledgement, on a timer — SHALL be readable after the restart, and a write the kill cut inside that window, acknowledged or not, SHALL be absent or whole — never a torn value and never a read error. The assertion SHALL be paired, in the same scenario, with the tightest denial: a node started from the same image on an empty state directory holds none of it. Without that arm the scenario passes just as well against a node that quietly re-created everything.

#### Scenario: A restarted node is the same node
- **WHEN** a node holding an identity, a connection and a grant is stopped and started again on its own state directory
- **THEN** it reports the same node id, hosts the same identity, lists the same connection, reads the same grant, and reads an entry written before the stop

#### Scenario: A killed node comes back the same way
- **WHEN** a node holding an identity, a connection and a grant is killed without grace and started again on its own state directory
- **THEN** it reports the same node id, hosts the same identity, lists the same connection, and reads an entry acknowledged before the stores' settle window

#### Scenario: A kill mid-stream loses nothing settled
- **WHEN** entries are being written to a node in a stream and its container is killed without grace mid-stream, then started again
- **THEN** every entry whose write was acknowledged before the stores' settle window is readable with its payload, and an entry the kill cut inside that window — acknowledged or not — is either absent or read whole, never partial

#### Scenario: A node on an empty directory holds nothing
- **WHEN** a node is started from the same image on an empty state directory
- **THEN** it hosts no identity, lists no connection, and refuses reads addressed to the identity the restarted node hosts

#### Scenario: A peer converges with the restarted node without a new ceremony
- **WHEN** the restarted node writes an entry after coming back
- **THEN** its counterparty converges on that entry, with no invite minted and no linking performed after the restart

### Requirement: The stand shows a storage failure arriving as a failure
The stand SHALL run one node whose state directory is a filesystem with a bounded size, write until the store refuses, and assert that the refusal reaches the caller as a failed request rather than as a success. A node that reports a write it did not store is the failure mode a full disk produces on a device, and it is invisible on an in-memory node.

#### Scenario: Writing past the bound is refused, not absorbed
- **WHEN** entries are written to a node whose state directory has no free space left
- **THEN** a write fails with an error response, and a read of that path does not report the value as stored
