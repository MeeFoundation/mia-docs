# data-layer: connections store (multi-identity, ungated)

The connections store loses its dependence on the ingest gate: registration on the node serves addressing only, several identities' connections stores coexist on one node, and replication into an empty store needs no admission policy because there is no admission step. Entry format, tombstones, replication, and conflict resolution are unchanged.

## MODIFIED Requirements

### Requirement: Connections live in a dedicated replica
Connection state SHALL be stored in its own pdn-store replica, separate from every data namespace and from every other identity's connections store. The replica is identified on the node by its owning identity's `PdnId` for addressing; no domain `NamespaceId` is allocated for it. Connections stores of several identities SHALL coexist on one node without sharing a replica.

#### Scenario: Creating the store allocates a dedicated replica
- **WHEN** a node creates the connections store of an identity
- **THEN** a fresh pdn-store replica is created for it, addressed by that identity, and no domain `NamespaceId` is allocated

#### Scenario: Importing the store on a second device
- **WHEN** a second device imports the connections store from a ticket
- **THEN** the replica participates in sync with the first device under the same identity's addressing

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
