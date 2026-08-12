## ADDED Requirements

### Requirement: The stand runs each node as its own process in its own container
The stand SHALL run every node as a separate process in a separate container, all attached to one container network per scenario. No scenario SHALL place two nodes in one process.

#### Scenario: Nodes are separate processes
- **WHEN** a scenario spawns 3 nodes
- **THEN** each runs in its own container, and stopping one leaves the others running

#### Scenario: A scenario's network is its own
- **WHEN** a scenario ends, whether it passes or fails
- **THEN** its network is removed and its containers are gone

### Requirement: The image serves the host binary and nothing else
The image SHALL contain the HTTP host binary, run it as a non-root user, and listen for HTTP on all interfaces. It SHALL leave the runtime's endpoint bind unconfigured, so the endpoint binds every interface and publishes the container's own address.

#### Scenario: A container answers liveness
- **WHEN** a container starts from the image
- **THEN** `GET /live` answers 200 on the published port

#### Scenario: A peer dials the address a payload carries
- **WHEN** a node on one container consumes an invite payload minted on another
- **THEN** the dial reaches the minting node over the container network, with no relay and no discovery configured

#### Scenario: The debug surface follows its flag inside the image too
- **WHEN** a container starts without the debug flag set
- **THEN** requests under `/debug/` return 404 and `GET /live` still answers 200

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

#### Scenario: A device that never restarts
- **WHEN** a container is stopped in a scenario
- **THEN** the scenario asserts nothing about it starting again, because a restarted node keeps no state and takes a new node id

### Requirement: Convergence is waited for at the runtime's own cadence
A scenario SHALL wait for convergence by repeating a read, bounded by a budget above the runtime's periodic reconciliation interval. No route, environment variable, or harness call SHALL force a reconciliation or shorten the runtime's cadence.

#### Scenario: A wait ends when the value arrives
- **WHEN** a scenario waits for a value written on another container
- **THEN** it repeats the read until the value appears or its budget expires, and a failed wait names what it waited for

### Requirement: The suite is opt-in and states what it needs
The suite SHALL NOT run as part of the workspace's default test run, nor be selected by the flaky hunt's default selection, and SHALL be reachable through a recipe that builds the image first. Its tests SHALL state that they need a container daemon and a built image.

#### Scenario: The inner loop is untouched
- **WHEN** the default test run or the flaky hunt runs with no selection given
- **THEN** none of the stand's tests run and no image is built

#### Scenario: The recipe builds before it runs
- **WHEN** the container-suite recipe runs
- **THEN** it builds the image and then runs the stand's suite against it

### Requirement: The image carries the workspace as it resolves
The image SHALL be built from the workspace's own dependency resolution, including a store fork pointed at a checkout beside it.

#### Scenario: A locally resolved fork reaches the image
- **WHEN** the workspace points the store fork at a checkout beside it and the image is rebuilt
- **THEN** the containers run that fork, and no step of the build refuses the resolution
