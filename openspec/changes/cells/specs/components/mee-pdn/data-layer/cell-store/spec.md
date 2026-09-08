# data-layer: cell store

A cell is a space shared by 0..n members — identities, of persons or organizations — identified by a cell id that carries no key material. Its content lives in one dedicated pdn-store replica, the **cell store**, held whole by every device of every member: no egress filter runs inside a cell, member devices form the replica's swarm, and any member device catches up from any other. What keeps a cell honest is admission: a session is served to member devices only, and an entry is admitted by its author — a claim or an immutable-document from the devices of the member under whose name it sits, a mergeable-document's operation from any member's devices — judged on every member device, so that a forged entry stops at the first honest device it meets. The runtime's cells service ([pdn-node cells](../../pdn-node/cells/spec.md)) creates and joins cell stores; this spec covers the store itself.

## ADDED Requirements

### Requirement: A cell is one dedicated replica

A cell SHALL be served by exactly one pdn-store replica, its cell store, separate from every data store, every directory, every connection metadata store and every other cell's store. Two cells SHALL NOT share a replica, whatever their member sets. The store SHALL be addressed by the cell id, and no domain namespace id is allocated for it.

#### Scenario: Creating a cell allocates a dedicated replica

- **WHEN** a node creates a cell store
- **THEN** a fresh pdn-store replica is created for it, reached through the cell id, and no domain namespace id is allocated

#### Scenario: Two cells with the same members are two replicas

- **WHEN** the same identities are members of two cells and an entry is written into one of them
- **THEN** the entry never appears in the other cell's store

### Requirement: The cell id carries no key material

A cell SHALL be identified by a 32-byte cell id minted at creation. The id SHALL carry no key material and SHALL NOT equal the replica's namespace id: knowing the cell id grants no access, and no operation on a cell requires a signature by the cell — every write into the store is signed by the writing device's author key, and every membership act is a member's act.

#### Scenario: The cell id is not the namespace id

- **WHEN** a cell store is created
- **THEN** its cell id and its replica's namespace id differ

#### Scenario: Knowing the cell id is not holding the store

- **WHEN** a party knows a cell's id but holds no ticket to its store and is a device of no member
- **THEN** it obtains no session, no entry and no existence signal for the store

### Requirement: Every member device holds the whole store and the write ticket

Every device of every member SHALL hold the cell store whole and SHALL hold its write ticket: a session between two member devices delivers every entry with no egress filter, and authority to write inside the cell is judged by the ingest gate per entry, never by ticket mode. Member devices SHALL form the replica's swarm, so a write reaches the other member devices through the content-free announcement and the pull it triggers, and a member device SHALL be able to catch up from any other member device, not only from an entry's author.

#### Scenario: A write reaches a member through another member

- **WHEN** member A writes an entry, A's devices go offline, and a device of member C — which never synced with A — reconciles with a device of member B that holds the entry
- **THEN** C's device receives the entry, payload included

#### Scenario: A write arrives live over the swarm

- **WHEN** a member writes an entry while devices of the other members are members of the store's swarm
- **THEN** every such device converges on the entry through the announcement and a pull, none of them holding a grant

### Requirement: Only member devices are served

A session for a cell store SHALL be served only to a caller that resolves, by authenticated node id, as a device of a current member; every other caller SHALL be refused indistinguishably from the store not being hosted — a holder of the store's ticket included. A device of a member removed from the cell SHALL be refused from the first session set up after the removal record reaches the serving device; what it obtained while a member is retained.

#### Scenario: A member device is served whole

- **WHEN** a device of a current member requests a session for the store
- **THEN** the session is served and delivers every entry

#### Scenario: A ticket holder that is no member obtains nothing

- **WHEN** a caller holding the store's ticket but a device of no member requests a session
- **THEN** the request is refused with the answer an unhosted replica would produce, and no fingerprint, count or existence signal is revealed

#### Scenario: A removed member is refused from the next session

- **WHEN** a member is removed and the removal record has reached a serving device, and a device of the removed member then requests a session
- **THEN** the request is refused as for an unhosted replica, while the remaining members' devices are still served, and what the removed device obtained while a member is still readable on it

### Requirement: Membership needs no connection

Access to a cell store SHALL rest on membership alone: no connection between two members is required for either to read what the other wrote, and joining a cell SHALL create no connection.

#### Scenario: Three identities share through a cell with no connections

- **WHEN** identities A, B and C hold no connection to one another, A creates a cell and invites B and C, and B writes an entry
- **THEN** C's device reads the entry, and no identity lists any connection

### Requirement: A claim is written only by its issuer

An entry that is a claim SHALL be admitted over sync only when it was authored by a device of the member the claim names as its issuer. A claim entry authored by a device of any other member SHALL be dropped before persisting, on every member device, silently — the verdict is on the entry's author, not on the session peer that carried it, so an entry relayed by a third member keeps the verdict its author earns.

#### Scenario: The issuer's own claim is admitted

- **WHEN** a device of member A writes a claim issued by A and a device of member B reconciles
- **THEN** B's device persists the claim

#### Scenario: Another member's entry under the issuer's claims is dropped

- **WHEN** a device of member B produces an entry that names A as the claim's issuer and reconciles with a device of A or of a third member
- **THEN** the entry is not persisted, no rejection is signalled, and A's own claim at that key survives unchanged

#### Scenario: A relayed claim is judged by its author

- **WHEN** a device of member C receives, from a device of member B, a claim authored by a device of A that names A as issuer
- **THEN** C's device persists it, although the session peer is B

### Requirement: A mergeable-document is edited by every member

A document SHALL be readable by every member. An operation on a mergeable-document SHALL be admitted from a device of any current member, whoever's name the document sits under, each operation carrying its writer's author signature. The one ground for dropping an operation is its author: an operation authored by a key that resolves to no current member's device SHALL be dropped before persisting, silently, on every member device — no role, no document and no time of authoring narrows admission further. Membership is judged as of the session, from the member map frozen at session setup: an operation authored by a device of a removed member SHALL be dropped from the first session set up after the removal record reaches the judging device, whichever member device carries it; everything the member wrote while a member — its own documents, its operations on other members' documents — stays after it leaves or is removed. A member that joins again SHALL be admitted again from the first session after its new membership record arrives, its new operations persisted as any member's; whether its earlier operations resolve to it is not specified. An operation that reaches a device before the membership record authorizing its author is dropped like any other and persisted from the first session after the record arrives, since reconciliation offers again what the device lacks. No document carries a sharing mode.

#### Scenario: Any member edits another member's mergeable-document

- **WHEN** a device of member C, no owner, appends an operation to a mergeable-document under member B's name and the members' devices reconcile
- **THEN** every member's devices persist C's operation, its author being C's device

#### Scenario: An operation by no member's device is dropped

- **WHEN** a device of member B carries an operation on a mergeable-document authored by a key that resolves to no member's device, and reconciles with a device of a third member
- **THEN** no member device persists it, no rejection is signalled, and the document's own operations survive unchanged

#### Scenario: A removed member's relayed operation is dropped from the next session

- **WHEN** member C is removed, the removal record reaches a device of member B, and a device of member D then relays an operation authored by C's device in a session set up after that
- **THEN** B's device drops the operation, while C's operations admitted before the removal stay — in C's own documents and in B's alike

#### Scenario: A member that joins again is admitted again

- **WHEN** member C was removed, a member invites C again, C's new membership record reaches a device of B, and C's device then appends an operation in a session set up after that
- **THEN** B's device persists the operation

#### Scenario: An operation ahead of its author's membership record is persisted once the record arrives

- **WHEN** a device of member B receives, from a device of member E, an operation authored by a device of D while no record of D's membership has reached B's device
- **THEN** the operation is dropped, and it is persisted from the first session after D's membership record reaches B's device, reconciliation offering it again

### Requirement: A mergeable-document keeps every operation; an immutable-document is placed once by its member

A mergeable-document SHALL hold each edit as its own entry under its own key, never overwritten by another edit: concurrent operations by two writers the cell admits SHALL both persist on every member device, and their merge is above the data layer. An immutable-document SHALL be one entry under one key, admitted only when authored by a device of the member under whose name it sits; an entry at that key authored by a device of any other member — an owner included — SHALL be dropped before persisting, silently, on every member device, a tombstone excepted: an owner deletes, then places its own.

#### Scenario: Concurrent operations on a mergeable-document both persist

- **WHEN** a device of member B and a device of member C each append an operation to a mergeable-document under B's name while disconnected, and the members' devices then reconcile
- **THEN** every member device holds both operations

#### Scenario: An immutable-document is admitted from its member and from nobody else

- **WHEN** a device of member B places an immutable-document, a device of owner A then produces an entry at its key, and the members' devices reconcile
- **THEN** every member device persists B's document and drops A's entry, B's document reading unchanged

### Requirement: A member's devices are announced by the member itself

A member's device-list statement SHALL be admitted by the signature embedded in it, verified against the announcement key the member's join record carries — never by the entry's author or the session peer: a statement written by a freshly linked device of the member itself and a statement relayed by any other member earn the same verdict. A statement whose embedded signature does not verify under the member's announcement key SHALL be dropped silently on every member device. Device resolution SHALL follow the highest validly signed version among the member's statements, never entry timestamps, so an older statement written later displaces nothing.

#### Scenario: A new device registers itself

- **WHEN** a device freshly linked into member B writes B's newest device statement into its local replica and reconciles with a device of member C
- **THEN** C's device admits the statement, and the new device's next session is served as a member device

#### Scenario: A statement under a wrong key is dropped

- **WHEN** a device of member M produces a device statement for member B signed by a key that is not B's announcement key
- **THEN** no member device persists it, and B's device set stays what B's own statements say

#### Scenario: An old version displaces nothing

- **WHEN** a device of B holding version 2 of B's statement writes it into a replica already holding version 3
- **THEN** device resolution still follows version 3 on every member device

### Requirement: A cell store can be forgotten

Forgetting a cell store SHALL stop reconciling its replica, leave its swarm, drop the replica, and remove the cell's registration together, so that operations addressed to that cell afterwards fail with an unknown-cell error distinguishable from transport and storage failures.

#### Scenario: Forgetting a cell unregisters it

- **WHEN** a node holds a cell store and forgets it
- **THEN** reading or writing under that cell fails with the unknown-cell error, and the node's other cell stores are unaffected
