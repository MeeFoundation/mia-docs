## MODIFIED Requirements

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

### Requirement: One endpoint carries all protocols, exposed as a dial handle
All protocols — the built-in stack and every supplied handler — SHALL share the node's single endpoint, so the node presents one wire identity (its `NodeId`) regardless of how many it serves. `SyncNode` SHALL expose a narrow dial handle onto that endpoint for runtime code to dial a peer's address under a chosen ALPN and to read the node's own address and wire id. The dial handle SHALL NOT offer the endpoint's lifecycle controls (closing the socket, rewriting its ALPN set), so the node remains the sole owner of the endpoint's lifecycle (shutdown stays with the node).

#### Scenario: The dial handle carries the node's wire identity
- **WHEN** the dial handle's identifier is compared with the node's reported node id
- **THEN** they are equal

#### Scenario: Dialing out rides the node's own identity
- **WHEN** node B dials node A's supplied protocol through B's dial handle
- **THEN** the connection A's handler observes carries B's node id as the remote identity
