# Key event store

Where an identity's key events live and how their complete validation inputs reach the runtime. The events sit in the identity's [private metadata directory](../data-layer-private-metadata-store/spec.md), so an identity keeps exactly one device-internal replica and no second store can silently fall behind. What the events mean — root identifiers, delegated devices, store commitments, and the accepted branch — is [keri-identity](../pdn-node-keri-identity/spec.md); this capability covers storage, payload integrity, enumeration, and payload-arrival notification only.

The runtime-owned durable view that consumes this store presupposes the `durable-runtime-storage` change that SHALL land before implementation of this change begins. Its durability is not an optional requirement that may be removed to land an in-process subset.

## ADDED Requirements

### Requirement: Key events are entries of the directory, addressed by content
A key event SHALL be stored as an entry of the identity's directory replica under the disjoint family `kel/<aid-hex>/<sn-16hex>/<event-content-digest-64hex>`, where the identifier and digest encodings are lowercase hexadecimal and the path sequence number is the event's profile-1 `u64` sequence rendered as exactly 16 lowercase hexadecimal digits with leading zeros. `event-content-digest` SHALL mean the unqualified 32-byte BLAKE3-256 digest of the exact final serialized event bytes as stored, after all SAID fields are populated. It is a storage content address and is deliberately distinct from the event's normative `d` SAID, which is derived through profile-1 dummy serialization; neither value may be substituted for the other. The event itself uses the wire profile's minimal canonical sequence spelling (`0`, otherwise no leading zero); parse and range validation SHALL occur before producing the padded path component. The 3 key components identify the event's identifier, sequence number, and storage content digest — so 2 events that claim the same position in a log are 2 entries, not 1. Keying without the digest would collapse a competing version by last-writer-wins when both come from 1 author, and would leave the outcome to how a reader queries when they come from different authors; addressing by content removes the choice from the store. The `kel/` prefix SHALL be disjoint from every device, ticket, connection, and retraction family.

The payload SHALL be exactly the canonical `KEL1` container defined by `pdn-node-keri-wire-profile`. The wire profile is the sole owner of its format and shared 61,440-byte signed-event-material limit. The store SHALL enforce that limit before accepting or allocating from an announced event length, require exactly one complete event and indexed signature, and reject alternate tags, extra attachments, non-canonical lengths, or trailing bytes. Conversion to or from a linking `PDL1/0x02` body SHALL preserve the event JSON and indexed-signature bytes exactly rather than parse and reserialize them. The store SHALL NOT admit an event that profile 1 cannot replay to another device.

The event-content digest in the key covers the exact final `event-json` bytes and not the `KEL1` tag, length, or signature, so the payload is a function of the key only under a profile that fixes the attachments: this change SHALL use one signing key, a threshold of one, a single-key pre-rotation commitment, and a deterministic signature scheme, which makes one author's payload for one event a single fixed byte string and a rewrite byte-identical. A profile with several signers, or one where partial sets of signatures arrive separately, SHALL NOT be layered onto these keys unchanged: two valid payloads under one key would collapse by last-writer-wins and lose signatures, so such a profile needs the attachment set inside the address or a deterministic merge, and both are outside this change.

Before an entry can affect the accepted view, the reader SHALL parse its payload, recompute the storage event-content digest over the exact final bytes, independently verify the event's `d` through profile-1 SAIDification, and require the payload's identifier, sequence number, and recomputed content digest to equal the three corresponding components of the entry key. A mismatch in either digest SHALL leave the accepted head unchanged and SHALL be surfaced as malformed key-event material; trusting the key's claimed content digest or treating `d` as that digest would defeat the content-addressing and SAID rules above.

A device SHALL write into the replica only the events it is the controller of: its own device events, and the events of the identity's root while it holds the root's keys — which in this change means the founding device, writing the root's inception and the seal that delegates the first device into a replica nothing has yet replicated. Events of other devices SHALL arrive by replication and SHALL NOT be re-authored locally: a device that copied another device's event under its own author id would turn one event into two records and make the entry count meaningless. A device MAY hold events it has verified but not yet received by replication — the ones a linking reply handed it — in the runtime-owned accepted view, which is local and answers to no author.

The directory is the only replicated home of an identity's key events: no second replicated copy SHALL be kept. The runtime-owned accepted view is not a copy in that sense — it is local, unreplicated, and may hold an event verified in a ceremony before that event has replicated in. Before an identity's directory has been prepared — the first window inside creation — the durable state SHALL be the key material and creation record only; once prepared, events are derived deterministically and written there ([device-linking](../pdn-node-device-linking/spec.md)).

#### Scenario: Competing versions coexist
- **WHEN** two events claiming one identifier's sequence number, with different digests, are present
- **THEN** the replica holds both as separate entries, and neither displaces the other

#### Scenario: KEL payload encoding is exact

- **WHEN** an entry payload has another tag, a non-canonical length, a second attachment, or trailing bytes after its one indexed signature
- **THEN** it is malformed and cannot affect the accepted view even if its event JSON and signature could be extracted

#### Scenario: The same event under one author is one entry
- **WHEN** a device writes an event it already wrote, byte for byte
- **THEN** the replica holds one entry for it under that author

#### Scenario: One event yields one payload under this profile
- **WHEN** a device re-derives and rewrites one of its own events after a restart
- **THEN** the payload it writes is byte-identical to the one already there, so no signature set is displaced by another

#### Scenario: Two authors do not merge into one entry
- **WHEN** two devices of an identity each write the same event bytes
- **THEN** the replica holds two entries, because a record is identified by namespace, author, and key — which is why the accepted branch is decided by the view below and not by counting entries

#### Scenario: No events exist before the directory does
- **WHEN** a creation is interrupted after its key material is durable and before its directory exists
- **THEN** no key event is stored anywhere else, and the resumed creation derives the same events into the directory once it is created

#### Scenario: The payload must match its content address
- **WHEN** a key-event entry's payload carries another identifier or sequence number, its recomputed event-content digest differs from the key, or its independently recomputed `d` SAID differs from the event
- **THEN** it does not enter or advance the accepted view, the accepted head is unchanged, and the malformed material is reported

### Requirement: Key-event reads preserve every runtime validation input
The store SHALL enumerate every candidate key-event entry for an identity without selecting an accepted branch, resolving a competing version, or treating replica arrival order as authority. It SHALL expose each record's content-address components and whether its payload bytes are readable, and SHALL notify the runtime when previously missing payload bytes arrive so the runtime can re-evaluate its own durable accepted-history view. Accepted-head, awaiting-delegation, gap, and discrepancy semantics are owned normatively by [keri-identity](../pdn-node-keri-identity/spec.md), not by this storage capability.

An event authored by another device that is presented during a ceremony MAY be held by the runtime's local accepted-history state before replication delivers it, but SHALL NOT be written into the directory under the receiving device's author id.

#### Scenario: Competing candidates are both returned
- **WHEN** 2 readable entries claim the same identifier and sequence number with different event-content digests
- **THEN** the store returns both candidates and makes no accepted-head choice between them

#### Scenario: An out-of-order candidate receives no storage verdict
- **WHEN** an entry beyond the runtime's current head is readable before an intervening event
- **THEN** the store returns it without classifying it as accepted, awaiting, or discrepant

#### Scenario: Payload arrival triggers re-evaluation input
- **WHEN** a key-event record is present before its payload and the payload later becomes readable
- **THEN** the store notifies the runtime and returns the complete candidate on the next read

#### Scenario: An event authored elsewhere is not re-authored here
- **WHEN** a device holds an event of another device that it verified during a ceremony
- **THEN** it keeps that event in runtime-owned local state and does not write it into the replica under its own author id

### Requirement: Ingest checking stays where the material is available
Validation of key events SHALL NOT be placed in the replica's ingest hook: that hook receives a signed entry and the sending peer, never the event's bytes, and it is not consulted for a device's own writes — so signatures, digest chaining, and delegation cannot be decided there. The checks SHALL run in the runtime where the payload and accepted-history state are available.

#### Scenario: A locally written event is checked
- **WHEN** a device writes a key event into its own directory
- **THEN** that event is checked on the path that builds the accepted view, not skipped as ingest checking would skip it
