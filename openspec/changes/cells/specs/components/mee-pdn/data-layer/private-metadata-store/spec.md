# data-layer: private metadata store — delta for cells

## MODIFIED Requirements

### Requirement: Typed tickets, kind in the key

The ticket for a store of kind `k` SHALL be stored at path `tickets/<k>`, with the serialized ticket as the payload. Kinds are an open set of names. `data` is the kind under which the identity's own data-namespace ticket is published at creation — the durable record of the flat bootstrap model; the linking dialogue hands the bootstrap tickets over directly, so nothing in the linking critical path reads this entry (see [device-linking](../../pdn-node/device-linking/spec.md)). A connection's metadata pair is published under per-connection kinds keyed by the counterparty's `PdnId` (64 lowercase hex chars): the write ticket to the identity's own store toward peer `P` at kind `connection-metadata/<P-hex>/own`, and the received read ticket to the counterpart's store at kind `connection-metadata/<P-hex>/peer` — this is how establishment performed on one device reaches the identity's other devices, which open the pair from these tickets on demand. A [cell](../../../../architecture/language/cell.md)'s two stores are published under per-cell kinds keyed by the cell id (32 lowercase hex chars): the write ticket to its membership store at kind `cell/<cell-id-hex>/membership`, and the write ticket to its record store at kind `cell/<cell-id-hex>/records` — this is how a cell created or joined on one device reaches the identity's other devices, which open both stores from these tickets on demand. Each of the two tickets SHALL name the device that recorded it and, at a join, the inviting device as well, so that a device opening the cell from them — another device of the identity, or the recording device after a restart — has a member's device to dial without address lookup.

**Example:** the ticket entries in Bob's directory once he holds a connection to Alice and is a member of "Family"; `<alice-hex>`: 64 lowercase hex chars of Alice's `PdnId`.

| path | payload |
|---|---|
| `tickets/data` | the ticket to Bob's own data namespace |
| `tickets/connection-metadata/<alice-hex>/own` | the write ticket to Bob's store toward Alice |
| `tickets/connection-metadata/<alice-hex>/peer` | the read ticket to Alice's store toward Bob |
| `tickets/cell/9cbcbe4da7cc35a44360d64e45621957/membership` | the write ticket to the membership store of "Family" |
| `tickets/cell/9cbcbe4da7cc35a44360d64e45621957/records` | the write ticket to its record store |

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

The directory carries the identity's own device-internal state — its device set, its connections records, its cell records, its announcement key pair, and the tickets to its own stores, to its connections' metadata pairs and to the stores of the cells it is a member of. It SHALL NOT hold tickets to another identity's data stores: those travel only inside [connection metadata stores](../connection-metadata-store/spec.md), where the granting side can withdraw them, so no copy in a directory outlives the grant.

**Example:** what Bob's directory holds once he holds a connection to Alice, a grant from her, and a membership of "Family"; Bob's devices are his phone b1 and his laptop b2; `<b1-hex>`, `<b2-hex>`, `<alice-hex>`: 64 lowercase hex chars of each `NodeId` and of Alice's `PdnId`.

| entry | in Bob's directory |
|---|---|
| `devices/<b1-hex>`, `devices/<b2-hex>` | yes |
| `connections/<alice-hex>` | yes |
| `cells/9cbcbe4da7cc35a44360d64e45621957/1` | yes |
| `announcement-key` | yes |
| the tickets to Bob's own stores, to the connection's metadata pair and to both stores of "Family" | yes |
| the ticket to Alice's data namespace, which her grant carries | no: it sits in the connection metadata store Alice writes toward Bob |

#### Scenario: No counterparty data ticket in the directory

- **WHEN** establishment and a data-grant exchange with a peer complete
- **THEN** the receiving identity's directory contains the metadata-pair kinds for that peer and no ticket to the peer's data namespace — the data-store ticket is read from the metadata store

## ADDED Requirements

### Requirement: One announcement key pair per identity, at a fixed path

An identity's device-announcement key pair (cells D16) SHALL be minted when the identity is created and stored in its directory at path `announcement-key`, the serialized key pair as the payload, written once and never rewritten. It replicates to the identity's other devices like every directory entry, so every device of the identity holds the same key pair, and reading it SHALL return it only once its payload bytes have arrived. The key pair is one per identity and serves every cell the identity is a member of; no cell kind carries a copy.

**Example:** Alice is created on her phone a1 and her laptop a2 is linked into her; her announcement key pair is the one whose secret is 32 bytes of `33`.

| state | the entry at `announcement-key` on a2 | a read of the key pair on a2 |
|---|---|---|
| a1 has created Alice | absent | nothing yet |
| a2 linked, the entry's record arrived, its payload bytes not | present | nothing yet |
| the payload bytes arrived | present | the pair whose public key is `17cb79fb2b4120f2b1ec65e4198d6e08b28e813feb01e4a400839b85e18080ce`, the one a1 holds |
| On Alice's tablet a3, which hosts both of her identities — Alice-leisure, the one above, and Alice-work — each directory holds a pair of its own at `announcement-key`: Alice-leisure's with the public key `17cb79fb2b4120f2b1ec65e4198d6e08b28e813feb01e4a400839b85e18080ce`, Alice-work's with `d759793bbc13a2819a827c76adb6fba8a49aee007f49f2d0992d99b825ad2c48`. | | |

#### Scenario: The announcement key reaches a linked device

- **WHEN** an identity is created on the phone and a laptop is linked into it
- **THEN** the laptop reads from its directory replica, once the payload arrives, the same announcement key pair the phone holds

#### Scenario: Co-hosted identities hold their own announcement keys

- **WHEN** a node hosts identities A and B
- **THEN** each directory holds its own announcement key pair and the two differ; denied: a device of B only, requesting a session for A's directory, obtains no session and no entry of it

### Requirement: One entry per membership event of the identity, cell id and sequence in the key

A cell the identity creates or joins SHALL be recorded by a directory entry at path `cells/<cell-id-hex>/<seq>` — 32 lowercase hex chars of the cell id, then the sequence, in the identity's own chain in the cell's membership store, of the founding or joined event the entry records — written by the device that creates or joins, a joining device writing it at the sequence the join dialogue names, before its catch-up; leaving the cell, or learning of the identity's kick from it, SHALL write a pdn-store tombstone at `cells/<cell-id-hex>/<seq>`, `<seq>` being the sequence of the left or kicked event. A cell SHALL count as held if and only if the entry at its highest sequence across all authors has non-zero length, a tombstone outweighing a non-empty entry at one sequence, and SHALL NOT be judged by entry timestamps, so a later join after a leave holds it again and a leave from a device whose clock runs behind still ends holding; the payload is opaque, and listing the held cells SHALL read records alone, before any payload arrives.

**Example:** Bob's phone b1, whose clock is right, and his laptop b2, whose clock runs 80 minutes behind, act on his membership of "Family".

| real time | device | act | entry | entry timestamp |
|---|---|---|---|---|
| 10:00 | b1 | Bob joins "Family", at his sequence 1 | `cells/9cbcbe4da7cc35a44360d64e45621957/1`, b1's author, non-empty | 10:00 |
| 11:00 | b2 | Bob leaves it, at his sequence 2 | `cells/9cbcbe4da7cc35a44360d64e45621957/2`, b2's author, length 0: the tombstone | 09:40 |
| after sync both read the tombstone at the highest sequence: neither lists the cell as held | | | | |
| 12:00 | b1 | Bob joins again on a new invite, at his sequence 3 | `cells/9cbcbe4da7cc35a44360d64e45621957/3`, b1's author, non-empty: the cell is held on both again | 12:00 |

#### Scenario: A created cell is recorded on the identity's other devices

- **WHEN** the identity creates a cell on the phone and the laptop's directory replica syncs
- **THEN** the laptop lists the cell among the held cells, without waiting on payload content

#### Scenario: A leave ends holding on every device

- **WHEN** the identity leaves a cell on the phone, while the cell was held on the laptop too, and the laptop's directory replica syncs
- **THEN** the laptop no longer lists the cell as held

#### Scenario: A leave from a device whose clock runs behind ends holding

- **WHEN** the identity joins a cell on one device and later leaves it on another whose clock runs an hour behind the first's, and the two directory replicas sync
- **THEN** neither device lists the cell as held, although the tombstone's timestamp is the older of the two entries
