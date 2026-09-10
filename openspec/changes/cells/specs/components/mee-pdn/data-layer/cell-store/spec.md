# data-layer: cell stores

A cell is a space shared by 0..n members — identities, of persons or organizations — identified by a cell id that carries no key material. It lives in two dedicated pdn-store replicas, both held whole by every device of every member: the **membership store**, the cell's authority — who is a member, with what role, on which devices — and the **record store**, the records that authority governs. No egress filter runs inside a cell, member devices form each store's swarm, any member device catches up from any other, and a session reconciles the membership store to convergence before the record store. What keeps a cell honest is admission: a session is served to member devices only, and a record-store entry is admitted by its author — a claim or an immutable-document from the devices of the member under whose name it sits, a mergeable-document's operation from any member's devices — judged on every member device against the membership the session brought, so that a forged entry stops at the first honest device it meets. The runtime's cells service ([pdn-node cells](../../pdn-node/cells/spec.md)) creates and joins the stores; this spec covers the stores themselves.

## ADDED Requirements

### Requirement: A cell is two dedicated replicas

A cell SHALL be served by exactly two pdn-store replicas — its membership store and its record store — separate from every data store, every directory, every connection metadata store and every other cell's stores. Two cells SHALL NOT share a replica, whatever their member sets. Both stores SHALL be addressed through the cell id, and no domain namespace id is allocated for either. The membership store SHALL hold the membership material and nothing else; the record store SHALL hold records and nothing else.

#### Scenario: Creating a cell allocates two dedicated replicas

- **WHEN** a node creates a cell
- **THEN** two fresh pdn-store replicas are created for it, both reached through the cell id, and no domain namespace id is allocated

#### Scenario: Two cells with the same members are four replicas

- **WHEN** the same identities are members of two cells and a record is written into one of them
- **THEN** the record never appears in the other cell's stores

#### Scenario: A record in the membership store is dropped

- **WHEN** a device of a member produces, in the membership store, an entry under the record store's key layout
- **THEN** no member device persists it

### Requirement: The cell id carries no key material

A cell SHALL be identified by a 32-byte cell id minted at creation. The id SHALL carry no key material and SHALL NOT equal either store's namespace id: knowing the cell id grants no access, and no operation on a cell requires a signature by the cell — every write into either store is signed by the writing device's author key, and every membership act is a member's act.

#### Scenario: The cell id is not a namespace id

- **WHEN** a cell is created
- **THEN** its cell id differs from both stores' namespace ids

#### Scenario: Knowing the cell id is not holding the stores

- **WHEN** a party knows a cell's id but holds no ticket to either store and is a device of no member
- **THEN** it obtains no session, no entry and no existence signal for either store

### Requirement: Every member device holds both stores whole and their write tickets

Every device of every member SHALL hold both stores whole and SHALL hold the write ticket of each: a session between two member devices delivers every entry of either store with no egress filter, and authority to write inside the cell is judged by the ingest gate per entry, never by ticket mode — a member's write ticket widens nothing the gate refuses. Member devices SHALL form each store's swarm, so a write reaches the other member devices through the content-free announcement and the pull it triggers, and a member device SHALL be able to catch up from any other member device, not only from an entry's author.

#### Scenario: A write reaches a member through another member

- **WHEN** member A writes an entry, A's devices go offline, and a device of member C — which never synced with A — reconciles with a device of member B that holds the entry
- **THEN** C's device receives the entry, payload included

#### Scenario: A write arrives live over the swarm

- **WHEN** a member writes an entry while devices of the other members are members of the record store's swarm
- **THEN** every such device converges on the entry through the announcement and a pull, none of them holding a grant

#### Scenario: A newcomer writes with the tickets it was handed

- **WHEN** a newcomer joins, is handed both stores' write tickets, and its device writes a claim
- **THEN** every member's devices persist the claim

#### Scenario: A member's write ticket widens nothing

- **WHEN** a device of member C, no owner, holding the record store's write ticket, produces a tombstone on B's record and reconciles with a device of B
- **THEN** B's device drops it and B's record is still read on every member device

### Requirement: Only member devices are served

A session for either of a cell's stores SHALL be served only to a caller that resolves, by authenticated node id, as a device of a current member; every other caller SHALL be refused indistinguishably from the store not being hosted — a holder of its ticket included. A device of a member removed from the cell SHALL be refused from the first session set up after the removal event reaches the serving device; what it obtained while a member is retained.

#### Scenario: A member device is served whole

- **WHEN** a device of a current member requests a session for either store
- **THEN** the session is served and delivers every entry

#### Scenario: A ticket holder that is no member obtains nothing

- **WHEN** a caller holding a store's ticket but a device of no member requests a session
- **THEN** the request is refused with the answer an unhosted replica would produce, and no fingerprint, count or existence signal is revealed

#### Scenario: A removed member is refused from the next session

- **WHEN** a member is removed and the removal event has reached a serving device, and a device of the removed member then requests a session
- **THEN** the request is refused as for an unhosted replica, while the remaining members' devices are still served, and what the removed device obtained while a member is still readable on it

### Requirement: Membership needs no connection

Access to a cell's stores SHALL rest on membership alone: no connection between two members is required for either to read what the other wrote, and joining a cell SHALL create no connection.

#### Scenario: Three identities share through a cell with no connections

- **WHEN** identities A, B and C hold no connection to one another, A creates a cell and invites B and C, and B writes an entry
- **THEN** C's device reads the entry, and no identity lists any connection

### Requirement: The membership store holds each member's event sequence, append-only

The membership store SHALL hold, per member, one sequence of membership events under `member/<pdnid>/<seq>` — join, leave, removal, made-owner, unmade-owner — with the sequence number inside the signed bytes, and the member's device-list statements under `member/<pdnid>/devices/<version>`, one entry per version. A join event SHALL be admitted from a device of any current member, a leave event only from a device of the member itself, a removal, made-owner or unmade-owner event only from a device of an owner; an event from any other author SHALL be dropped silently on every member device. Every entry SHALL be written once: an entry at a key the write admission already shows held by the same author SHALL be dropped, and no entry in the membership store is overwritten or deleted — the store holds no tombstones. A member's standing and role SHALL be folded by walking its events in sequence order on every member device, whatever order the events arrived in and never by entry timestamp: a join makes it a plain member, made-owner an owner, unmade-owner a plain member, leave and removal no member, a later join a plain member again.

#### Scenario: A role flip resolves by sequence whatever the arrival order

- **WHEN** owner A makes B an owner (B's sequence 2, after B's join at 1), unmakes B (3) and makes B an owner again (4), and the three events reach a device of member C in the order 4, 2, 3
- **THEN** C's device lists B by the highest sequence it holds after each arrival — an owner throughout — and as an owner once all three have arrived

#### Scenario: A role event from a plain member is dropped

- **WHEN** a device of member C, no owner, produces a made-owner event for C and reconciles with a device of B
- **THEN** B's device drops it and B still lists the owners unchanged

#### Scenario: A leave ends the standing and a new join restores it as a plain member

- **WHEN** B, an owner, writes a leave event (sequence 5) from its own device, and a member later invites B again, writing a join event (sequence 6)
- **THEN** every member device lists B as no member after sequence 5 and as a plain member — no owner — after sequence 6

#### Scenario: A rewritten event is dropped

- **WHEN** owner A's device writes B's made-owner event at sequence 2, and later produces a different entry at the same key
- **THEN** every member device keeps the first entry and drops the second

### Requirement: The membership store is reconciled before the record store

A session between two member devices SHALL reconcile the membership store to convergence, fold it into the write admission, and only then reconcile the record store under it; both stores SHALL be reconciled whole, with no capability filter on either. A record whose author's membership the same session brings SHALL be judged under that membership; a record that reaches a device ahead of its author's join event SHALL be dropped and persisted from the first session after the record arrives.

#### Scenario: A newcomer's first record is admitted in the session that brings its membership

- **WHEN** newcomer D's join event and D's first claim are both unknown to a device of B, and B's device sessions with a device holding both
- **THEN** B's device persists D's claim in that session

#### Scenario: A removal is applied before the record store is judged

- **WHEN** C's removal event and a later operation authored by C's device are both unknown to a device of B, and B's device sessions with a device holding both
- **THEN** B's device drops C's operation in that session, C's earlier operations staying

### Requirement: The record store's key names the member, the kind and the type

A record SHALL sit under the name of the member that placed it, the key carrying the kind and a document's type: `by/<pdnid>/claim/<id>` for a claim, `by/<pdnid>/doc/immutable/<id>` for an immutable-document, `by/<pdnid>/doc/mergeable/<id>/<op>` for each operation of a mergeable-document, `<op>` being the writer's author key followed by the writer's own sequence. `<pdnid>` SHALL be the member's identity, never a device. A tombstone SHALL be the store's empty entry at a record's key, or at a mergeable-document's key above its operations.

#### Scenario: A record sits under the name of the member that placed it

- **WHEN** member B places a claim, an immutable-document and a mergeable-document with one operation, from two of B's devices
- **THEN** their keys are `by/<B>/claim/<id>`, `by/<B>/doc/immutable/<id>` and `by/<B>/doc/mergeable/<id>/<op>`, the same `<B>` from either device, and a listing under B's prefix returns exactly them

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

A document SHALL be readable by every member. An operation on a mergeable-document SHALL be admitted from a device of any current member, whoever's name the document sits under, each operation carrying its writer's author signature. The one ground for dropping an operation is its author: an operation authored by a key that resolves to no current member's device SHALL be dropped before persisting, silently, on every member device — no role, no document and no time of authoring narrows admission further. Membership is judged as of the session, from the member map frozen at session setup: an operation authored by a device of a removed member SHALL be dropped from the first session set up after the removal event reaches the judging device, whichever member device carries it; everything the member wrote while a member — its own documents, its operations on other members' documents — stays after it leaves or is removed. A member that joins again SHALL be admitted again from the first session after its new join event arrives, its new operations persisted as any member's; whether its earlier operations resolve to it is not specified. An operation that reaches a device before the join event authorizing its author is dropped like any other and persisted from the first session after the record arrives, since reconciliation offers again what the device lacks. No document carries a sharing mode.

#### Scenario: Any member edits another member's mergeable-document

- **WHEN** a device of member C, no owner, appends an operation to a mergeable-document under member B's name and the members' devices reconcile
- **THEN** every member's devices persist C's operation, its author being C's device

#### Scenario: An operation by no member's device is dropped

- **WHEN** a device of member B carries an operation on a mergeable-document authored by a key that resolves to no member's device, and reconciles with a device of a third member
- **THEN** no member device persists it, no rejection is signalled, and the document's own operations survive unchanged

#### Scenario: A removed member's relayed operation is dropped from the next session

- **WHEN** member C is removed, the removal event reaches a device of member B, and a device of member D then relays an operation authored by C's device in a session set up after that
- **THEN** B's device drops the operation, while C's operations admitted before the removal stay — in C's own documents and in B's alike

#### Scenario: A member that joins again is admitted again

- **WHEN** member C was removed, a member invites C again, C's new join event reaches a device of B, and C's device then appends an operation in a session set up after that
- **THEN** B's device persists the operation

#### Scenario: An operation ahead of its author's join event is persisted once the event arrives

- **WHEN** a device of member B receives, from a device of member E, an operation authored by a device of D while no join event of D has reached B's device
- **THEN** the operation is dropped, and it is persisted from the first session after D's join event reaches B's device, reconciliation offering it again

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

### Requirement: A cell's stores are forgotten together

Forgetting a cell SHALL stop reconciling both replicas, leave both swarms, drop both replicas, and remove the cell's registration together, so that operations addressed to that cell afterwards fail with an unknown-cell error distinguishable from transport and storage failures.

#### Scenario: Forgetting a cell unregisters it

- **WHEN** a node holds a cell's stores and forgets the cell
- **THEN** reading or writing under that cell fails with the unknown-cell error, neither replica is reconciled or served, and the node's other cells are unaffected
