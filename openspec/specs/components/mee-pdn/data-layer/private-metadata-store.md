# Private metadata store

## Purpose

The one device-replicated **directory** of an identity's own state: its devices, the tickets to its other stores, its connections records, and its write-retraction markers. A dedicated pdn-store replica, one per identity, replicated across that identity's devices; its ticket is what the linking dialogue hands to a new device — see [device-linking.md](../pdn-node/device-linking.md) for the ceremony; this spec covers the store itself. Access is bounded by possession of the store's ticket (Invariant 1). Removing a device from the set is not provided at this stage — with bearer tickets, removal would not revoke access anyway; identity-bound, revocable access lands with UWill.

## Requirements

### Requirement: The directory lives in a dedicated replica
An identity's private metadata SHALL be stored in its own pdn-store replica, separate from every data store and from every other identity's private metadata store. The store handle returned at creation or import is how the replica is addressed; no domain `NamespaceId` is allocated for it. Private metadata stores of several identities SHALL coexist on one node without sharing a replica.

#### Scenario: Creating the store allocates a dedicated replica
- **WHEN** a node creates a private metadata store
- **THEN** a fresh pdn-store replica is created for it, reached through the returned store handle, and no domain `NamespaceId` is allocated

#### Scenario: Two identities' directories on one node
- **WHEN** private metadata stores are created on one node for identity A and identity B
- **THEN** they are two distinct replicas, and entries written under A are invisible under B

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
The ticket for a store of kind `k` SHALL be stored at path `tickets/<k>`, with the serialized ticket as the payload. Kinds are an open set of names. `data` is the kind under which the identity's own data-namespace ticket is published at creation — the durable record of the flat bootstrap model; the linking dialogue hands the bootstrap tickets over directly, so nothing in the linking critical path reads this entry (see [device-linking](../pdn-node/device-linking.md)). A connection's metadata pair is published under per-connection kinds keyed by the counterparty's `PdnId` (64 lowercase hex chars): the write ticket to the identity's own store toward peer `P` at kind `connection-metadata/<P-hex>/own`, and the received read ticket to the counterpart's store at kind `connection-metadata/<P-hex>/peer` — this is how establishment performed on one device reaches the identity's other devices, which open the pair from these tickets on demand.

#### Scenario: A published ticket round-trips
- **WHEN** a ticket is published under a kind on one device and read on another after replication
- **THEN** the ticket read equals the ticket published

#### Scenario: The pair's tickets are discoverable on a linked device
- **WHEN** establishment publishes the `own` and `peer` kinds for a counterparty on the phone, and a laptop is linked into the identity
- **THEN** the laptop reads both tickets from its directory replica after replication, keyed by that counterparty

#### Scenario: The data ticket is published at creation
- **WHEN** an identity is created and a second device is linked
- **THEN** the linked device eventually reads the identity's data-namespace ticket under the `data` kind from its directory replica

### Requirement: The directory routes; grants live in connection metadata stores
The directory carries the identity's own device-internal state — its device set, its connections records, and the tickets to its own stores and to its connections' metadata pairs. It SHALL NOT hold tickets to another identity's data stores: those travel only inside [connection metadata stores](connection-metadata-store.md), where the granting side can withdraw them, so no copy in a directory outlives the grant.

#### Scenario: No counterparty data ticket in the directory
- **WHEN** establishment and a data-grant exchange with a peer complete
- **THEN** the receiving identity's directory contains the metadata-pair kinds for that peer and no ticket to the peer's data namespace — the data-store ticket is read from the metadata store

### Requirement: Ticket reads wait for content
Reading a ticket SHALL return it only once its payload bytes have arrived: an entry whose record has synced but whose payload has not yet been fetched SHALL read as absent. Entry records and payloads travel independently, so "record present" precedes "ticket readable"; consumers poll until the payload lands.

#### Scenario: Record without payload reads as absent
- **WHEN** a ticket entry's record has synced to a device but its payload bytes have not yet been fetched
- **THEN** reading that ticket returns absent, and a later read (after the payload arrives) returns the ticket

### Requirement: One entry per connection, counterparty in the key
A live connection to peer `P` SHALL be represented by a directory entry at path `connections/<P-hex>` (64 lowercase hex chars of the counterparty's `PdnId`). The payload SHALL be treated as opaque, and liveness decisions MUST NOT depend on payload bytes: a connection is visible as soon as its record syncs, before any payload is fetched.

#### Scenario: Connect writes the marker entry
- **WHEN** `connect(P)` is called on a device
- **THEN** an entry exists at `connections/<P-hex>` in the directory replica with a non-zero length

#### Scenario: Connect on one device, observed on another
- **WHEN** the phone calls `connect(P)` while the phone and the laptop are reachable
- **THEN** the laptop's directory eventually lists `P` as a live connection, without waiting on payload content

### Requirement: Disconnect is a tombstone
`disconnect(P)` SHALL write a pdn-store tombstone (empty entry, length 0) at `connections/<P-hex>`. A connection SHALL be considered live if and only if the latest entry for its key across all authors has non-zero length; tombstones participate in per-key last-writer-wins like ordinary entries.

#### Scenario: Disconnect ends liveness
- **WHEN** `disconnect(P)` is called after a prior `connect(P)`
- **THEN** the latest entry at `connections/<P-hex>` is empty and the connection to `P` is not live

#### Scenario: Revocation propagates
- **WHEN** the phone calls `disconnect(P)` after `P` was live on the laptop
- **THEN** the laptop's directory eventually shows `P` as not live

#### Scenario: Offline conflict resolves deterministically
- **WHEN** the phone calls `connect(P)` and the laptop calls `disconnect(P)` while partitioned, and the devices then sync
- **THEN** both devices resolve to the mutation with the newest timestamp

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

### Requirement: Retraction markers, granted issuer in the key

A write-retraction verdict SHALL be recorded as a directory entry at `retractions/<issuer-hex>/<author-hex>/<path>` — the granted data store's issuer, the retracted entry's author, and the retracted entry's path. The payload SHALL carry the bounding timestamp, the writing device's node id, and the retracted entry's content hash and timestamp; a marker acts once its payload is readable, since the bound lives in it. Markers replicate between the identity's devices like every directory entry, and only the identity's own devices ever write them (Invariant 1). A marker SHALL be pruned when the entry it addresses can no longer win — superseded by a newer own entry at that author and path, or aged out by a retention window — or in bulk when the issuer's namespace binding is forgotten; a bare re-grant of write SHALL NOT prune it. The consuming behaviour — removal, ingest refusal, the event — is [write retraction](write-retraction.md); this store carries the record.

#### Scenario: A marker round-trips between devices
- **WHEN** one device of the identity writes a retraction marker and a sibling's directory replica syncs
- **THEN** the sibling reads the marker with its bound, node id, content hash, and timestamp once the payload arrives

#### Scenario: Pruning follows the grant binding
- **WHEN** the granted namespace of an issuer with live markers is forgotten
- **THEN** the directory carries no markers for that issuer afterwards

### Requirement: The replica reports its namespace and waits for a sync session
The directory SHALL expose the namespace of its replica, so a caller that imported it can name it to forget it, and SHALL offer a bounded wait for the first successful sync session of that replica which started after a given instant. The property waited on is "this replica has caught up with a peer" — a session that started and succeeded — not "some content arrived": polling contents cannot distinguish a replica that synced and found nothing new from one that never synced at all. A wait that elapses SHALL surface as a timeout, never as a hang. Importing a replica already starts its first session and enrols it in the node's periodic reconcile pass with the ticket's contacts, so the wait needs no trigger of its own and a first exchange that fails is re-dialed within the wait's own budget.

#### Scenario: The wait returns on a successful session, not on content
- **WHEN** a directory replica is imported and a sync session with a peer holding it starts after the given instant and completes successfully
- **THEN** the wait returns; it would not have returned for a session that started before that instant, nor for one that failed

#### Scenario: A replica that cannot reach a peer times out
- **WHEN** no successful sync session of the replica starts after the given instant within the bound
- **THEN** the wait fails with a timeout, and the caller can tell it apart from a successful catch-up
