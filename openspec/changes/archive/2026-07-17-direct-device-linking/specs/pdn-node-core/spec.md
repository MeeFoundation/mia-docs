## MODIFIED Requirements

### Requirement: Identity service creates and links identities
The identity service SHALL create an identity on its first device — minting a placeholder `PdnId` (no key material; a KERI-backed service is the future second implementation) and provisioning its store set: the private-metadata directory and the data namespace, with the data-namespace ticket published in the directory ([device-linking](device-linking.md)). It SHALL mint a linking invite for a hosted identity — the one-time secret and the bearer-free linking payload — and SHALL link this runtime into an existing identity from a scanned linking payload, one explicit linking act per identity; the payload names the identity, and a runtime already hosting it refuses before dialing.

#### Scenario: Create on one runtime, link on another
- **WHEN** an identity is created on runtime A and runtime B links from a linking invite minted on A
- **THEN** B hosts the identity: it appears among B's hosted identities, and the identity's directory and data namespace converge on B

#### Scenario: Linking one identity imports nothing of another
- **WHEN** runtime B is linked into identity X while identity Y exists elsewhere
- **THEN** B hosts X only, and operations addressed to Y on B are refused as unknown

### Requirement: Connections service establishes, lists, and carries grants
The connections service SHALL produce connections through the establishment dialogue — minting invites for a hosted identity and establishing from an invite payload ([connection-establishment](connection-establishment.md)) — and SHALL list a hosted identity's current connections, delegating to the connections records of that identity's [directory](../data-layer/private-metadata-store.md). It SHALL carry data grants over the connection's [metadata pair](../data-layer/connection-metadata-store.md): publishing a grant of a hosted issuer's namespace toward a connected peer, and reading the grants a connected peer has published — opening the pair from the directory's tickets on demand, so linked devices reach it too. Manual one-sided recording is not offered: establishment is the producer of connections. Reading a grant yields the ticket it carries; importing that namespace remains an explicit data-service act. (The grant payload is the interim whole-store ticket; capability-scoped grants land with the read-capability mechanism, and this requirement changes with it.)

#### Scenario: Hosted identities' connection lists are disjoint
- **WHEN** identity X on a runtime establishes a connection with peer P and identity Y on the same runtime establishes none
- **THEN** listing Y's connections yields nothing

#### Scenario: A grant crosses to the peer with no new pairing
- **WHEN** X publishes a grant of its namespace toward its established peer P, after establishment completed
- **THEN** P's runtime reads the grant from the metadata pair, and importing the carried ticket through the data service lets P read X's entries once synced

#### Scenario: Connections operations on an unhosted identity are refused
- **WHEN** an invite, establishment, listing, or grant operation addresses an identity the runtime neither created nor linked
- **THEN** the operation fails with an unknown-identity error and nothing is minted, established, listed, or published
