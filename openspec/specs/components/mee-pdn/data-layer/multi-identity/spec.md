# Multi-identity node

## Purpose

One node hosts several identities — for example Alice-at-work and Alice-at-leisure, later groups and organizations — each with its own store set (the private-metadata directory and the data store), added to a device explicitly and addressed independently. Read admission to a data store is classified per session — an identity's own devices see it whole, granted counterparties see what their grants cover, other callers are refused ([subset reconciliation](../subset-reconciliation/spec.md), Invariant 2); identity-bound authorization lands with UWill.

## Requirements

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
### Requirement: An identity is added to a device explicitly
Each identity SHALL arrive on a device through its own explicit linking act, from a linking invite minted by one of that identity's devices ([device-linking](../../pdn-node/device-linking/spec.md)). Linking one identity SHALL NOT import, discover, or propagate any other identity: no cascade at linking time, and no automatic appearance of an identity on already-linked devices.

#### Scenario: Second identity requires its own linking
- **WHEN** a device is linked into identity A and identity B's stores exist elsewhere
- **THEN** identity B's stores appear on the device only after a separate linking act with a linking invite for identity B

### Requirement: Every replica has an owner, and no session is served without a verdict
Every replica a node holds SHALL be held for an identity that node hosts, and every reconciliation session SHALL be judged before it serves anything: the store SHALL take the verdict of a session access provider on both session roles, and a node SHALL NOT be assemblable without one. A data replica SHALL be judged by the records of the identity that holds it — an identity's directory arms its data namespace, a connection registers its metadata pair — as [subset reconciliation](../subset-reconciliation/spec.md) and [capability-gated ingest](../capability-gated-ingest/spec.md) state, judging it by the identities the session names. A session for a data replica whose identity holds no records to judge the caller by SHALL be refused indistinguishably from the replica not being hosted: possession of a ticket SHALL bound no data replica by itself.

A directory and a connection metadata store SHALL keep the bound Invariants 1 and 3 give them — their ticket — rather than the records: a directory is where the records that judge every other session arrive, and judging it by its own device set, before that set has converged, would close the bootstrap that delivers it.

#### Scenario: A data replica with no records to judge by refuses
- **WHEN** a node holds a data replica for an identity whose access book holds no records that resolve the caller, and a holder of that replica's ticket requests a sync
- **THEN** the request is refused indistinguishably from the replica not being hosted, and no entry is served

#### Scenario: A directory still replicates between the identity's devices
- **WHEN** a device of an identity syncs that identity's directory with a sibling holding its ticket
- **THEN** the session proceeds, so the device records that judge every other session arrive
