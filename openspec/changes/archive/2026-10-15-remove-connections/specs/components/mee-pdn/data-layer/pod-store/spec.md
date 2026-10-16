## REMOVED Requirements

### Requirement: Membership needs no connection

**Reason**: Connections are removed by this change, so no pod could rest on one and the requirement states nothing a test can tell apart.

**Migration**: None: the pod's members reach each other's records through membership, as before.

## MODIFIED Requirements

### Requirement: A pod is two dedicated stores, held per member identity

A pod SHALL be served by exactly two pdn-store namespaces — its membership store and its record store — separate from every private metadata store (PMS) and every other pod's stores. Two pods SHALL NOT share a store, whatever their member sets. Both stores SHALL be addressed through the pod id, and no domain namespace id is allocated for either. Every member identity SHALL hold a replica of each store of its own, created or imported for that identity ([identity-scoped replicas](../identity-scoped-replicas/spec.md)): two identities of one node that are both members SHALL each hold both stores, the two copies converging inside the process ([in-process sessions](../in-process-sessions/spec.md)) and sharing no replica. The membership store SHALL hold the membership material and the record store records; an entry that fits neither layout is kept apart and used by nothing, as the requirement on entries outside the key layout states. An import of a pod's store SHALL refuse a ticket whose namespace the importing identity already holds in any other role — a PMS, another pod's store or the pod's other store — with nothing registered, and a PMS import SHALL refuse a ticket naming a pod's store: a ticket is the word of whoever minted it, and a replica held in two roles is dropped when either role is forgotten.

**Example:** the replicas Alice's tablet a3 holds; a3 hosts Alice-leisure and Alice-work, both members of the pod "Wedding", Alice-leisure a member of "Family" too and Alice-work no member of it.

| replica on a3 | held for |
|---|---|
| Wedding's membership store | Alice-leisure |
| Wedding's record store | Alice-leisure |
| Wedding's membership store, converging with Alice-leisure's copy inside the process | Alice-work |
| Wedding's record store, likewise | Alice-work |
| Family's membership store and record store | Alice-leisure alone |
| each identity's own PMS | Alice-leisure, Alice-work |
| An import for Alice-leisure, as Wedding's record store, of a ticket naming Family's record store is refused, nothing registered, and Family's record store is held and reconciled as before. | |

#### Scenario: Creating a pod allocates two dedicated replicas

- **WHEN** a hosted identity creates a pod
- **THEN** two fresh pdn-store replicas are created for that identity, both reached through the pod id, and no domain namespace id is allocated

#### Scenario: A store ticket naming a replica held in another role is refused

- **WHEN** a joining identity is handed a store ticket whose namespace it already holds as another pod's store
- **THEN** the join fails with no pod registered, and the other pod's store is still held and reconciled as before

#### Scenario: Two pods with the same members are four stores

- **WHEN** the same identities are members of two pods and a record is written into one of them
- **THEN** the record never appears in the other pod's stores

#### Scenario: Two members hosted on one node hold the pod twice

- **WHEN** identities B and D, hosted on one node, are both members of a pod, and B places a record with no other node reachable
- **THEN** the node holds each store twice, one replica per identity, D's replica comes to carry B's record, payload included, and the record's entry carries B's author, which resolves to B alone

#### Scenario: A record in the membership store is kept and used by nothing

- **WHEN** a device of a member produces, in the membership store, an entry under the record store's key layout
- **THEN** every member device holds it, no membership state or record view changes, and each lists it as an entry outside the layout

### Requirement: Every member device holds both stores whole and their write tickets

Every device of every member SHALL hold both stores whole — every record readable by every member — and SHALL hold the write ticket of each: a session between two member devices delivers every entry of either store with no egress filter, and what an entry counts for inside the pod is judged by the membership view and the record view per entry, never by ticket mode — a member's write ticket widens nothing they refuse. Member devices SHALL form each store's swarm, so a write reaches the other member devices through the content-free announcement and the pull it triggers, and a member device SHALL be able to catch up from any other member device, not only from an entry's author. A store's contacts SHALL be the devices the current members' statements list, each paired with the member it is dialed as, and the holding identity's own other devices by its PMS, dialed as that identity, derived afresh whenever the membership store changes, at each run of the store's periodic pass, and whenever the holding identity's PMS lists a device it did not — which each store then dials, as that identity, since a sibling whose first dial came before its listing reached this device was refused, and nothing else dials it again before the pass — and replacing the previous list whole — save while the replica's membership view lists no identity, holding nothing yet, when the contacts its ticket named stay — each peer of either store dialed as the member a derivation pairs it with; a contact naming this node's own address SHALL be reached inside the process, and a write SHALL announce to a co-located member's replica directly, as the in-process sessions spec states. Both stores' sync SHALL start with their contacts as they stand before either starts, since the membership store's first session derives them again, from a membership view that may list no device of the inviter yet while the statements' payloads are still on their way. A pull an announcement triggers SHALL address the member the announcement names when no derivation pairs its sender with a member and a contact of the store or its import already names that member, and SHALL otherwise address the member whose ticket the store was imported from: the name is the sender's word, so it picks only among the names this device gave, and a sender naming fresh identities opens no exchange for each. Any other peer no derivation pairs with a member SHALL be dialed as the member whose ticket the store was imported from, whatever the device shares of the store since.

**Example:** Alice places a claim in "Family" on her phone a1 while Bob's phone b1 is in the record store's swarm and Carol's phone c1 is offline; then a1 goes offline and c1 comes back.

| time | a1, Alice | b1, Bob | c1, Carol |
|---|---|---|---|
| 10:00 | places the claim and announces it on the store's topic, content-free | pulls the claim from a1 in a session | offline |
| 10:30 | offline | | back online: a session with b1 brings the claim, payload included |
| Every one of them holds both write tickets. | | | |

#### Scenario: A write reaches a member through another member

- **WHEN** member A writes an entry, A's devices go offline, and a device of member C — which never synced with A — reconciles with a device of member B that holds the entry
- **THEN** C's device receives the entry, payload included

#### Scenario: A write arrives live over the swarm

- **WHEN** a member writes an entry while devices of the other members are members of the record store's swarm
- **THEN** every such device converges on the entry through the announcement and a pull

#### Scenario: A newcomer writes with the tickets it was handed

- **WHEN** a newcomer joins, is handed both stores' write tickets, and its device writes a claim
- **THEN** every member's devices read the claim

#### Scenario: A write announced from a device no statement lists is pulled as its member

- **WHEN** a device of member B whose node no statement lists writes an entry, and a device of member A receives its announcement
- **THEN** A's device pulls the entry addressing B, and reads it

#### Scenario: A pull from a node no contact names is addressed as a member this device named

- **WHEN** a node no derivation pairs with a member announces a write to a member device, its announcement naming an identity no contact of the store names
- **THEN** the member device's pull addresses the member whose ticket the store was imported from, never the identity the announcement names

#### Scenario: A newcomer's record store reaches the inviter whatever the first membership session derives

- **WHEN** a newcomer imports both stores, and the membership store's first session derives contacts listing no device of the inviter before the record store's sync starts
- **THEN** the record store's sync starts with the inviter's device among its contacts, and the newcomer reads the inviter's claim

#### Scenario: A sibling refused before its listing arrived is dialed once it does

- **WHEN** a member's device takes both stores before its record in the member's PMS has reached the member's other device, which refuses its dials, and the record then arrives there
- **THEN** that other device dials the new one on both stores as the member, and the new device holds the pod

#### Scenario: A member's write ticket widens nothing

- **WHEN** a device of member C, no owner, holding the record store's write ticket, produces an entry at the key of B's claim and reconciles with a device of B
- **THEN** B's device holds it and reads nothing of it, and B's claim reads unchanged on every member device

### Requirement: A pod store's periodic pass reaches at most 5 peers every 5 minutes

The periodic reconcile pass SHALL reconcile each of a pod's stores at `SpawnOptions::pod_reconcile_interval`, 5 minutes by default, and each run SHALL open sessions for that store with at most 5 peers, drawn at random on every run from the store's contacts alone — the devices its membership view derives, or its ticket's while that view lists nobody. The store's sync SHALL start with its contacts alone when the store is created, imported or reopened, and minting the store's ticket — as a member's device does for every join it serves — SHALL dial no one, so a node the derivation leaves out, a former member's device or a member's device a converged tombstone is done with, is reached by no run, no such start and no join. Every other replica a node tracks SHALL keep `SpawnOptions::reconcile_interval` and every contact. Live delivery inside a pod rides the swarm's announcements and the pulls they trigger; the pass bounds how long an announcement gossip lost delays an entry.

**Example:** Bob's phone b1 holds 50 pods of 100 members on 2 devices each, and Bob's PMS, which his laptop b2 holds too.

| replica on b1 | one run reaches | runs per hour |
|---|---|---|
| each store of the 50 pods, 199 contacts each | at most 5 of them | 12 |
| Bob's PMS | b2, its one contact | 360 |

#### Scenario: A run over a pod store reaches at most 5 peers

- **WHEN** a device holds a pod's stores, each with more than 5 contacts, and a periodic pass runs over them
- **THEN** it opens sessions for each store with at most 5 peers

#### Scenario: A write whose announcement was lost arrives at the next run

- **WHEN** a device of member B misses the announcement of member A's write, and holds at most 5 contacts for the store
- **THEN** the next run of the pass over that store brings the write

#### Scenario: A run reaches no former member's device

- **WHEN** a member's device had sessions with a device of member C, C departs, and C's tombstone has converged
- **THEN** no later run of the member's device's pass dials C's device, and no run of C's tombstone dials the member's device

#### Scenario: A join served after a departure reaches no former member's device

- **WHEN** a member's device had sessions with a device of member C, C departs, and the member's device then mints its tickets to the pod's stores for a join it serves
- **THEN** the mint dials no one, C's device included

#### Scenario: A pod store keeps its own interval

- **WHEN** a device holds its identity's PMS and a pod's stores, and its reconcile interval is shorter than its pod reconcile interval
- **THEN** the pass reconciles the PMS once per reconcile interval and each pod store at most once per pod reconcile interval

### Requirement: Only member devices are served

A session for either of a pod's stores SHALL name the member whose replica it addresses and the member its caller acts as, and SHALL be served only when the member the caller names is a current member whose records list the caller's authenticated node id: that identity's own PMS where the caller names the identity the serving replica belongs to, as a sibling device of it; that member's device statements in the membership store where the caller names another member, over the network and inside the process alike. Every other caller SHALL be refused indistinguishably from the store not being hosted — a holder of its ticket included, and a caller naming an identity that is no member included, even from a node that hosts a member and so shares its node id — except that a session on the membership store naming a current member whose records do not list the caller SHALL be accepted, SHALL send the caller nothing and SHALL take from it that member's device statements alone, so a device whose siblings are gone before any member device took its statement reaches a member device by dialing it; such a caller learns that the store is hosted, which the holder of its ticket knows from the namespace id already. A dial from a replica whose membership view lists nobody yet, toward a callee it serves nothing, SHALL send that callee the replica's own identity's device statements and nothing else. A caller naming a member removed from the pod, or one that left it, SHALL be refused the record store from the first session set up after its departure event reaches the serving device, and served the membership store only as the requirement on a departed member's tombstone states; what it obtained while a member is retained. The announcements in a store's swarm are no session: each names the identity whose replica sends it ([reconciliation sessions](../reconciliation-sessions/spec.md)), so a ticket holder that is no member learns from them which members write, and nothing of what.

**Example:** callers ask Bob's phone b1 for a session on the record store of "Family", addressing Bob's replica; Alice's tablet a3 hosts Alice-leisure, a member, and Alice-work, no member, and Dave, no member, holds the store's ticket on his phone d1.

| caller | names | b1 |
|---|---|---|
| c1, Carol's phone | Carol | serves every entry |
| a3 | Alice-leisure | serves every entry, as Alice-leisure |
| a3 | Alice-work | refuses with `00 00 00 02 02 00`, the answer for a store b1 does not host |
| d1 | Dave | refuses with the same frame, the ticket notwithstanding |
| c1, once Carol's removed event has reached b1 | Carol | refuses with the same frame from the next session; what c1 took before stays readable on it |
| c2, Carol's laptop no statement lists yet, c1 gone | Carol | refuses with the same frame; on the membership store it sends nothing and takes Carol's statements alone, and serves c2 whole once one lists it |

#### Scenario: A member device is served whole

- **WHEN** a device of a current member requests a session for either store
- **THEN** the session is served and delivers every entry

#### Scenario: A ticket holder that is no member obtains nothing

- **WHEN** a caller holding a store's ticket but a device of no member requests a session
- **THEN** the request is refused with the answer an unhosted replica would produce, and no fingerprint, count or existence signal is revealed

#### Scenario: A co-located identity that is no member is refused

- **WHEN** a node hosts member B and identity E, no member, and a session from that node names E as its caller for either store
- **THEN** the session is refused as for an unhosted store, while a session from the same node naming B is served

#### Scenario: A device no statement lists reaches a member device with its statement

- **WHEN** a device of member C holds C's statement listing it, no other device holds that statement, and the device dials a member device on the membership store
- **THEN** the member device takes that statement and nothing else from it and sends it nothing, lists the device among C's, and serves it whole from the next session

#### Scenario: A removed member is refused from the next session

- **WHEN** a member is removed and the removed event has reached a serving device, and a device of the removed member then requests a session on the record store
- **THEN** the request is refused as for an unhosted replica, while the remaining members' devices are still served, and what the removed member's device obtained while a member is still readable on it

### Requirement: The membership store is reconciled before the record store

A session between two member devices SHALL reconcile the membership store to convergence, build its membership view, and only then reconcile the record store; both stores SHALL be reconciled whole, with no filter on either. The record store's session SHALL be served by the membership view built after the membership store's session, so that a newcomer whose joined event that session brings is served and a member whose departure it brings is refused; a session that would refuse its caller SHALL first wait, for a few seconds at most, for the payloads the caller's own chain and statements still lack, since a joined event counts only once its join statement has arrived. A record SHALL be held whatever it arrives ahead of, and SHALL read once the membership its entries name has arrived.

**Example:** Alice's laptop a2 holds neither Dave's joined event nor Dave's first claim, and sessions with Carol's phone c1, which holds both; `<dave>`: 64 lowercase hex chars of Dave's `PdnId`; `<id>`: the id `put_record` minted.

| step of the session | a2 |
|---|---|
| 1. the membership store reconciled to convergence | takes Dave's joined event, its join statement naming his phone d1 |
| 2. the membership view built | Dave a member at his sequence 1, writing on d1 |
| 3. the record store reconciled | takes `by/<dave>/claim/<id>/1` from d1's author, which the record view reads at Dave's sequence 1 at once |

#### Scenario: A newcomer's first record reads once the session brings its membership

- **WHEN** newcomer D's joined event and D's first claim are both unknown to a device of B, and B's device sessions with a device holding both
- **THEN** B's device reads D's claim at the end of that session

### Requirement: Entries outside the key layout are kept, used by nothing, and listed

An entry in either store whose key fits neither store's layout, or fits one only in part, SHALL be held like every entry a session carries from a member device, whoever its author, and reconciled and relayed like any entry. A key longer than the store's bound of 8,192 bytes is dropped before any layout is read ([reconciliation sessions](../reconciliation-sessions/spec.md)), so every record key the layouts define, a record's id included, has to fit under that bound. No membership view and no record view SHALL read it, nor load its payload into memory, and the store SHALL list such entries with their authors so the application can show them.

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

### Requirement: The record store's key names the member and the kind

A record SHALL sit under the name of the member that placed it, the key carrying the record's kind and the writer's membership sequence at the time of writing: `by/<pdnid>/claim/<id>/<mseq>` for a claim, `by/<pdnid>/immutable-document/<id>/<mseq>` for an immutable-document, `by/<pdnid>/mergeable-document/<id>/<op>` for each operation of a mergeable-document, `<op>` being one segment, `<writer>.<author>.<mseq>.<opseq>` — the writer's `PdnId`, its author key, its membership sequence and its own operation sequence — the author being the one that signs the entry and counting only among the writer's devices. The operation sequence SHALL count one author's operations on one mergeable-document from 1, the writing device taking the one above the highest its replica holds under its author. Every segment of either store's keys SHALL be text: a number decimal with no leading zeros, a `PdnId` or an author key 64 lowercase hexadecimal characters, a record id the 16 random bytes `put_record` mints as 32; the store orders keys byte by byte, so the membership view and the record view SHALL parse every number they order. `<pdnid>` SHALL be the member's identity, never a device. A record's identity SHALL be its key without its last segment, whatever its kind, and a record SHALL be addressed by the pod id beside that key, never by either store's namespace id, whose holder can join the store's swarm.

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
