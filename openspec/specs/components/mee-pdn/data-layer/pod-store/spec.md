# Pod stores

## Purpose

A [pod](../../../../architecture/language/pod.md) is a space shared by 0..n members — identities — identified by a pod id that carries no key material and is derived from its creator's announcement key and a random nonce. It lives in two dedicated pdn-store namespaces, each held whole, as a replica of its own, by every member identity on every device that hosts it: the **membership store**, the pod's authority — who is a member, with what role, on which devices — and the **record store**, the records that authority governs. No egress filter runs inside a pod, member devices form each store's swarm, any member device catches up from any other, and a session reconciles the membership store to convergence before the record store. What keeps a pod honest is who is served and what counts: a session names the member whose replica it addresses and the member its caller acts as, and is served to member devices only; either store holds whatever such a session carries; and a record-store entry reads by its author — a claim or an immutable-document from the devices of the member under whose name it sits, a mergeable-document's operation from any member's devices — judged on every member device against the writer's membership state at the membership sequence the entry names, so that a forged entry counts on no honest device, while every member device holds and relays it. What a member's own devices write as that member — records under its name and acts in any member's chain — is taken on the member's word: an act or a record naming a point the member has since lost, an entry replacing one the member's own author wrote at the same key, two events of the member's at one point, and two entries of one of its records from two of its devices or under two membership sequences are held as they come, a read of such a record returning the one with the newest timestamp, and nothing below specifies or tests what the fold and the record view do with them. The runtime's pods service ([pdn-node pods](../../pdn-node/pods/spec.md)) creates and joins the stores; this spec covers the stores themselves.

The membership store is two shapes: what a device writes — an act — and what the fold computes for a member from everything written about it — its chain of events. An act is one entry; its key names the subject, the position in the subject's chain (`subject_seq`), the kind, the actor — the identity whose device writes it — and the actor's own sequence at the time of acting (`actor_seq`), and its author counts only among the actor's devices.

```rust
/// One entry a device writes into the membership store.
enum MembershipAct {
    /// The creator's first act: itself a member and an owner. Self-authored; subject = actor; subject_seq = 1; the root.
    /// Derives the pod id and is checked against it by the steps below.
    Create  { nonce: [u8; 16], announcement_key: PublicKey, signature: Signature },
    /// Written by the inviting device once the newcomer's one-time secret is verified and burned, never when the invite is minted.
    /// Any member; subject ≠ actor; `announcement_key` and `subject_signature` are the newcomer's join statement, made and
    /// counted by the joining steps below. Held as `Joined`.
    Invite  { subject: PdnId, subject_seq: Seq, actor_seq: Seq, announcement_key: PublicKey, subject_signature: Signature },
    /// The member itself; subject = actor.
    Leave   { subject_seq: Seq, actor_seq: Seq },
    /// An owner; subject ≠ actor.
    Remove  { subject: PdnId, subject_seq: Seq, actor_seq: Seq },
    /// An owner.
    Promote { subject: PdnId, subject_seq: Seq, actor_seq: Seq },
    /// An owner; subject ≠ actor.
    Demote  { subject: PdnId, subject_seq: Seq, actor_seq: Seq },
    /// The member's devices, one key per version; counted by the embedded signature under the member's announcement key, whoever writes it.
    /// `signature` by the announcement key over "pdn/pod-devices/v1" ‖ version ‖ devices.
    AnnounceDevices { version: u64, devices: Vec<MemberDevice>, signature: Signature },
}

/// A device of the member: its node id, which sessions are classified and contacts dialed by, and the author the member
/// writes with there — one author per hosted identity on a device (ADR-0013), so two members on one node share the node id only.
struct MemberDevice { node: NodeId, author: AuthorId }

/// A member's chain: `member/<pdnid>/<seq>/<kind>/<by>/<by_seq>`, walked in `seq` order. `by` is the actor the key names, `by_seq`
/// the actor's own sequence then; the entry's author counts only among `by`'s devices.
enum MembershipEvent {
    Created  { seq: Seq, nonce: [u8; 16], announcement_key: PublicKey },       // by the member itself; the creator's seq 1 only
    Joined   { seq: Seq, by: PdnId, by_seq: Seq, announcement_key: PublicKey }, // by any member other than the member
    Left     { seq: Seq, by_seq: Seq },                                         // by the member itself
    Removed   { seq: Seq, by: PdnId, by_seq: Seq },                              // by an owner other than the member
    Promoted { seq: Seq, by: PdnId, by_seq: Seq },                              // by an owner
    Demoted  { seq: Seq, by: PdnId, by_seq: Seq },                              // by an owner other than the member
}

/// Folding a chain up to a sequence, as far as the first sequence holding no entry: Created makes a member and an owner, Joined a plain
/// member, Promoted an owner, Demoted a plain member, Left and Removed no member; at each sequence only the events whose transition the
/// state allows compete, the highest-ranking taking effect, and the rest count for nothing (Promoted of no member, Joined of a member).
struct MemberState { member: bool, owner: bool, announcement_key: Option<PublicKey>, devices: Vec<MemberDevice> }

/// The fold's check of one event, over everything the device holds:
///   Created          → seq == 1 and the receiving steps below pass
///   Joined           → by != subject, state(by, by_seq).member, and the joining steps below pass
///   Left             → by == subject
///   Promoted         → state(by, by_seq).owner
///   Removed | Demoted → by != subject and state(by, by_seq).owner
/// and for every kind: the author among by's devices, and by's chain held up to by_seq, every sequence of it holding an entry — else the
/// event counts once it is; an event whose transition the state before its sequence does not allow counts for nothing without
/// waiting on its actor, and events left waiting on each other's outcome in a loop count for nothing.
```

The `PdnId`, the pod id and the created event, `‖` being byte concatenation of fixed-size fields, numbers as big-endian bytes:

```text
Creating an identity, on its first device:
1. announcement key pair = a fresh Ed25519 key pair
2. pdn_id     = BLAKE3 derive_key(context "pdn/pdn-id/v1", announcement_pubkey[32]), all 32 bytes

Creating a pod, on the creator's device:
1. nonce      = 16 random bytes
2. pod_id     = BLAKE3 derive_key(context "pdn/pod-id/v1",
                                  pdn_id[32] ‖ announcement_pubkey[32] ‖ nonce[16]), first 16 bytes
                text form: 32 lowercase hex characters
3. signature  = Ed25519 sign(announcement_secret,
                             "pdn/pod-creation/v1" ‖ pdn_id ‖ announcement_pubkey ‖ nonce)
4. write the created event at member/<pdn_id>/1/created/<pdn_id>/0:
   { nonce, announcement_pubkey, signature }   — pdn_id is the key's <pdnid>; pod_id is not stored
5. pod_id goes to the identity's directory, the invite, links in notes

Counting a created event, on every member device, once its payload has arrived (a fresh device's first session included):
1. recompute pod_id from the event's pdn_id, announcement_pubkey, nonce → must equal the pod id the device holds
2. recompute pdn_id from announcement_pubkey → must equal the key's <pdnid>
3. verify signature under announcement_pubkey over "pdn/pod-creation/v1" ‖ pdn_id ‖ announcement_pubkey ‖ nonce
4. any check fails → the event counts for nothing, whatever order it arrived in
```

The join statement:

```text
Joining, in the join dialogue:
1. the inviting device, once it has burned the secret, names subject_seq: the first sequence past the newcomer's chain, as the inviting device holds it or as the newcomer reports its own, whichever runs further
2. subject_signature = Ed25519 sign(announcement_secret, on the newcomer's device,
                                    "pdn/pod-join/v1" ‖ pdn_id ‖ announcement_pubkey ‖ pod_id[16] ‖ subject_seq[8])
3. the inviting device writes the invite act at member/<pdn_id>/<subject_seq>/joined/<actor>/<actor_seq>:
   { announcement_pubkey, subject_signature }   — pdn_id and subject_seq are the key's; pod_id is not stored

Counting a joined event, on every member device, once its payload has arrived:
1. recompute pdn_id from announcement_pubkey → must equal the key's <pdnid>
2. verify subject_signature under announcement_pubkey over "pdn/pod-join/v1" ‖ pdn_id ‖ announcement_pubkey ‖ pod_id ‖ subject_seq
3. either check fails → the event counts for nothing, whatever order it arrived in
```

A device-list statement:

```text
Writing one, on a device of the member:
1. signature  = Ed25519 sign(announcement_secret, "pdn/pod-devices/v1" ‖ version[8] ‖ (node_id[32] ‖ author[32])…)
2. write it at member/<pdn_id>/devices/<version>: { devices, signature }   — version is the key's

Counting one, on every member device, once its payload has arrived:
1. the announcement key: the one a held created or joined event in the member's chain carries that derives the member's pdn_id
   → none held yet: the statement counts once one is
2. verify signature under that key over "pdn/pod-devices/v1" ‖ version ‖ devices, version being the key's
3. the check fails → the statement counts for nothing, whatever order it arrived in
```

## Requirements

### Requirement: A pod is two dedicated stores, held per member identity

A pod SHALL be served by exactly two pdn-store namespaces — its membership store and its record store — separate from every data store, every directory, every connection metadata store and every other pod's stores. Two pods SHALL NOT share a store, whatever their member sets. Both stores SHALL be addressed through the pod id, and no domain namespace id is allocated for either. Every member identity SHALL hold a replica of each store of its own, created or imported for that identity ([identity-scoped replicas](../identity-scoped-replicas/spec.md)): two identities of one node that are both members SHALL each hold both stores, the two copies converging inside the process ([in-process sessions](../in-process-sessions/spec.md)) and sharing no replica. The membership store SHALL hold the membership material and the record store records; an entry that fits neither layout is kept apart and used by nothing, as the requirement on entries outside the key layout states. An import of a pod's store SHALL refuse a ticket whose namespace the importing identity already holds in any other role — a data store, a directory, a connection metadata store, another pod's store or the pod's other store — with nothing registered, and a data import SHALL refuse a ticket naming a pod's store: a ticket is the word of whoever minted it, and a replica held in two roles is dropped when either role is forgotten.

**Example:** the replicas Alice's tablet a3 holds; a3 hosts Alice-leisure and Alice-work, both members of the pod "Wedding", Alice-leisure a member of "Family" too and Alice-work no member of it, and Alice-work holds Erin's data namespace under her grant.

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

#### Scenario: Creating a pod allocates two dedicated replicas

- **WHEN** a hosted identity creates a pod
- **THEN** two fresh pdn-store replicas are created for that identity, both reached through the pod id, and no domain namespace id is allocated

#### Scenario: A store ticket naming a replica held in another role is refused

- **WHEN** a joining identity is handed a store ticket whose namespace it already holds as a data store received under a grant
- **THEN** the join fails with no pod registered, and the data store is still held and reconciled as before

#### Scenario: Two pods with the same members are four stores

- **WHEN** the same identities are members of two pods and a record is written into one of them
- **THEN** the record never appears in the other pod's stores

#### Scenario: Two members hosted on one node hold the pod twice

- **WHEN** identities B and D, hosted on one node, are both members of a pod, and B places a record with no other node reachable
- **THEN** the node holds each store twice, one replica per identity, D's replica comes to carry B's record, payload included, and the record's entry carries B's author, which resolves to B alone

#### Scenario: A record in the membership store is kept and used by nothing

- **WHEN** a device of a member produces, in the membership store, an entry under the record store's key layout
- **THEN** every member device holds it, no membership state or record view changes, and each lists it as an entry outside the layout

### Requirement: The pod id carries no key material

A pod SHALL be identified by a 16-byte pod id, derived on the creator's device and checked on every member device that receives the created event, by the pod id steps above. The id SHALL carry no key material and SHALL NOT equal either store's namespace id: knowing the pod id grants no access, and no operation on a pod requires a signature by the pod — every write into either store is signed by the writing device's author key, and every membership act is a member's act.

**Example:** the id of "Family", which Alice creates; her announcement key is the public key of the secret made of 32 bytes of `33`, her `PdnId` derives from it, and the nonce her device draws is 16 bytes of `5a`.

```
announcement_pubkey   17cb79fb2b4120f2b1ec65e4198d6e08b28e813feb01e4a400839b85e18080ce
pdn_id                65bcff20d2b149925daa94e3750937044e8ef27385d24cb6cb7bf4182b408ba5
                      BLAKE3 derive_key("pdn/pdn-id/v1", announcement_pubkey)
nonce                 5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a
pod_id                ad58a3faa04cdc5576c8dc5823a347c6
                      the first 16 bytes of BLAKE3 derive_key("pdn/pod-id/v1", pdn_id ‖ announcement_pubkey ‖ nonce)
signature             806ce2029b681a9a…0420513704, 64 bytes of Ed25519
                      over "pdn/pod-creation/v1" ‖ pdn_id ‖ announcement_pubkey ‖ nonce, 99 bytes
a created event in Alice's chain under another announcement key, d759793bbc13a2819a827c76adb6fba8a49aee007f49f2d0992d99b825ad2c48,
with the same nonce, derives 0b1c51caa1cc711a3079f791899c43a7, its key deriving another pdn_id than Alice's, and every device holding ad58a3faa04cdc5576c8dc5823a347c6 counts it for nothing
both stores' namespace ids are 32-byte public keys of their own, and neither is the pod id
```

#### Scenario: The pod id is derived from the created event

- **WHEN** an identity creates a pod
- **THEN** recomputing the pod id from the created event's `PdnId`, announcement key and nonce gives the pod id, and the event's signature verifies under that announcement key, both by the pod id steps above

#### Scenario: The pod id is not a namespace id

- **WHEN** a pod is created
- **THEN** its pod id differs from both stores' namespace ids

#### Scenario: Knowing the pod id is not holding the stores

- **WHEN** a party knows a pod's id but holds no ticket to either store and is a device of no member
- **THEN** it obtains no session, no entry and no existence signal for either store

### Requirement: Every member device holds both stores whole and their write tickets

Every device of every member SHALL hold both stores whole — every record readable by every member — and SHALL hold the write ticket of each: a session between two member devices delivers every entry of either store with no egress filter, and what an entry counts for inside the pod is judged by the membership fold and the record view per entry, never by ticket mode — a member's write ticket widens nothing they refuse. Member devices SHALL form each store's swarm, so a write reaches the other member devices through the content-free announcement and the pull it triggers, and a member device SHALL be able to catch up from any other member device, not only from an entry's author. A store's contacts SHALL be the devices the current members' statements list, each paired with the member it is dialed as, and the holding identity's own other devices by its directory, dialed as that identity, derived afresh whenever the membership store changes, at each run of the store's periodic pass, and whenever the holding identity's directory lists a device it did not — which each store then dials, as that identity, since a sibling whose first dial came before its listing reached this device was refused, and nothing else dials it again before the pass — and replacing the previous list whole — save while the replica folds into no identity, holding nothing yet, when the contacts its ticket named stay — each peer of either store dialed as the member a derivation pairs it with; a contact naming this node's own address SHALL be reached inside the process, and a write SHALL announce to a co-located member's replica directly, as the in-process sessions spec states. Both stores' sync SHALL start with their contacts as they stand before either starts, since the membership store's first session derives them again, from a fold that may list no device of the inviter yet while the statements' payloads are still on their way. A pull an announcement triggers SHALL address the member the announcement names, when no derivation pairs its sender with a member: the name is the sender's word and picks only which replica of the sender's node the pull addresses, the session judged on both sides as any other. Any other peer no derivation pairs with a member SHALL be dialed as the member whose ticket the store was imported from, whatever the device shares of the store since.

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
- **THEN** every member's devices read the claim

#### Scenario: A write announced from a device no statement lists is pulled as its member

- **WHEN** a device of member B whose node no statement lists writes an entry, and a device of member A receives its announcement
- **THEN** A's device pulls the entry addressing B, and reads it

#### Scenario: A newcomer's share reaches its inviter as the inviter

- **WHEN** a newcomer whose derived contacts list no device of the inviter is out of the record store's swarm while the inviter writes an entry, and then shares its own tickets to both stores
- **THEN** the dials the share's restart makes reach the inviter's device as the inviter, and the newcomer receives the entry

#### Scenario: A newcomer's record store reaches the inviter whatever the first membership session derives

- **WHEN** a newcomer imports both stores, and the membership store's first session derives contacts listing no device of the inviter before the record store's sync starts
- **THEN** the record store's sync starts with the inviter's device among its contacts, and the newcomer reads the inviter's claim

#### Scenario: A sibling refused before its listing arrived is dialed once it does

- **WHEN** a member's device takes both stores before its record in the member's directory has reached the member's other device, which refuses its dials, and the record then arrives there
- **THEN** that other device dials the new one on both stores as the member, and the new device holds the pod

#### Scenario: A member's write ticket widens nothing

- **WHEN** a device of member C, no owner, holding the record store's write ticket, produces an entry at the key of B's claim and reconciles with a device of B
- **THEN** B's device holds it and reads nothing of it, and B's claim reads unchanged on every member device

### Requirement: A pod store's periodic pass reaches at most 5 peers every 5 minutes

The periodic reconcile pass SHALL reconcile each of a pod's stores at `SpawnOptions::pod_reconcile_interval`, 5 minutes by default, and each run SHALL open sessions for that store with at most 5 peers, drawn at random on every run from the store's contacts and the peers the engine recorded. Every other replica a node tracks SHALL keep `SpawnOptions::reconcile_interval` and every contact. Live delivery inside a pod rides the swarm's announcements and the pulls they trigger; the pass bounds how long an announcement gossip lost delays an entry.

**Example:** Bob's phone b1 holds 50 pods of 100 members on 2 devices each, and Bob's data namespace, which his laptop b2 holds too.

| replica on b1 | one run reaches | runs per hour |
|---|---|---|
| each store of the 50 pods, 199 contacts each | at most 5 of them | 12 |
| Bob's data namespace | b2, its one contact | 360 |

#### Scenario: A run over a pod store reaches at most 5 peers

- **WHEN** a device holds a pod's stores, each with more than 5 contacts, and a periodic pass runs over them
- **THEN** it opens sessions for each store with at most 5 peers

#### Scenario: A write whose announcement was lost arrives at the next run

- **WHEN** a device of member B misses the announcement of member A's write, and holds at most 5 contacts for the store
- **THEN** the next run of the pass over that store brings the write

#### Scenario: A pod store keeps its own interval

- **WHEN** a device holds a data namespace and a pod's stores, and its reconcile interval is shorter than its pod reconcile interval
- **THEN** the pass reconciles the data namespace once per reconcile interval and each pod store at most once per pod reconcile interval

### Requirement: Only member devices are served

A session for either of a pod's stores SHALL name the member whose replica it addresses and the member its caller acts as, and SHALL be served only when the member the caller names is a current member whose records list the caller's authenticated node id: that identity's own directory where the caller names the identity the serving replica belongs to, as a sibling device of it; that member's device statements in the membership store where the caller names another member, over the network and inside the process alike. Every other caller SHALL be refused indistinguishably from the store not being hosted — a holder of its ticket included, and a caller naming an identity that is no member included, even from a node that hosts a member and so shares its node id. A caller naming a member removed from the pod, or one that left it, SHALL be refused the record store from the first session set up after its departure event reaches the serving device, and served the membership store only as the requirement on a departed member's tombstone states; what it obtained while a member is retained.

**Example:** callers ask Bob's phone b1 for a session on the record store of "Family", addressing Bob's replica; Alice's tablet a3 hosts Alice-leisure, a member, and Alice-work, no member, and Dave, no member, holds the store's ticket on his phone d1.

| caller | names | b1 |
|---|---|---|
| c1, Carol's phone | Carol | serves every entry |
| a3 | Alice-leisure | serves every entry, as Alice-leisure |
| a3 | Alice-work | refuses with `00 00 00 02 02 00`, the answer for a store b1 does not host |
| d1 | Dave | refuses with the same frame, the ticket notwithstanding |
| c1, once Carol's removed event has reached b1 | Carol | refuses with the same frame from the next session; what c1 took before stays readable on it |

#### Scenario: A member device is served whole

- **WHEN** a device of a current member requests a session for either store
- **THEN** the session is served and delivers every entry

#### Scenario: A ticket holder that is no member obtains nothing

- **WHEN** a caller holding a store's ticket but a device of no member requests a session
- **THEN** the request is refused with the answer an unhosted replica would produce, and no fingerprint, count or existence signal is revealed

#### Scenario: A co-located identity that is no member is refused

- **WHEN** a node hosts member B and identity E, no member, and a session from that node names E as its caller for either store
- **THEN** the session is refused as for an unhosted store, while a session from the same node naming B is served

#### Scenario: A removed member is refused from the next session

- **WHEN** a member is removed and the removed event has reached a serving device, and a device of the removed member then requests a session on the record store
- **THEN** the request is refused as for an unhosted replica, while the remaining members' devices are still served, and what the removed member's device obtained while a member is still readable on it

### Requirement: A pod store holds whatever a session it serves carries

Either store of a pod SHALL hold every entry a session carries from a caller it serves — a member device's session whole, a former member's over its departure's past — and SHALL drop only what pdn-store drops on its own: a key over 8,192 bytes, a timestamp more than 10 minutes ahead, an entry whose signature does not verify. No entry SHALL be judged at ingest by its author, its key or the membership, and no entry SHALL wait at ingest. What an entry counts for SHALL follow from the whole set of entries a device holds, whatever order they arrived in: the membership fold counts an event, and the record view reads a record's entry, by the rules the requirements below state, and an entry whose payload or whose dependencies have not arrived counts once they have. Every member device then holds the same entries, and a forged entry is held and relayed by every member device and counts on none.

**Example:** Bob's modified phone b1, Bob being a plain member of "Family", carries into a session with Carol's phone c1 Alice's claim, an entry of its own at that claim's key, and a promoted event for Bob it wrote; `<alice>`: 64 lowercase hex chars of Alice's `PdnId`; `<id>`: the claim's id.

| entry b1 carries | its author | on c1 |
|---|---|---|
| `by/<alice>/claim/<id>/1` | a1's | held, and read as Alice's claim |
| `by/<alice>/claim/<id>/1` | b1's | held, and read by nothing: Alice's claim reads unchanged |
| a promoted event in Bob's chain | b1's | held, and counted for nothing: Bob is no owner |
| a later session between c1 and b1 | | finds no difference |

#### Scenario: A forged entry is held and counts for nothing

- **WHEN** a device of member B, no owner, carries into a session with a device of member C member A's claim, an entry of its own at that claim's key, and a promoted event for B
- **THEN** C's device holds all three, reads A's claim as A's and nothing of B's entry at its key, lists B as a plain member, and a later session between the two devices finds no difference

#### Scenario: Entries arriving in any order converge

- **WHEN** two member devices take the same entries of both stores — a newcomer's joined event, its device statement and its first claim among them — one in that order and the other in the reverse
- **THEN** both hold the same entries, list the same members and read the same records

### Requirement: A departed member's devices keep the membership store as the pod's tombstone

A member's departure event — its left event, or a removed event in its chain — SHALL end its devices' hold on the record store and SHALL NOT end their hold on the membership store: every device of the departed member's identity SHALL keep the membership store for good as the pod's tombstone, and forget the record store. The departure's past SHALL be the departure event and every entry it depends on — the earlier events of its subject's chain, its actor's chain up to the point it names, and, for each of these in turn, the same, with the joined events and device statements that resolve their authors — down to the created event. A member device SHALL serve a session naming a former member, from a device the former member's statements list, on the membership store alone and over the departure's past alone, in both directions, and SHALL serve it nothing outside that past; a sibling device of the former member SHALL serve it the tombstone whole. A device whose own identity departed SHALL hold its sessions with member devices to its departure's past in both directions as well, taking beside it the events of its own chain after the departure, so that a member device that does not yet know of the departure sends it nothing outside that past and a join after the departure reaches it. A tombstone SHALL be reconciled with member devices until one session with a member device has converged over the departure's past, and then with the identity's own devices alone.

**Example:** Carol leaves "Family" on her phone c1 while c1 is offline, and an hour later c1 reaches Bob's phone b1; meanwhile Bob invited Dave, and nothing in Carol's departure depends on Dave's join.

| on b1 | c1 |
|---|---|
| a session on the membership store naming Carol | served over the past of her left event: b1 takes the left event and sends what of that past c1 lacks, and not Dave's joined event |
| a session on the record store naming Carol | refused with `00 00 00 02 02 00` |
| a record Alice places afterwards | reaches b1 and never c1 |

#### Scenario: A left event written offline reaches the members

- **WHEN** a member leaves on a device with no member device reachable, and that device later reaches a member device
- **THEN** the member device holds the left event and every member device lists the member as no member, while the departed device is refused the record store

#### Scenario: A device offline during its member's removal learns of the removal

- **WHEN** member C's device is offline while an owner removes C, and the device then requests a session from a member device
- **THEN** the session on the membership store delivers C's removed event and the entries it rests on, C's device forgets the record store and keeps the membership store, and neither a record placed after the removal nor a membership event outside the removal's past reaches it from any member device

#### Scenario: A device that left takes nothing outside its departure's past

- **WHEN** a member leaves on a device with no member device reachable, another member then invites a newcomer, and the leaving device reaches that member's device, which does not know of the leave yet
- **THEN** the member's device holds the left event, and the leaving device holds no entry of the newcomer's

#### Scenario: A departed member joins again

- **WHEN** a removed member's device holds the pod's tombstone, and an owner invites the member again
- **THEN** the device takes its new joined event from a member device, folds its member as a member again, and writes under its new sequence records every member device reads

#### Scenario: Every device of a departed identity keeps the tombstone

- **WHEN** a member leaves on one device while another device of its identity holds the pod, and the identity's directory syncs
- **THEN** both devices hold the membership store and neither holds the record store

### Requirement: Membership needs no connection

Access to a pod's stores SHALL rest on membership alone: no connection between two members is required for either to read what the other wrote, and joining a pod SHALL create no connection.

**Example:** Alice, Bob and Carol hold no connection to one another; Alice creates "Family" and invites Bob and Carol, and Bob places a claim. Asked on Carol's phone c1:

| call | answer |
|---|---|
| `list_connections` on Carol's directory | `[]` |
| a read of Bob's claim in "Family" | the claim's bytes |

#### Scenario: Three identities share through a pod with no connections

- **WHEN** identities A, B and C hold no connection to one another, A creates a pod and invites B and C, and B writes an entry
- **THEN** C's device reads the entry, and no identity lists any connection

### Requirement: The membership store holds each member's event sequence, append-only

The membership store SHALL hold, per member, one sequence of membership events under `member/<pdnid>/<seq>/<kind>/<actor>/<aseq>` — created, joined, left, removed, promoted, demoted — with the sequence number inside the signed bytes, `<actor>` the actor's `PdnId`, among whose devices the entry's author has to be, and `<aseq>` the actor's own sequence at the time of acting — the writing device placing the event at the first sequence of the subject's chain at which it holds no entry and naming as `<aseq>` the last sequence before the first such one of the actor's chain — and the member's device-list statements under `member/<pdnid>/devices/<version>`, one key per version. An event SHALL count as its actor's chain folded up to `<aseq>` allows: a joined event counts when the actor was a member there and is not the subject, and its announcement key derives the subject's `PdnId` and its join statement verifies under that key over the subject's sequence, by the joining steps above, a promoted event when the actor was an owner there, a removed or demoted event when the actor was an owner there and is not the subject, a left event when the actor is the subject itself; the created event — the creator's first, self-authored, making it a member and an owner, its `<aseq>` `0` — counts when its `PdnId`, announcement key and nonce derive the pod id, its announcement key derives its `PdnId`, and its signature verifies under that key, and is the root of every verification; an event whose payload has not arrived, or whose actor's chain the device does not hold up to `<aseq>` — a sequence being held once any entry at it is, whatever it counts for — SHALL count once it does, events left waiting on each other's outcome in a loop SHALL count for nothing, and an event failing its check SHALL count for nothing on every member device, held as every entry is. Honest devices overwrite and delete no entry in the membership store — the store holds no tombstones. A member's membership state and role SHALL be folded by walking its events in sequence order on every member device, as far as the first sequence at which the device holds no entry, an event beyond it waiting until the sequences below it arrive, whatever order the events arrived in and never by entry timestamp: a join makes it a plain member, a promotion an owner, a demotion a plain member, a leave or a removal no member, a later join a plain member again. Events at one sequence of one subject SHALL all be held, and among those whose transition the subject's state before that sequence allows the fold SHALL take effect with the one that ranks highest — removed, then left, then demoted, then promoted, then joined, the created event above a joined event — an event that state does not allow counting for nothing and the same event written twice counting once. When the folded membership holds no owner and the roles of some of its former owners ended in demotions, the fold SHALL take those demotions in the order of their actors' `PdnId`, lowest first, each against the former owners it has not yet demoted, and SHALL ignore every one that would demote the last of them.

**Example:** Bob's chain in "Family" as every member device holds it; the key's last two segments are the actor and the actor's sequence; `<alice>`, `<bob>`, `<carol>`: 64 lowercase hex chars of each `PdnId`.

```
member/<bob>/1/joined/<alice>/1       Alice at her sequence 1, from a1          Bob a plain member
member/<bob>/2/promoted/<alice>/1     Alice at her sequence 1, from a1          an owner
member/<bob>/3/demoted/<alice>/1      Alice at her sequence 1, from a1          a plain member
member/<bob>/4/left/<bob>/3           Bob himself at his sequence 3, from b1    no member
member/<bob>/5/joined/<carol>/1       Carol at her sequence 1, from c1          a plain member again
member/<bob>/devices/1                Bob's device statement, version 1: b1

the fold walks the chain by sequence, whatever order the entries arrived in
```

#### Scenario: A role flip resolves by sequence whatever the arrival order

- **WHEN** owner A promotes B (B's sequence 2, after B's join at 1), demotes B (3) and promotes B again (4), and the three events reach a device of member C in the order 4, 2, 3
- **THEN** C's device lists B as a plain member while the promotion at 4 waits for the sequences below it, as an owner once 2 arrives, and as an owner once all three have arrived

#### Scenario: An event placed at a member's joining point changes nothing

- **WHEN** a device of owner A writes a removed event at member B's sequence 1, beside the invite act that brought B in, after B invited C
- **THEN** every member device holds the removed event, counts it for nothing, and lists B and C as members

#### Scenario: An entry far beyond a chain waits and blocks nothing

- **WHEN** a device of member D writes an event in owner A's chain at A's sequence 1,000,000, and A's device then promotes member B
- **THEN** every member device holds D's entry without counting it, counts A's promotion, and lists B as an owner

#### Scenario: A chain past sequence 9 folds in number order

- **WHEN** B's chain holds a promoted event at B's sequence 9 and a demoted event at B's sequence 10, whose keys the store orders `…/10/…` before `…/9/…`
- **THEN** every member device lists B as a plain member, the demotion at 10 applied after the promotion at 9

#### Scenario: A role event from a plain member counts for nothing

- **WHEN** a device of member C, no owner, produces a promoted event for C and reconciles with a device of B
- **THEN** B's device holds it and still lists the owners unchanged

#### Scenario: A leave ends the membership and a new join restores it as a plain member

- **WHEN** B, an owner, writes a left event (sequence 5) from its own device, and a member later invites B again, writing a joined event (sequence 6)
- **THEN** every member device lists B as no member after sequence 5 and as a plain member — no owner — after sequence 6

#### Scenario: A device holding nothing verifies the store from the created event

- **WHEN** newcomer D's device, holding no membership store, sessions with the inviter's device, which holds the created event and every event since
- **THEN** D's device converges on the same membership as the inviter in that session, every event verified against its actor's chain, whatever order the events arrived in

#### Scenario: What an owner did while an owner stands after its demotion

- **WHEN** owner A promoted C naming A's sequence 3, A was then demoted at A's sequence 4, and a device linked into member B after that catches up
- **THEN** B's new device lists C as an owner

#### Scenario: An event naming an actor point without the membership state it needs counts for nothing

- **WHEN** A was demoted at A's sequence 4 and a device of member E relays a promoted event for F authored by A's device naming A's sequence 4
- **THEN** every member device holds it, counts it for nothing, and lists F as a plain member

#### Scenario: Nobody leaves for another member

- **WHEN** a device of member D produces a left event in B's chain
- **THEN** every member device holds it, counts it for nothing, and still lists B as a member

#### Scenario: Nobody removes or demotes itself

- **WHEN** a device of owner A produces a removed event and a demoted event in A's own chain
- **THEN** every member device holds both, counts neither, and still lists A as a member and an owner

#### Scenario: A departed member does not readmit itself

- **WHEN** C left at C's sequence 2, and a device of member D relays a joined event in C's chain at C's sequence 3, authored by C's device and naming C's sequence 1
- **THEN** every member device holds it, counts it for nothing, and lists C as no member

#### Scenario: A departed member readmitted under a key that does not derive its `PdnId` stays out

- **WHEN** C left at C's sequence 2, and a device of member B writes a joined event in C's chain at C's sequence 3 under an announcement key B's device minted, with a join statement that verifies under that key, and a device statement for C listing B's device under the same key
- **THEN** every member device holds both, counts neither, and lists C as no member

#### Scenario: A second joined event at a member's first sequence changes nothing

- **WHEN** a device of member B writes a joined event under an announcement key B's device minted at C's sequence 1, beside the joined event that brought C in, and another in the chain of an identity E that was never a member
- **THEN** every member device holds both, counts neither, resolves C's devices by C's own statements alone, and lists E as no member

#### Scenario: A join statement copied from an earlier join counts for nothing

- **WHEN** C left at C's sequence 2, and a device of member B writes a joined event at C's sequence 3 carrying C's announcement key and C's join statement from C's sequence 1
- **THEN** every member device holds it, counts it for nothing, and lists C as no member

#### Scenario: A created event that does not derive the pod id counts for nothing

- **WHEN** a device of owner C produces a created event in C's own chain, or one in the creator's chain under another announcement key or nonce
- **THEN** every member device holds it, counts it for nothing, and lists the owners unchanged

#### Scenario: A device holding nothing counts no invented creator, whatever arrives first

- **WHEN** a device freshly linked into member D, holding the pod id from D's directory and no membership store, sessions first with a modified device of member B that serves a created event in B's chain and withholds the creator's, and then with a device of member C
- **THEN** the linked device holds B's invented chain and counts none of it, and after the session with C lists the members and owners C's device lists

#### Scenario: A promoted event for no member changes nothing

- **WHEN** owner A produces a promoted event in the chain of an identity that never joined
- **THEN** every member device holds the entry as written and lists that identity as no member and no owner

#### Scenario: Two owners' concurrent events at one point both persist

- **WHEN** owners A and C, disconnected from each other, each write an event in B's chain at B's sequence 5 — A a promoted event, C a removed event — and the members' devices then reconcile
- **THEN** every member device holds both entries and lists B as no member, the removal outranking the promotion

#### Scenario: Two owners demoting each other leave one owner

- **WHEN** owners A and C, disconnected from each other and the pod's only owners, demote each other, A's `PdnId` sorting below C's, and the members' devices then reconcile
- **THEN** every member device holds both entries and lists A as the one owner and C as a plain member

#### Scenario: A leave beside a demotion at one point leaves the member out

- **WHEN** owner A demotes owner B at B's sequence 4 while B, disconnected from A, leaves at its sequence 4, and the members' devices then reconcile
- **THEN** every member device holds both entries and lists B as no member, the leave outranking the demotion

#### Scenario: An event by no member's device counts for nothing

- **WHEN** a device of member D relays an event in B's chain authored by a key that resolves to no member's device
- **THEN** every member device holds it, counts it for nothing, and reads B's chain unchanged

#### Scenario: An event ahead of its actor's point counts once the point arrives

- **WHEN** a device of member D receives a promoted event for C authored by A's device naming A's sequence 3 while holding A's chain only up to sequence 2, and A's sequence 3 arrives in a later session
- **THEN** the event is held from the first session and counts from the session that brings A's sequence 3

### Requirement: Verdicts hold their limits without an anchored log

The fold and the record view SHALL judge an entry by the point it names and by nothing else, and a session SHALL be served by the membership as of its setup: an event or a record whose named point checks out counts, whoever carries it and whenever it arrives, and what the entries a device holds cannot resolve counts for nothing until they can. The scenarios below are the consequences on honest devices — what the platform does, not what a pod wants — each named after the decision that keeps it.

**Example:** verdicts in "Family" beside what a pod would want of each.

| case | the platform | a pod wants | kept by |
|---|---|---|---|
| Alice's promotion of Carol, naming Alice's sequence 3, an event only devices that have since died ever held | counts it never | counted | the actor's point, until a current owner promotes Carol anew |
| Dave's phone d1 asks Alice's phone a1 for a session before Dave's joined event reaches a1 | refuses it | served | the session order, healed once the joined event arrives |

#### Scenario: A newcomer is refused a session until its joined event arrives

- **WHEN** D joined through member E, D's joined event has not reached a device of A, and D's device requests a session from A's device
- **THEN** the session is refused as for an unhosted store, and served once the joined event reaches A's device

#### Scenario: A dependency whose authoring device died is never resolved until re-issued

- **WHEN** A's sequence 3 — the event that promoted A — reached only A's device before B's device, which authored it, died; A's device then promoted C naming A's sequence 3, spread that event to a device of D, and died too, so no live device holds A's sequence 3
- **THEN** every device holds C's promoted event and counts it never, listing C as a plain member meanwhile, and lists C as an owner only after a current owner promotes C anew — an ordinary promotion at a point every device holds

### Requirement: The membership store is reconciled before the record store

A session between two member devices SHALL reconcile the membership store to convergence, fold it, and only then reconcile the record store; both stores SHALL be reconciled whole, with no capability filter on either. The record store's session SHALL be served by the membership folded after the membership store's session, so that a newcomer whose joined event that session brings is served and a member whose departure it brings is refused; a session that would refuse its caller SHALL first wait, for a few seconds at most, for the payloads the caller's own chain and statements still lack, since a joined event counts only once its join statement has arrived. A record SHALL be held whatever it arrives ahead of, and SHALL read once the membership its entries name has arrived.

**Example:** Alice's laptop a2 holds neither Dave's joined event nor Dave's first claim, and sessions with Carol's phone c1, which holds both; `<dave>`: 64 lowercase hex chars of Dave's `PdnId`; `<id>`: the id `put_record` minted.

| step of the session | a2 |
|---|---|
| 1. the membership store reconciled to convergence | takes Dave's joined event and his device statement, listing his phone d1 |
| 2. the membership folded | Dave a member at his sequence 1, writing on d1 |
| 3. the record store reconciled | takes `by/<dave>/claim/<id>/1` from d1's author, which the record view reads at Dave's sequence 1 at once |

#### Scenario: A newcomer's first record reads once the session brings its membership

- **WHEN** newcomer D's joined event and D's first claim are both unknown to a device of B, and B's device sessions with a device holding both
- **THEN** B's device reads D's claim at the end of that session

### Requirement: The record store's key names the member and the kind

A record SHALL sit under the name of the member that placed it, the key carrying the record's kind and the writer's membership sequence at the time of writing: `by/<pdnid>/claim/<id>/<mseq>` for a claim, `by/<pdnid>/immutable-document/<id>/<mseq>` for an immutable-document, `by/<pdnid>/mergeable-document/<id>/<op>` for each operation of a mergeable-document, `<op>` being one segment, `<writer>.<author>.<mseq>.<opseq>` — the writer's `PdnId`, its author key, its membership sequence and its own operation sequence — the author being the one that signs the entry and counting only among the writer's devices. The operation sequence SHALL count one author's operations on one mergeable-document from 1, the writing device taking the one above the highest its replica holds under its author. Every segment of either store's keys SHALL be text: a number decimal with no leading zeros, a `PdnId` or an author key 64 lowercase hexadecimal characters, a record id the 16 random bytes `put_record` mints as 32; the store orders keys byte by byte, so the fold and the record view SHALL parse every number they order. `<pdnid>` SHALL be the member's identity, never a device. A record's identity SHALL be its key without its last segment, whatever its kind, and a record SHALL be addressed by the pod id beside that key, never by either store's namespace id, which is the store's read capability.

**Example:** Bob's three records in "Family", placed from his phone b1 and from his laptop b2; Bob and Carol each joined at their sequence 1; `<bob>`, `<carol>`: 64 lowercase hex chars of each `PdnId`; `<claim>`, `<scan>`, `<note>`: 32 lowercase hex chars of the ids `put_record` minted for the three records; `<b1-author>`, `<c1-author>`: 64 lowercase hex chars of the authors Bob writes with on b1 and Carol on her phone c1.

```
by/<bob>/claim/<claim>/1                                       from b1
by/<bob>/immutable-document/<scan>/1                           from b2, under b2's author
by/<bob>/mergeable-document/<note>/<bob>.<b1-author>.1.1      Bob, b1's author, Bob's sequence 1, that author's operation 1
by/<bob>/mergeable-document/<note>/<carol>.<c1-author>.1.1    Carol, c1's author, Carol's sequence 1, that author's operation 1 — under Bob's name all the same

a listing under by/<bob>/ returns these four entries; each record's identity is its key without the last segment
```

#### Scenario: A record sits under the name of the member that placed it

- **WHEN** member B places a claim, an immutable-document and a mergeable-document with one operation, from two of B's devices
- **THEN** their keys are `by/<B>/claim/<id>/<mseq>`, `by/<B>/immutable-document/<id>/<mseq>` and `by/<B>/mergeable-document/<id>/<op>`, the same `<B>` and the same `<mseq>` from either device, and a listing under B's prefix returns exactly them

#### Scenario: An operation sequence continues after a restart

- **WHEN** a device of member B appends three operations to a mergeable-document, its runtime restarts, and it appends a fourth
- **THEN** the fourth operation's `<op>` carries operation sequence 4 under the same author, and every member device holds four operations of that author on the record

### Requirement: A claim is written only by its issuer

A claim SHALL read only from an entry authored by a device of the member the claim names as its issuer, that member being a member at the sequence the claim's key names. An entry at a claim's key authored by a device of any other member SHALL be held and read by nothing, on every member device, silently — the verdict is on the entry's author, not on the session peer that carried it, so an entry relayed by a third member keeps the verdict its author earns.

**Example:** entries at the key of Alice's claim `by/<alice>/claim/<id>/1` reach Carol's phone c1; `<alice>`: 64 lowercase hex chars of Alice's `PdnId`; `<id>`: the id `put_record` minted; a1 is Alice's phone, b1 Bob's.

| entry | its author | carried by | c1 |
|---|---|---|---|
| Alice's claim | a1's | a1 | reads it |
| Alice's claim | a1's | b1 | reads it: judged by its author, not by b1 |
| another entry at that key | b1's | b1 | holds it and reads nothing of it, signalling nothing; Alice's claim reads unchanged |

#### Scenario: The issuer's own claim is read

- **WHEN** a device of member A writes a claim issued by A and a device of member B reconciles
- **THEN** B's device reads the claim

#### Scenario: Another member's entry under the issuer's claims is read by nothing

- **WHEN** a device of member B produces an entry that names A as the claim's issuer and reconciles with a device of A or of a third member
- **THEN** the entry is held and read by nothing, no rejection is signalled, and A's own claim at that key reads unchanged

#### Scenario: A relayed claim is judged by its author

- **WHEN** a device of member C receives, from a device of member B, a claim authored by a device of A that names A as issuer
- **THEN** C's device reads it, although the session peer is B

### Requirement: A mergeable-document is edited by every member

An operation on a mergeable-document SHALL read from a device of any member, whoever's name the mergeable-document sits under, each operation carrying its writer's author signature and naming, in its key, its writer and the writer's membership sequence at the time of writing. The one ground for not reading an operation is its writer's membership state at that sequence: an operation signed by an author other than the one its `<op>` names, one whose author is no device of the writer its key names, or one whose writer was not a member at the named sequence of its own events, SHALL be held and read by nothing, silently, on every member device — no role, no mergeable-document and no time of authoring narrows reading further; an operation naming a sequence the device does not yet hold SHALL read once the events arrive. An operation is judged the same on every device whenever it arrives: everything a member wrote while a member — its operations on its own mergeable-documents and on other members' — SHALL read after it leaves or is removed, on a device that catches up later included, and SHALL resolve to that member after it joins again, its new operations naming its new sequence. No record carries a sharing mode.

**Example:** operations on Bob's note reach Alice's laptop a2, linked after all of them were written; Carol, on her phone c1, joined at her sequence 1, was removed at 2 and invited again at 3.

| operation | its author | names | a2 |
|---|---|---|---|
| Carol's, written while a member | c1's | her sequence 1 | reads it |
| Carol's, written after the removal | c1's | her sequence 2 | holds it and reads nothing of it, signalling nothing |
| Carol's, written after she joined again | c1's | her sequence 3 | reads it; her operation naming 1 still resolves to her |
| one whose author no member's statement lists | — | — | holds it and reads nothing of it, signalling nothing |

#### Scenario: An operation reads as the writer its key names

- **WHEN** a device of member B lists, in B's device statement signed by B's announcement key, the author member A writes with on A's device, and A appends an operation from that device
- **THEN** every member device counts B's statement and reads A's operation as A's, and no operation of A's reads as B's

#### Scenario: Any member edits another member's mergeable-document

- **WHEN** a device of member C, no owner, appends an operation to a mergeable-document under member B's name and the members' devices reconcile
- **THEN** every member's devices read C's operation, its author being C's device

#### Scenario: An operation by no member's device is read by nothing

- **WHEN** a device of member B carries an operation on a mergeable-document authored by a key that resolves to no member's device, and reconciles with a device of a third member
- **THEN** every member device holds it and reads nothing of it, no rejection is signalled, and the mergeable-document's own operations read unchanged

#### Scenario: An entry at another writer's operation key is read by nothing

- **WHEN** a device of member C writes an entry at the key of member B's operation, its `<op>` naming B and the author B's device signed it with, and reconciles with a device of a third member
- **THEN** every member device holds both entries, reads B's operation once and as B's, and reads nothing of C's entry, no rejection being signalled

#### Scenario: A departed member's earlier operation reaches a device that catches up later

- **WHEN** member C, a member from sequence 1, appended an operation naming sequence 1, C was then removed at sequence 2, and a device linked into member B after the removal catches up from a device of member D
- **THEN** B's new device reads C's operation, in C's own mergeable-documents and in B's alike

#### Scenario: An operation naming a sequence at which its writer was no member is read by nothing

- **WHEN** C was removed at sequence 2 and a device of member D relays an operation authored by C's device naming sequence 2
- **THEN** every member device holds it and reads nothing of it, no rejection is signalled, and C's operations naming sequence 1 still read

#### Scenario: A member that joins again writes under its new sequence

- **WHEN** member C was removed at sequence 2, a member invites C again at sequence 3, and C's device then appends an operation naming sequence 3
- **THEN** every member device reads the operation, and C's earlier operations, naming sequence 1, still resolve to C

#### Scenario: An operation ahead of its author's joined event reads once the event arrives

- **WHEN** a device of member B receives, from a device of member E, an operation authored by a device of D while no joined event of D has reached B's device
- **THEN** B's device holds the operation and reads nothing of it, and reads it as D's once D's joined event reaches B's device, with no session offering it again

### Requirement: A mergeable-document keeps every operation; an immutable-document is placed once by its member

A mergeable-document SHALL hold each edit as its own entry under its own key, never overwritten by another edit: concurrent operations by two writers the pod reads SHALL both be held and read on every member device, and their merge is above the data layer. An immutable-document SHALL be one entry under one key, read only when authored by a device of the member under whose name it sits; an entry at that key authored by a device of any other member — an owner included — SHALL be held and read by nothing, silently, on every member device.

**Example:** Bob and Carol, disconnected from each other on b1 and c1, each append an operation to Bob's note, and Alice, an owner, writes from a1 at the key of Bob's lease scan; `<bob>`: 64 lowercase hex chars of Bob's `PdnId`; `<note>`, `<lease>`: ids `put_record` minted; `<op>`: the writer's `PdnId`, its author key, membership sequence and operation sequence, so each operation has its own.

| entry | key | every member device |
|---|---|---|
| Bob's operation | `by/<bob>/mergeable-document/<note>/<op>`, `<op>` naming Bob and b1's author | holds it |
| Carol's operation | `by/<bob>/mergeable-document/<note>/<op>`, `<op>` naming Carol and c1's author | holds it beside Bob's |
| Alice's entry at the scan's key | `by/<bob>/immutable-document/<lease>/1` | holds it and reads nothing of it, a1 included, and reads Bob's scan unchanged |

#### Scenario: Concurrent operations on a mergeable-document both persist

- **WHEN** a device of member B and a device of member C each append an operation to a mergeable-document under B's name while disconnected, and the members' devices then reconcile
- **THEN** every member device holds both operations

#### Scenario: An immutable-document is read from its member and from nobody else

- **WHEN** a device of member B places an immutable-document, a device of owner A then produces an entry at its key, and the members' devices reconcile
- **THEN** every member device reads B's immutable-document, and every member device, A's included, holds A's entry and reads nothing of it

### Requirement: Entries outside the key layout are kept, used by nothing, and listed

An entry in either store whose key fits neither store's layout, or fits one only in part, SHALL be held like every entry a session carries from a member device, whoever its author, and reconciled and relayed like any entry. A key longer than the store's bound of 8,192 bytes is dropped before any layout is read ([capability-gated ingest](../capability-gated-ingest/spec.md)), so every record key the layouts define, a record's id included, has to fit under that bound. No membership fold and no record view SHALL read it, and the store SHALL list such entries with their authors so the application can show them.

**Example:** entries outside the layout reach Carol's phone c1 from Bob's phone b1; `<bob>`: 64 lowercase hex chars of Bob's `PdnId`; `<id>`: an id `put_record` minted.

| entry | its author | c1 |
|---|---|---|
| `ext/anything` in the record store | b1's | holds it and lists it with b1's author; every record reads as before, and the next session with b1 finds no difference |
| `by/<bob>/claim/<id>/1` in the membership store | b1's | holds it the same way, and no membership state changes |
| `ext/anything`, relayed | one no member's statement lists | holds it and lists it with that author |

#### Scenario: An unknown entry from a member converges and changes nothing

- **WHEN** a device of member B writes an entry at `ext/anything` in the record store, and the members' devices reconcile
- **THEN** every member device holds the entry and lists it with B as its author, every record reads as before, and a later session between any two member devices finds no difference

#### Scenario: An unknown entry is held whoever authored it

- **WHEN** a device of member D relays an entry at `ext/anything` authored by a key that resolves to no member's device
- **THEN** every member device holds it and lists it with that author, and no record and no membership state changes

### Requirement: A member's devices are announced by the member itself

A member's device-list statement — each device's node id beside the author the member writes with on that device — SHALL count by the signature embedded in it — made by the announcement key over the prefix `pdn/pod-devices/v1` followed by the statement — verified against the announcement key the member's join statement, or the creator's created event, carries — never by the entry's author or the session peer: a statement written by a freshly linked device of the member itself and a statement relayed by any other member earn the same verdict. A statement whose embedded signature does not verify under the member's announcement key SHALL count for nothing on every member device, held as every entry is. A statement SHALL count once its payload has arrived and the event carrying the member's announcement key is held, whatever order the two arrive in, and an entry whose author only that statement lists SHALL read from then on. Device resolution SHALL follow the union of every validly signed statement of the member a device holds, whatever its version, whichever author wrote each and never by entry timestamps, so a device that a later version leaves out stays listed by the version that named it, and two statements written at one version by two authors list every device either names.

**Example:** device statements in "Wedding"; Erin invited Bob, whose phone is b1, and Alice-work, whose one device is Alice's tablet a3; Bob invited Alice-leisure, whose phone is a1, and a3 was later linked into Alice-leisure too; Dave, a member, has the phone d1; `<bob>`, `<alice-leisure>`, `<alice-work>`: 64 lowercase hex chars of each `PdnId`.

| entry | written by | signed by | every member device |
|---|---|---|---|
| `member/<bob>/devices/1`: b1 with b1's author | e1, Erin's phone, in the join dialogue that brought Bob in | Bob's announcement key | counts it: the writer is not the member |
| `member/<alice-leisure>/devices/2`: a1, and a3 with a3's author for Alice-leisure | a3, just linked into Alice-leisure | Alice-leisure's announcement key | counts it, whoever relays it, and adds a3 to Alice-leisure's devices |
| `member/<bob>/devices/2` twice: b1 and b2 under b2's author, b1 and b3 under b3's author | b2 and b3, each just linked into Bob while holding version 1 alone | Bob's announcement key | counts both and resolves Bob's devices to b1, b2 and b3 |
| `member/<bob>/devices/3`: b1, b2, b3 and d1 | d1 | Dave's announcement key | holds it and counts it for nothing |
| `member/<alice-work>/devices/1`: a3 with a3's author for Alice-work | e1, in the join dialogue that brought Alice-work in | Alice-work's announcement key | counts it: a3 stands under two authors, one per member |

#### Scenario: A new device registers itself through its siblings

- **WHEN** a device freshly linked into member B writes the next version of B's device statement, listing itself, into its local replica, reconciles with another device of B that holds the pod, and that device then reconciles with a device of member C
- **THEN** C's device counts the statement and serves the new device's next session, which it refused before the statement arrived

#### Scenario: Two members on one node are two authors under one node id

- **WHEN** identities B and D, hosted on one node, are both members of a pod and each places a record from that node
- **THEN** B's and D's statements list the same node id under two different authors, and every member device resolves each record to the one member whose author signed it

#### Scenario: A statement under a wrong key counts for nothing

- **WHEN** a device of member M produces a device statement for member B signed by a key that is not B's announcement key
- **THEN** every member device holds it and counts it for nothing, and B's device set stays what B's own statements say

#### Scenario: A device statement ahead of its join counts once the join arrives

- **WHEN** in one session a device of A receives B's device statement, and an event authored by a device only that statement lists, before the joined event carrying B's announcement key
- **THEN** both are held and count once the joined event arrives, in that session or a later one, while a statement for B signed by a key no joined event carries counts on no member device

#### Scenario: An old version displaces nothing

- **WHEN** a device of B holding version 2 of B's statement writes it into a replica already holding version 3
- **THEN** every member device still lists every device version 3 names

#### Scenario: A device a later version misses stays listed

- **WHEN** version 3 of B's statement lists B's device X, X places a claim under B's name and never syncs again, and another device of B, which never saw version 3, writes version 4 without X
- **THEN** every member device lists X among B's devices and reads X's claim as B's, while a device named only by a statement under a key that is not B's stays off the list

#### Scenario: Two statements at one version list both devices

- **WHEN** two devices of B, out of reach of each other, each write the next version of B's statement listing a different new device, and both statements reach a member device in either order
- **THEN** that device resolves B's devices to every device either statement lists, and a third statement at that version signed by a key that is not B's announcement key adds nothing

### Requirement: A departure forgets the record store and keeps the membership store

Forgetting a pod at a departure SHALL stop reconciling the record store, leave both swarms, drop the record store's replica, and turn the pod's registration into its tombstone together, so that operations addressed to that pod afterwards fail with an unknown-pod error distinguishable from transport and storage failures, while the membership store's replica stays as the tombstone the requirement on a departed member's tombstone describes. Forgetting SHALL reach the replicas of the identity that forgets alone: a co-located member's replicas of the same pod go on as before.

**Example:** Alice's tablet a3 hosts Alice-leisure and Alice-work, both members of "Wedding", and Alice-work leaves the pod.

| on a3, afterwards | as Alice-work | as Alice-leisure |
|---|---|---|
| a read of Erin's claim | the unknown-pod error | the claim |
| Wedding's record store | dropped, its swarm left, reconciled no more | open and reconciling |
| Wedding's membership store | kept as the tombstone, its swarm left | open and reconciling |

#### Scenario: Forgetting a pod unregisters it

- **WHEN** a node holds a pod's stores and forgets the pod at a departure
- **THEN** reading or writing under that pod fails with the unknown-pod error, the record store is neither reconciled nor served, the membership store is held as the pod's tombstone alone, and the node's other pods are unaffected

#### Scenario: One member forgetting spares the co-located other

- **WHEN** a node hosts members B and D of one pod and B forgets it
- **THEN** operations addressed to the pod as B fail with the unknown-pod error, while D still reads and writes the pod and D's replicas keep reconciling
