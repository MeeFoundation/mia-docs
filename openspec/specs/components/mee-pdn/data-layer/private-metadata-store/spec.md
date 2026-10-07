# Private metadata store

## Purpose

The one device-replicated **directory** of an identity's own state: its devices — confirmed and pending — the tickets to its other stores, its connections records, and its write-retraction markers. A dedicated pdn-store replica, one per identity, replicated across that identity's devices; its ticket is what the linking dialogue hands to a new device — see [device-linking/spec.md](../../pdn-node/device-linking/spec.md) for the ceremony; this spec covers the store itself. Access is bounded by possession of the store's ticket (Invariant 1). Removing a device from the set is not provided at this stage — with bearer tickets, removal would not revoke access anyway; identity-bound, revocable access lands with UWill.

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

**Example:** Alice's directory once a1 has created Alice and a2 has linked; `<a1-hex>`, `<a2-hex>`: 64 lowercase hex chars of each `NodeId`.

| key | written by | payload |
|---|---|---|
| `devices/<a1-hex>` | a1, at create | `01` |
| `devices/<a2-hex>` | a2, by its `confirm_device` | `01` |
| `list_devices` answers a1 and a2; a second `add_device(a2)` replaces a2's entry, and a2 is still listed once | | |

#### Scenario: Registering a device writes the record
- **WHEN** `add_device` is called with a device's node id
- **THEN** an entry exists at `devices/<node-id>` in the replica

#### Scenario: Registration is idempotent
- **WHEN** the same device is registered twice
- **THEN** the device set contains that device once

### Requirement: Pending device records are disjoint from the device set
A device that a linking dialogue registered before its reply could be known to have arrived SHALL be recorded at `pending-devices/<node-id>`, a prefix disjoint from `devices/`, with a payload carrying the record's creation time. A pending record SHALL confer nothing: session classification and every published device set read `devices/` alone. The device promotes itself with `confirm_device`, which tombstones the pending record and writes the device record in one act. Cleanup runs before every pending listing and after every linking import, judges by its own clock, and SHALL treat each pending record by its payload. A record whose payload is the version byte `01` followed by the creation time as Unix seconds in an 8-byte big-endian integer SHALL be tombstoned once it is 24 hours old. A record whose payload is a bare `01` carries no creation time and SHALL be rewritten with the cleanup's time, so it expires 24 hours from then. Any other payload opening with `01` — a wrong length, or a time past the range of the system clock — is malformed, and its record SHALL be tombstoned at once, whatever its age. A record whose payload opens with any other version byte SHALL be left untouched, so a record a newer build wrote never expires on this one. A record whose payload has not arrived is skipped until it does.

**Example:** cleanup in Alice's directory at 2026-09-27 12:00:00 UTC; a2 to a6 have begun linking and not confirmed; payload: the version byte `01`, then the creation time as Unix seconds in a big-endian `u64`.

| key | payload | created | cleanup |
|---|---|---|---|
| `pending-devices/<a2-hex>` | `01 00 00 00 00 6a b7 b3 c0` | 2026-09-26 12:00:00 | tombstones it: 24 hours old |
| `pending-devices/<a3-hex>` | `01 00 00 00 00 6a b8 f7 30` | 2026-09-27 11:00:00 | leaves it: 1 hour old |
| `pending-devices/<a4-hex>` | `01` | none | rewrites it with the cleanup's time: `01 00 00 00 00 6a b9 05 40` |
| `pending-devices/<a5-hex>` | `01 00 00 6a b8` | unreadable | tombstones it at once: 4 bytes of time, not 8 |
| `pending-devices/<a6-hex>` | `02 00 00 00 00 6a b7 b3 c0` | unknown to this build | leaves it, now and at every later cleanup |
| `list_devices` names none of the five; a3's `confirm_device` tombstones its pending record and writes `devices/<a3-hex>` | | | |

#### Scenario: A pending record grants nothing
- **WHEN** a device is recorded as pending in an identity's directory
- **THEN** the device set does not list it, and a session from it is classified as a stranger's

#### Scenario: An abandoned pending record expires
- **WHEN** a pending record is 24 hours old and its device never confirmed
- **THEN** cleanup tombstones it, and a record younger than that stays

### Requirement: The device set reads at record level
Listing devices SHALL depend only on entry records, never on payload bytes, so the device set is visible as soon as records sync — before any payload is fetched.

#### Scenario: A device is listed as soon as its record arrives
- **WHEN** a device record has replicated to another device of the identity
- **THEN** `list_devices` there includes it, without waiting on payload content

### Requirement: Typed tickets, kind in the key

The ticket for a store of kind `k` SHALL be stored at path `tickets/<k>`, with the serialized ticket as the payload. Kinds are an open set of names. `data` is the kind under which the identity's own data-namespace ticket is published at creation — the durable record of the flat bootstrap model; the linking dialogue hands the bootstrap tickets over directly, so nothing in the linking critical path reads this entry (see [device-linking](../../pdn-node/device-linking/spec.md)). A connection's metadata pair is published under per-connection kinds keyed by the counterparty's `PdnId` (64 lowercase hex chars): the write ticket to the identity's own store toward peer `P` at kind `connection-metadata/<P-hex>/own`, and the received read ticket to the counterpart's store at kind `connection-metadata/<P-hex>/peer` — this is how establishment performed on one device reaches the identity's other devices, which open the pair from these tickets on demand. A [pod](../../../../architecture/language/pod.md)'s two stores are published under per-pod kinds keyed by the pod id (32 lowercase hex chars): the write ticket to its membership store at kind `pod/<pod-id-hex>/membership`, and the write ticket to its record store at kind `pod/<pod-id-hex>/records` — this is how a pod created or joined on one device reaches the identity's other devices, which open both stores from these tickets on demand. Each of the two tickets SHALL name the device that recorded it, as the identity's own. At a join, the tickets the inviting device handed over SHALL be published beside them, unchanged, at kinds `pod/<pod-id-hex>/inviter/membership` and `pod/<pod-id-hex>/inviter/records`, naming the inviting device as the identity it holds the stores for: a ticket names all its nodes as the one identity that minted it, so a device named in another identity's ticket would be dialed as an identity it does not hold. A device opening the pod from them — another device of the identity, or the recording device after a restart — dials the nodes of both, each as its own ticket names it, so it has a member's device to dial without address lookup before its replica folds anyone.

**Example:** the ticket entries in Bob's directory once he holds a connection to Alice and has joined "Family" from his phone b1 on the invitation of Alice's phone a1; `<alice-hex>`: 64 lowercase hex chars of Alice's `PdnId`.

| path | payload |
|---|---|
| `tickets/data` | the ticket to Bob's own data namespace |
| `tickets/connection-metadata/<alice-hex>/own` | the write ticket to Bob's store toward Alice |
| `tickets/connection-metadata/<alice-hex>/peer` | the read ticket to Alice's store toward Bob |
| `tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/membership` | the write ticket to the membership store of "Family", naming b1 as Bob |
| `tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/records` | the write ticket to its record store, naming b1 as Bob |
| `tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/inviter/membership` | the write ticket to the membership store a1 handed over, naming a1 as Alice |
| `tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/inviter/records` | the write ticket to the record store a1 handed over, naming a1 as Alice |

#### Scenario: A published ticket round-trips

- **WHEN** a ticket is published under a kind on one device and read on another after replication
- **THEN** the ticket read equals the ticket published

#### Scenario: The pair's tickets are discoverable on a linked device

- **WHEN** establishment publishes the `own` and `peer` kinds for a counterparty on the phone, and a laptop is linked into the identity
- **THEN** the laptop reads both tickets from its directory replica after replication, keyed by that counterparty

#### Scenario: The data ticket is published at creation

- **WHEN** an identity is created and a second device is linked
- **THEN** the linked device eventually reads the identity's data-namespace ticket under the `data` kind from its directory replica

#### Scenario: A pod's tickets are discoverable on a linked device

- **WHEN** the identity creates or joins a pod on the phone, and a laptop is linked into the identity
- **THEN** the laptop reads both write tickets from its directory replica after replication, under `pod/<pod-id-hex>/membership` and `pod/<pod-id-hex>/records` for that pod, and for a joined pod the two the inviting device handed over as well, under `pod/<pod-id-hex>/inviter/membership` and `pod/<pod-id-hex>/inviter/records`

### Requirement: The directory routes; grants live in connection metadata stores

The directory carries the identity's own device-internal state — its device set, its connections records, its pod records, its announcement key pair, and the tickets to its own stores, to its connections' metadata pairs and to the stores of the pods it is a member of. It SHALL NOT hold tickets to another identity's data stores: those travel only inside [connection metadata stores](../connection-metadata-store/spec.md), where the granting side can withdraw them, so no copy in a directory outlives the grant.

**Example:** what Bob's directory holds once he holds a connection to Alice, a grant from her, and a membership of "Family"; Bob's devices are his phone b1 and his laptop b2; `<b1-hex>`, `<b2-hex>`, `<alice-hex>`: 64 lowercase hex chars of each `NodeId` and of Alice's `PdnId`.

| entry | in Bob's directory |
|---|---|
| `devices/<b1-hex>`, `devices/<b2-hex>` | yes |
| `connections/<alice-hex>` | yes |
| `pods/ad58a3faa04cdc5576c8dc5823a347c6/1` | yes |
| `announcement-key` | yes |
| the tickets to Bob's own stores, to the connection's metadata pair and to both stores of "Family" | yes |
| the ticket to Alice's data namespace, which her grant carries | no: it sits in the connection metadata store Alice writes toward Bob |

#### Scenario: No counterparty data ticket in the directory

- **WHEN** establishment and a data-grant exchange with a peer complete
- **THEN** the receiving identity's directory contains the metadata-pair kinds for that peer and no ticket to the peer's data namespace — the data-store ticket is read from the metadata store

### Requirement: Ticket reads wait for content
Reading a ticket SHALL return it only once its payload bytes have arrived: an entry whose record has synced but whose payload has not yet been fetched SHALL read as absent. Entry records and payloads travel independently, so "record present" precedes "ticket readable"; consumers poll until the payload lands.

**Example:** a2 reads Alice's directory while the entry at `tickets/data` travels from a1.

| state on a2 | `list_ticket_kinds` | `get_ticket("data")` |
|---|---|---|
| nothing arrived | `[]` | `Ok(None)` |
| entry record arrived, payload bytes not | `["data"]` | `Ok(None)` |
| payload bytes arrived | `["data"]` | `Ok(Some(ticket))` |

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

**Example:** Alice's phone p and laptop l act on her connection to Bob while partitioned; `t1 < t2 < t3` are entry timestamps.

| device | act | entry at `connections/<bob-hex>` |
|---|---|---|
| p | `connect(Bob)` | p's author, t1, length 1, payload `01` |
| l | `disconnect(Bob)` | l's author, t2, length 0: the tombstone |
| after sync both read l's tombstone as the latest across authors: Bob is not live, and `list_connections` omits him | | |
| p connecting again at t3 makes p's entry the latest, and Bob is live on both | | |

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

**Example:** Alice's phone p and laptop l publish a ticket at `tickets/data` concurrently, each with its own author.

| p's entry | l's entry | every device reads |
|---|---|---|
| timestamp t1 | timestamp t2, above t1 | l's ticket |
| timestamp t1 | timestamp t1 | the ticket whose content hash is larger, compared byte by byte |

#### Scenario: Concurrent ticket updates converge
- **WHEN** two devices concurrently publish a ticket under the same kind and then sync
- **THEN** both devices resolve to the same single ticket

### Requirement: Retraction markers, granted issuer in the key

A write-retraction verdict SHALL be recorded as a directory entry at `retractions/<issuer-hex>/<author-hex>/<path>` — the granted data store's issuer, the retracted entry's author, and the retracted entry's path. The payload SHALL carry the bounding timestamp, the writing device's node id, and the retracted entry's content hash and timestamp; a marker acts once its payload is readable, since the bound lives in it. Markers replicate between the identity's devices like every directory entry, and only the identity's own devices ever write them (Invariant 1). A device SHALL prune only the markers it recorded, since deletion is per directory author: once a marker's entry ages past the retention window, the device drops it and reports its address, so the caller can disarm what that marker armed; and when the grant binder unbinds the issuer's withdrawn grant, the device drops every marker it recorded for that issuer. Neither prune touches a sibling's markers: they stay listed until the sibling prunes them, the marker of a device that never runs again is pruned by no device, and the aged prune reports only the addresses it dropped itself. A marker at one path SHALL leave the markers at every other path standing, a longer path beginning with the same bytes included; a bare re-grant of write SHALL NOT prune it, and a newer own write at the marked path is not matched by it. The consuming behaviour — removal, ingest refusal, the event — is [write retraction](../write-retraction/spec.md); this store carries the record.

**Example:** Bob's phone b1 records a verdict: Alice (issuer) refused b1's entry at `contact/phone`, timestamp t1 in microseconds.

```
key       retractions/<alice-hex>/<b1-author-hex>/contact/phone    the namespace's issuer, the entry's author, its path
payload   {"bound":<t1>,                                            entries of that author and path at or below t1
(JSON)     "decided_by":"<b1-node-id-hex>",                         the device that recorded the verdict
           "content_hash":[<32 numbers, one per byte>],             the retracted payload's address in the blob store
           "timestamp":<t1>}                                        the retracted entry's timestamp
```

#### Scenario: A marker round-trips between devices
- **WHEN** one device of the identity writes a retraction marker and a sibling's directory replica syncs
- **THEN** the sibling reads the marker with its bound, node id, content hash, and timestamp once the payload arrives

#### Scenario: Pruning follows the grant binding
- **WHEN** a device prunes an issuer's markers, as the grant binder's unbind does once the issuer's grant is withdrawn, while the device and a sibling both hold markers for that issuer
- **THEN** every marker that device recorded for the issuer is dropped, nested paths included, and the sibling's marker for the issuer and the device's markers for another issuer stay listed, on both devices

#### Scenario: Aged markers are pruned by the device that recorded them
- **WHEN** a marker this device recorded is older than the retention window and another is younger
- **THEN** the aged one is dropped and its address reported, and the younger one stays

#### Scenario: A marker at a path leaves the markers at longer paths

- **WHEN** a device records a marker for an entry at `contact/email` and then one for an entry at `contact`, under the same issuer and author
- **THEN** both markers list, on that device and on a sibling once its directory replica syncs

### Requirement: The replica reports its namespace and waits for a sync session
The directory SHALL expose the namespace of its replica, so a caller that imported it can name it to forget it, and SHALL offer a bounded wait for the first successful sync session of that replica which started after a given instant. The property waited on is "this replica has caught up with a peer" — a session that started and succeeded — not "some content arrived": polling contents cannot distinguish a replica that synced and found nothing new from one that never synced at all. A wait that elapses SHALL surface as a timeout, never as a hang. Importing a replica enrols it in the node's periodic reconcile pass with the ticket's contacts, and hosting the identity on it starts its first session ([identity-scoped replicas](../identity-scoped-replicas/spec.md)), so the wait needs no trigger of its own and a first exchange that fails is re-dialed within the wait's own budget. The wait watches the replica's events, and a watch left unread past its buffer drops them ([change subscription](../change-subscription/spec.md)): a session whose event it dropped goes unseen, and the wait then returns on the next session, one reconcile interval later at most.

**Example:** a2 links into Alice; the wait gets what the dialogue leaves of the HTTP host's default 30 s link budget; reconcile interval 10 s.

| session of Alice's directory replica on a2 | the wait |
|---|---|
| the first exchange with a1 fails | goes on waiting |
| the next reconcile pass, within 10 s, re-dials a1 and succeeds | returns `Ok(())` |
| that success's event dropped by a watch left unread | returns on the next session, within 10 s more |
| no successful session before the budget runs out | fails with `CatchUpTimeout`, and link rolls back |

#### Scenario: The wait returns on a successful session, not on content
- **WHEN** a directory replica is imported and a sync session with a peer holding it starts after the given instant and completes successfully
- **THEN** the wait returns; it would not have returned for a session that started before that instant, nor for one that failed

#### Scenario: A replica that cannot reach a peer times out
- **WHEN** no successful sync session of the replica starts after the given instant within the bound
- **THEN** the wait fails with a timeout, and the caller can tell it apart from a successful catch-up

### Requirement: One announcement key pair per identity, at a fixed path

An identity's device-announcement key pair SHALL be minted when the identity is created and stored in its directory at path `announcement-key`, the serialized key pair as the payload, written once and never rewritten. It replicates to the identity's other devices like every directory entry, so every device of the identity holds the same key pair, and reading it SHALL return it only once its payload bytes have arrived. The key pair is one per identity and serves every pod the identity is a member of; no pod kind carries a copy.

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

### Requirement: One entry per membership event of the identity, pod id and sequence in the key

A pod the identity creates or joins SHALL be recorded by a directory entry at path `pods/<pod-id-hex>/<seq>` — 32 lowercase hex chars of the pod id, then the sequence, in the identity's own chain in the pod's membership store, of the created or joined event the entry records — written by the device that creates or joins, a joining device writing it at the sequence the join dialogue names, before its catch-up; leaving the pod, or learning of the identity's removal from it, SHALL write a pdn-store tombstone at `pods/<pod-id-hex>/<seq>`, `<seq>` being the sequence of the left or removed event. A pod SHALL count as held if and only if the entry at its highest sequence across all authors has non-zero length, a tombstone outweighing a non-empty entry at one sequence, and SHALL NOT be judged by entry timestamps, so a later join after a leave holds it again and a leave from a device whose clock runs behind still ends holding; the payload is opaque, and listing the held pods SHALL read records alone, before any payload arrives.

**Example:** Bob's phone b1, whose clock is right, and his laptop b2, whose clock runs 80 minutes behind, act on his membership of "Family".

| real time | device | act | entry | entry timestamp |
|---|---|---|---|---|
| 10:00 | b1 | Bob joins "Family", at his sequence 1 | `pods/ad58a3faa04cdc5576c8dc5823a347c6/1`, b1's author, non-empty | 10:00 |
| 11:00 | b2 | Bob leaves it, at his sequence 2 | `pods/ad58a3faa04cdc5576c8dc5823a347c6/2`, b2's author, length 0: the tombstone | 09:40 |
| after sync both read the tombstone at the highest sequence: neither lists the pod as held | | | | |
| 12:00 | b1 | Bob joins again on a new invite, at his sequence 3 | `pods/ad58a3faa04cdc5576c8dc5823a347c6/3`, b1's author, non-empty: the pod is held on both again | 12:00 |

#### Scenario: A created pod is recorded on the identity's other devices

- **WHEN** the identity creates a pod on the phone and the laptop's directory replica syncs
- **THEN** the laptop lists the pod among the held pods, without waiting on payload content

#### Scenario: A leave ends holding on every device

- **WHEN** the identity leaves a pod on the phone, while the pod was held on the laptop too, and the laptop's directory replica syncs
- **THEN** the laptop no longer lists the pod as held

#### Scenario: A leave from a device whose clock runs behind ends holding

- **WHEN** the identity joins a pod on one device and later leaves it on another whose clock runs an hour behind the first's, and the two directory replicas sync
- **THEN** neither device lists the pod as held, although the tombstone's timestamp is the older of the two entries
