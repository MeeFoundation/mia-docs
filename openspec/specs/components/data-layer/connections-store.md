# Connections store

## Purpose

Device-replicated registry of a user's connections: a dedicated pdn-store replica, separate from data namespaces, replicated across all of one identity's devices. Its entries pass the ingest gate via Invariant 1 (see [ingest-policies.md](ingest-policies.md)); having the gate *read* this store to admit data is a deferred follow-up. This spec covers the store and its replication between devices.

## Requirements
### Requirement: Connections live in a dedicated replica
Connection state SHALL be stored in its own pdn-store replica, separate from every data namespace. The replica SHALL be bound in the node's registry as `Connections { identity }` (no domain `NamespaceId`); data namespaces keep the `(about, issued_by)` pair unchanged.

#### Scenario: Creating the store binds it by kind
- **WHEN** a node creates its connections store
- **THEN** a fresh pdn-store replica is created and bound as `Connections { identity: <local PdnId> }`, and no domain `NamespaceId` is allocated for it

#### Scenario: Importing the store on a second device
- **WHEN** a second device imports the connections store from a ticket
- **THEN** the replica is bound as `Connections { identity }` on that device and participates in sync with the first device

### Requirement: One entry per connection, identity in the key
A live connection to peer `P` SHALL be represented by an entry at path `connections/<P-hex>` (64 lowercase hex chars of the PdnId). The payload SHALL be treated as opaque: admission decisions MUST NOT depend on payload bytes.

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

### Requirement: The store bootstraps through its own gate
A device SHALL admit incoming connections-store entries of its own identity through Invariant 1 — decided without reading the store — so the gate does not block replication into a still-empty store.

#### Scenario: First sync into an empty store
- **WHEN** laptop imports the connections store ticket while laptop's connections replica is empty
- **THEN** entries authored on phone are admitted and persisted on laptop

### Requirement: Concurrent edits resolve by last-writer-wins
Concurrent mutations of the same connection key on different devices SHALL resolve on every device to the entry with the newest timestamp (pdn-store per-key LWW across authors), with tombstones participating like ordinary entries.

#### Scenario: Offline conflict resolves deterministically
- **WHEN** phone calls `connect(P)` and laptop calls `disconnect(P)` while partitioned, and the devices then sync
- **THEN** both devices resolve to the mutation with the newest timestamp

