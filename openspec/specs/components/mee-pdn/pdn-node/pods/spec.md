# Pods

## Purpose

The pods service of the runtime: creating a [pod](../../../../architecture/language/pod.md) for a hosted identity, inviting and joining, ownership, reaching a member's other devices, removing and leaving, writing records — claims, mergeable-documents and immutable-documents — into the pod, and recovering hosted pods across a restart. The two stores underneath — the membership store and the record store — are the data layer's [pod stores](../../data-layer/pod-store/spec.md); this spec covers the runtime surface and the ceremonies. A pod has two roles, owner and member — the creator the first owner. Who may do what by role is in the tables below: on the pod itself, then on each kind of record, where "own" is a record under one's own name — a record is created under one's own name only.

**Pod**

|                                | Pod owner  | Pod member  |
| ------------------------------ | ---------- | ----------- |
| Invite member to a pod         | yes        | yes         |
| Leave pod                      | yes        | yes         |
| Delete pod for all members     | no         | no          |
| Promote member to owner        | yes        | no          |
| Demote another owner to member | yes        | no          |
| Demote oneself to member       | no         | no          |
| Remove member from pod         | yes        | no          |
| Remove another owner from pod  | yes        | no          |
| Remove oneself from pod        | no         | no          |

**Immutable-document** — attachments, for example a PDF file.

|                                                                     | Pod owner  | Pod member  |
| ------------------------------------------------------------------- | ---------- | ----------- |
| Read own immutable-document                                         | yes        | yes         |
| Read another member's immutable-document                            | yes        | yes         |
| Create own immutable-document                                       | yes        | yes         |
| Create an immutable-document as if it is authored by another member | no         | no          |
| Update own immutable-document                                       | no         | no          |
| Update another member's immutable-document                          | no         | no          |

**Mergeable-document** — for example a note.

|                                                                           | Pod owner  | Pod member  |
| ------------------------------------------------------------------------- | ---------- | ----------- |
| Read own mergeable-document                                               | yes        | yes         |
| Read another member's mergeable-document                                  | yes        | yes         |
| Create own mergeable-document                                             | yes        | yes         |
| Create a mergeable-document as if it is authored by another member        | no         | no          |
| Edit own mergeable-document                                               | yes        | yes         |
| Edit another member's mergeable-document (preserving per-edit authorship) | yes        | yes         |

**Claim**

|                                                    | Pod owner  | Pod member  |
| -------------------------------------------------- | ---------- | ----------- |
| Read own claim                                     | yes        | yes         |
| Read another member's claim                        | yes        | yes         |
| Issue own claim                                    | yes        | yes         |
| Issue a claim as if it is issued by another member | no         | no          |
| Update own claim                                   | no         | no          |
| Update another member's claim                      | no         | no          |

The service's surface — the operations the requirements below constrain:

```rust
/// The pods service of a runtime. `identity` is the hosted identity acting; a call on a pod the identity is no member of
/// fails with the unknown-pod error, and a refusal by role is a typed error that writes nothing.
trait PodsService {
    /// Derives the pod id, creates both stores, writes the signed created event; the identity is the first owner.
    async fn create(&self, identity: PdnId) -> Result<PodId>;
    /// The pods the identity is a member of.
    async fn list(&self, identity: PdnId) -> Result<Vec<PodInfo>>;
    /// The current members, each with its role.
    async fn members(&self, identity: PdnId, pod: PodId) -> Result<Vec<Member>>;

    /// Mints a one-time invite: the inviting device's address, the secret, the pod id. Any member. Writes nothing to the pod:
    /// the invite act is written by the inviting device once a newcomer presents the secret.
    async fn invite(&self, identity: PdnId, pod: PodId, lifetime: Option<Duration>) -> Result<PodInvite>;
    /// Joins through the invite's dialogue and returns once both stores have caught up and its membership view lists the identity as a member; the identity joins as a plain member.
    async fn join(&self, identity: PdnId, invite: PodInvite) -> Result<PodId>;
    /// Writes a membership act after checking the identity's role; the service picks both sequences.
    /// `Remove` and `Demote` name another member; `Leave` also forgets the record store on the identity's devices and keeps the membership store as the pod's tombstone.
    async fn act(&self, identity: PdnId, pod: PodId, act: PodAct) -> Result<()>;

    /// Places a record under the identity's own name at a fresh id: a claim's or an immutable-document's one entry,
    /// or a mergeable-document's first operation.
    async fn put_record(&self, identity: PdnId, pod: PodId, kind: RecordKind, payload: &[u8]) -> Result<RecordRef>;
    /// Appends an operation to an existing mergeable-document, whoever's name it sits under. Any member.
    async fn append_op(&self, identity: PdnId, pod: PodId, record: RecordRef, op: &[u8]) -> Result<()>;
    /// A claim's or an immutable-document's payload; `None` for a record the pod does not hold.
    async fn read(&self, identity: PdnId, pod: PodId, record: RecordRef) -> Result<Option<Vec<u8>>>;
    /// A mergeable-document's operations, each with its writer.
    async fn read_ops(&self, identity: PdnId, pod: PodId, record: RecordRef) -> Result<Vec<Operation>>;
    /// Every record the pod holds.
    async fn list_records(&self, identity: PdnId, pod: PodId) -> Result<Vec<RecordRef>>;
    /// Entries outside the key layout, each with its author.
    async fn list_unknown(&self, identity: PdnId, pod: PodId) -> Result<Vec<UnknownEntry>>;
}

/// The create act is written by `create`, the invite act by the inviting device inside the join dialogue, device statements by the device sweep — never through `act`.
enum PodAct { Promote(PdnId), Demote(PdnId), Remove(PdnId), Leave }
struct RecordRef { member: PdnId, kind: RecordKind, id: RecordId }
enum RecordKind { Claim, MergeableDocument, ImmutableDocument }
```

## Requirements

### Requirement: The pods service creates a pod for a hosted identity

The pods service SHALL create a pod for a hosted identity: it draws a random nonce, derives the pod id from the identity's `PdnId`, its announcement key and the nonce, creates the membership store and the record store, writes the created event signed by the announcement key — the creating identity the first member — and answers the pod id, the one address of the pod. Creating a pod for an identity the runtime does not host SHALL be refused with an unknown-identity error and no state created.

**Example:** `create` calls on Alice's phone a1, which hosts Alice and not Erin; the nonces a1 draws are 16 bytes of `5a`, then 16 bytes of `a5`.

| call | result |
|---|---|
| `create(Alice)` | `ad58a3faa04cdc5576c8dc5823a347c6`; `members` answers Alice alone, an owner |
| `create(Alice)` again | `920657b318e1bb314e4cb2cf2174451a`: another nonce, another id; `list` answers both pods |
| `create(Erin)` | the unknown-identity error, and no store exists for Erin |

#### Scenario: A created pod is listed with its creator as member

- **WHEN** a hosted identity creates a pod
- **THEN** the identity lists a pod with a fresh pod id, whose members are exactly that identity

#### Scenario: Two pods of one identity are two ids

- **WHEN** a hosted identity creates two pods
- **THEN** both are listed, with different pod ids, and each is addressed by its own id

#### Scenario: Creating for an unhosted identity is refused

- **WHEN** a pod is requested for an identity the runtime neither created nor linked
- **THEN** the operation fails with the unknown-identity error and no store exists for it

### Requirement: Any member invites; a newcomer joins after a one-time secret is verified and burned

Any member's device SHALL mint a pod invite: a fresh one-time, short-lived secret pending on the inviting runtime, and a self-contained payload carrying a format version, the inviting device's node address, the secret and the pod id — no ticket and no identity proof; minting SHALL write nothing to either store. A newcomer SHALL join by presenting the secret in a dialogue with the inviter, reporting beside it the highest sequence of its own chain its replica holds, a tombstone's included; the inviter SHALL verify and burn the secret atomically before any state change, then name the sequence the newcomer's joined event takes — past the newcomer's chain as the inviter's replica holds it and past the run the newcomer reports, so a departure that has reached the newcomer's devices and not yet the inviter's is not left standing — and the version and device list its device statement extends — the identity's own, when the pod has listed it before — write the invite act, which records the newcomer as a member — a plain member, no owner — and hand it the write tickets of both stores. The dialogue SHALL carry, beside the newcomer's join statement, signed over that sequence by the joining steps of the [pod stores](../../data-layer/pod-store/spec.md) spec, its first device statement, which the inviter writes beside the invite act into the replica of the identity the secret was minted for, so the inviter serves the newcomer's first session. The inviter SHALL write the invite act before it hands over the tickets, and the newcomer's device SHALL record both tickets and the pod's private metadata store (PMS) entry before it catches up, so the armer's sweep finishes a catch-up that a dropped connection, a dropped `join` future or a restart interrupts. A secret presented by an identity the pod already lists as a member SHALL write no joined event: the inviter hands over both tickets again, and writes the device statement the dialogue carries when the member's device list does not name that device. Between two identities of one node the dialogue SHALL run inside the process ([in-process sessions](../../data-layer/in-process-sessions/spec.md)), the secret verified and burned as between two nodes. A refused presentation — wrong, expired or already burned — SHALL leave no observable state and SHALL NOT burn a live pending invite, and refusals SHALL be uniform. After joining, the newcomer's device holds the store, catches up on its existing content, and every member's devices list the newcomer.

**Example:** Bob's phone b1 mints an invite to "Family" as Bob — a format version, b1's node address, the secret and `ad58a3faa04cdc5576c8dc5823a347c6`, no ticket — and Bob hands it to Carol; three presentations follow.

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
- **THEN** the second attempt is refused, and the pod's members and store are exactly as the first join left them

#### Scenario: A former member joins again

- **WHEN** C left the pod or was removed from it, and a member invites C again and C joins
- **THEN** C reads the pod, its earlier records among what it reads, and a new record C writes reaches every member

#### Scenario: A former member invited by a device that has not seen its departure joins

- **WHEN** C leaves the pod, and a member's device whose replica does not yet hold C's left event invites C again
- **THEN** the inviter names a sequence past C's left event and writes C's joined event there, and C's join returns caught up with C a plain member

#### Scenario: A catch-up the join lost is finished by the armer

- **WHEN** a newcomer's device has received both tickets in the join dialogue, and its connection drops during the catch-up, or its caller drops the `join` future then, or its runtime restarts then
- **THEN** the device holds both tickets and the pod's PMS entry, and the armer's next sweep opens the pod and catches it up with no second invite

#### Scenario: A member whose join lost the reply joins through a second invite

- **WHEN** the connection drops after the inviter wrote newcomer C's joined event and before its reply reached C, and C then presents a second invite
- **THEN** the second dialogue writes no joined event and hands C both tickets, C catches up, and every member device lists C by the one joined event

#### Scenario: A wrong secret burns nothing

- **WHEN** a dialer presents a secret that was never minted while an invite is pending
- **THEN** the attempt is refused with no observable state, and a subsequent join with the pending invite's real secret succeeds

#### Scenario: Two identities of one node invite and join

- **WHEN** a hosted identity invites and a co-located identity joins with the invite, with no other node reachable
- **THEN** both list each other among the members, a record one places reads back on the other, and a second presentation of the same secret is refused

### Requirement: A pod reaches a member's other devices

A pod created or joined on one device of an identity SHALL become reachable from that identity's other devices without a second join: the identity's PMS carries what its other devices need to open both stores — the announcement key pair beside their tickets, as the [private metadata store](../../data-layer/private-metadata-store/spec.md) lays them out — and a device that opens the pod from its PMS registers itself: once the membership view of its replica lists the member, and at every later change to that store and every run of the pod stores' pass, it SHALL check that the member's device list, as the [pod stores](../../data-layer/pod-store/spec.md) resolve it, names it with the author its identity writes with there, and when it does not SHALL write the next version — that list with itself added — into the membership store. An identity that is no member SHALL NOT reach the pod, a co-located one on a member's node included: it lists no such pod, and its calls on the pod fail with the unknown-pod error.

**Example:** Alice-leisure's PMS once she has created "Family" on her phone a1, and what Alice's tablet a3, linked into Alice-leisure and hosting Alice-work too, does with it, Alice-work being no member of "Family"; `<alice-leisure>`: 64 lowercase hex chars of Alice-leisure's `PdnId`.

```
pods/ad58a3faa04cdc5576c8dc5823a347c6/1                       the pod's record at the created event, Alice-leisure's sequence 1
tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/membership       the membership store's write ticket
tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/records          the record store's write ticket
announcement-key                                              Alice-leisure's announcement key pair, minted with her

a3 opens both stores from these tickets and writes member/<alice-leisure>/devices/2 — a1 and a3 — into the membership store
Alice-work's PMS holds no pods/ entry and no tickets/pod/ kind for Family, and an announcement-key of her own: list answers no such pod for Alice-work, and her read of Family fails with the unknown-pod error
```

#### Scenario: A linked device reaches the pod

- **WHEN** identity B joins a pod on its phone while B's laptop is linked into B
- **THEN** the laptop eventually lists the pod, reads its entries, and its own device is served by the other members

#### Scenario: A device a later version missed stays listed

- **WHEN** a device D of identity B has written a version of B's device statement listing itself, and another device of B that has not seen it writes the next version without D
- **THEN** D's first sync after that version reaches it is preceded by no statement of D's, and the other members' devices keep admitting D's entries throughout

#### Scenario: A device statement a restart cut off is written after the restart

- **WHEN** a device linked into B holds two of B's pods, and its runtime restarts after its device statement landed in one of them and before it landed in the other
- **THEN** after the restart the device writes its statement into the other pod, and the other members' devices read what it placed there

#### Scenario: A co-located non-member identity does not reach the pod

- **WHEN** a node hosts identity B, a member, and identity D, a non-member
- **THEN** D lists no such pod and D's read of the pod fails with the unknown-pod error, while B reads it

### Requirement: The creator is the first owner; owners promote members and demote other owners

A created pod SHALL record its creating identity as the pod's first owner. An owner SHALL be able to promote any member to owner, and demoting an owner SHALL be available only to another owner. A promotion or a demotion by a member that is no owner, and a demotion of oneself, SHALL be refused with a typed error and change no state. A demoted owner remains a member. A member that joins again SHALL be a plain member, whatever role it held before, and its owner's acts SHALL be refused with a typed error until an owner promotes it anew.

**Example:** role calls in "Family", in this order, Alice being its one owner and Bob and Carol plain members; `Family` stands for its pod id.

| call | result |
|---|---|
| `act(Alice, Family, Promote(Bob))` | written: every member lists Alice and Bob as owners |
| `act(Carol, Family, Demote(Bob))` | a typed error, nothing written |
| `act(Alice, Family, Demote(Alice))` | a typed error, nothing written |
| `act(Bob, Family, Demote(Alice))` | written: Alice a plain member, still a member |
| `act(Bob, Family, Promote(Carol))` | written: Carol an owner |
| Carol removes Bob and Alice invites him again, then `act(Bob, Family, Promote(Alice))` | a typed error: Bob is a plain member until an owner promotes him anew |

#### Scenario: The creator is listed as owner

- **WHEN** a hosted identity creates a pod
- **THEN** the pod's owners are exactly the creating identity

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

- **WHEN** owners A and B both own the pod and A attempts to demote itself
- **THEN** the attempt is refused with a typed error and every member still lists A among the owners

#### Scenario: A former owner joins again as a plain member

- **WHEN** owner B is removed, a member invites B again and B joins, and B then attempts to promote a member
- **THEN** every member lists B as a plain member, and B's attempt is refused with a typed error

### Requirement: Only an owner removes a member, and only another member; leaving is forgetting

Removing a member — an owner or a plain member alike — SHALL be available only to an owner's device and only on another member: a removal by a member that is no owner, and a removal of oneself, SHALL be refused with a typed error and change no state — a member's own way out is leaving. A leave by the one owner of a pod that has other members SHALL be refused with a typed error and change no state until another member is an owner; the one member of a pod leaves as any member does. The refusal runs on the writing device, so two leaves the last two owners write while disconnected from each other both stand, and the pod then has no owner. A removed event replicates like every pod entry; the remaining members' devices refuse the removed member's devices the record store from the next session and serve them the membership store up to the removal, per the pod stores' rules; a device of the removed member that learns of the removal SHALL tombstone the pod's record in its PMS at the removed event's sequence, forget the record store and keep the membership store as the pod's tombstone. A member that leaves SHALL tombstone the pod's record in its PMS at the sequence of its left event, as the [private metadata store](../../data-layer/private-metadata-store/spec.md) lays the records out, and forget the record store on its own devices, keeping the membership store as the pod's tombstone, so the pod is no longer listed there, while the remaining members, a co-located member of the same pod among them, are unaffected and everything the member wrote — its records, its operations on other members' mergeable-documents — stays in the pod. Before it writes its left event, the leaving device SHALL reconcile both stores with devices of the pod's other members and wait up to 10 seconds for a session with one of them, begun after the flush started, to go through on each store, since nothing outside the departure's past leaves the device once it departs; a leave that reaches no member's device in that time SHALL proceed all the same, and what no member's device held by then is lost.

**Example:** removals and a leave in "Wedding", in this order: Erin is an owner, Bob, Dave, Alice-leisure and Alice-work plain members, and Alice's tablet a3 hosts Alice-leisure and Alice-work; `Wedding` stands for its pod id.

| call | result |
|---|---|
| `act(Bob, Wedding, Remove(Alice-work))` | a typed error, nothing written |
| `act(Erin, Wedding, Remove(Erin))` | a typed error, nothing written |
| `act(Erin, Wedding, Remove(Dave))` | written: Dave's devices are refused the record store from their next session with each member device the removed event has reached, and learn of the removal from the membership store |
| `act(Erin, Wedding, Leave)` | a typed error, nothing written: Erin is the one owner, and the pod has other members |
| `act(Alice-work, Wedding, Leave)` on a3 | her left event written at her sequence 2 and `pods/f942dfc21acd0218d48f61f714ddfff3/2` tombstoned in her PMS; the record store forgotten for Alice-work on a3, and on each of her other devices once her PMS syncs there, the membership store kept as the pod's tombstone, while Alice-leisure's replicas on a3 go on; her records and operations stay in the pod |

#### Scenario: An owner removes a member

- **WHEN** owner A removes member C from a pod with members A, B and C, and the removal reaches B's devices
- **THEN** A and B still sync the pod, and C's next session is refused

#### Scenario: A member's removals follow its role through promotion, demotion and promotion again

- **WHEN** owner A promotes B, B removes C, A demotes B, B attempts to remove D, A promotes B again, and B removes D
- **THEN** B's first and last removals are written, the attempt between them is refused with a typed error, and every remaining member lists A and B as owners and neither C nor D as a member

#### Scenario: A plain member removes nobody

- **WHEN** member C, no owner, attempts to remove member B
- **THEN** the attempt is refused with a typed error, B is still listed by every member, and B's devices are still served

#### Scenario: An owner removes another owner

- **WHEN** owners A and B both own the pod and A removes B
- **THEN** B's next session is refused, and B is listed by no remaining member

#### Scenario: An owner does not remove itself

- **WHEN** owner A attempts to remove itself
- **THEN** the attempt is refused with a typed error, and every member still lists A as a member and an owner

#### Scenario: The last owner does not leave a pod with other members

- **WHEN** A, the one owner of a pod whose members are A, B and C, attempts to leave, then promotes B and attempts to leave again
- **THEN** the first attempt is refused with a typed error and every member still lists A as a member and the one owner, and the second is written, leaving B the one owner

#### Scenario: The last two owners leaving at once leave the pod without an owner

- **WHEN** A and C, a pod's only owners, leave while disconnected from each other, and plain member B's device then reconciles with both
- **THEN** B's device lists no owner, B reads and appends to the pod's mergeable-documents, and B's removal of a member and promotion of itself are refused with a typed error

#### Scenario: A member leaves

- **WHEN** C leaves the pod from one of its devices
- **THEN** C's devices no longer list the pod, A and B still read each other's entries, and C's records and operations are still read by A and B

#### Scenario: A device linked after the leave holds the tombstone alone

- **WHEN** member C leaves the pod on its one device, and another device is linked into C afterwards
- **THEN** the new device holds the pod's membership store, the left event taken from C's first device among its entries, holds no record store, and lists no such pod

#### Scenario: What a member wrote just before its leave reaches the pod

- **WHEN** member C places a claim, appends an operation to A's mergeable-document and leaves at once, a device of A being reachable
- **THEN** every remaining member reads C's claim and C's operation

#### Scenario: A promotion just before the one owner's leave reaches the pod

- **WHEN** A, the one owner, promotes B and leaves at once, B's and C's devices being reachable
- **THEN** B's and C's devices list B as the one owner and A as no member

### Requirement: A claim and an immutable-document are placed once; a mergeable-document is edited by every member

The pods service SHALL place a record as one of three kinds — claim, mergeable-document or immutable-document — under the placing identity's name, and every member SHALL read it back. A claim SHALL be written as an immutable entry: the service offers no operation that changes a stored claim's payload, and a write addressed at an existing claim SHALL be refused with a typed error, the stored payload surviving. An immutable-document SHALL be placed once, like a claim: a write addressed at an existing one SHALL be refused with a typed error, whoever the caller is, the placing identity included. An edit of a mergeable-document SHALL be accepted from any member, each operation under the writer's own signature; an edit by an identity that is no member SHALL fail with the unknown-pod error. Reading a mergeable-document SHALL return its operations as they are held, each with its writer, and the service computes no document state from them. Reading SHALL be by pod id, and reading a pod the identity is no member of SHALL fail with the unknown-pod error.

**Example:** record calls in "Family", in this order: Alice-leisure is an owner, Bob and Carol plain members, and Alice-work, hosted on Alice's tablet a3 beside Alice-leisure, no member; Bob's note is a mergeable-document he placed earlier; `Family` stands for its pod id.

| call | result |
|---|---|
| `put_record(Bob, Family, Claim, …)` | a `RecordRef` with member Bob, kind `Claim` and a fresh id; every member reads Bob's bytes |
| `append_op(Bob, Family, that claim, …)` | a typed error: a claim is placed once |
| `append_op(Carol, Family, Bob's note, …)` | written: `read_ops` lists it with Carol as its writer |
| `append_op(Alice-work, Family, Bob's note, …)` | the unknown-pod error |

#### Scenario: A claim round-trips unchanged

- **WHEN** member A writes a claim into a pod and member B reads it
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

- **WHEN** a hosted identity that is no member of the pod appends an operation to its mergeable-document
- **THEN** the edit fails with the unknown-pod error and no member's device holds such an operation

### Requirement: Hosted pods survive a restart

A directory-configured runtime SHALL host again, after a restart, every pod its hosted identities are members of, from durable state alone — both stores keep replicating and its members' devices are served — while a memory runtime's pods end with the process. The hosted pods SHALL be re-derived from each hosted identity's PMS, as its connections are: every pod whose record in the [private metadata store](../../data-layer/private-metadata-store/spec.md) is live, both stores opened from the pod's published tickets in the identity's own replica store, and a contact that names this node's own address reached inside the process. The identity's hosting record SHALL name no pod.

**Example:** Alice's tablet a3 runs on a storage directory and hosts Alice-leisure and Alice-work, both members of "Wedding"; Alice-work left a second pod, `684aad236ce530cd7b5dedb6ab6b755a`, before a3 stops.

| step | a3 |
|---|---|
| a3 stops | on disk, the entry at the highest sequence under `pods/f942dfc21acd0218d48f61f714ddfff3/` is non-empty in Alice-leisure's PMS and in Alice-work's, and the one under `pods/684aad236ce530cd7b5dedb6ab6b755a/` is a tombstone in Alice-work's |
| Erin places a claim from her phone e1 meanwhile | — |
| a3 starts on the same directory | opens Wedding's two stores for Alice-leisure and for Alice-work, each from the tickets in the identity's own PMS, and for `684aad236ce530cd7b5dedb6ab6b755a` Alice-work's tombstone alone, no record store; neither hosting record names a pod |
| a3's first sessions | Erin's claim arrives, and Alice-leisure's and Alice-work's replicas converge inside the process |

#### Scenario: A pod is hosted again after a restart

- **WHEN** a runtime on a storage directory hosts a member of a pod, stops, and starts again on the same directory, while another member wrote an entry in between
- **THEN** the identity lists the pod, and the entry written meanwhile arrives

#### Scenario: Two members hosted on one node come back each with its own copy

- **WHEN** a runtime on a storage directory hosts two members of one pod, restarts on the same directory, and one of them places a record, with no other node reachable
- **THEN** both list the pod and the other reads the record

#### Scenario: A pod left before the restart stays left

- **WHEN** a runtime on a storage directory hosts a member of a pod, the member leaves the pod, and the runtime stops and starts again on the same directory
- **THEN** the identity lists no such pod, the record store is neither opened nor served, and the membership store stays as the pod's tombstone
