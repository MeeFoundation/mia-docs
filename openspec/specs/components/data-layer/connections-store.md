# Connections store

## Purpose

Device-replicated registry of an identity's connections: a dedicated pdn-store replica, separate from data stores, replicated across all of one identity's devices; connections stores of several identities coexist on one node. Access is bounded by possession of the store's ticket (Invariant 1). This spec covers the store and its replication between devices.

## Requirements
### Requirement: Connections live in a dedicated replica
Connection state SHALL be stored in its own pdn-store replica, separate from every data store and from every other identity's connections store. The store handle returned at creation or import is how the replica is addressed — the node keys no registry by identity for it, and no domain `NamespaceId` is allocated. Connections stores of several identities SHALL coexist on one node without sharing a replica.

#### Scenario: Creating the store allocates a dedicated replica
- **WHEN** a node creates a connections store
- **THEN** a fresh pdn-store replica is created for it, reached through the returned store handle, and no domain `NamespaceId` is allocated

#### Scenario: Importing the store on a second device
- **WHEN** a second device imports the connections store from a ticket
- **THEN** the replica participates in sync with the first device, reached through the importing device's own store handle

#### Scenario: Two identities' connections stores on one node
- **WHEN** connections stores are created on one node for identity A and identity B
- **THEN** they are two distinct replicas, and mutations under A are invisible under B

### Requirement: One entry per connection, identity in the key
A live connection to peer `P` SHALL be represented by an entry at path `connections/<P-hex>` (64 lowercase hex chars of the PdnId). The payload SHALL be treated as opaque: liveness decisions MUST NOT depend on payload bytes.

#### Scenario: Connect writes the marker entry
- **WHEN** `connect(P)` is called on a device
- **THEN** an entry exists at `connections/<P-hex>` in the connections replica with a non-zero length

### Requirement: Disconnect is a tombstone
`disconnect(P)` SHALL write a pdn-store tombstone (empty entry, length 0) at `connections/<P-hex>`. A connection SHALL be considered live if and only if the latest entry for its key across all authors has non-zero length.

#### Scenario: Disconnect ends liveness
- **WHEN** `disconnect(P)` is called after a prior `connect(P)`
- **THEN** the latest entry at `connections/<P-hex>` is empty and the connection to `P` is not live

### Requirement: Mutations replicate between devices
Connection mutations performed on one device SHALL become visible on the identity's other devices through standard pdn-store sync (set reconciliation for catch-up, gossip for live updates), with no additional transport or server.

#### Scenario: Connect on one device, observed on another
- **WHEN** phone calls `connect(P)` while phone and laptop are reachable
- **THEN** laptop's connections store eventually contains a live entry for `P`

#### Scenario: Revocation propagates
- **WHEN** phone calls `disconnect(P)` after `P` was live on laptop
- **THEN** laptop's connections store eventually shows `P` as not live

### Requirement: Concurrent edits resolve by last-writer-wins
Concurrent mutations of the same connection key on different devices SHALL resolve on every device to the entry with the newest timestamp (pdn-store per-key LWW across authors), with tombstones participating like ordinary entries.

#### Scenario: Offline conflict resolves deterministically
- **WHEN** phone calls `connect(P)` and laptop calls `disconnect(P)` while partitioned, and the devices then sync
- **THEN** both devices resolve to the mutation with the newest timestamp

