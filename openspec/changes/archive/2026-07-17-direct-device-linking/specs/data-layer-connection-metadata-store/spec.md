## MODIFIED Requirements

### Requirement: Each direction of a connection lives in a dedicated replica
A connection between identities A and B SHALL be served by two dedicated pdn-store replicas: one issued by A toward B and one issued by B toward A. Each SHALL be separate from every data store, from the private-metadata directory, and from every other connection's metadata stores; no domain `NamespaceId` is allocated — the store handle returned at creation or import is how the replica is addressed. Metadata stores of several connections and several identities SHALL coexist on one node without sharing a replica.

#### Scenario: Creating the store allocates a dedicated replica
- **WHEN** a node creates a connection metadata store
- **THEN** a fresh pdn-store replica is created for it, reached through the returned store handle, and no domain `NamespaceId` is allocated

#### Scenario: The two directions are distinct replicas
- **WHEN** a connection between A and B is assembled
- **THEN** the store issued by A toward B and the store issued by B toward A are two distinct replicas, and an entry written in one never appears in the other

#### Scenario: One identity's connections do not share a replica
- **WHEN** identity A holds connections to B and to C
- **THEN** A's store toward B and A's store toward C are two distinct replicas, and a grant written toward B is invisible in the store toward C
