# data-layer: private metadata store — delta for cells

## MODIFIED Requirements

### Requirement: Typed tickets, kind in the key

The ticket for a store of kind `k` SHALL be stored at path `tickets/<k>`, with the serialized ticket as the payload. Kinds are an open set of names. `data` is the kind under which the identity's own data-namespace ticket is published at creation — the durable record of the flat bootstrap model; the linking dialogue hands the bootstrap tickets over directly, so nothing in the linking critical path reads this entry (see [device-linking](../../pdn-node/device-linking/spec.md)). A connection's metadata pair is published under per-connection kinds keyed by the counterparty's `PdnId` (64 lowercase hex chars): the write ticket to the identity's own store toward peer `P` at kind `connection-metadata/<P-hex>/own`, and the received read ticket to the counterpart's store at kind `connection-metadata/<P-hex>/peer` — this is how establishment performed on one device reaches the identity's other devices, which open the pair from these tickets on demand. A cell's two stores are published under per-cell kinds keyed by the cell id (32 lowercase hex chars): the write ticket to its membership store at kind `cell/<cell-id-hex>/membership`, and the write ticket to its record store at kind `cell/<cell-id-hex>/records` — this is how a cell created or joined on one device reaches the identity's other devices, which open both stores from these tickets on demand.

#### Scenario: A published ticket round-trips

- **WHEN** a ticket is published under a kind on one device and read on another after replication
- **THEN** the ticket read equals the ticket published

#### Scenario: The pair's tickets are discoverable on a linked device

- **WHEN** establishment publishes the `own` and `peer` kinds for a counterparty on the phone, and a laptop is linked into the identity
- **THEN** the laptop reads both tickets from its directory replica after replication, keyed by that counterparty

#### Scenario: The data ticket is published at creation

- **WHEN** an identity is created and a second device is linked
- **THEN** the linked device eventually reads the identity's data-namespace ticket under the `data` kind from its directory replica

#### Scenario: A cell's tickets are discoverable on a linked device

- **WHEN** the identity creates or joins a cell on the phone, and a laptop is linked into the identity
- **THEN** the laptop reads both write tickets from its directory replica after replication, under `cell/<cell-id-hex>/membership` and `cell/<cell-id-hex>/records` for that cell

### Requirement: The directory routes; grants live in connection metadata stores

The directory carries the identity's own device-internal state — its device set, its connections records, its announcement key pair, and the tickets to its own stores, to its connections' metadata pairs and to the stores of the cells it is a member of. It SHALL NOT hold tickets to another identity's data stores: those travel only inside [connection metadata stores](../connection-metadata-store/spec.md), where the granting side can withdraw them, so no copy in a directory outlives the grant.

#### Scenario: No counterparty data ticket in the directory

- **WHEN** establishment and a data-grant exchange with a peer complete
- **THEN** the receiving identity's directory contains the metadata-pair kinds for that peer and no ticket to the peer's data namespace — the data-store ticket is read from the metadata store

## ADDED Requirements

### Requirement: One announcement key pair per identity, at a fixed path

An identity's device-announcement key pair (cells D16) SHALL be minted when the identity is created and stored in its directory at path `announcement-key`, the serialized key pair as the payload, written once and never rewritten. It replicates to the identity's other devices like every directory entry, so every device of the identity holds the same key pair, and reading it SHALL return it only once its payload bytes have arrived. The key pair is one per identity and serves every cell the identity is a member of; no cell kind carries a copy.

#### Scenario: The announcement key reaches a linked device

- **WHEN** an identity is created on the phone and a laptop is linked into it
- **THEN** the laptop reads from its directory replica, once the payload arrives, the same announcement key pair the phone holds

#### Scenario: Co-hosted identities hold their own announcement keys

- **WHEN** a node hosts identities A and B
- **THEN** each directory holds its own announcement key pair and the two differ; denied: a device of B only, requesting a session for A's directory, obtains no session and no entry of it
