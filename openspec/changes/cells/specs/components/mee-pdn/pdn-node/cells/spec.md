# pdn-node: cells

The cells service of the runtime: creating a cell for a hosted identity, inviting and joining, ownership, reaching a member's other devices, kicking and leaving, writing records — claims, mergeable-documents and immutable-documents — into the cell, and recovering hosted cells across a restart. The two stores underneath — the membership store and the record store — are the data layer's [cell stores](../../data-layer/cell-store/spec.md); this spec covers the runtime surface and the ceremonies. A cell has two roles, owner and member — the creator the first owner. Who may do what by role is in the tables below: on the cell itself, then on each kind of record, where "own" is a record under one's own name — a record is created under one's own name only.

**Cell**

|                                | Cell owner | Cell member |
| ------------------------------ | ---------- | ----------- |
| Invite member to a cell        | yes        | yes         |
| Leave cell                     | yes        | yes         |
| Delete cell for all members    | no         | no          |
| Promote member to owner        | yes        | no          |
| Demote another owner to member | yes        | no          |
| Demote oneself to member       | no         | no          |
| Kick member from cell          | yes        | no          |
| Kick another owner from cell   | yes        | no          |
| Kick oneself from cell         | no         | no          |

**Immutable-document** — attachments, for example a PDF file.

|                                                                     | Cell owner | Cell member |
| ------------------------------------------------------------------- | ---------- | ----------- |
| Read own immutable-document                                         | yes        | yes         |
| Read another member's immutable-document                            | yes        | yes         |
| Create own immutable-document                                       | yes        | yes         |
| Create an immutable-document as if it is authored by another member | no         | no          |
| Update own immutable-document                                       | no         | no          |
| Update another member's immutable-document                          | no         | no          |

**Mergeable-document** — for example a note.

|                                                                           | Cell owner | Cell member |
| ------------------------------------------------------------------------- | ---------- | ----------- |
| Read own mergeable-document                                               | yes        | yes         |
| Read another member's mergeable-document                                  | yes        | yes         |
| Create own mergeable-document                                             | yes        | yes         |
| Create a mergeable-document as if it is authored by another member        | no         | no          |
| Edit own mergeable-document                                               | yes        | yes         |
| Edit another member's mergeable-document (preserving per-edit authorship) | yes        | yes         |

**Claim**

|                                                    | Cell owner | Cell member |
| -------------------------------------------------- | ---------- | ----------- |
| Read own claim                                     | yes        | yes         |
| Read another member's claim                        | yes        | yes         |
| Issue own claim                                    | yes        | yes         |
| Issue a claim as if it is issued by another member | no         | no          |
| Update own claim                                   | no         | no          |
| Update another member's claim                      | no         | no          |

The service's surface — the operations the requirements below constrain:

```rust
/// The cells service of a runtime. `identity` is the hosted identity acting; a call on a cell the identity is no member of
/// fails with the unknown-cell error, and a refusal by role is a typed error that writes nothing.
trait CellsService {
    /// Derives the cell id, creates both stores, writes the signed founding event; the identity is the first owner.
    async fn create(&self, identity: PdnId) -> Result<CellId>;
    /// The cells the identity is a member of.
    async fn list(&self, identity: PdnId) -> Result<Vec<CellInfo>>;
    /// The current members, each with its role.
    async fn members(&self, identity: PdnId, cell: CellId) -> Result<Vec<Member>>;

    /// Mints a one-time invite: the inviting device's address, the secret, the cell id. Any member. Writes nothing to the cell:
    /// the invite act is written by the inviting device once a newcomer presents the secret.
    async fn invite(&self, identity: PdnId, cell: CellId, lifetime: Option<Duration>) -> Result<CellInvite>;
    /// Joins through the invite's dialogue and returns once caught up; the identity joins as a plain member.
    async fn join(&self, identity: PdnId, invite: CellInvite) -> Result<CellId>;
    /// Writes a membership act after checking the identity's role; the service picks both sequences (cells D23).
    /// `Kick` and `Demote` name another member; `Leave` also forgets both stores on the identity's devices.
    async fn act(&self, identity: PdnId, cell: CellId, act: CellAct) -> Result<()>;

    /// Places a record under the identity's own name at a fresh id: a claim's or an immutable-document's one entry,
    /// or a mergeable-document's first operation.
    async fn put_record(&self, identity: PdnId, cell: CellId, kind: RecordKind, payload: &[u8]) -> Result<RecordRef>;
    /// Appends an operation to an existing mergeable-document, whoever's name it sits under. Any member.
    async fn append_op(&self, identity: PdnId, cell: CellId, record: RecordRef, op: &[u8]) -> Result<()>;
    /// A claim's or an immutable-document's payload; `None` for a record the cell does not hold.
    async fn read(&self, identity: PdnId, cell: CellId, record: RecordRef) -> Result<Option<Vec<u8>>>;
    /// A mergeable-document's operations, each with its writer.
    async fn read_ops(&self, identity: PdnId, cell: CellId, record: RecordRef) -> Result<Vec<Operation>>;
    /// Every record the cell holds.
    async fn list_records(&self, identity: PdnId, cell: CellId) -> Result<Vec<RecordRef>>;
    /// Entries outside the key layout, each with its author (cells D27).
    async fn list_unknown(&self, identity: PdnId, cell: CellId) -> Result<Vec<UnknownEntry>>;
}

/// The founding act is written by `create`, the invite act by the inviting device inside the join dialogue, device statements by the device sweep — never through `act`.
enum CellAct { Promote(PdnId), Demote(PdnId), Kick(PdnId), Leave }
struct RecordRef { member: PdnId, kind: RecordKind, id: RecordId }
enum RecordKind { Claim, MergeableDocument, ImmutableDocument }
```

## ADDED Requirements

### Requirement: The cells service creates a cell for a hosted identity

The cells service SHALL create a cell for a hosted identity: it draws a random nonce, derives the cell id from the identity's `PdnId`, its announcement key and the nonce, creates the membership store and the record store, writes the founding event signed by the announcement key — the creating identity the first member — and answers the cell id, the one address of the cell. Creating a cell for an identity the runtime does not host SHALL be refused with an unknown-identity error and no state created.

**Example:** `create` calls on Alice's phone a1, which hosts Alice and not Erin; the nonces a1 draws are 16 bytes of `5a`, then 16 bytes of `a5`.

| call | result |
|---|---|
| `create(Alice)` | `eead8ef96aa1254969d63c12631b799c`; `members` answers Alice alone, an owner |
| `create(Alice)` again | `684aad236ce530cd7b5dedb6ab6b755a`: another nonce, another id; `list` answers both cells |
| `create(Erin)` | the unknown-identity error, and no store exists for Erin |

#### Scenario: A created cell is listed with its creator as member

- **WHEN** a hosted identity creates a cell
- **THEN** the identity lists a cell with a fresh cell id, whose members are exactly that identity

#### Scenario: Two cells of one identity are two ids

- **WHEN** a hosted identity creates two cells
- **THEN** both are listed, with different cell ids, and each is addressed by its own id

#### Scenario: Creating for an unhosted identity is refused

- **WHEN** a cell is requested for an identity the runtime neither created nor linked
- **THEN** the operation fails with the unknown-identity error and no store exists for it

### Requirement: Any member invites; a newcomer joins after a one-time secret is verified and burned

Any member's device SHALL mint a cell invite: a fresh one-time, short-lived secret pending on the inviting runtime, and a self-contained payload carrying a format version, the inviting device's node address, the secret and the cell id — no ticket and no identity proof; minting SHALL write nothing to either store. A newcomer SHALL join by presenting the secret in a dialogue with the inviter; the inviter SHALL verify and burn the secret atomically before any state change, then write the invite act, which records the newcomer as a member — a plain member, no owner — and hand it the write tickets of both stores. The dialogue SHALL carry, beside the newcomer's signed join statement, its first device statement, which the inviter writes beside the invite act into the replica of the identity the secret was minted for, so the inviter serves the newcomer's first session. Between two identities of one node the dialogue SHALL run inside the process ([in-process sessions](../../data-layer/in-process-sessions/spec.md)), the secret verified and burned as between two nodes. A refused presentation — wrong, expired or already burned — SHALL leave no observable state and SHALL NOT burn a live pending invite, and refusals SHALL be uniform. After joining, the newcomer's device holds the store, catches up on its existing content, and every member's devices list the newcomer.

**Example:** Bob's phone b1 mints an invite to "Family" as Bob — a format version, b1's node address, the secret and `eead8ef96aa1254969d63c12631b799c`, no ticket — and Bob hands it to Carol; three presentations follow.

| presented to b1 | b1 |
|---|---|
| a secret b1 never minted | refuses; nothing is written, and the pending invite stays live |
| the invite's secret, by Carol's phone c1 | burns it, then writes into Bob's replica Carol's joined event, a plain member, and her device statement, and hands c1 both stores' write tickets; `join` on c1 returns caught up |
| the same secret again | refuses, as it refused the never-minted one |

#### Scenario: A newcomer joins and catches up

- **WHEN** a member invites and a hosted identity on another runtime joins with the invite
- **THEN** the newcomer reads the entries written before it joined, and the inviter's and the newcomer's devices both list the newcomer among the members

#### Scenario: An invited member invites in turn

- **WHEN** A invites B, and B then invites C from B's own device
- **THEN** C joins, and A's devices list C among the members without any act by A

#### Scenario: A replayed secret is refused without state

- **WHEN** a join completed against an invite and a second join presents the same secret
- **THEN** the second attempt is refused, and the cell's members and store are exactly as the first join left them

#### Scenario: A former member joins again

- **WHEN** C left the cell or was kicked from it, and a member invites C again and C joins
- **THEN** C reads the cell, its earlier records among what it reads, and a new record C writes reaches every member

#### Scenario: A wrong secret burns nothing

- **WHEN** a dialer presents a secret that was never minted while an invite is pending
- **THEN** the attempt is refused with no observable state, and a subsequent join with the pending invite's real secret succeeds

#### Scenario: Two identities of one node invite and join

- **WHEN** a hosted identity invites and a co-located identity joins with the invite, with no other node reachable
- **THEN** both list each other among the members, a record one places reads back on the other, and a second presentation of the same secret is refused

### Requirement: A cell reaches a member's other devices

A cell created or joined on one device of an identity SHALL become reachable from that identity's other devices without a second join: the identity's directory carries what its other devices need to open both stores — the announcement key pair beside their tickets, as the [private metadata store](../../data-layer/private-metadata-store/spec.md) lays them out — and a device that opens the cell from its directory registers itself: before it syncs the cell, and before every later sync, it SHALL check that the member's device list, as the [cell stores](../../data-layer/cell-store/spec.md) resolve it, names it with the author its identity writes with there, and when it does not SHALL write the next version — that list with itself added — into the membership store. An identity that is no member SHALL NOT reach the cell, a co-located one on a member's node included: it lists no such cell, and its calls on the cell fail with the unknown-cell error.

**Example:** Alice-leisure's directory once she has created "Family" on her phone a1, and what Alice's tablet a3, linked into Alice-leisure and hosting Alice-work too, does with it, Alice-work being no member of "Family"; `<alice-leisure>`: 64 lowercase hex chars of Alice-leisure's `PdnId`.

```
cells/eead8ef96aa1254969d63c12631b799c/1                      the cell's record at the founding, Alice-leisure's sequence 1
tickets/cell/eead8ef96aa1254969d63c12631b799c/membership      the membership store's write ticket
tickets/cell/eead8ef96aa1254969d63c12631b799c/records         the record store's write ticket
announcement-key                                              Alice-leisure's announcement key pair, minted with her

a3 opens both stores from these tickets and writes member/<alice-leisure>/devices/2 — a1 and a3 — into the membership store
Alice-work's directory holds no cells/ entry and no tickets/cell/ kind for Family, and an announcement-key of her own: list answers no such cell for Alice-work, and her read of Family fails with the unknown-cell error
```

#### Scenario: A linked device reaches the cell

- **WHEN** identity B joins a cell on its phone while B's laptop is linked into B
- **THEN** the laptop eventually lists the cell, reads its entries, and its own device is served by the other members

#### Scenario: A device a later version missed puts itself back

- **WHEN** a device D of identity B has written a version of B's device statement listing itself, and another device of B that has not seen it writes the next version without D
- **THEN** D's first sync after that version reaches it is preceded by a statement at the version after it, listing D beside every device the version that missed D lists, and the other members' devices admit D's entries again

#### Scenario: A co-located non-member identity does not reach the cell

- **WHEN** a node hosts identity B, a member, and identity D, a non-member
- **THEN** D lists no such cell and D's read of the cell fails with the unknown-cell error, while B reads it

### Requirement: The creator is the first owner; owners promote members and demote other owners

A created cell SHALL record its creating identity as the cell's first owner. An owner SHALL be able to promote any member to owner, and demoting an owner SHALL be available only to another owner. A promotion or a demotion by a member that is no owner, and a demotion of oneself, SHALL be refused with a typed error and change no state. A demoted owner remains a member. A member that joins again SHALL be a plain member, whatever role it held before, and its owner's acts SHALL be refused with a typed error until an owner promotes it anew.

**Example:** role calls in "Family", in this order, Alice being its one owner and Bob and Carol plain members; `Family` stands for its cell id.

| call | result |
|---|---|
| `act(Alice, Family, Promote(Bob))` | written: every member lists Alice and Bob as owners |
| `act(Carol, Family, Demote(Bob))` | a typed error, nothing written |
| `act(Alice, Family, Demote(Alice))` | a typed error, nothing written |
| `act(Bob, Family, Demote(Alice))` | written: Alice a plain member, still a member |
| `act(Bob, Family, Promote(Carol))` | written: Carol an owner |
| Carol kicks Bob and Alice invites him again, then `act(Bob, Family, Promote(Alice))` | a typed error: Bob is a plain member until an owner promotes him anew |

#### Scenario: The creator is listed as owner

- **WHEN** a hosted identity creates a cell
- **THEN** the cell's owners are exactly the creating identity

#### Scenario: An owner promotes a member

- **WHEN** owner A promotes member B and the promotion reaches member C's devices
- **THEN** C lists both A and B among the owners

#### Scenario: A plain member's promotion or demotion is refused

- **WHEN** member C, no owner, attempts to promote a member or to demote owner B
- **THEN** the act is refused with a typed error and every member still lists the owners unchanged

#### Scenario: An owner demotes another owner

- **WHEN** owner A demotes owner B and the demotion reaches the members' devices
- **THEN** B is listed among the members and not among the owners

#### Scenario: An owner does not demote itself

- **WHEN** owners A and B both own the cell and A attempts to demote itself
- **THEN** the attempt is refused with a typed error and every member still lists A among the owners

#### Scenario: A former owner joins again as a plain member

- **WHEN** owner B is kicked, a member invites B again and B joins, and B then attempts to promote a member
- **THEN** every member lists B as a plain member, and B's attempt is refused with a typed error

### Requirement: Only an owner kicks a member, and only another member; leaving is forgetting

Kicking a member — an owner or a plain member alike — SHALL be available only to an owner's device and only on another member: a kick by a member that is no owner, and a kick of oneself, SHALL be refused with a typed error and change no state — a member's own way out is leaving. A kicked event replicates like every cell entry; the remaining members' devices refuse the kicked member's devices from the next session, per the cell stores' admission rule. A member that leaves SHALL tombstone the cell's record in its directory at the sequence of its left event, as the [private metadata store](../../data-layer/private-metadata-store/spec.md) lays the records out, and forget both stores on its own devices, so the cell is no longer listed there, while the remaining members, a co-located member of the same cell among them, are unaffected and everything the member wrote — its records, its operations on other members' mergeable-documents — stays in the cell.

**Example:** kicks and a leave in "Wedding", in this order: Erin is an owner, Bob, Dave, Alice-leisure and Alice-work plain members, and Alice's tablet a3 hosts Alice-leisure and Alice-work; `Wedding` stands for its cell id.

| call | result |
|---|---|
| `act(Bob, Wedding, Kick(Alice-work))` | a typed error, nothing written |
| `act(Erin, Wedding, Kick(Erin))` | a typed error, nothing written |
| `act(Erin, Wedding, Kick(Dave))` | written: Dave's devices are refused from their next session with each member device the kicked event has reached |
| `act(Alice-work, Wedding, Leave)` on a3 | her left event written at her sequence 2 and `cells/f942dfc21acd0218d48f61f714ddfff3/2` tombstoned in her directory; both stores forgotten for Alice-work on a3, and on each of her other devices once her directory syncs there, while Alice-leisure's replicas on a3 go on; her records and operations stay in the cell |

#### Scenario: An owner kicks a member

- **WHEN** owner A kicks member C from a cell with members A, B and C, and the kick reaches B's devices
- **THEN** A and B still sync the cell, and C's next session is refused

#### Scenario: A plain member kicks nobody

- **WHEN** member C, no owner, attempts to kick member B
- **THEN** the attempt is refused with a typed error, B is still listed by every member, and B's devices are still served

#### Scenario: An owner kicks another owner

- **WHEN** owners A and B both own the cell and A kicks B
- **THEN** B's next session is refused, and B is listed by no remaining member

#### Scenario: An owner does not kick itself

- **WHEN** owner A attempts to kick itself
- **THEN** the attempt is refused with a typed error, and every member still lists A as a member and an owner

#### Scenario: A member leaves

- **WHEN** C leaves the cell from one of its devices
- **THEN** C's devices no longer list the cell, A and B still read each other's entries, and C's records and operations are still read by A and B

### Requirement: A claim and an immutable-document are placed once; a mergeable-document is edited by every member

The cells service SHALL place a record as one of three kinds — claim, mergeable-document or immutable-document — under the placing identity's name, and every member SHALL read it back. A claim SHALL be written as an immutable entry: the service offers no operation that changes a stored claim's payload, and a write addressed at an existing claim SHALL be refused with a typed error, the stored payload surviving. An immutable-document SHALL be placed once, like a claim: a write addressed at an existing one SHALL be refused with a typed error, whoever the caller is, the placing identity included. An edit of a mergeable-document SHALL be accepted from any member, each operation under the writer's own signature; an edit by an identity that is no member SHALL fail with the unknown-cell error. Reading a mergeable-document SHALL return its operations as they are held, each with its writer, and the service computes no document state from them. Reading SHALL be by cell id, and reading a cell the identity is no member of SHALL fail with the unknown-cell error.

**Example:** record calls in "Family", in this order: Alice-leisure is an owner, Bob and Carol plain members, and Alice-work, hosted on Alice's tablet a3 beside Alice-leisure, no member; Bob's note is a mergeable-document he placed earlier; `Family` stands for its cell id.

| call | result |
|---|---|
| `put_record(Bob, Family, Claim, …)` | a `RecordRef` with member Bob, kind `Claim` and a fresh id; every member reads Bob's bytes |
| `append_op(Bob, Family, that claim, …)` | a typed error: a claim is placed once |
| `append_op(Carol, Family, Bob's note, …)` | written: `read_ops` lists it with Carol as its writer |
| `append_op(Alice-work, Family, Bob's note, …)` | the unknown-cell error |

#### Scenario: A claim round-trips unchanged

- **WHEN** member A writes a claim into a cell and member B reads it
- **THEN** B reads the bytes A wrote

#### Scenario: A claim cannot be overwritten

- **WHEN** a write is addressed at an existing claim
- **THEN** it is refused with a typed error and every member still reads the original bytes

#### Scenario: An immutable-document is not updated, by its member either

- **WHEN** member B places an immutable-document and B's device writes to it again
- **THEN** the write is refused with a typed error and every member still reads the bytes B placed first

#### Scenario: Any member edits another member's mergeable-document

- **WHEN** member B places a mergeable-document and member C, no owner, appends an operation to it
- **THEN** B's devices hold C's operation, authored by C

#### Scenario: A non-member edits nothing

- **WHEN** a hosted identity that is no member of the cell appends an operation to its mergeable-document
- **THEN** the edit fails with the unknown-cell error and no member's device holds such an operation

### Requirement: Hosted cells survive a restart

A directory-configured runtime SHALL host again, after a restart, every cell its hosted identities are members of, from durable state alone — both stores keep replicating and its members' devices are served — while a memory runtime's cells end with the process. The hosted cells SHALL be re-derived from each hosted identity's directory, as its connections are: every cell whose record in the [private metadata store](../../data-layer/private-metadata-store/spec.md) is live, both stores opened from the cell's published tickets in the identity's own replica store, and a contact that names this node's own address reached inside the process. The identity's hosting record SHALL name no cell.

**Example:** Alice's tablet a3 runs on a storage directory and hosts Alice-leisure and Alice-work, both members of "Wedding"; Alice-work left a second cell, `684aad236ce530cd7b5dedb6ab6b755a`, before a3 stops.

| step | a3 |
|---|---|
| a3 stops | on disk, the entry at the highest sequence under `cells/f942dfc21acd0218d48f61f714ddfff3/` is non-empty in Alice-leisure's directory and in Alice-work's, and the one under `cells/684aad236ce530cd7b5dedb6ab6b755a/` is a tombstone in Alice-work's |
| Erin places a claim from her phone e1 meanwhile | — |
| a3 starts on the same directory | opens Wedding's two stores for Alice-leisure and for Alice-work, each from the tickets in the identity's own directory, and nothing for `684aad236ce530cd7b5dedb6ab6b755a`; neither hosting record names a cell |
| a3's first sessions | Erin's claim arrives, and Alice-leisure's and Alice-work's replicas converge inside the process |

#### Scenario: A cell is hosted again after a restart

- **WHEN** a runtime on a storage directory hosts a member of a cell, stops, and starts again on the same directory, while another member wrote an entry in between
- **THEN** the identity lists the cell, and the entry written meanwhile arrives

#### Scenario: Two members hosted on one node come back each with its own copy

- **WHEN** a runtime on a storage directory hosts two members of one cell, restarts on the same directory, and one of them places a record, with no other node reachable
- **THEN** both list the cell and the other reads the record

#### Scenario: A cell left before the restart stays left

- **WHEN** a runtime on a storage directory hosts a member of a cell, the member leaves the cell, and the runtime stops and starts again on the same directory
- **THEN** the identity lists no such cell, and neither store is opened or served
