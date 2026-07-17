## REMOVED Requirements

### Requirement: Connections live in a dedicated replica
**Reason**: The dedicated replica is gone: connections are records in the private-metadata directory (`data-layer-private-metadata-store`). The two stores always had the same audience (Invariant 1), so the separation bought no isolation while keeping a second reconciliation unit and gossip topic per identity and a cross-replica skew state ("directory synced, connections store silently didn't") alive.
**Migration**: Per-identity separation of connection state is carried by the directory's dedicated-replica requirement; the store handle surface becomes the directory's connections surface.

#### Scenario: Removed with the store
- **WHEN** the connections store is folded into the directory
- **THEN** this requirement's separation guarantees are carried by "The directory lives in a dedicated replica"

### Requirement: One entry per connection, identity in the key
**Reason**: Folded verbatim into `data-layer-private-metadata-store` ("One entry per connection, counterparty in the key") — the key scheme, the opaque payload, and record-level liveness are unchanged; only the hosting replica changed.
**Migration**: The entries live at the same `connections/<P-hex>` paths, now inside the directory replica.

#### Scenario: Folded into the directory spec
- **WHEN** a connection is recorded after the fold
- **THEN** the marker-entry behavior is specified by the directory's connections requirements

### Requirement: Disconnect is a tombstone
**Reason**: Folded verbatim into `data-layer-private-metadata-store` ("Disconnect is a tombstone").
**Migration**: Same tombstone semantics, directory replica.

#### Scenario: Folded into the directory spec
- **WHEN** a connection is dropped after the fold
- **THEN** the tombstone behavior is specified by the directory's connections requirements

### Requirement: Mutations replicate between devices
**Reason**: The directory's own "Mutations replicate between devices" requirement covers every directory key, connections records included; connection-specific propagation scenarios moved into the folded connections requirements.
**Migration**: No behavior change — the records replicate as directory entries.

#### Scenario: Covered by the directory spec
- **WHEN** a connection mutation replicates after the fold
- **THEN** the replication guarantee is the directory's

### Requirement: Concurrent edits resolve by last-writer-wins
**Reason**: The directory's own "Concurrent edits resolve by last-writer-wins" requirement covers every directory key; the offline-conflict scenario for connections moved into the folded tombstone requirement.
**Migration**: No behavior change — pdn-store per-key last-writer-wins across authors, unchanged.

#### Scenario: Covered by the directory spec
- **WHEN** concurrent connection edits converge after the fold
- **THEN** the resolution rule is the directory's
