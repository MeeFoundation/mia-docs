## REMOVED Requirements

### Requirement: Typed tickets, kind in the key

**Reason**: Two of its kinds go with this change — `data`, the identity's own data-namespace ticket, and `connection-metadata/<P-hex>/own` and `/peer`, a connection's metadata pair — and their scenarios with them; the requirement returns as "A ticket is stored under its kind", carrying the kinds of a pod's stores.

**Migration**: A PMS a build with connections wrote keeps entries under `tickets/data` and `tickets/connection-metadata/`; nothing reads them, and such a directory is not supported by this build.

### Requirement: The PMS routes; grants live in connection metadata stores

**Reason**: It keeps tickets to another identity's data stores out of the PMS, and no such store exists once the data namespace and grants go.

**Migration**: None.

### Requirement: One entry per connection, counterparty in the key

**Reason**: Connections are removed by this change.

**Migration**: None: a relationship between two identities is a pod of two.

### Requirement: Disconnect is a tombstone

**Reason**: Connections are removed by this change.

**Migration**: Leaving a pod writes its own tombstone, as "One entry per membership event of the identity, pod id and sequence in the key" states.

### Requirement: Retraction markers, granted issuer in the key

**Reason**: Writer-side retraction exists for a write a grant's issuer refused, and grants are removed by this change.

**Migration**: None: a pod's store holds whatever a session carries, so no write into it is refused and retracted.

## MODIFIED Requirements

### Requirement: Pending device records are disjoint from the device set
A device that a linking dialogue registered before its reply could be known to have arrived SHALL be recorded at `pending-devices/<node-id>`, a prefix disjoint from `devices/`, with a payload carrying the record's creation time. A pending record SHALL confer nothing: session classification reads `devices/` alone. The device promotes itself with `confirm_device`, which tombstones the pending record and writes the device record in one act. Cleanup runs before every pending listing and after every linking import, judges by its own clock, and SHALL treat each pending record by its payload. A record whose payload is the version byte `01` followed by the creation time as Unix seconds in an 8-byte big-endian integer SHALL be tombstoned once it is 24 hours old. A record whose payload is a bare `01` carries no creation time and SHALL be rewritten with the cleanup's time, so it expires 24 hours from then. Any other payload opening with `01` — a wrong length, or a time past the range of the system clock — is malformed, and its record SHALL be tombstoned at once, whatever its age. A record whose payload opens with any other version byte SHALL be left untouched, so a record a newer build wrote never expires on this one. A record whose payload has not arrived is skipped until it does.

**Example:** cleanup in Alice's PMS at 2026-09-27 12:00:00 UTC; a2 to a6 have begun linking and not confirmed; payload: the version byte `01`, then the creation time as Unix seconds in a big-endian `u64`.

| key | payload | created | cleanup |
|---|---|---|---|
| `pending-devices/<a2-hex>` | `01 00 00 00 00 6a b7 b3 c0` | 2026-09-26 12:00:00 | tombstones it: 24 hours old |
| `pending-devices/<a3-hex>` | `01 00 00 00 00 6a b8 f7 30` | 2026-09-27 11:00:00 | leaves it: 1 hour old |
| `pending-devices/<a4-hex>` | `01` | none | rewrites it with the cleanup's time: `01 00 00 00 00 6a b9 05 40` |
| `pending-devices/<a5-hex>` | `01 00 00 6a b8` | unreadable | tombstones it at once: 4 bytes of time, not 8 |
| `pending-devices/<a6-hex>` | `02 00 00 00 00 6a b7 b3 c0` | unknown to this build | leaves it, now and at every later cleanup |
| `list_devices` names none of the five; a3's `confirm_device` tombstones its pending record and writes `devices/<a3-hex>` | | | |

#### Scenario: A pending record grants nothing
- **WHEN** a device is recorded as pending in an identity's PMS
- **THEN** the device set does not list it, and a session from it is classified as a stranger's

#### Scenario: An abandoned pending record expires
- **WHEN** a pending record is 24 hours old and its device never confirmed
- **THEN** cleanup tombstones it, and a record younger than that stays

### Requirement: Ticket reads wait for content
Reading a ticket SHALL return it only once its payload bytes have arrived: an entry whose record has synced but whose payload has not yet been fetched SHALL read as absent. Entry records and payloads travel independently, so "record present" precedes "ticket readable"; consumers poll until the payload lands.

**Example:** a2 reads Alice's PMS while the entry at `tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/membership` travels from a1.

| state on a2 | `list_ticket_kinds` | `get_ticket("pod/ad58a3faa04cdc5576c8dc5823a347c6/membership")` |
|---|---|---|
| nothing arrived | `[]` | `Ok(None)` |
| entry record arrived, payload bytes not | `["pod/ad58a3faa04cdc5576c8dc5823a347c6/membership"]` | `Ok(None)` |
| payload bytes arrived | `["pod/ad58a3faa04cdc5576c8dc5823a347c6/membership"]` | `Ok(Some(ticket))` |

#### Scenario: Record without payload reads as absent
- **WHEN** a ticket entry's record has synced to a device but its payload bytes have not yet been fetched
- **THEN** reading that ticket returns absent, and a later read (after the payload arrives) returns the ticket

### Requirement: Concurrent edits resolve by last-writer-wins
Concurrent mutations of the same key on different devices SHALL resolve on every device to the entry with the newest timestamp (pdn-store per-key LWW across authors), with equal timestamps broken deterministically by content hash.

**Example:** Alice's phone p and laptop l publish a ticket at `tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/membership` concurrently, each with its own author.

| p's entry | l's entry | every device reads |
|---|---|---|
| timestamp t1 | timestamp t2, above t1 | l's ticket |
| timestamp t1 | timestamp t1 | the ticket whose content hash is larger, compared byte by byte |

#### Scenario: Concurrent ticket updates converge
- **WHEN** two devices concurrently publish a ticket under the same kind and then sync
- **THEN** both devices resolve to the same single ticket

## ADDED Requirements

### Requirement: A ticket is stored under its kind

The ticket for a store of kind `k` SHALL be stored at path `tickets/<k>`, with the serialized ticket as the payload. Kinds are an open set of names. A [pod](../../../../architecture/language/pod.md)'s two stores are published under per-pod kinds keyed by the pod id (32 lowercase hex chars): the write ticket to its membership store at kind `pod/<pod-id-hex>/membership`, and the write ticket to its record store at kind `pod/<pod-id-hex>/records` — this is how a pod created or joined on one device reaches the identity's other devices, which open both stores from these tickets on demand. Each of the two tickets SHALL name the device that recorded it, as the identity's own. At a join, the tickets the inviting device handed over SHALL be published beside them, unchanged, at kinds `pod/<pod-id-hex>/inviter/membership` and `pod/<pod-id-hex>/inviter/records`, naming the inviting device as the identity it holds the stores for: a ticket names all its nodes as the one identity that minted it, so a device named in another identity's ticket would be dialed as an identity it does not hold. A device opening the pod from them — another device of the identity, or the recording device after a restart — dials the nodes of both, each as its own ticket names it, so it has a member's device to dial without address lookup before its membership view lists anyone.

**Example:** the ticket entries in Bob's PMS once he has joined "Family" from his phone b1 on the invitation of Alice's phone a1.

| path | payload |
|---|---|
| `tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/membership` | the write ticket to the membership store of "Family", naming b1 as Bob |
| `tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/records` | the write ticket to its record store, naming b1 as Bob |
| `tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/inviter/membership` | the write ticket to the membership store a1 handed over, naming a1 as Alice |
| `tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/inviter/records` | the write ticket to the record store a1 handed over, naming a1 as Alice |

#### Scenario: A published ticket round-trips

- **WHEN** a ticket is published under a kind on one device and read on another after replication
- **THEN** the ticket read equals the ticket published

#### Scenario: A pod's tickets are discoverable on a linked device

- **WHEN** the identity creates or joins a pod on the phone, and a laptop is linked into the identity
- **THEN** the laptop reads both write tickets from its PMS replica after replication, under `pod/<pod-id-hex>/membership` and `pod/<pod-id-hex>/records` for that pod, and for a joined pod the two the inviting device handed over as well, under `pod/<pod-id-hex>/inviter/membership` and `pod/<pod-id-hex>/inviter/records`
