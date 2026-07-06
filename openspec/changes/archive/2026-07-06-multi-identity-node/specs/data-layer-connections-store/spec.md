# data-layer: connections store (multi-identity, ungated)

The connections store loses its dependence on the ingest gate: registration on the node serves addressing only, several identities' connections stores coexist on one node, and replication into an empty store needs no admission policy because there is no admission step. Entry format, tombstones, replication, and conflict resolution are unchanged.

## MODIFIED Requirements

### Requirement: Connections live in a dedicated replica
Connection state SHALL be stored in its own pdn-store replica, separate from every data namespace and from every other identity's connections store. The store handle returned at creation or import is how the replica is addressed — the node keys no registry by identity for it, and no domain `NamespaceId` is allocated. Connections stores of several identities SHALL coexist on one node without sharing a replica.

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

## REMOVED Requirements

### Requirement: The store bootstraps through its own gate
**Reason**: The ingest gate is removed; there is no admission step for replication to pass, so a still-empty store fills from sync unconditionally. The property this requirement protected — bootstrap against empty local state — holds trivially without a gate.
**Migration**: Admission is bounded by ticket possession alone until subset-rbsr and UWill; the bootstrap scenario stays covered by the device-linking and two-device sync tests.
