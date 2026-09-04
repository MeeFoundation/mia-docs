# Multi-identity node

## Purpose

One node hosts several identities — for example Alice-at-work and Alice-at-leisure, later groups and organizations — each with its own store set (the private-metadata directory and the data store), added to a device explicitly and addressed independently. Read admission to a data store is classified per session — an identity's own devices see it whole, granted counterparties see what their grants cover, other callers are refused ([subset reconciliation](subset-reconciliation.md), Invariant 2); identity-bound authorization lands with UWill.

## Requirements

### Requirement: A node hosts several identities side by side
A `SyncNode` SHALL host the store sets of any number of identities concurrently: each identity's private metadata store (the directory, carrying its device set, tickets, and connections records) and data store are separate replicas, created or imported on the same node. Data stores are addressed by their issuer's `PdnId`; the directory is reached through its store handle. The stores of different identities SHALL NOT share a replica.

#### Scenario: Two identities' private stores on one node
- **WHEN** private metadata stores are created on one node for identity A and identity B
- **THEN** they are two distinct replicas, each reached through its own handle and holding only its identity's entries — device records and connections records included

#### Scenario: Two issuers' data stores on one node
- **WHEN** data stores are created on one node for issuer A and issuer B and one entry is written into each
- **THEN** reading a path under issuer A returns only what was written in A's namespace, and likewise for B

### Requirement: An identity is added to a device explicitly
Each identity SHALL arrive on a device through its own explicit linking act, from a linking invite minted by one of that identity's devices ([device-linking](../pdn-node/device-linking.md)). Linking one identity SHALL NOT import, discover, or propagate any other identity: no cascade at linking time, and no automatic appearance of an identity on already-linked devices.

#### Scenario: Second identity requires its own linking
- **WHEN** a device is linked into identity A and identity B's stores exist elsewhere
- **THEN** identity B's stores appear on the device only after a separate linking act with a linking invite for identity B

### Requirement: Interim admission is ticket possession
Until egress filtering (subset-rbsr) lands, a node SHALL install no ingest filter: every entry syncing into a replica the node imported or created is persisted. Access to a replica is bounded by possession of its ticket and by nothing else.

#### Scenario: Full replication for a ticket holder
- **WHEN** a node imports a replica from its ticket and syncs with a peer holding that replica
- **THEN** all entries of that replica replicate and persist, with no entry dropped by an admission decision
