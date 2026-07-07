# Private metadata store

## Purpose

Device-replicated registry of an identity's own infrastructure: its devices and the tickets to its other stores. A dedicated pdn-store replica, one per identity, replicated across that identity's devices; it is the bootstrap **directory** device linking reads — see [device-linking.md](device-linking.md) for the procedure; this spec covers the store itself. Access is bounded by possession of the store's ticket (Invariant 1). Removing a device from the set is not provided at this stage — with bearer tickets, removal would not revoke access anyway; identity-bound, revocable access lands with UWill.

## Requirements

### Requirement: The directory lives in a dedicated replica
An identity's private metadata SHALL be stored in its own pdn-store replica, separate from every data store, from the connections store, and from every other identity's private metadata store. The store handle returned at creation or import is how the replica is addressed; no domain `NamespaceId` is allocated for it. Private metadata stores of several identities SHALL coexist on one node without sharing a replica.

#### Scenario: Creating the store allocates a dedicated replica
- **WHEN** a node creates a private metadata store
- **THEN** a fresh pdn-store replica is created for it, reached through the returned store handle, and no domain `NamespaceId` is allocated

#### Scenario: Two identities' directories on one node
- **WHEN** private metadata stores are created on one node for identity A and identity B
- **THEN** they are two distinct replicas, and records written under A are invisible under B

### Requirement: One entry per device, node id in the key
A device SHALL be recorded by an entry at path `devices/<node-id>` (64 lowercase hex chars of the device's `NodeId`). The payload SHALL be treated as opaque: device-set membership MUST NOT depend on payload bytes.

#### Scenario: Registering a device writes the record
- **WHEN** `add_device` is called with a device's node id
- **THEN** an entry exists at `devices/<node-id>` in the replica

#### Scenario: Registration is idempotent
- **WHEN** the same device is registered twice
- **THEN** the device set contains that device once

### Requirement: The device set reads at record level
Listing devices SHALL depend only on entry records, never on payload bytes, so the device set is visible as soon as records sync — before any payload is fetched.

#### Scenario: A device is listed as soon as its record arrives
- **WHEN** a device record has replicated to another device of the identity
- **THEN** `list_devices` there includes it, without waiting on payload content

### Requirement: Typed tickets, kind in the key
The ticket for a store of kind `k` SHALL be stored at path `tickets/<k>`, with the serialized ticket as the payload. Kinds are an open set of names; `connections` is the kind device linking discovers (see [device-linking.md](device-linking.md)).

#### Scenario: A published ticket round-trips
- **WHEN** a ticket is published under a kind on one device and read on another after replication
- **THEN** the ticket read equals the ticket published

### Requirement: Ticket reads wait for content
Reading a ticket SHALL return it only once its payload bytes have arrived: an entry whose record has synced but whose payload has not yet been fetched SHALL read as absent. Entry records and payloads travel independently, so "record present" precedes "ticket readable"; consumers poll until the payload lands.

#### Scenario: Record without payload reads as absent
- **WHEN** a ticket entry's record has synced to a device but its payload bytes have not yet been fetched
- **THEN** reading that ticket returns absent, and a later read (after the payload arrives) returns the ticket

### Requirement: Mutations replicate between devices
Directory mutations performed on one device SHALL become visible on the identity's other devices through standard pdn-store sync (set reconciliation for catch-up, gossip for live updates), with no additional transport or server.

#### Scenario: Registration on one device, observed on another
- **WHEN** a device registers itself while another device of the identity is reachable
- **THEN** the other device's view of the device set eventually contains it

### Requirement: Concurrent edits resolve by last-writer-wins
Concurrent mutations of the same key on different devices SHALL resolve on every device to the entry with the newest timestamp (pdn-store per-key LWW across authors), with equal timestamps broken deterministically by content hash.

#### Scenario: Concurrent ticket updates converge
- **WHEN** two devices concurrently publish a ticket under the same kind and then sync
- **THEN** both devices resolve to the same single ticket
