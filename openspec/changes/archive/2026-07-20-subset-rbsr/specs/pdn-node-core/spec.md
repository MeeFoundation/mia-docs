## MODIFIED Requirements

### Requirement: Connections service establishes, lists, and carries grants
The connections service SHALL produce connections through the establishment dialogue — minting invites for a hosted identity and establishing from an invite payload ([connection-establishment](connection-establishment.md)) — and SHALL list a hosted identity's current connections, delegating to the connections records of that identity's [directory](../data-layer/private-metadata-store.md). It SHALL carry data grants over the connection's [metadata pair](../data-layer/connection-metadata-store.md): publishing a grant of the identity's own namespace toward a connected peer — whole-store, or capability-scoped by an exact claim set with optional write — and reading the grants a connected peer has published, opening the pair from the directory's tickets on demand, so linked devices reach it too. Manual one-sided recording is not offered: establishment is the producer of connections. Reading a grant yields what it carries — the ticket, and for a scoped grant the capability beside it; importing that namespace remains an explicit data-service act.

A grant SHALL name the granting identity itself as the data issuer; publishing a grant of any other issuer's data SHALL be refused loudly, with nothing minted or written. Granting foreign data is delegation: the serving side evaluates grants from the records of the *data issuer's* own connections (subset-rbsr D8/D9), so a grant recorded under a different granting identity could never be honored — without the refusal it would publish successfully, replicate, and enforce as nothing, a silent no-op on both sides. The grant keying by data issuer is untouched — it is the groundwork delegation chains use; the boundary lifts when `UWill` chains make a foreign issuer's grant provable.

(The whole-store grant payload is the interim whole-store **write** ticket: the store's capability is swarm membership, not access control. Its read side is enforced since subset-rbsr — session classification serves a whole-store grantee the full replica and refuses bare ticket holders — while the write side stays unscoped until the ingest gate (ADR-0008) lands. A scoped grant's ticket mode follows its commands: read-only grants ship a read ticket and cannot write at all.)

#### Scenario: Hosted identities' connection lists are disjoint
- **WHEN** identity X on a runtime establishes a connection with peer P and identity Y on the same runtime establishes none
- **THEN** listing Y's connections yields nothing

#### Scenario: A grant crosses to the peer with no new pairing
- **WHEN** X publishes a grant of its namespace toward its established peer P, after establishment completed
- **THEN** P's runtime reads the grant from the metadata pair, and importing the carried ticket through the data service lets P read X's entries once synced

#### Scenario: Connections operations on an unhosted identity are refused
- **WHEN** an invite, establishment, listing, or grant operation addresses an identity the runtime neither created nor linked
- **THEN** the operation fails with an unknown-identity error and nothing is minted, established, listed, or published

#### Scenario: Granting a foreign issuer's data is refused
- **WHEN** identity X publishes a grant — whole-store or scoped — naming a data issuer other than X, even one hosted on the same runtime
- **THEN** the operation is refused as unsupported delegation, and no grant record for that issuer ever reaches the peer's view of the pair
