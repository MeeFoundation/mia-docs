## MODIFIED Requirements

### Requirement: The image serves the host binary and nothing else
The image SHALL contain the HTTP host binary, run it as a non-root user, and listen for HTTP on all interfaces. It SHALL leave the runtime's endpoint bind unconfigured, so the endpoint binds every interface and publishes the container's own address. It SHALL name the directory the runtime stores its state in, writable by the user the binary runs as, and SHALL declare no volume of its own — what is mounted over that directory is the caller's decision, so an image-declared volume is never created behind a caller's back.

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

### Requirement: A stopped device does not stop the connection
The stand SHALL show a granted peer still converging after the device that published the grant is stopped, with a sibling device of the same identity serving the namespace.

#### Scenario: The publishing device is stopped
- **WHEN** an identity on 2 containers publishes a grant from the first, and that container is stopped
- **THEN** the peer converges on an entry written by the surviving container

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

## ADDED Requirements

### Requirement: The stand restarts a node and asserts what came back
The stand SHALL stop a node's container and start it again with its state directory intact, and SHALL assert that the node came back as itself: the same node id, the identity still hosted, the connection still listed, the grant still readable, and an entry written before the stop still readable — with no ceremony repeated. The stand SHALL also kill a node's container — no grace, no shutdown path — and start it again, asserting the same recovery, because a process that ends without warning is the ordinary end of a process, and recovery that differs by the manner of stopping depends on a goodbye a kill does not provide. One kill SHALL land in the middle of a stream of writes: every write acknowledged before the stores' settle window — the bounded delay after which an acknowledged write has committed (a finding of this change: both stores commit after the acknowledgement, on a timer) — SHALL be readable after the restart, and a write the kill cut inside that window, acknowledged or not, SHALL be absent or whole — never a torn value and never a read error. The assertion SHALL be paired, in the same scenario, with the tightest denial: a node started from the same image on an empty state directory holds none of it. Without that arm the scenario passes just as well against a node that quietly re-created everything.

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
