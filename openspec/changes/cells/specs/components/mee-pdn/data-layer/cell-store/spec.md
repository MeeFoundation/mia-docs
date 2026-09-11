# data-layer: cell stores

A cell is a space shared by 0..n members — identities, of persons or organizations — identified by a cell id that carries no key material. It lives in two dedicated pdn-store replicas, both held whole by every device of every member: the **membership store**, the cell's authority — who is a member, with what role, on which devices — and the **record store**, the records that authority governs. No egress filter runs inside a cell, member devices form each store's swarm, any member device catches up from any other, and a session reconciles the membership store to convergence before the record store. What keeps a cell honest is admission: a session is served to member devices only, and a record-store entry is admitted by its author — a claim or an immutable-document from the devices of the member under whose name it sits, a mergeable-document's operation from any member's devices — judged on every member device against the writer's membership state at the membership sequence the entry names, so that a forged entry stops at the first honest device it meets. The runtime's cells service ([pdn-node cells](../../pdn-node/cells/spec.md)) creates and joins the stores; this spec covers the stores themselves.

The membership store is two shapes: what a device writes — an act — and what the fold computes for a member from everything written about it — its chain of events. An act is one entry; its author key resolves to the actor, the actor's own sequence at the time of acting (`actor_seq`) and the position in the subject's chain (`subject_seq`) sit in the key (cells D21, D23).

```rust
/// One entry a device writes into the membership store.
enum MembershipAct {
    /// The creator's first act: itself a member and an owner. Self-authored; subject = actor; subject_seq = 1; the root.
    Found       { announcement_key: PublicKey },
    /// Records a newcomer's join after its one-time secret was verified and burned. Any member.
    Join        { subject: PdnId, subject_seq: Seq, actor_seq: Seq, announcement_key: PublicKey, subject_signature: Signature },
    /// The member itself; subject = actor.
    Leave       { subject_seq: Seq, actor_seq: Seq },
    /// An owner.
    Remove      { subject: PdnId, subject_seq: Seq, actor_seq: Seq },
    /// An owner.
    MakeOwner   { subject: PdnId, subject_seq: Seq, actor_seq: Seq },
    /// An owner.
    UnmakeOwner { subject: PdnId, subject_seq: Seq, actor_seq: Seq },
    /// The member's devices, one entry per version; judged by the embedded signature under the member's announcement key, whoever writes it (D16).
    AnnounceDevices { version: u64, devices: Vec<AuthorId>, signature: Signature },
}

/// A member's chain: `member/<pdnid>/<seq>/<kind>/<aseq>`, walked in `seq` order. `by` is the actor, `by_seq` the actor's own sequence then.
enum MembershipEvent {
    Founded     { seq: Seq, announcement_key: PublicKey },                          // by the member itself; the creator's seq 1 only
    Joined      { seq: Seq, by: PdnId, by_seq: Seq, announcement_key: PublicKey },  // by any member
    Left        { seq: Seq, by_seq: Seq },                                          // by the member itself
    Removed     { seq: Seq, by: PdnId, by_seq: Seq },                               // by an owner
    MadeOwner   { seq: Seq, by: PdnId, by_seq: Seq },                               // by an owner
    UnmadeOwner { seq: Seq, by: PdnId, by_seq: Seq },                               // by an owner
}

/// Folding a chain up to a sequence: Founded and Joined make a plain member, MadeOwner an owner, UnmadeOwner a plain member,
/// Left and Removed no member; a transition the state does not allow (MadeOwner of no member, Joined of a member) is ignored.
struct MemberState { member: bool, owner: bool, announcement_key: Option<PublicKey>, devices: Vec<AuthorId> }

/// The gate's check of one event, from the write admission alone:
///   Founded            → subject is the creator and seq == 1
///   Joined             → state(by, by_seq).member
///   Left               → by == subject
///   Removed | MadeOwner | UnmadeOwner → state(by, by_seq).owner
/// and for every kind: no entry under member/<subject>/<seq>/ by this author yet; by's chain held up to by_seq, else deferred.
```

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

The membership store SHALL hold, per member, one sequence of membership events under `member/<pdnid>/<seq>/<kind>/<aseq>` — founded, joined, left, removed, made-owner, unmade-owner — with the sequence number inside the signed bytes and `<aseq>` the actor's own sequence at the time of acting, and the member's device-list statements under `member/<pdnid>/devices/<version>`, one entry per version. An event SHALL be judged against its actor's chain folded up to `<aseq>`: a joined event is admitted when the actor was a member there, a removed, made-owner or unmade-owner event when the actor was an owner there, a left event when the actor is the subject itself; the founding event — the creator's first, self-authored, making it a member and an owner — needs nothing and is the root of every verification; an event failing its check SHALL be dropped silently on every member device, and an event whose actor's chain the device does not hold up to `<aseq>` SHALL be deferred within the session and re-judged once the chain arrives, or dropped and offered again by the next session. Every entry SHALL be written once: an entry under a subject sequence the write admission already shows held by the same author SHALL be dropped, and no entry in the membership store is overwritten or deleted — the store holds no tombstones. A member's membership state and role SHALL be folded by walking its events in sequence order on every member device, whatever order the events arrived in and never by entry timestamp: a join makes it a plain member, made-owner an owner, unmade-owner a plain member, leave and removal no member, a later join a plain member again.

#### Scenario: A role flip resolves by sequence whatever the arrival order

- **WHEN** owner A makes B an owner (B's sequence 2, after B's join at 1), unmakes B (3) and makes B an owner again (4), and the three events reach a device of member C in the order 4, 2, 3
- **THEN** C's device lists B by the highest sequence it holds after each arrival — an owner throughout — and as an owner once all three have arrived

#### Scenario: A role event from a plain member is dropped

- **WHEN** a device of member C, no owner, produces a made-owner event for C and reconciles with a device of B
- **THEN** B's device drops it and B still lists the owners unchanged

#### Scenario: A leave ends the membership and a new join restores it as a plain member

- **WHEN** B, an owner, writes a leave event (sequence 5) from its own device, and a member later invites B again, writing a join event (sequence 6)
- **THEN** every member device lists B as no member after sequence 5 and as a plain member — no owner — after sequence 6

#### Scenario: A device holding nothing verifies the store from the founding event

- **WHEN** newcomer D's device, holding no membership store, sessions with the inviter's device, which holds the creator's founding event and every event since
- **THEN** D's device converges on the same membership as the inviter in that session, every event verified against its actor's chain, whatever order the events arrived in

#### Scenario: What an owner did while an owner stands after its demotion

- **WHEN** owner A made C an owner naming A's sequence 3, A was then unmade at A's sequence 4, and a device linked into member B after that catches up
- **THEN** B's new device lists C as an owner

#### Scenario: An event naming an actor point without the membership state it needs is dropped

- **WHEN** A was unmade at A's sequence 4 and a device of member E relays a made-owner event for F authored by A's device naming A's sequence 4
- **THEN** no member device persists it and F is listed as a plain member

#### Scenario: Nobody leaves for another member

- **WHEN** a device of member D produces a left event in B's chain
- **THEN** no member device persists it and B is still listed as a member

#### Scenario: There is one founding event

- **WHEN** a device of owner C produces a founded event in C's own chain, or a second one in the creator's
- **THEN** no member device persists it and the owners are listed unchanged

#### Scenario: A made-owner event for no member changes nothing

- **WHEN** owner A produces a made-owner event in the chain of an identity that never joined
- **THEN** every member device holds the entry as written and lists that identity as no member and no owner

#### Scenario: Two owners' concurrent events at one point both persist

- **WHEN** owners A and C, disconnected from each other, each write an event in B's chain at B's sequence 5 — A a made-owner, C a removed — and the members' devices then reconcile
- **THEN** every member device holds both entries, and every member device lists B's membership state the same (the rule is cells B10)

#### Scenario: An event by no member's device is dropped

- **WHEN** a device of member D relays an event in B's chain authored by a key that resolves to no member's device
- **THEN** no member device persists it and B's chain is read unchanged

#### Scenario: An event ahead of its actor's point is admitted when the point arrives

- **WHEN** a device of member D receives a made-owner event for C authored by A's device naming A's sequence 3 while holding A's chain only up to sequence 2, and A's sequence 3 arrives in a later session
- **THEN** the event is deferred, not persisted, in the first session, and persisted in the session that brings A's sequence 3

#### Scenario: A rewritten event is dropped

- **WHEN** owner A's device writes B's made-owner event at sequence 2, and later produces a different entry at the same key
- **THEN** every member device keeps the first entry and drops the second

### Requirement: Verdicts hold their limits without an anchored log

Until an anchored log carries the retrograde direction (cells F7, F8), the gate SHALL judge by the point an entry names and by the membership state as of the session, and by nothing else: it SHALL admit an event or a record whose named point checks out, whoever carries it and whenever it arrives, and SHALL refuse or defer what the session's own state cannot resolve. The scenarios below are the consequences — what the gate does, not what a cell wants — each named after the open question that closes it and expected to flip when it does, or after the decision that keeps it.

#### Scenario: A demoted owner's act under its old point is admitted (F7)

- **WHEN** owner A was unmade at A's sequence 4, and a device of plain member E relays a made-owner event for A itself, authored by A's device after the demotion and naming A's sequence 3
- **THEN** every member device persists it and lists A as an owner again

#### Scenario: A removed owner rejoins and re-promotes itself through a relaying member (F7)

- **WHEN** A, an owner at A's sequence 3, was removed at A's sequence 5, and a device of plain member E relays a joined event for A at A's sequence 6 and a made-owner event for A at A's sequence 7, both authored by A's device and naming A's sequence 3
- **THEN** every member device lists A as an owner — a plain member and a former owner together did what the rules reserve to an owner

#### Scenario: A departed member's new record under its old sequence is admitted (F7)

- **WHEN** C was removed at C's sequence 2, and a device of member D relays an operation C's device authored after the removal, naming C's sequence 1
- **THEN** every member device persists it

#### Scenario: A rewrite that reaches a device first stays there (F8)

- **WHEN** owner A's device rewrote B's made-owner event at B's sequence 2 under A's own author key, and a device linked into member E catches up first from A's device and only then from a device holding the original
- **THEN** E's new device keeps the rewrite and drops the original, while every device that held the original keeps it — two devices, two memberships

#### Scenario: A deletion an owner wrote before its demotion is dropped after it (D24, by decision)

- **WHEN** owner A's device placed a tombstone on B's record while A was an owner, A was then unmade, and the tombstone reaches a device of C after the unmade-owner event did
- **THEN** C's device drops the tombstone and B's record is still read, until a current owner deletes it again

#### Scenario: A newcomer is refused a session until its join event arrives (D19)

- **WHEN** D joined through member E, D's join event has not reached a device of A, and D's device requests a session from A's device
- **THEN** the session is refused as for an unhosted store, and served once the join event reaches A's device

#### Scenario: A device statement ahead of its join is dropped in that session (D19)

- **WHEN** in one session a device of A receives B's device statement before the join event carrying B's announcement key
- **THEN** the statement is dropped in that session and admitted in the next

#### Scenario: A dependency whose authoring device died is never resolved until re-issued (G1)

- **WHEN** A's sequence 3 — the event that made A an owner — reached only A's device before B's device, which authored it, died; A's device then made C an owner naming A's sequence 3, spread that event to a device of D, and died too, so no live device holds A's sequence 3
- **THEN** every device defers C's made-owner event indefinitely and lists it as waiting on A's sequence 3, and lists C as an owner only after a current owner makes C an owner anew — an ordinary made-owner at a point every device holds

### Requirement: The membership store is reconciled before the record store

A session between two member devices SHALL reconcile the membership store to convergence, fold it into the write admission, and only then reconcile the record store under it; both stores SHALL be reconciled whole, with no capability filter on either. A record whose author's membership the same session brings SHALL be judged under that membership; a record that reaches a device ahead of its author's join event SHALL be dropped and persisted from the first session after the record arrives.

#### Scenario: A newcomer's first record is admitted in the session that brings its membership

- **WHEN** newcomer D's join event and D's first claim are both unknown to a device of B, and B's device sessions with a device holding both
- **THEN** B's device persists D's claim in that session

#### Scenario: A role change is applied before a deletion is judged

- **WHEN** A's unmade-owner event and a tombstone A's device then placed on B's record are both unknown to a device of member C, and C's device sessions with a device holding both
- **THEN** C's device drops the tombstone in that session, and B's record is still read

### Requirement: The record store's key names the member, the kind and the type

A record SHALL sit under the name of the member that placed it, the key carrying the kind, a document's type and the writer's membership sequence at the time of writing: `by/<pdnid>/claim/<id>/<mseq>` for a claim, `by/<pdnid>/doc/immutable/<id>/<mseq>` for an immutable-document, `by/<pdnid>/doc/mergeable/<id>/<op>` for each operation of a mergeable-document, `<op>` being the writer's author key, the writer's membership sequence and the writer's own operation sequence. `<pdnid>` SHALL be the member's identity, never a device. A record's identity SHALL be its key without the trailing sequence, and a tombstone SHALL be the store's empty entry at that key — above the content entry, above a mergeable-document's operations.

#### Scenario: A record sits under the name of the member that placed it

- **WHEN** member B places a claim, an immutable-document and a mergeable-document with one operation, from two of B's devices
- **THEN** their keys are `by/<B>/claim/<id>/<mseq>`, `by/<B>/doc/immutable/<id>/<mseq>` and `by/<B>/doc/mergeable/<id>/<op>`, the same `<B>` and the same `<mseq>` from either device, and a listing under B's prefix returns exactly them

### Requirement: A claim is written only by its issuer

An entry that is a claim SHALL be admitted over sync only when it was authored by a device of the member the claim names as its issuer, that member being a member at the sequence the claim's key names. A claim entry authored by a device of any other member SHALL be dropped before persisting, on every member device, silently — the verdict is on the entry's author, not on the session peer that carried it, so an entry relayed by a third member keeps the verdict its author earns.

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

A document SHALL be readable by every member. An operation on a mergeable-document SHALL be admitted from a device of any member, whoever's name the document sits under, each operation carrying its writer's author signature and naming, in its key, the writer's membership sequence at the time of writing. The one ground for dropping an operation is its writer's membership state at that sequence: an operation whose author resolves to no member's device, or to a member that was not a member at the named sequence of its own events, SHALL be dropped before persisting, silently, on every member device — no role, no document and no time of authoring narrows admission further; an operation naming a sequence the device does not yet hold SHALL be dropped and persisted from the first session after the events arrive, since reconciliation offers again what the device lacks. An operation is judged the same on every device whenever it arrives: everything a member wrote while a member — its own documents, its operations on other members' documents — SHALL be admitted after it leaves or is removed, on a device that catches up later included, and SHALL resolve to that member after it joins again, its new operations naming its new sequence. No document carries a sharing mode.

#### Scenario: Any member edits another member's mergeable-document

- **WHEN** a device of member C, no owner, appends an operation to a mergeable-document under member B's name and the members' devices reconcile
- **THEN** every member's devices persist C's operation, its author being C's device

#### Scenario: An operation by no member's device is dropped

- **WHEN** a device of member B carries an operation on a mergeable-document authored by a key that resolves to no member's device, and reconciles with a device of a third member
- **THEN** no member device persists it, no rejection is signalled, and the document's own operations survive unchanged

#### Scenario: A departed member's earlier operation reaches a device that catches up later

- **WHEN** member C, a member from sequence 1, appended an operation naming sequence 1, C was then removed at sequence 2, and a device linked into member B after the removal catches up from a device of member D
- **THEN** B's new device persists C's operation, in C's own documents and in B's alike

#### Scenario: An operation naming a sequence at which its writer was no member is dropped

- **WHEN** C was removed at sequence 2 and a device of member D relays an operation authored by C's device naming sequence 2
- **THEN** no member device persists it, no rejection is signalled, and C's operations naming sequence 1 stay

#### Scenario: A member that joins again writes under its new sequence

- **WHEN** member C was removed at sequence 2, a member invites C again at sequence 3, and C's device then appends an operation naming sequence 3
- **THEN** every member device persists the operation, and C's earlier operations, naming sequence 1, still resolve to C

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

### Requirement: Deleting a record kills its key

A tombstone SHALL be the store's empty entry at a record's key without its trailing sequence, or at a mergeable-document's key above its operations. It SHALL be admitted from a device of the member under whose name the record sits or of an owner, judged as of the session, and dropped silently from any other device. Once admitted, the store SHALL remove every author's content entries under that key and release their blobs at once, SHALL insert no content under that key again whatever the entry's timestamp, and SHALL keep the tombstone entry, so that a peer holding the content and not the tombstone converges on the deletion.

#### Scenario: An owner's deletion removes the record and its blob everywhere

- **WHEN** owner A's device places a tombstone on B's immutable-document and the members' devices reconcile
- **THEN** no member device reads the document, none holds its content entry or its blob, and each holds the tombstone

#### Scenario: A member deletes its own record; a plain member deletes no other member's

- **WHEN** member B's device places a tombstone on B's claim, and member C's device, no owner, places one on B's immutable-document, and the members' devices reconcile
- **THEN** B's claim is gone on every member device while B's immutable-document is still read, C's tombstone dropped

#### Scenario: A removed member's records are deleted by an owner, by nobody else

- **WHEN** C was removed, and then a device of owner A, a device of plain member D, a device of C and a device of no member each place a tombstone on a record under C's name
- **THEN** A's tombstone is admitted and the record gone, and the other three are dropped

#### Scenario: A dead key admits no content, whatever its timestamp

- **WHEN** B's immutable-document was deleted by an owner, and a device of B then offers a content entry at the same key carrying a timestamp newer than the tombstone's
- **THEN** no member device inserts it and the document stays deleted

#### Scenario: A peer that missed the tombstone converges on the deletion

- **WHEN** a device of member D holds B's document and has not received the tombstone, and it reconciles with a device holding the tombstone
- **THEN** D's device drops the document and its blob and holds the tombstone, and the device it reconciled with does not receive the document back

#### Scenario: Deleting a mergeable-document kills its operations

- **WHEN** owner A's device places a tombstone at B's mergeable-document's key, and a device of C then offers an operation under it
- **THEN** every member device removes the document's operations and inserts no more under it

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
