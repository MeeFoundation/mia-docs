# data-layer: cell stores

A cell is a space shared by 0..n members — identities — identified by a cell id that carries no key material and is derived from its creator's announcement key and a random nonce. It lives in two dedicated pdn-store namespaces, each held whole, as a replica of its own, by every member identity on every device that hosts it: the **membership store**, the cell's authority — who is a member, with what role, on which devices — and the **record store**, the records that authority governs. No egress filter runs inside a cell, member devices form each store's swarm, any member device catches up from any other, and a session reconciles the membership store to convergence before the record store. What keeps a cell honest is admission: a session names the member whose replica it addresses and the member its caller acts as, and is served to member devices only, and a record-store entry is admitted by its author — a claim or an immutable-document from the devices of the member under whose name it sits, a mergeable-document's operation from any member's devices — judged on every member device against the writer's membership state at the membership sequence the entry names, so that a forged entry stops at the first honest device it meets. The runtime's cells service ([pdn-node cells](../../pdn-node/cells/spec.md)) creates and joins the stores; this spec covers the stores themselves.

The membership store is two shapes: what a device writes — an act — and what the fold computes for a member from everything written about it — its chain of events. An act is one entry; its author key resolves to the actor, the actor's own sequence at the time of acting (`actor_seq`), the position in the subject's chain (`subject_seq`) and the author's own act number (`act_no`) sit in the key (cells D21, D23, D33).

```rust
/// One entry a device writes into the membership store. `act_no` is the writing author's own act number in the cell:
/// 1 for its first act, one more for each next (cells D33).
enum MembershipAct {
    /// The creator's first act: itself a member and an owner. Self-authored; subject = actor; subject_seq = 1; act_no = 1; the root.
    /// Derives the cell id and is checked against it by the steps below.
    Found   { nonce: [u8; 16], announcement_key: PublicKey, signature: Signature },
    /// Written by the inviting device once the newcomer's one-time secret is verified and burned, never when the invite is minted.
    /// Any member; subject ≠ actor; `announcement_key` and `subject_signature` are the newcomer's join statement. Held as `Joined`.
    Invite  { subject: PdnId, subject_seq: Seq, actor_seq: Seq, act_no: u64, announcement_key: PublicKey, subject_signature: Signature },
    /// The member itself; subject = actor.
    Leave   { subject_seq: Seq, actor_seq: Seq, act_no: u64, mark: Mark },
    /// An owner; subject ≠ actor.
    Kick    { subject: PdnId, subject_seq: Seq, actor_seq: Seq, act_no: u64, mark: Mark },
    /// An owner.
    Promote { subject: PdnId, subject_seq: Seq, actor_seq: Seq, act_no: u64 },
    /// An owner; subject ≠ actor.
    Demote  { subject: PdnId, subject_seq: Seq, actor_seq: Seq, act_no: u64, mark: Mark },
    /// The member's devices, one entry per version; judged by the embedded signature under the member's announcement key, whoever writes it (D16).
    /// `signature` by the announcement key over "pdn/cell-devices/v1" ‖ version ‖ devices.
    AnnounceDevices { version: u64, devices: Vec<MemberDevice>, signature: Signature },
}

/// A device of the member: its node id, which sessions are classified and contacts dialed by, and the author the member
/// writes with there — one author per hosted identity on a device (ADR-0013), so two members on one node share the node id only.
struct MemberDevice { node: NodeId, author: AuthorId }

/// What a narrowing saw of its subject: for each author the subject's device statements list, the highest `act_no` of that
/// author the writing device holds. An act of the subject naming a point before the narrowing counts only within it (cells D33).
struct Mark(Vec<(AuthorId, u64)>);

/// A member's chain: `member/<pdnid>/<seq>/<kind>/<aseq>/<an>`, walked in `seq` order. `by` is the actor, `by_seq` the actor's
/// own sequence then, `act_no` the writing author's `<an>`.
enum MembershipEvent {
    Founded  { seq: Seq, nonce: [u8; 16], announcement_key: PublicKey },                      // by the member itself; the creator's seq 1 only
    Joined   { seq: Seq, by: PdnId, by_seq: Seq, act_no: u64, announcement_key: PublicKey },  // by any member other than the member
    Left     { seq: Seq, by_seq: Seq, act_no: u64, mark: Mark },                              // by the member itself
    Kicked   { seq: Seq, by: PdnId, by_seq: Seq, act_no: u64, mark: Mark },                   // by an owner other than the member
    Promoted { seq: Seq, by: PdnId, by_seq: Seq, act_no: u64 },                               // by an owner
    Demoted  { seq: Seq, by: PdnId, by_seq: Seq, act_no: u64, mark: Mark },                   // by an owner other than the member
}

/// Folding a chain up to a sequence: Founded makes a member and an owner, Joined a plain member, Promoted an owner, Demoted a plain member,
/// Left and Kicked no member; a transition the state does not allow (Promoted of no member, Joined of a member) is ignored.
/// An act naming a point before a Left, Kicked or Demoted of its actor that forbids it is ignored when its act_no exceeds that
/// event's mark for its author — the first such event after the point decides, the highest mark at one sequence — and so is
/// every event resting on it; two acts of one author under one act_no are both ignored (cells D33).
struct MemberState { member: bool, owner: bool, announcement_key: Option<PublicKey>, devices: Vec<MemberDevice> }

/// The gate's check of one event, from the write admission alone, `state` folded without the mark (cells D33):
///   Founded          → seq == 1 and the receiving steps below pass
///   Joined           → by != subject and state(by, by_seq).member
///   Left             → by == subject
///   Promoted         → state(by, by_seq).owner
///   Kicked | Demoted → by != subject and state(by, by_seq).owner
/// and for every kind: no entry under member/<subject>/<seq>/ by this author yet; by's chain held up to by_seq, this author's
/// acts held below act_no, and for Left | Kicked | Demoted the acts the mark names held — else deferred.
```

The cell id and the founding event (cells D25), `‖` being byte concatenation of fixed-size fields:

```text
Creating a cell, on the creator's device:
1. nonce      = 16 random bytes
2. cell_id    = BLAKE3 derive_key(context "pdn/cell-id/v1",
                                  pdn_id[32] ‖ announcement_pubkey[32] ‖ nonce[16]), first 16 bytes
                text form: 32 lowercase hex characters
3. signature  = Ed25519 sign(announcement_secret,
                             "pdn/cell-founding/v1" ‖ pdn_id ‖ announcement_pubkey ‖ nonce)
4. write the founding event at member/<pdn_id>/1/founded/…:
   { nonce, announcement_pubkey, signature }   — pdn_id is the key's <pdnid>; cell_id is not stored
5. cell_id goes to the identity's directory, the invite, links in notes

Receiving a founding event, on every member device (reconciliation, a fresh device's first session included):
1. recompute cell_id from the event's pdn_id, announcement_pubkey, nonce → must equal the cell id the device holds
2. verify signature under announcement_pubkey over "pdn/cell-founding/v1" ‖ pdn_id ‖ announcement_pubkey ‖ nonce
3. either check fails → drop the event, whatever order it arrived in
```

## ADDED Requirements

### Requirement: A cell is two dedicated stores, held per member identity

A cell SHALL be served by exactly two pdn-store namespaces — its membership store and its record store — separate from every data store, every directory, every connection metadata store and every other cell's stores. Two cells SHALL NOT share a store, whatever their member sets. Both stores SHALL be addressed through the cell id, and no domain namespace id is allocated for either. Every member identity SHALL hold a replica of each store of its own, created or imported for that identity ([identity-scoped replicas](../identity-scoped-replicas/spec.md)): two identities of one node that are both members SHALL each hold both stores, the two copies converging inside the process ([in-process sessions](../in-process-sessions/spec.md)) and sharing no replica. The membership store SHALL hold the membership material and the record store records; an entry that fits neither layout is kept apart and used by nothing, as the requirement on entries outside the key layout states. An import of a cell's store SHALL refuse a ticket whose namespace the importing identity already holds in any other role — a data store, a directory, a connection metadata store, another cell's store or the cell's other store — with nothing registered, and a data import SHALL refuse a ticket naming a cell's store: a ticket is the word of whoever minted it, and a replica held in two roles is dropped when either role is forgotten.

#### Scenario: Creating a cell allocates two dedicated replicas

- **WHEN** a hosted identity creates a cell
- **THEN** two fresh pdn-store replicas are created for that identity, both reached through the cell id, and no domain namespace id is allocated

#### Scenario: A store ticket naming a replica held in another role is refused

- **WHEN** a joining identity is handed a store ticket whose namespace it already holds as a data store received under a grant
- **THEN** the join fails with no cell registered, and the data store is still held and reconciled as before

#### Scenario: Two cells with the same members are four stores

- **WHEN** the same identities are members of two cells and a record is written into one of them
- **THEN** the record never appears in the other cell's stores

#### Scenario: Two members hosted on one node hold the cell twice

- **WHEN** identities B and D, hosted on one node, are both members of a cell, and B places a record with no other node reachable
- **THEN** the node holds each store twice, one replica per identity, D's replica comes to carry B's record, payload included, and the record's entry carries B's author, which resolves to B alone

#### Scenario: A record in the membership store is kept and used by nothing

- **WHEN** a device of a member produces, in the membership store, an entry under the record store's key layout
- **THEN** every member device holds it, no membership state or record view changes, and each lists it as an entry outside the layout

### Requirement: The cell id carries no key material

A cell SHALL be identified by a 16-byte cell id, derived on the creator's device and checked on every member device that receives the founding event, by the cell id steps above. The id SHALL carry no key material and SHALL NOT equal either store's namespace id: knowing the cell id grants no access, and no operation on a cell requires a signature by the cell — every write into either store is signed by the writing device's author key, and every membership act is a member's act.

#### Scenario: The cell id is derived from the founding event

- **WHEN** an identity creates a cell
- **THEN** recomputing the cell id from the founding event's `PdnId`, announcement key and nonce gives the cell id, and the event's signature verifies under that announcement key, both by the cell id steps above

#### Scenario: The cell id is not a namespace id

- **WHEN** a cell is created
- **THEN** its cell id differs from both stores' namespace ids

#### Scenario: Knowing the cell id is not holding the stores

- **WHEN** a party knows a cell's id but holds no ticket to either store and is a device of no member
- **THEN** it obtains no session, no entry and no existence signal for either store

### Requirement: Every member device holds both stores whole and their write tickets

Every device of every member SHALL hold both stores whole — every record readable by every member — and SHALL hold the write ticket of each: a session between two member devices delivers every entry of either store with no egress filter, and authority to write inside the cell is judged by the ingest gate per entry, never by ticket mode — a member's write ticket widens nothing the gate refuses. Member devices SHALL form each store's swarm, so a write reaches the other member devices through the content-free announcement and the pull it triggers, and a member device SHALL be able to catch up from any other member device, not only from an entry's author. A store's contacts SHALL be the devices the members' statements list, each paired with the member it is dialed as, and the holding identity's own other devices, dialed as that identity; a contact naming this node's own address SHALL be reached inside the process, and a write SHALL announce to a co-located member's replica directly, as the in-process sessions spec states.

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

A session for either of a cell's stores SHALL name the member whose replica it addresses and the member its caller acts as, and SHALL be served only when the member the caller names is a current member whose records list the caller's authenticated node id: that identity's own directory where the caller names the identity the serving replica belongs to, as a sibling device of it; that member's device statements in the membership store where the caller names another member, over the network and inside the process alike. Every other caller SHALL be refused indistinguishably from the store not being hosted — a holder of its ticket included, and a caller naming an identity that is no member included, even from a node that hosts a member and so shares its node id. A caller naming a member kicked from the cell SHALL be refused from the first session set up after the kicked event reaches the serving device; what it obtained while a member is retained.

#### Scenario: A member device is served whole

- **WHEN** a device of a current member requests a session for either store
- **THEN** the session is served and delivers every entry

#### Scenario: A ticket holder that is no member obtains nothing

- **WHEN** a caller holding a store's ticket but a device of no member requests a session
- **THEN** the request is refused with the answer an unhosted replica would produce, and no fingerprint, count or existence signal is revealed

#### Scenario: A co-located identity that is no member is refused

- **WHEN** a node hosts member B and identity E, no member, and a session from that node names E as its caller for either store
- **THEN** the session is refused as for an unhosted store, while a session from the same node naming B is served

#### Scenario: A kicked member is refused from the next session

- **WHEN** a member is kicked and the kicked event has reached a serving device, and a device of the kicked member then requests a session
- **THEN** the request is refused as for an unhosted replica, while the remaining members' devices are still served, and what the kicked member's device obtained while a member is still readable on it

### Requirement: Membership needs no connection

Access to a cell's stores SHALL rest on membership alone: no connection between two members is required for either to read what the other wrote, and joining a cell SHALL create no connection.

#### Scenario: Three identities share through a cell with no connections

- **WHEN** identities A, B and C hold no connection to one another, A creates a cell and invites B and C, and B writes an entry
- **THEN** C's device reads the entry, and no identity lists any connection

### Requirement: The membership store holds each member's event sequence, append-only

The membership store SHALL hold, per member, one sequence of membership events under `member/<pdnid>/<seq>/<kind>/<aseq>/<an>` — founded, joined, left, kicked, promoted, demoted — with the sequence number inside the signed bytes and `<aseq>` the actor's own sequence at the time of acting — the writing device placing the event at the sequence after the highest it holds in the subject's chain and naming as `<aseq>` the highest sequence it holds in the actor's chain, and `<an>` the writing author's own act number, one more than its previous act in the cell — and the member's device-list statements under `member/<pdnid>/devices/<version>`, one entry per version. An event SHALL be judged against its actor's chain folded up to `<aseq>`: a joined event is admitted when the actor was a member there and is not the subject, a promoted event when the actor was an owner there, a kicked or demoted event when the actor was an owner there and is not the subject, a left event when the actor is the subject itself; the founding event — the creator's first, self-authored, making it a member and an owner — is admitted when its `PdnId`, announcement key and nonce derive the cell id and its signature verifies under that key, and is the root of every verification; an event failing its check SHALL be dropped silently on every member device, and an event whose actor's chain the device does not hold up to `<aseq>`, or whose author's acts it does not hold below `<an>`, SHALL be deferred within the session and re-judged once they arrive, or dropped and offered again by the next session. Every entry SHALL be written once: an entry under a subject sequence the write admission already shows held by the same author SHALL be dropped, and no entry in the membership store is overwritten or deleted — the store holds no tombstones. A member's membership state and role SHALL be folded by walking its events in sequence order on every member device, whatever order the events arrived in and never by entry timestamp: a join makes it a plain member, a promotion an owner, a demotion a plain member, a leave or a kick no member, a later join a plain member again.

#### Scenario: A role flip resolves by sequence whatever the arrival order

- **WHEN** owner A promotes B (B's sequence 2, after B's join at 1), demotes B (3) and promotes B again (4), and the three events reach a device of member C in the order 4, 2, 3
- **THEN** C's device lists B by the highest sequence it holds after each arrival — an owner throughout — and as an owner once all three have arrived

#### Scenario: A role event from a plain member is dropped

- **WHEN** a device of member C, no owner, produces a promoted event for C and reconciles with a device of B
- **THEN** B's device drops it and B still lists the owners unchanged

#### Scenario: A leave ends the membership and a new join restores it as a plain member

- **WHEN** B, an owner, writes a left event (sequence 5) from its own device, and a member later invites B again, writing a joined event (sequence 6)
- **THEN** every member device lists B as no member after sequence 5 and as a plain member — no owner — after sequence 6

#### Scenario: A device holding nothing verifies the store from the founding event

- **WHEN** newcomer D's device, holding no membership store, sessions with the inviter's device, which holds the creator's founding event and every event since
- **THEN** D's device converges on the same membership as the inviter in that session, every event verified against its actor's chain, whatever order the events arrived in

#### Scenario: What an owner did while an owner stands after its demotion

- **WHEN** owner A promoted C naming A's sequence 3, A was then demoted at A's sequence 4 by an owner whose device held that promotion, and a device linked into member B after that catches up
- **THEN** B's new device lists C as an owner

#### Scenario: An event naming an actor point without the membership state it needs is dropped

- **WHEN** A was demoted at A's sequence 4 and a device of member E relays a promoted event for F authored by A's device naming A's sequence 4
- **THEN** no member device persists it and F is listed as a plain member

#### Scenario: Nobody leaves for another member

- **WHEN** a device of member D produces a left event in B's chain
- **THEN** no member device persists it and B is still listed as a member

#### Scenario: Nobody kicks or demotes itself

- **WHEN** a device of owner A produces a kicked event and a demoted event in A's own chain
- **THEN** no member device persists either, and A is still listed as a member and an owner

#### Scenario: A departed member does not readmit itself

- **WHEN** C left at C's sequence 2, and a device of member D relays a joined event in C's chain at C's sequence 3, authored by C's device and naming C's sequence 1
- **THEN** no member device persists it and C is listed as no member

#### Scenario: A founding event that does not derive the cell id is dropped

- **WHEN** a device of owner C produces a founding event in C's own chain, or one in the creator's chain under another announcement key or nonce
- **THEN** no member device persists it and the owners are listed unchanged

#### Scenario: A device holding nothing refuses an invented founder whatever arrives first

- **WHEN** a device freshly linked into member D, holding the cell id from D's directory and no membership store, sessions first with a modified device of member B that serves a founding event in B's chain and withholds the creator's, and then with a device of member C
- **THEN** the linked device persists no event of B's invented chain, and after the session with C lists the members and owners C's device lists

#### Scenario: A promoted event for no member changes nothing

- **WHEN** owner A produces a promoted event in the chain of an identity that never joined
- **THEN** every member device holds the entry as written and lists that identity as no member and no owner

#### Scenario: Two owners' concurrent events at one point both persist

- **WHEN** owners A and C, disconnected from each other, each write an event in B's chain at B's sequence 5 — A a promoted event, C a kicked event — and the members' devices then reconcile
- **THEN** every member device holds both entries, and every member device lists B's membership state the same (the rule is cells B10)

#### Scenario: An event by no member's device is dropped

- **WHEN** a device of member D relays an event in B's chain authored by a key that resolves to no member's device
- **THEN** no member device persists it and B's chain is read unchanged

#### Scenario: An event ahead of its actor's point is admitted when the point arrives

- **WHEN** a device of member D receives a promoted event for C authored by A's device naming A's sequence 3 while holding A's chain only up to sequence 2, and A's sequence 3 arrives in a later session
- **THEN** the event is deferred, not persisted, in the first session, and persisted in the session that brings A's sequence 3

#### Scenario: A rewritten event is dropped

- **WHEN** owner A's device writes B's promoted event at sequence 2, and later produces a different entry at the same key
- **THEN** every member device keeps the first entry and drops the second

### Requirement: A narrowing counts the narrowed member's acts only as far as its writer saw them

Every left, kicked and demoted event SHALL carry a mark — for each author the subject's device statements list, the highest act number of that author the writing device holds — and SHALL be admitted only once the device holds the acts its mark names. An act of the subject naming a point before a narrowing that forbids it — any act before a left or kicked event, an owner's act before a demoted event — SHALL count only if its act number is within that narrowing's mark for its author, the first such narrowing after the named point deciding and, at a sequence holding several, the highest of their marks. Every other such act SHALL be held and relayed like any entry and ignored by the fold on every member device, whatever order the entries arrived in, and so SHALL every event resting on it; the gate SHALL judge an event's named point by the membership folded without this rule, so every member device holds the same entries. Two acts of one author under one act number SHALL both be ignored. A member that joins again SHALL be a plain member at its new point and an owner only through a later promotion.

#### Scenario: A kicked owner that joins again is a plain member until promoted

- **WHEN** A, an owner from A's sequence 2, is kicked at A's sequence 4 by owner C, whose device holds A's acts up to act number 7, member E invites A again at A's sequence 5, and A's device then writes under act numbers 8 and 9 a promoted event for A itself and one for plain member X, both naming A's sequence 2
- **THEN** every member device holds both entries and lists A and X as plain members, and lists A as an owner only once an owner promotes it anew

#### Scenario: A demoted owner's act under its old point does not count

- **WHEN** owner A is demoted at A's sequence 4 by owner C, whose device holds A's acts up to act number 7, and a device of plain member E relays a promoted event for A itself, authored by A's device after the demotion, naming A's sequence 3 under act number 8
- **THEN** every member device holds the entry and lists A as a plain member

#### Scenario: An event resting on an ignored act is ignored with it

- **WHEN** kicked owner A's promotion of X, beyond the kick's mark, reaches a device of X before the kick does, and X's device then promotes Y
- **THEN** once the kick has arrived, every member device holds both promotions and lists X and Y as plain members

#### Scenario: A concurrent act loses to its actor's narrowing

- **WHEN** owner A's device, disconnected, kicks member Z under act number 8, while owner C's device, holding A's acts up to act number 7, demotes A, and the members' devices then reconcile
- **THEN** every member device holds both entries and lists A as a plain member and Z as a member, until a current owner kicks Z again

#### Scenario: A narrowing leaves the acts it does not forbid

- **WHEN** owner A, demoted at A's sequence 4 under a mark of act number 7, invites newcomer N under act number 8 naming A's sequence 3
- **THEN** every member device lists N as a plain member

#### Scenario: Two acts under one act number are both ignored

- **WHEN** a device of owner A writes, under one act number of its author, a promoted event for X and a promoted event for Y
- **THEN** every member device holds both entries and lists X and Y as plain members

#### Scenario: An act ahead of its author's lower act numbers is deferred

- **WHEN** a device of member D receives an act of A's author numbered 5 while holding that author's acts only up to 3
- **THEN** the act is not persisted until act 4 arrives, and is persisted in the session that brings it

#### Scenario: A mark naming acts that do not exist holds the narrowing back

- **WHEN** a device of member A writes a left event whose mark names act number 20 of A's author while that author's acts go up to 7
- **THEN** no member device persists the left event until acts 8 to 20 of that author arrive, and every member device lists A as a member meanwhile

### Requirement: Verdicts hold their limits without an anchored log

While the retrograde direction stays open (cells F7), the gate SHALL judge by the point an entry names, by the mark of its actor's narrowing (cells D33) and by the membership state as of the session, and by nothing else: it SHALL admit an event or a record whose named point checks out, whoever carries it and whenever it arrives, and SHALL refuse or defer what the session's own state cannot resolve. The scenarios below are the consequences — what the gate does, not what a cell wants — each named after the decision or the open question that keeps it, those under cells F7 expected to flip once that question is answered.

#### Scenario: A departed member's new record under its old sequence is admitted (F7)

- **WHEN** C was kicked at C's sequence 2, and a device of member D relays an operation C's device authored after the kick, naming C's sequence 1
- **THEN** every member device persists it

#### Scenario: A rewrite that reaches a device first stays there (F7)

- **WHEN** owner A's device rewrote B's promoted event at B's sequence 2 under A's own author key, and a device linked into member E catches up first from A's device and only then from a device holding the original
- **THEN** E's new device keeps the rewrite and drops the original, while every device that held the original keeps it — two devices, two memberships

#### Scenario: A deletion an owner wrote before its demotion is dropped after it (D24, by decision)

- **WHEN** owner A's device placed a tombstone on B's record while A was an owner, A was then demoted, and the tombstone reaches a device of C after the demoted event did
- **THEN** C's device drops the tombstone and B's record is still read, until a current owner deletes it again

#### Scenario: A newcomer is refused a session until its joined event arrives (D19)

- **WHEN** D joined through member E, D's joined event has not reached a device of A, and D's device requests a session from A's device
- **THEN** the session is refused as for an unhosted store, and served once the joined event reaches A's device

#### Scenario: A device statement ahead of its join is dropped in that session (D19)

- **WHEN** in one session a device of A receives B's device statement before the joined event carrying B's announcement key
- **THEN** the statement is dropped in that session and admitted in the next

#### Scenario: A dependency whose authoring device died is never resolved until re-issued (D23)

- **WHEN** A's sequence 3 — the event that promoted A — reached only A's device before B's device, which authored it, died; A's device then promoted C naming A's sequence 3, spread that event to a device of D, and died too, so no live device holds A's sequence 3
- **THEN** every device defers C's promoted event indefinitely and lists C as a plain member meanwhile, and lists C as an owner only after a current owner promotes C anew — an ordinary promotion at a point every device holds

### Requirement: The membership store is reconciled before the record store

A session between two member devices SHALL reconcile the membership store to convergence, fold it into the write admission, and only then reconcile the record store under it; both stores SHALL be reconciled whole, with no capability filter on either. The write admission a session is judged by SHALL be that session's own — the fold of the replica it addresses, carried from its setup to the gate, and on the membership store grown within the session as deferred events are admitted — so two sessions of one node acting as two members never judge by each other's. A record whose author's membership the same session brings SHALL be judged under that membership; a record that reaches a device ahead of its author's joined event SHALL be dropped and persisted from the first session after the record arrives.

#### Scenario: A newcomer's first record is admitted in the session that brings its membership

- **WHEN** newcomer D's joined event and D's first claim are both unknown to a device of B, and B's device sessions with a device holding both
- **THEN** B's device persists D's claim in that session

#### Scenario: A role change is applied before a deletion is judged

- **WHEN** A's demoted event and a tombstone A's device then placed on B's record are both unknown to a device of member C, and C's device sessions with a device holding both
- **THEN** C's device drops the tombstone in that session, and B's record is still read

### Requirement: The record store's key names the member and the kind

A record SHALL sit under the name of the member that placed it, the key carrying the record's kind and the writer's membership sequence at the time of writing: `by/<pdnid>/claim/<id>/<mseq>` for a claim, `by/<pdnid>/immutable-document/<id>/<mseq>` for an immutable-document, `by/<pdnid>/mergeable-document/<id>/<op>` for each operation of a mergeable-document, `<op>` being the writer's author key, the writer's membership sequence and the writer's own operation sequence. `<pdnid>` SHALL be the member's identity, never a device. A record's identity SHALL be its key without the trailing sequence, and a tombstone SHALL be the store's empty entry at that key — above the content entry, above a mergeable-document's operations.

#### Scenario: A record sits under the name of the member that placed it

- **WHEN** member B places a claim, an immutable-document and a mergeable-document with one operation, from two of B's devices
- **THEN** their keys are `by/<B>/claim/<id>/<mseq>`, `by/<B>/immutable-document/<id>/<mseq>` and `by/<B>/mergeable-document/<id>/<op>`, the same `<B>` and the same `<mseq>` from either device, and a listing under B's prefix returns exactly them

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

An operation on a mergeable-document SHALL be admitted from a device of any member, whoever's name the mergeable-document sits under, each operation carrying its writer's author signature and naming, in its key, the writer's membership sequence at the time of writing. The one ground for dropping an operation is its writer's membership state at that sequence: an operation whose author resolves to no member's device, or to a member that was not a member at the named sequence of its own events, SHALL be dropped before persisting, silently, on every member device — no role, no mergeable-document and no time of authoring narrows admission further; an operation naming a sequence the device does not yet hold SHALL be dropped and persisted from the first session after the events arrive, since reconciliation offers again what the device lacks. An operation is judged the same on every device whenever it arrives: everything a member wrote while a member — its operations on its own mergeable-documents and on other members' — SHALL be admitted after it leaves or is kicked, on a device that catches up later included, and SHALL resolve to that member after it joins again, its new operations naming its new sequence. No record carries a sharing mode.

#### Scenario: Any member edits another member's mergeable-document

- **WHEN** a device of member C, no owner, appends an operation to a mergeable-document under member B's name and the members' devices reconcile
- **THEN** every member's devices persist C's operation, its author being C's device

#### Scenario: An operation by no member's device is dropped

- **WHEN** a device of member B carries an operation on a mergeable-document authored by a key that resolves to no member's device, and reconciles with a device of a third member
- **THEN** no member device persists it, no rejection is signalled, and the mergeable-document's own operations survive unchanged

#### Scenario: A departed member's earlier operation reaches a device that catches up later

- **WHEN** member C, a member from sequence 1, appended an operation naming sequence 1, C was then kicked at sequence 2, and a device linked into member B after the kick catches up from a device of member D
- **THEN** B's new device persists C's operation, in C's own mergeable-documents and in B's alike

#### Scenario: An operation naming a sequence at which its writer was no member is dropped

- **WHEN** C was kicked at sequence 2 and a device of member D relays an operation authored by C's device naming sequence 2
- **THEN** no member device persists it, no rejection is signalled, and C's operations naming sequence 1 stay

#### Scenario: A member that joins again writes under its new sequence

- **WHEN** member C was kicked at sequence 2, a member invites C again at sequence 3, and C's device then appends an operation naming sequence 3
- **THEN** every member device persists the operation, and C's earlier operations, naming sequence 1, still resolve to C

#### Scenario: An operation ahead of its author's joined event is persisted once the event arrives

- **WHEN** a device of member B receives, from a device of member E, an operation authored by a device of D while no joined event of D has reached B's device
- **THEN** the operation is dropped, and it is persisted from the first session after D's joined event reaches B's device, reconciliation offering it again

### Requirement: A mergeable-document keeps every operation; an immutable-document is placed once by its member

A mergeable-document SHALL hold each edit as its own entry under its own key, never overwritten by another edit: concurrent operations by two writers the cell admits SHALL both persist on every member device, and their merge is above the data layer. An immutable-document SHALL be one entry under one key, admitted only when authored by a device of the member under whose name it sits; an entry at that key authored by a device of any other member — an owner included — SHALL be dropped before persisting, silently, on every member device, a tombstone excepted: an owner deletes, then places its own.

#### Scenario: Concurrent operations on a mergeable-document both persist

- **WHEN** a device of member B and a device of member C each append an operation to a mergeable-document under B's name while disconnected, and the members' devices then reconcile
- **THEN** every member device holds both operations

#### Scenario: An immutable-document is admitted from its member and from nobody else

- **WHEN** a device of member B places an immutable-document, a device of owner A then produces an entry at its key, and the members' devices reconcile
- **THEN** every member device persists B's immutable-document and drops A's entry, B's immutable-document reading unchanged

### Requirement: Deleting a record kills it

A tombstone SHALL be the store's empty entry at a record's key — the key of the record's content entries without their last segment. It SHALL be admitted from a device of the member under whose name the record sits or of an owner, judged as of the session, and dropped silently from any other device. Once it is admitted, the record store SHALL remove every author's content entries of that record and release their blobs as soon as no replica on the node references them — the blob store is one for every identity the node hosts, so a co-located member's replica of the record keeps them until it takes the tombstone too — SHALL refuse at ingest every content entry of that record afterwards whatever its timestamp, and SHALL keep the tombstone entry, so that a peer holding the content and not the tombstone converges on the deletion. Beyond this rule no entry in either store, empty or not, SHALL remove, supersede or refuse an entry at any other key.

#### Scenario: An owner's deletion removes the record and its blob everywhere

- **WHEN** owner A's device places a tombstone on B's immutable-document and the members' devices reconcile
- **THEN** no member device reads the immutable-document, none holds its content entry or its blob, and each holds the tombstone

#### Scenario: A member deletes its own record; a plain member deletes no other member's

- **WHEN** member B's device places a tombstone on B's claim, and member C's device, no owner, places one on B's immutable-document, and the members' devices reconcile
- **THEN** B's claim is gone on every member device while B's immutable-document is still read, C's tombstone dropped

#### Scenario: A kicked member's records are deleted by an owner, by nobody else

- **WHEN** C was kicked, and then a device of owner A, a device of plain member D, a device of C and a device of no member each place a tombstone on a record under C's name
- **THEN** A's tombstone is admitted and the record gone, and the other three are dropped

#### Scenario: A deleted record admits no content, whatever its timestamp

- **WHEN** B's immutable-document was deleted by an owner, and a device of B then offers a content entry at the same key carrying a timestamp newer than the tombstone's
- **THEN** no member device inserts it and the immutable-document stays deleted

#### Scenario: A peer that missed the tombstone converges on the deletion

- **WHEN** a device of member D holds B's immutable-document and has not received the tombstone, and it reconciles with a device holding the tombstone
- **THEN** D's device drops the immutable-document and its blob and holds the tombstone, and the device it reconciled with does not receive the immutable-document back

#### Scenario: Deleting a mergeable-document kills its operations

- **WHEN** owner A's device places a tombstone at B's mergeable-document's key, and a device of C then offers an operation under it
- **THEN** every member device removes the mergeable-document's operations and inserts no more under it

#### Scenario: An empty entry at a shorter key deletes nothing

- **WHEN** a device of owner A places an empty entry at `by/<B>/`, and the members' devices reconcile
- **THEN** every member device still reads all of B's records, and holds A's entry as an entry outside the layout

#### Scenario: A non-empty entry at a record's key erases nothing

- **WHEN** a device of member B writes a non-empty entry at the key of B's own mergeable-document, without an operation segment, and the members' devices reconcile
- **THEN** every member device still holds all of the document's operations, reads the document unchanged, and holds B's entry as an entry outside the layout

### Requirement: Entries outside the key layout are kept, used by nothing, and listed

An entry in either store whose key fits neither store's layout, or fits one only in part, SHALL be admitted when its author resolves to a device of a current member, and dropped silently otherwise; once admitted it SHALL be reconciled, held and relayed like any entry. A key longer than the store's bound of 8,192 bytes is dropped before any layout is read ([capability-gated ingest](../capability-gated-ingest/spec.md)), so every record key the layouts define, a record's id included, has to fit under that bound. No membership fold, no admission verdict and no record view SHALL read it, and the store SHALL list such entries with their authors so the application can show them.

#### Scenario: An unknown entry from a member converges and changes nothing

- **WHEN** a device of member B writes an entry at `ext/anything` in the record store, and the members' devices reconcile
- **THEN** every member device holds the entry and lists it with B as its author, every record reads as before, and a later session between any two member devices finds no difference

#### Scenario: An unknown entry from no member's device is dropped

- **WHEN** a device of member D relays an entry at `ext/anything` authored by a key that resolves to no member's device
- **THEN** no member device persists it

### Requirement: A member's devices are announced by the member itself

A member's device-list statement — each device's node id beside the author the member writes with on that device — SHALL be admitted by the signature embedded in it — made by the announcement key over the prefix `pdn/cell-devices/v1` followed by the statement — verified against the announcement key the member's join statement, or the creator's founding event, carries — never by the entry's author or the session peer: a statement written by a freshly linked device of the member itself and a statement relayed by any other member earn the same verdict. A statement whose embedded signature does not verify under the member's announcement key SHALL be dropped silently on every member device. Device resolution SHALL follow the highest validly signed version among the member's statements, never entry timestamps, so an older statement written later displaces nothing.

#### Scenario: A new device registers itself through its siblings

- **WHEN** a device freshly linked into member B writes B's newest device statement into its local replica, reconciles with another device of B that holds the cell, and that device then reconciles with a device of member C
- **THEN** C's device admits the statement and serves the new device's next session, which it refused before the statement arrived

#### Scenario: Two members on one node are two authors under one node id

- **WHEN** identities B and D, hosted on one node, are both members of a cell and each places a record from that node
- **THEN** B's and D's statements list the same node id under two different authors, and every member device resolves each record to the one member whose author signed it

#### Scenario: A statement under a wrong key is dropped

- **WHEN** a device of member M produces a device statement for member B signed by a key that is not B's announcement key
- **THEN** no member device persists it, and B's device set stays what B's own statements say

#### Scenario: An old version displaces nothing

- **WHEN** a device of B holding version 2 of B's statement writes it into a replica already holding version 3
- **THEN** device resolution still follows version 3 on every member device

### Requirement: A cell's stores are forgotten together

Forgetting a cell SHALL stop reconciling both replicas, leave both swarms, drop both replicas, and remove the cell's registration together, so that operations addressed to that cell afterwards fail with an unknown-cell error distinguishable from transport and storage failures. Forgetting SHALL reach the replicas of the identity that forgets alone: a co-located member's replicas of the same cell go on as before.

#### Scenario: Forgetting a cell unregisters it

- **WHEN** a node holds a cell's stores and forgets the cell
- **THEN** reading or writing under that cell fails with the unknown-cell error, neither replica is reconciled or served, and the node's other cells are unaffected

#### Scenario: One member forgetting spares the co-located other

- **WHEN** a node hosts members B and D of one cell and B forgets it
- **THEN** operations addressed to the cell as B fail with the unknown-cell error, while D still reads and writes the cell and D's replicas keep reconciling
