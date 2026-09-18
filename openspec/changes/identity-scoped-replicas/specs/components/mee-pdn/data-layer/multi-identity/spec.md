# data-layer: multi-identity node — delta for identity-scoped-replicas

## MODIFIED Requirements

### Requirement: A node hosts several identities side by side
A `SyncNode` SHALL host the store sets of any number of identities concurrently, each in its own scope ([identity-scoped replicas](../identity-scoped-replicas/spec.md)): each identity's private metadata store (the directory, carrying its device set, tickets, and connections records) and data store are separate replicas, created or imported on the same node. Data stores are addressed by their issuer's `PdnId` within the scope that holds them; the directory is reached through its store handle. The stores of different identities SHALL NOT share a replica, and neither SHALL two identities that acquired one namespace — under two grants of one issuer, or as the two ends of one connection's metadata pair: each holds a replica of its own.

#### Scenario: Two identities' private stores on one node
- **WHEN** private metadata stores are created on one node for identity A and identity B
- **THEN** they are two distinct replicas, each reached through its own handle and holding only its identity's entries — device records and connections records included

#### Scenario: Two issuers' data stores on one node
- **WHEN** data stores are created on one node for issuer A and issuer B and one entry is written into each
- **THEN** reading a path under issuer A returns only what was written in A's namespace, and likewise for B

#### Scenario: One namespace acquired by two identities is two replicas
- **WHEN** two identities hosted on one node are each granted a claim of one issuer's namespace
- **THEN** the node holds two replicas of that namespace, one per identity, and neither identity reads what the other's grant covers

### Requirement: Admission is classified per session, and an unregistered replica is ticket-bounded
A node SHALL classify every reconciliation session of a replica whose scope it holds registration for — an identity's directory arms its data namespace, a connection registers its metadata pair — as [subset reconciliation](../subset-reconciliation/spec.md) and [capability-gated ingest](../capability-gated-ingest/spec.md) state, judging it by the scopes the session names. A replica in a scope the node holds no such registration for — an assembly that hosts no identity — SHALL be served and admitted whole to any holder of its ticket: possession of the ticket bounds access there, and nothing else does.

#### Scenario: Full replication between ticket holders of an unregistered replica
- **WHEN** a node that registers no identity imports a replica from its ticket into a scope of its own and syncs with a peer holding that replica
- **THEN** all entries of that replica replicate and persist, with no entry dropped by an admission decision
