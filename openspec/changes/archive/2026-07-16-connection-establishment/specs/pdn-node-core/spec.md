# Runtime core: the connections service produces connections by establishment

The connections service stops recording one-sided assertions and becomes the surface of the establishment dialogue and the grants channel: invites, establishment from a scanned invite, listing, and grants over the connection's metadata pair. The procedure itself is specified in [connection-establishment](connection-establishment.md); this delta reshapes the service requirement in the runtime core.

## RENAMED Requirements
- FROM: `### Requirement: Connections service records and lists an identity's connections`
- TO: `### Requirement: Connections service establishes, lists, and carries grants`

## MODIFIED Requirements

### Requirement: Connections service establishes, lists, and carries grants
The connections service SHALL produce connections through the establishment dialogue — minting invites for a hosted identity and establishing from an invite payload ([connection-establishment](connection-establishment.md)) — and SHALL list a hosted identity's current connections, delegating to that identity's [connections store](../data-layer/connections-store.md). It SHALL carry data grants over the connection's [metadata pair](../data-layer/connection-metadata-store.md): publishing a grant of a hosted issuer's namespace toward a connected peer, and reading the grants a connected peer has published — opening the pair from the directory's tickets on demand, so linked devices reach it too. Manual one-sided recording is not offered: establishment is the producer of connections. Reading a grant yields the ticket it carries; importing that namespace remains an explicit data-service act. (The grant payload is the interim whole-store ticket; capability-scoped grants land with the read-capability mechanism, and this requirement changes with it.)

#### Scenario: Hosted identities' connection lists are disjoint
- **WHEN** identity X on a runtime establishes a connection with peer P and identity Y on the same runtime establishes none
- **THEN** listing Y's connections yields nothing

#### Scenario: A grant crosses to the peer with no new pairing
- **WHEN** X publishes a grant of its namespace toward its established peer P, after establishment completed
- **THEN** P's runtime reads the grant from the metadata pair, and importing the carried ticket through the data service lets P read X's entries once synced

#### Scenario: Connections operations on an unhosted identity are refused
- **WHEN** an invite, establishment, listing, or grant operation addresses an identity the runtime neither created nor linked
- **THEN** the operation fails with an unknown-identity error and nothing is minted, established, listed, or published
