# Node assembly: hosting the ceremony protocols

## Purpose

The assembled node (`SyncNode`) runs its protocols on one endpoint, keyed by application-layer protocol negotiation (ALPN) identifier: document sync, gossip, and blob transfer built in. ADR-0011 puts pairing — the raw dialogue that establishes a connection between two identities — on that same endpoint, and ADR-0012 puts device linking beside it; this capability is what lets them: a spawn-time registration point for the supplied handlers, a panic guard around each, and a dial handle onto the endpoint for the initiators' side. This registration point is protocol-agnostic (the handlers are opaque here) only because the ceremonies' semantics belong above in pdn-node, not because the assembly is a general protocol-extension facility. The stores and flows riding the assembly stay specified in the other `data-layer` specs; this capability covers the assembly itself.

## Requirements

### Requirement: The assembly accepts a supplied protocol handler
`SyncNode` SHALL accept, at spawn, zero or more externally supplied protocol handlers — today pairing ([ADR-0011](../../architecture/adr/0011-pairing-over-raw-iroh.md)) and device linking ([ADR-0012](../../architecture/adr/0012-linking-over-raw-iroh.md)) — each keyed by an ALPN identifier, and SHALL serve them on its protocol router alongside the built-in protocols (document sync, gossip, blob transfer). A connection arriving under a registered supplied ALPN SHALL be dispatched to that handler as a raw bidirectional connection, not a document-sync session. Spawning with no supplied handler SHALL preserve the assembly exactly as it is without this surface.

#### Scenario: An extra protocol answers on its ALPN
- **WHEN** node A spawns with a test echo handler under a test ALPN and node B dials A's address under that ALPN and sends bytes
- **THEN** the bytes return over the same raw bidirectional connection, with no document-sync session involved

#### Scenario: The built-in stack is unaffected by extras
- **WHEN** node A spawns with an extra protocol and node B imports a replica from A's ticket
- **THEN** the replica converges between A and B exactly as it does between nodes spawned without extras

#### Scenario: A node that did not register the ALPN refuses it
- **WHEN** node B dials node A under an ALPN that A did not register
- **THEN** the dial fails, no connection is established, and no handler runs on A

#### Scenario: Two supplied handlers serve side by side
- **WHEN** a node spawns with two supplied handlers under distinct ALPNs and each is dialed in turn
- **THEN** each dial reaches its own handler, and neither handler observes the other's connections

### Requirement: ALPN registrations are unique
The ALPNs of supplied protocols SHALL be distinct from the built-in protocols' ALPNs and from each other. A spawn presenting a collision SHALL fail with no node started and nothing bound — a supplied protocol silently replacing the sync stack must be impossible.

#### Scenario: A built-in ALPN is refused at spawn
- **WHEN** a node spawns with a supplied protocol claiming the document-sync ALPN
- **THEN** the spawn fails and no node starts

#### Scenario: A duplicate supplied ALPN is refused at spawn
- **WHEN** a node spawns with two supplied protocols claiming the same ALPN
- **THEN** the spawn fails and no node starts

### Requirement: One endpoint carries all protocols, exposed as a dial handle
All protocols — the built-in stack and every supplied handler — SHALL share the node's single endpoint, so the node presents one wire identity (its `NodeId`) regardless of how many it serves. `SyncNode` SHALL expose a narrow dial handle onto that endpoint for runtime code to dial a peer's address under a chosen ALPN and to read the node's own address and wire id. The dial handle SHALL NOT offer the endpoint's lifecycle controls (closing the socket, rewriting its ALPN set), so the node remains the sole owner of the endpoint's lifecycle (shutdown stays with the node).

#### Scenario: The dial handle carries the node's wire identity
- **WHEN** the dial handle's identifier is compared with the node's reported node id
- **THEN** they are equal

#### Scenario: Dialing out rides the node's own identity
- **WHEN** node B dials node A's supplied protocol through B's dial handle
- **THEN** the connection A's handler observes carries B's node id as the remote identity

### Requirement: A supplied handler's panic is contained
A panic in a supplied handler's accept path SHALL NOT tear down the node. It SHALL be caught, failing only that one connection, while the built-in protocols keep serving. (Under a `panic = "abort"` build no catch is possible; the spawn form's contract asks handlers not to panic.)

#### Scenario: A panicking handler does not take down the node
- **WHEN** node A spawns with a handler that panics mid-accept, and node B dials it and drives a stream
- **THEN** that connection fails and node A still converges a replica with node B over the ordinary ticket flow

### Requirement: Every replica the node holds open joins a periodic reconcile pass, at a cadence the spawn names
`SyncNode` SHALL run a periodic pass that re-requests a sync for every document it holds open, whichever synchronization strategy that document follows, and the interval SHALL be named at the spawn with a default of 10 seconds.

The interval is what bounds every convergence no read of its own nudges: a grant record reaching the peer's copy of a connection's metadata pair, a write reaching another device of the same identity, and a linking catch-up, whose re-dial cadence is that pass. It is written down here because a host that configures its own value — a phone trading battery against how long a person waits — needs somewhere to configure it *from*, and because the resulting speed is otherwise read as a property of the network rather than of a number somebody chose.

#### Scenario: A spawn that names no interval gets the default
- **WHEN** a node is spawned without naming a reconcile interval
- **THEN** its periodic pass runs at 10 seconds

#### Scenario: A host's own interval is what the node runs at
- **WHEN** a node is spawned with an interval of its embedder's choosing
- **THEN** the periodic pass runs at that interval, and no route, environment variable or harness call changes it afterwards
