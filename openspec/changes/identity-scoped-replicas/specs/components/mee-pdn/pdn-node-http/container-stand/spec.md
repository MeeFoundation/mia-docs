# pdn-node-http: container stand — delta for identity-scoped-replicas

## ADDED Requirements

### Requirement: The stand asserts that two identities on one node read only their own

The stand SHALL run two identities on one container, each connected to a peer of its own, and SHALL assert in the same scenario that each reads what its own peer granted it and that neither reads what the other's peer granted. Asserting it from outside the process is the point: the property is what the node serves and answers over its surface, not what its internal calls happen to do.

#### Scenario: Each identity reads what its own peer granted

- **WHEN** two peers each grant a claim to one of the two identities on one container, and each identity reads its own issuer
- **THEN** each read returns the entry that peer wrote

#### Scenario: Neither identity reads the other's granted namespace

- **WHEN** each identity reads the issuer that granted the other
- **THEN** both reads are refused, and neither returns an entry

#### Scenario: An outsider reads neither

- **WHEN** a container holding no connection and no grant reads both issuers
- **THEN** both reads are refused
