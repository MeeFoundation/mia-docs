## ADDED Requirements

### Requirement: A registered data namespace can be forgotten
Registering a data store under an issuer SHALL have a counterpart: forgetting an issuer's data namespace stops reconciling its replica, drops it, and removes the issuer's registration together — so operations addressed to that issuer afterwards fail with the unknown-issuer error, exactly as before the import, rather than resolving to a dropped replica. Dropping the replica without removing the registration is not sufficient and SHALL NOT be the surface offered: the issuer would still resolve, and its operations would fail as storage errors instead of the distinguishable refusal this store's addressing requirement mandates. This is the rollback path for an import that must not survive the operation that made it ([device-linking](../pdn-node/device-linking.md)).

#### Scenario: Forgetting a namespace unregisters its issuer
- **WHEN** a node imports the data namespace of an issuer, then forgets it
- **THEN** the replica is no longer reconciled, and reading, writing, or listing under that issuer fails with the unknown-issuer error

#### Scenario: Forgetting one issuer leaves the others addressable
- **WHEN** a node hosts the data namespaces of two issuers and forgets one
- **THEN** the other issuer's entries remain readable under its own `PdnId`
