# data-layer: node assembly — delta for identity-scoped-replicas

## ADDED Requirements

### Requirement: An accepted sync connection is dispatched to the scope it names

The node SHALL read the scope an accepted sync connection names before the session reaches any replica, and SHALL hand the session to that scope alone. A connection naming a scope the node does not hold SHALL be refused indistinguishably from the replica not being hosted, and no scope SHALL observe a session addressed to another.

#### Scenario: A session reaches the scope it names

- **WHEN** a peer syncs a namespace two scopes of one node hold, naming one of them
- **THEN** the entries it delivers land in the named scope's replica, and the other scope's replica is unchanged by that session

#### Scenario: An unknown scope is refused

- **WHEN** a session names a scope the node does not hold
- **THEN** it is refused indistinguishably from the replica not being hosted, and no replica is touched
