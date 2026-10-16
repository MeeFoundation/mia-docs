## REMOVED Requirements

### Requirement: Connections live in a dedicated replica
**Reason**: The dedicated replica is gone: connections are records in the private metadata store (PMS) (`data-layer-private-metadata-store`). The two stores always had the same audience (Invariant 1), so the separation bought no isolation while keeping a second reconciliation unit and gossip topic per identity and a cross-replica skew state ("PMS synced, connections store silently didn't") alive.
**Migration**: Per-identity separation of connection state is carried by the PMS's dedicated-replica requirement; the store handle surface becomes the PMS's connections surface.

#### Scenario: Removed with the store
- **WHEN** the connections store is merged into the PMS
- **THEN** this requirement's separation guarantees are carried by "The PMS lives in a dedicated replica"

### Requirement: One entry per connection, identity in the key
**Reason**: Merged verbatim into `data-layer-private-metadata-store` ("One entry per connection, counterparty in the key") — the key scheme, the opaque payload, and record-level liveness are unchanged; only the hosting replica changed.
**Migration**: The entries live at the same `connections/<P-hex>` paths, now inside the PMS replica.

#### Scenario: Merged into the PMS spec
- **WHEN** a connection is recorded after the merge
- **THEN** the marker-entry behavior is specified by the PMS's connections requirements

### Requirement: Disconnect is a tombstone
**Reason**: Merged verbatim into `data-layer-private-metadata-store` ("Disconnect is a tombstone").
**Migration**: Same tombstone semantics, PMS replica.

#### Scenario: Merged into the PMS spec
- **WHEN** a connection is dropped after the merge
- **THEN** the tombstone behavior is specified by the PMS's connections requirements

### Requirement: Mutations replicate between devices
**Reason**: The PMS's own "Mutations replicate between devices" requirement covers every PMS key, connections records included; connection-specific propagation scenarios moved into the merged connections requirements.
**Migration**: No behavior change — the records replicate as PMS entries.

#### Scenario: Covered by the PMS spec
- **WHEN** a connection mutation replicates after the merge
- **THEN** the replication guarantee is the PMS's

### Requirement: Concurrent edits resolve by last-writer-wins
**Reason**: The PMS's own "Concurrent edits resolve by last-writer-wins" requirement covers every PMS key; the offline-conflict scenario for connections moved into the merged tombstone requirement.
**Migration**: No behavior change — pdn-store per-key last-writer-wins across authors, unchanged.

#### Scenario: Covered by the PMS spec
- **WHEN** concurrent connection edits converge after the merge
- **THEN** the resolution rule is the PMS's
