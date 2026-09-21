# data-layer: multi-identity node — delta for identity-scoped-replicas

## MODIFIED Requirements

### Requirement: A node hosts several identities side by side
A `SyncNode` SHALL host the store sets of any number of identities concurrently, each with stores of its own ([identity-scoped replicas](../identity-scoped-replicas/spec.md)): each identity's private metadata store (the directory, carrying its device set, tickets, and connections records) and data store are separate replicas, created or imported on the same node. Data stores are addressed by their issuer's `PdnId` within the identity that holds them; the directory is reached through its store handle. The stores of different identities SHALL NOT share a replica, and neither SHALL two identities that acquired one namespace — under two grants of one issuer, or as the two ends of one connection's metadata pair: each holds a replica of its own.

#### Scenario: Two identities' private stores on one node
- **WHEN** private metadata stores are created on one node for identity A and identity B
- **THEN** they are two distinct replicas, each reached through its own handle and holding only its identity's entries — device records and connections records included

#### Scenario: Two issuers' data stores on one node
- **WHEN** data stores are created on one node for issuer A and issuer B and one entry is written into each
- **THEN** reading a path under issuer A returns only what was written in A's namespace, and likewise for B

#### Scenario: One namespace acquired by two identities is two replicas
- **WHEN** two identities hosted on one node are each granted a claim of one issuer's namespace
- **THEN** the node holds two replicas of that namespace, one per identity, and neither identity reads what the other's grant covers

## ADDED Requirements

### Requirement: Every replica has an owner, and no session is served without a verdict
Every replica a node holds SHALL be held for an identity that node hosts, and every reconciliation session SHALL be judged before it serves anything: the store SHALL take the verdict of a session access provider on both session roles, and a node SHALL NOT be assemblable without one. A data replica SHALL be judged by the records of the identity that holds it — an identity's directory arms its data namespace, a connection registers its metadata pair — as [subset reconciliation](../subset-reconciliation/spec.md) and [capability-gated ingest](../capability-gated-ingest/spec.md) state, judging it by the identities the session names. A session for a data replica whose identity holds no records to judge the caller by SHALL be refused indistinguishably from the replica not being hosted: possession of a ticket SHALL bound no data replica by itself.

A directory and a connection metadata store SHALL keep the bound Invariants 1 and 3 give them — their ticket — rather than the records: a directory is where the records that judge every other session arrive, and judging it by its own device set, before that set has converged, would close the bootstrap that delivers it.

#### Scenario: A data replica with no records to judge by refuses
- **WHEN** a node holds a data replica for an identity whose access book holds no records that resolve the caller, and a holder of that replica's ticket requests a sync
- **THEN** the request is refused indistinguishably from the replica not being hosted, and no entry is served

#### Scenario: A directory still replicates between the identity's devices
- **WHEN** a device of an identity syncs that identity's directory with a sibling holding its ticket
- **THEN** the session proceeds, so the device records that judge every other session arrive

## REMOVED Requirements

### Requirement: Admission is classified per session, and an unregistered replica is ticket-bounded
**Reason**: Its second half serves a replica whole to any holder of its ticket wherever the node holds no registration for it, which is data belonging to nobody: an assembly reaches that state by holding a replica no identity is behind, and the store reaches it by running with no session access provider at all — the upstream default the fork kept.
**Migration**: The classification half is restated, with the owner and the verdict made mandatory, by "Every replica has an owner, and no session is served without a verdict"; a directory and a connection metadata store keep their ticket bound under Invariants 1 and 3, and an assembly that held replicas outside every identity hosts one.
