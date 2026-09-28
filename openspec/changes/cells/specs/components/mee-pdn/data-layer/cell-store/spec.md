# data-layer: cell stores

A cell is a space shared by 0..n members — identities — identified by a cell id that carries no key material and is derived from its creator's announcement key and a random nonce. It lives in two dedicated pdn-store namespaces, each held whole, as a replica of its own, by every member identity on every device that hosts it: the **membership store**, the cell's authority — who is a member, with what role, on which devices — and the **record store**, the records that authority governs. No egress filter runs inside a cell, member devices form each store's swarm, any member device catches up from any other, and a session reconciles the membership store to convergence before the record store. What keeps a cell honest is admission: a session names the member whose replica it addresses and the member its caller acts as, and is served to member devices only, and a record-store entry is admitted by its author — a claim or an immutable-document from the devices of the member under whose name it sits, a mergeable-document's operation from any member's devices — judged on every member device against the writer's membership state at the membership sequence the entry names, so that a forged entry stops at the first honest device it meets. What a member's own devices write as that member — records under its name and acts in any member's chain — is taken on the member's word: an act or a record naming a point the member has since lost, an entry replacing one the member's own author wrote at the same key, two events of the member's at one point, and two entries of one of its records from two of its devices or under two membership sequences are held as they come, a read of such a record returning the one with the newest timestamp, and nothing below specifies or tests what the gate does with them. The runtime's cells service ([pdn-node cells](../../pdn-node/cells/spec.md)) creates and joins the stores; this spec covers the stores themselves.

The membership store is two shapes: what a device writes — an act — and what the fold computes for a member from everything written about it — its chain of events. An act is one entry; its author key resolves to the actor, and the actor's own sequence at the time of acting (`actor_seq`) and the position in the subject's chain (`subject_seq`) sit in the key (cells D21, D23).

```rust
/// One entry a device writes into the membership store.
enum MembershipAct {
    /// The creator's first act: itself a member and an owner. Self-authored; subject = actor; subject_seq = 1; the root.
    /// Derives the cell id and is checked against it by the steps below.
    Found   { nonce: [u8; 16], announcement_key: PublicKey, signature: Signature },
    /// Written by the inviting device once the newcomer's one-time secret is verified and burned, never when the invite is minted.
    /// Any member; subject ≠ actor; `announcement_key` and `subject_signature` are the newcomer's join statement. Held as `Joined`.
    Invite  { subject: PdnId, subject_seq: Seq, actor_seq: Seq, announcement_key: PublicKey, subject_signature: Signature },
    /// The member itself; subject = actor.
    Leave   { subject_seq: Seq, actor_seq: Seq },
    /// An owner; subject ≠ actor.
    Kick    { subject: PdnId, subject_seq: Seq, actor_seq: Seq },
    /// An owner.
    Promote { subject: PdnId, subject_seq: Seq, actor_seq: Seq },
    /// An owner; subject ≠ actor.
    Demote  { subject: PdnId, subject_seq: Seq, actor_seq: Seq },
    /// The member's devices, one key per version; judged by the embedded signature under the member's announcement key, whoever writes it (D16).
    /// `signature` by the announcement key over "pdn/cell-devices/v1" ‖ version ‖ devices.
    AnnounceDevices { version: u64, devices: Vec<MemberDevice>, signature: Signature },
}

/// A device of the member: its node id, which sessions are classified and contacts dialed by, and the author the member
/// writes with there — one author per hosted identity on a device (ADR-0013), so two members on one node share the node id only.
struct MemberDevice { node: NodeId, author: AuthorId }

/// A member's chain: `member/<pdnid>/<seq>/<kind>/<aseq>`, walked in `seq` order. `by` is the actor, `by_seq` the actor's
/// own sequence then.
enum MembershipEvent {
    Founded  { seq: Seq, nonce: [u8; 16], announcement_key: PublicKey },       // by the member itself; the creator's seq 1 only
    Joined   { seq: Seq, by: PdnId, by_seq: Seq, announcement_key: PublicKey }, // by any member other than the member
    Left     { seq: Seq, by_seq: Seq },                                         // by the member itself
    Kicked   { seq: Seq, by: PdnId, by_seq: Seq },                              // by an owner other than the member
    Promoted { seq: Seq, by: PdnId, by_seq: Seq },                              // by an owner
    Demoted  { seq: Seq, by: PdnId, by_seq: Seq },                              // by an owner other than the member
}

/// Folding a chain up to a sequence: Founded makes a member and an owner, Joined a plain member, Promoted an owner, Demoted a plain member,
/// Left and Kicked no member; a transition the state does not allow (Promoted of no member, Joined of a member) is ignored.
struct MemberState { member: bool, owner: bool, announcement_key: Option<PublicKey>, devices: Vec<MemberDevice> }

/// The gate's check of one event, from the write admission alone:
///   Founded          → seq == 1 and the receiving steps below pass
///   Joined           → by != subject and state(by, by_seq).member
///   Left             → by == subject
///   Promoted         → state(by, by_seq).owner
///   Kicked | Demoted → by != subject and state(by, by_seq).owner
/// and for every kind: by's chain held up to by_seq — else deferred.
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

**Example:** the replicas Alice's tablet a3 holds; a3 hosts Alice-leisure and Alice-work, both members of the cell "Wedding", Alice-leisure a member of "Family" too and Alice-work no member of it, and Alice-work holds Erin's data namespace under her grant.

| replica on a3 | held for |
|---|---|
| Wedding's membership store | Alice-leisure |
| Wedding's record store | Alice-leisure |
| Wedding's membership store, converging with Alice-leisure's copy inside the process | Alice-work |
| Wedding's record store, likewise | Alice-work |
| Family's membership store and record store | Alice-leisure alone |
| Erin's data namespace, under her grant | Alice-work |
| the connection metadata pair between Erin and Alice-work | Alice-work |
| each identity's own directory and data store | Alice-leisure, Alice-work |
| An import for Alice-work, as Wedding's record store, of a ticket naming Erin's data namespace is refused, nothing registered, and Erin's namespace is held and reconciled as before. | |

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

**Example:** the id of "Family", which Alice creates; her `PdnId` is 32 bytes of `11`, her announcement key the public key of the secret made of 32 bytes of `33`, and the nonce her device draws 16 bytes of `5a`.

```
pdn_id                1111111111111111111111111111111111111111111111111111111111111111
announcement_pubkey   17cb79fb2b4120f2b1ec65e4198d6e08b28e813feb01e4a400839b85e18080ce
nonce                 5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a
cell_id               eead8ef96aa1254969d63c12631b799c
                      the first 16 bytes of BLAKE3 derive_key("pdn/cell-id/v1", pdn_id ‖ announcement_pubkey ‖ nonce)
signature             6eaf69a517c28cd7…d40e03370f, 64 bytes of Ed25519
                      over "pdn/cell-founding/v1" ‖ pdn_id ‖ announcement_pubkey ‖ nonce, 100 bytes
a founding event in Alice's chain under another announcement key, d759793bbc13a2819a827c76adb6fba8a49aee007f49f2d0992d99b825ad2c48,
with the same nonce, derives 816954cae150f2652ecaeceab07ae4ac, and every device holding eead8ef96aa1254969d63c12631b799c drops it
both stores' namespace ids are 32-byte public keys of their own, and neither is the cell id
```

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

**Example:** Alice places a claim in "Family" on her phone a1 while Bob's phone b1 is in the record store's swarm and Carol's phone c1 is offline; then a1 goes offline and c1 comes back.

| time | a1, Alice | b1, Bob | c1, Carol |
|---|---|---|---|
| 10:00 | places the claim and announces it on the store's topic, content-free | pulls the claim from a1 in a session | offline |
| 10:30 | offline | | back online: a session with b1 brings the claim, payload included |
| No device holds a grant, and every one of them holds both write tickets. | | | |

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

- **WHEN** a device of member C, no owner, holding the record store's write ticket, produces an entry at the key of B's claim and reconciles with a device of B
- **THEN** B's device drops it and B's claim reads unchanged on every member device

### Requirement: Only member devices are served

A session for either of a cell's stores SHALL name the member whose replica it addresses and the member its caller acts as, and SHALL be served only when the member the caller names is a current member whose records list the caller's authenticated node id: that identity's own directory where the caller names the identity the serving replica belongs to, as a sibling device of it; that member's device statements in the membership store where the caller names another member, over the network and inside the process alike. Every other caller SHALL be refused indistinguishably from the store not being hosted — a holder of its ticket included, and a caller naming an identity that is no member included, even from a node that hosts a member and so shares its node id. A caller naming a member kicked from the cell, or one that left it, SHALL be refused the record store from the first session set up after its departure event reaches the serving device, and served the membership store only as the requirement on a departed member's tombstone states; what it obtained while a member is retained.

**Example:** callers ask Bob's phone b1 for a session on the record store of "Family", addressing Bob's replica; Alice's tablet a3 hosts Alice-leisure, a member, and Alice-work, no member, and Dave, no member, holds the store's ticket on his phone d1.

| caller | names | b1 |
|---|---|---|
| c1, Carol's phone | Carol | serves every entry |
| a3 | Alice-leisure | serves every entry, as Alice-leisure |
| a3 | Alice-work | refuses with `00 00 00 02 02 00`, the answer for a store b1 does not host |
| d1 | Dave | refuses with the same frame, the ticket notwithstanding |
| c1, once Carol's kicked event has reached b1 | Carol | refuses with the same frame from the next session; what c1 took before stays readable on it |

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

- **WHEN** a member is kicked and the kicked event has reached a serving device, and a device of the kicked member then requests a session on the record store
- **THEN** the request is refused as for an unhosted replica, while the remaining members' devices are still served, and what the kicked member's device obtained while a member is still readable on it

### Requirement: A departed member's devices keep the membership store as the cell's tombstone

A member's departure event — its left event, or a kicked event in its chain — SHALL end its devices' hold on the record store and SHALL NOT end their hold on the membership store: every device of the departed member's identity SHALL keep the membership store for good as the cell's tombstone, and forget the record store. The departure's past SHALL be the departure event and every entry it depends on — the earlier events of its subject's chain, its actor's chain up to the point it names, and, for each of these in turn, the same, with the joined events and device statements that resolve their authors — down to the founding event. A member device SHALL serve a session naming a former member, from a device the former member's statements list, on the membership store alone and over the departure's past alone, in both directions, and SHALL serve it nothing outside that past; a sibling device of the former member SHALL serve it the tombstone whole. A tombstone SHALL be reconciled with member devices until one session with a member device has converged over the departure's past, and then with the identity's own devices alone.

**Example:** Carol leaves "Family" on her phone c1 while c1 is offline, and an hour later c1 reaches Bob's phone b1; meanwhile Bob invited Dave, and nothing in Carol's departure depends on Dave's join.

| on b1 | c1 |
|---|---|
| a session on the membership store naming Carol | served over the past of her left event: b1 admits the left event and sends what of that past c1 lacks, and not Dave's joined event |
| a session on the record store naming Carol | refused with `00 00 00 02 02 00` |
| a record Alice places afterwards | reaches b1 and never c1 |

#### Scenario: A left event written offline reaches the members

- **WHEN** a member leaves on a device with no member device reachable, and that device later reaches a member device
- **THEN** the member device persists the left event and every member device lists the member as no member, while the departed device is refused the record store

#### Scenario: A device offline during its member's kick learns of the kick

- **WHEN** member C's device is offline while an owner kicks C, and the device then requests a session from a member device
- **THEN** the session on the membership store delivers C's kicked event and the entries it rests on, C's device forgets the record store and keeps the membership store, and neither a record placed after the kick nor a membership event outside the kick's past reaches it from any member device

#### Scenario: Every device of a departed identity keeps the tombstone

- **WHEN** a member leaves on one device while another device of its identity holds the cell, and the identity's directory syncs
- **THEN** both devices hold the membership store and neither holds the record store

### Requirement: Membership needs no connection

Access to a cell's stores SHALL rest on membership alone: no connection between two members is required for either to read what the other wrote, and joining a cell SHALL create no connection.

**Example:** Alice, Bob and Carol hold no connection to one another; Alice creates "Family" and invites Bob and Carol, and Bob places a claim. Asked on Carol's phone c1:

| call | answer |
|---|---|
| `list_connections` on Carol's directory | `[]` |
| a read of Bob's claim in "Family" | the claim's bytes |

#### Scenario: Three identities share through a cell with no connections

- **WHEN** identities A, B and C hold no connection to one another, A creates a cell and invites B and C, and B writes an entry
- **THEN** C's device reads the entry, and no identity lists any connection

### Requirement: The membership store holds each member's event sequence, append-only

The membership store SHALL hold, per member, one sequence of membership events under `member/<pdnid>/<seq>/<kind>/<aseq>` — founded, joined, left, kicked, promoted, demoted — with the sequence number inside the signed bytes and `<aseq>` the actor's own sequence at the time of acting — the writing device placing the event at the sequence after the highest it holds in the subject's chain and naming as `<aseq>` the highest sequence it holds in the actor's chain — and the member's device-list statements under `member/<pdnid>/devices/<version>`, one key per version. An event SHALL be judged against its actor's chain folded up to `<aseq>`: a joined event is admitted when the actor was a member there and is not the subject, a promoted event when the actor was an owner there, a kicked or demoted event when the actor was an owner there and is not the subject, a left event when the actor is the subject itself; the founding event — the creator's first, self-authored, making it a member and an owner — is admitted when its `PdnId`, announcement key and nonce derive the cell id and its signature verifies under that key, and is the root of every verification; an event failing its check SHALL be dropped silently on every member device, and an event whose actor's chain the device does not hold up to `<aseq>` SHALL be deferred within the session and re-judged once it arrives, or dropped and offered again by the next session. Honest devices overwrite and delete no entry in the membership store — the store holds no tombstones. A member's membership state and role SHALL be folded by walking its events in sequence order on every member device, whatever order the events arrived in and never by entry timestamp: a join makes it a plain member, a promotion an owner, a demotion a plain member, a leave or a kick no member, a later join a plain member again. Events at one sequence of one subject SHALL all persist, and the fold SHALL take effect with the one that ranks highest — kicked, then left, then demoted, then promoted, then joined — applied to the subject's state before that sequence, the same event written twice counting once. When the folded membership holds no owner and the roles of some of its former owners ended in demotions, the fold SHALL take those demotions in the order of their actors' `PdnId`, lowest first, each against the former owners it has not yet removed, and SHALL ignore every one that would remove the last of them.

**Example:** Bob's chain in "Family" as every member device holds it; the key's last segment is the actor's sequence; `<bob>`: 64 lowercase hex chars of Bob's `PdnId`.

```
member/<bob>/1/joined/1       a1's author: Alice at her sequence 1          Bob a plain member
member/<bob>/2/promoted/1     a1's author: Alice at her sequence 1          an owner
member/<bob>/3/demoted/1      a1's author: Alice at her sequence 1          a plain member
member/<bob>/4/left/3         b1's author: Bob himself at his sequence 3    no member
member/<bob>/5/joined/1       c1's author: Carol at her sequence 1          a plain member again
member/<bob>/devices/1        Bob's device statement, version 1: b1

the fold walks the chain by sequence, whatever order the entries arrived in
```

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

- **WHEN** owner A promoted C naming A's sequence 3, A was then demoted at A's sequence 4, and a device linked into member B after that catches up
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
- **THEN** every member device holds both entries and lists B as no member, the kick outranking the promotion

#### Scenario: Two owners demoting each other leave one owner

- **WHEN** owners A and C, disconnected from each other and the cell's only owners, demote each other, A's `PdnId` sorting below C's, and the members' devices then reconcile
- **THEN** every member device holds both entries and lists A as the one owner and C as a plain member

#### Scenario: A leave beside a demotion at one point leaves the member out

- **WHEN** owner A demotes owner B at B's sequence 4 while B, disconnected from A, leaves at its sequence 4, and the members' devices then reconcile
- **THEN** every member device holds both entries and lists B as no member, the leave outranking the demotion

#### Scenario: An event by no member's device is dropped

- **WHEN** a device of member D relays an event in B's chain authored by a key that resolves to no member's device
- **THEN** no member device persists it and B's chain is read unchanged

#### Scenario: An event ahead of its actor's point is admitted when the point arrives

- **WHEN** a device of member D receives a promoted event for C authored by A's device naming A's sequence 3 while holding A's chain only up to sequence 2, and A's sequence 3 arrives in a later session
- **THEN** the event is deferred, not persisted, in the first session, and persisted in the session that brings A's sequence 3

### Requirement: Verdicts hold their limits without an anchored log

The gate SHALL judge by the point an entry names and by the membership state as of the session, and by nothing else: it SHALL admit an event or a record whose named point checks out, whoever carries it and whenever it arrives, and SHALL refuse or defer what the session's own state cannot resolve. The scenarios below are its consequences on honest devices — what the gate does, not what a cell wants — each named after the decision or the open question that keeps it.

**Example:** three verdicts in "Family" beside what a cell would want of each.

| case | the gate | a cell wants | kept by |
|---|---|---|---|
| Alice's promotion of Carol, naming Alice's sequence 3, an event only devices that have since died ever held | defers it for ever | admitted | the actor's point, until a current owner promotes Carol anew |
| Dave's phone d1 asks Alice's phone a1 for a session before Dave's joined event reaches a1 | refuses it | served | the session order, healed once the joined event arrives |

#### Scenario: A newcomer is refused a session until its joined event arrives (cells D19)

- **WHEN** D joined through member E, D's joined event has not reached a device of A, and D's device requests a session from A's device
- **THEN** the session is refused as for an unhosted store, and served once the joined event reaches A's device

#### Scenario: A dependency whose authoring device died is never resolved until re-issued (cells D23)

- **WHEN** A's sequence 3 — the event that promoted A — reached only A's device before B's device, which authored it, died; A's device then promoted C naming A's sequence 3, spread that event to a device of D, and died too, so no live device holds A's sequence 3
- **THEN** every device defers C's promoted event indefinitely and lists C as a plain member meanwhile, and lists C as an owner only after a current owner promotes C anew — an ordinary promotion at a point every device holds

### Requirement: The membership store is reconciled before the record store

A session between two member devices SHALL reconcile the membership store to convergence, fold it into the write admission, and only then reconcile the record store under it; both stores SHALL be reconciled whole, with no capability filter on either. The write admission a session is judged by SHALL be that session's own — the fold of the replica it addresses, carried from its setup to the gate, and on the membership store grown within the session as deferred events are admitted — so two sessions of one node acting as two members never judge by each other's. A record whose author's membership the same session brings SHALL be judged under that membership; a record that reaches a device ahead of its author's joined event SHALL be dropped and persisted from the first session after the joined event arrives.

**Example:** Alice's laptop a2 holds neither Dave's joined event nor Dave's first claim, and sessions with Carol's phone c1, which holds both; `<dave>`: 64 lowercase hex chars of Dave's `PdnId`; `<id>`: the id `put_record` minted.

| step of the session | a2 |
|---|---|
| 1. the membership store reconciled to convergence | takes Dave's joined event and his device statement, listing his phone d1 |
| 2. the write admission folded | Dave a member at his sequence 1, writing on d1 |
| 3. the record store reconciled under it | takes `by/<dave>/claim/<id>/1` from d1's author, judged at Dave's sequence 1: admitted in this session |

#### Scenario: A newcomer's first record is admitted in the session that brings its membership

- **WHEN** newcomer D's joined event and D's first claim are both unknown to a device of B, and B's device sessions with a device holding both
- **THEN** B's device persists D's claim in that session

### Requirement: The record store's key names the member and the kind

A record SHALL sit under the name of the member that placed it, the key carrying the record's kind and the writer's membership sequence at the time of writing: `by/<pdnid>/claim/<id>/<mseq>` for a claim, `by/<pdnid>/immutable-document/<id>/<mseq>` for an immutable-document, `by/<pdnid>/mergeable-document/<id>/<op>` for each operation of a mergeable-document, `<op>` being the writer's author key, the writer's membership sequence and the writer's own operation sequence. `<pdnid>` SHALL be the member's identity, never a device. A record's identity SHALL be its key without the trailing sequence, and a record SHALL be addressed by the cell id beside that key, never by either store's namespace id, which is the store's read capability.

**Example:** Bob's three records in "Family", placed from his phone b1 and from his laptop b2; Bob and Carol each joined at their sequence 1; `<bob>`: 64 lowercase hex chars of Bob's `PdnId`; `<claim>`, `<scan>`, `<note>`: the ids `put_record` minted for the three records.

```
by/<bob>/claim/<claim>/1                         from b1
by/<bob>/immutable-document/<scan>/1             from b2, under b2's author
by/<bob>/mergeable-document/<note>/<op>          <op>: b1's author, Bob's sequence 1, that author's operation 1
by/<bob>/mergeable-document/<note>/<op>          <op>: c1's author, Carol's sequence 1, that author's operation 1 — under Bob's name all the same

a listing under by/<bob>/ returns these four entries; each record's identity is its key without the last segment
```

#### Scenario: A record sits under the name of the member that placed it

- **WHEN** member B places a claim, an immutable-document and a mergeable-document with one operation, from two of B's devices
- **THEN** their keys are `by/<B>/claim/<id>/<mseq>`, `by/<B>/immutable-document/<id>/<mseq>` and `by/<B>/mergeable-document/<id>/<op>`, the same `<B>` and the same `<mseq>` from either device, and a listing under B's prefix returns exactly them

### Requirement: A claim is written only by its issuer

An entry that is a claim SHALL be admitted over sync only when it was authored by a device of the member the claim names as its issuer, that member being a member at the sequence the claim's key names. A claim entry authored by a device of any other member SHALL be dropped before persisting, on every member device, silently — the verdict is on the entry's author, not on the session peer that carried it, so an entry relayed by a third member keeps the verdict its author earns.

**Example:** entries at the key of Alice's claim `by/<alice>/claim/<id>/1` reach Carol's phone c1; `<alice>`: 64 lowercase hex chars of Alice's `PdnId`; `<id>`: the id `put_record` minted; a1 is Alice's phone, b1 Bob's.

| entry | its author | carried by | c1 |
|---|---|---|---|
| Alice's claim | a1's | a1 | persists it |
| Alice's claim | a1's | b1 | persists it: judged by its author, not by b1 |
| another entry at that key | b1's | b1 | drops it, signalling nothing; Alice's claim reads unchanged |

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

**Example:** operations on Bob's note reach Alice's laptop a2, linked after all of them were written; Carol, on her phone c1, joined at her sequence 1, was kicked at 2 and invited again at 3.

| operation | its author | names | a2 |
|---|---|---|---|
| Carol's, written while a member | c1's | her sequence 1 | persists it |
| Carol's, written after the kick | c1's | her sequence 2 | drops it, signalling nothing |
| Carol's, written after she joined again | c1's | her sequence 3 | persists it; her operation naming 1 still resolves to her |
| one whose author no member's statement lists | — | — | drops it, signalling nothing |

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

A mergeable-document SHALL hold each edit as its own entry under its own key, never overwritten by another edit: concurrent operations by two writers the cell admits SHALL both persist on every member device, and their merge is above the data layer. An immutable-document SHALL be one entry under one key, admitted only when authored by a device of the member under whose name it sits; an entry at that key authored by a device of any other member — an owner included — SHALL be dropped before persisting, silently, on every member device.

**Example:** Bob and Carol, disconnected from each other on b1 and c1, each append an operation to Bob's note, and Alice, an owner, writes from a1 at the key of Bob's lease scan; `<bob>`: 64 lowercase hex chars of Bob's `PdnId`; `<note>`, `<lease>`: ids `put_record` minted; `<op>`: the writer's author key, membership sequence and operation sequence, so each operation has its own.

| entry | key | every member device |
|---|---|---|
| Bob's operation | `by/<bob>/mergeable-document/<note>/<op>`, `<op>` naming b1's author | holds it |
| Carol's operation | `by/<bob>/mergeable-document/<note>/<op>`, `<op>` naming c1's author | holds it beside Bob's |
| Alice's entry at the scan's key | `by/<bob>/immutable-document/<lease>/1` | drops it, a1 excepted, and reads Bob's scan unchanged |

#### Scenario: Concurrent operations on a mergeable-document both persist

- **WHEN** a device of member B and a device of member C each append an operation to a mergeable-document under B's name while disconnected, and the members' devices then reconcile
- **THEN** every member device holds both operations

#### Scenario: An immutable-document is admitted from its member and from nobody else

- **WHEN** a device of member B places an immutable-document, a device of owner A then produces an entry at its key, and the members' devices reconcile
- **THEN** every member device persists B's immutable-document, and every member device other than A's drops A's entry and reads B's immutable-document unchanged

### Requirement: Entries outside the key layout are kept, used by nothing, and listed

An entry in either store whose key fits neither store's layout, or fits one only in part, SHALL be admitted when its author resolves to a device of a current member, and dropped silently otherwise; once admitted it SHALL be reconciled, held and relayed like any entry. A key longer than the store's bound of 8,192 bytes is dropped before any layout is read ([capability-gated ingest](../capability-gated-ingest/spec.md)), so every record key the layouts define, a record's id included, has to fit under that bound. No membership fold, no admission verdict and no record view SHALL read it, and the store SHALL list such entries with their authors so the application can show them.

**Example:** entries outside the layout reach Carol's phone c1 from Bob's phone b1; `<bob>`: 64 lowercase hex chars of Bob's `PdnId`; `<id>`: an id `put_record` minted.

| entry | its author | c1 |
|---|---|---|
| `ext/anything` in the record store | b1's | holds it and lists it with b1's author; every record reads as before, and the next session with b1 finds no difference |
| `by/<bob>/claim/<id>/1` in the membership store | b1's | holds it the same way, and no membership state changes |
| `ext/anything`, relayed | one no member's statement lists | drops it |

#### Scenario: An unknown entry from a member converges and changes nothing

- **WHEN** a device of member B writes an entry at `ext/anything` in the record store, and the members' devices reconcile
- **THEN** every member device holds the entry and lists it with B as its author, every record reads as before, and a later session between any two member devices finds no difference

#### Scenario: An unknown entry from no member's device is dropped

- **WHEN** a device of member D relays an entry at `ext/anything` authored by a key that resolves to no member's device
- **THEN** no member device persists it

### Requirement: A member's devices are announced by the member itself

A member's device-list statement — each device's node id beside the author the member writes with on that device — SHALL be admitted by the signature embedded in it — made by the announcement key over the prefix `pdn/cell-devices/v1` followed by the statement — verified against the announcement key the member's join statement, or the creator's founding event, carries — never by the entry's author or the session peer: a statement written by a freshly linked device of the member itself and a statement relayed by any other member earn the same verdict. A statement whose embedded signature does not verify under the member's announcement key SHALL be dropped silently on every member device. A statement that arrives before the event carrying the member's announcement key SHALL be deferred within the session and judged once that event is admitted, and so SHALL an entry whose author only a deferred statement lists. Device resolution SHALL follow the union of every validly signed statement at the highest version among the member's statements a device holds, whichever author wrote each and never by entry timestamps, so an older statement written later displaces nothing and two statements written at one version by two authors list every device either names.

**Example:** device statements in "Wedding"; Erin invited Bob, whose phone is b1, and Alice-work, whose one device is Alice's tablet a3; Bob invited Alice-leisure, whose phone is a1, and a3 was later linked into Alice-leisure too; Dave, a member, has the phone d1; `<bob>`, `<alice-leisure>`, `<alice-work>`: 64 lowercase hex chars of each `PdnId`.

| entry | written by | signed by | every member device |
|---|---|---|---|
| `member/<bob>/devices/1`: b1 with b1's author | e1, Erin's phone, in the join dialogue that brought Bob in | Bob's announcement key | admits it: the writer is not the member |
| `member/<alice-leisure>/devices/2`: a1, and a3 with a3's author for Alice-leisure | a3, just linked into Alice-leisure | Alice-leisure's announcement key | admits it, whoever relays it, and resolves Alice-leisure's devices by version 2 |
| `member/<bob>/devices/2` twice: b1 and b2 under b2's author, b1 and b3 under b3's author | b2 and b3, each just linked into Bob while holding version 1 alone | Bob's announcement key | admits both and resolves Bob's devices to b1, b2 and b3 |
| `member/<bob>/devices/3`: b1, b2, b3 and d1 | d1 | Dave's announcement key | drops it |
| `member/<alice-work>/devices/1`: a3 with a3's author for Alice-work | e1, in the join dialogue that brought Alice-work in | Alice-work's announcement key | admits it: a3 stands under two authors, one per member |

#### Scenario: A new device registers itself through its siblings

- **WHEN** a device freshly linked into member B writes the next version of B's device statement, listing itself, into its local replica, reconciles with another device of B that holds the cell, and that device then reconciles with a device of member C
- **THEN** C's device admits the statement and serves the new device's next session, which it refused before the statement arrived

#### Scenario: Two members on one node are two authors under one node id

- **WHEN** identities B and D, hosted on one node, are both members of a cell and each places a record from that node
- **THEN** B's and D's statements list the same node id under two different authors, and every member device resolves each record to the one member whose author signed it

#### Scenario: A statement under a wrong key is dropped

- **WHEN** a device of member M produces a device statement for member B signed by a key that is not B's announcement key
- **THEN** no member device persists it, and B's device set stays what B's own statements say

#### Scenario: A device statement ahead of its join waits for it in the session

- **WHEN** in one session a device of A receives B's device statement, and an event authored by a device only that statement lists, before the joined event carrying B's announcement key
- **THEN** both are deferred and persisted in that same session once the joined event arrives, while a statement for B signed by a key no joined event carries is persisted by no member device

#### Scenario: An old version displaces nothing

- **WHEN** a device of B holding version 2 of B's statement writes it into a replica already holding version 3
- **THEN** device resolution still follows version 3 on every member device

#### Scenario: Two statements at one version list both devices

- **WHEN** two devices of B, out of reach of each other, each write the next version of B's statement listing a different new device, and both statements reach a member device in either order
- **THEN** that device resolves B's devices to every device either statement lists, and a third statement at that version signed by a key that is not B's announcement key adds nothing

### Requirement: A departure forgets the record store and keeps the membership store

Forgetting a cell at a departure SHALL stop reconciling the record store, leave both swarms, drop the record store's replica, and turn the cell's registration into its tombstone together, so that operations addressed to that cell afterwards fail with an unknown-cell error distinguishable from transport and storage failures, while the membership store's replica stays as the tombstone the requirement on a departed member's tombstone describes. Forgetting SHALL reach the replicas of the identity that forgets alone: a co-located member's replicas of the same cell go on as before.

**Example:** Alice's tablet a3 hosts Alice-leisure and Alice-work, both members of "Wedding", and Alice-work leaves the cell.

| on a3, afterwards | as Alice-work | as Alice-leisure |
|---|---|---|
| a read of Erin's claim | the unknown-cell error | the claim |
| Wedding's record store | dropped, its swarm left, reconciled no more | open and reconciling |
| Wedding's membership store | kept as the tombstone, its swarm left | open and reconciling |

#### Scenario: Forgetting a cell unregisters it

- **WHEN** a node holds a cell's stores and forgets the cell at a departure
- **THEN** reading or writing under that cell fails with the unknown-cell error, the record store is neither reconciled nor served, the membership store is held as the cell's tombstone alone, and the node's other cells are unaffected

#### Scenario: One member forgetting spares the co-located other

- **WHEN** a node hosts members B and D of one cell and B forgets it
- **THEN** operations addressed to the cell as B fail with the unknown-cell error, while D still reads and writes the cell and D's replicas keep reconciling
