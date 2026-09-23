# data-layer: node assembly — delta for identity-scoped-replicas

## ADDED Requirements

### Requirement: An accepted sync connection is dispatched to the hosted identity it names

The node SHALL read the [identity](../../../../architecture/language/mee-identity.md) an accepted sync connection names before the session reaches any replica, and SHALL hand the session to that hosted identity alone. A connection naming an identity the node does not host SHALL be refused indistinguishably from the replica not being hosted, and no hosted identity SHALL observe a session addressed to another.

#### Scenario: A session reaches the hosted identity it names

- **WHEN** a peer syncs a namespace two identities of one node hold, naming one of them
- **THEN** the entries it delivers land in the named identity's replica, and the other hosted identity's replica is unchanged by that session

#### Scenario: An unknown identity is refused

- **WHEN** a session names an identity the node does not hold
- **THEN** it is refused indistinguishably from the replica not being hosted, and no replica is touched
