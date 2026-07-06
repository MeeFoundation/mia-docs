# data-layer: multi-identity node

One node hosts several identities — for example Alice-at-work and Alice-at-leisure, later groups and organizations — each with its own store set (private metadata store, connections store, data namespace), added to a device explicitly and addressed independently. Interim admission is ticket possession, until subset-rbsr (Invariant 2) and UWill restore enforcement.

## ADDED Requirements

### Requirement: A node hosts several identities side by side
A `SyncNode` SHALL host the store sets of any number of identities concurrently: each identity's private metadata store, connections store, and data namespace are separate replicas, created or imported on the same node. Data namespaces are addressed by their issuer's `PdnId`; the device-shared stores are reached through their store handles. The stores of different identities SHALL NOT share a replica.

#### Scenario: Two identities' private stores on one node
- **WHEN** private metadata stores and connections stores are created on one node for identity A and identity B
- **THEN** the node carries four distinct replicas, and each store is reached through its own handle and holds only its identity's records

#### Scenario: Two issuers' data namespaces on one node
- **WHEN** data namespaces are created on one node for issuer A and issuer B and one entry is written into each
- **THEN** reading a path under issuer A returns only what was written in A's namespace, and likewise for B

### Requirement: An identity is added to a device explicitly
Each identity SHALL arrive on a device through its own explicit linking act, given that identity's seed. Linking one identity SHALL NOT import, discover, or propagate any other identity: no cascade at linking time, and no automatic appearance of an identity on already-linked devices.

#### Scenario: Second identity requires its own linking
- **WHEN** a device is linked into identity A and identity B's stores exist elsewhere
- **THEN** identity B's stores appear on the device only after a separate linking act with identity B's seed

### Requirement: Interim admission is ticket possession
Until egress filtering (subset-rbsr) lands, a node SHALL install no ingest filter: every entry syncing into a replica the node imported or created is persisted. Access to a replica is bounded by possession of its ticket and by nothing else.

#### Scenario: Full replication for a ticket holder
- **WHEN** a node imports a replica from its ticket and syncs with a peer holding that replica
- **THEN** all entries of that replica replicate and persist, with no entry dropped by an admission decision
