# Design: cells

## Context

A cell is a space its members share: sharing a cell gives every member a complete live copy of its content, the relationship with one other person is a two-member cell, and a cell is expected to stay well under 100 members.

This design records the decisions taken for the platform side of cells and the questions left open. It works from the team's working note on cells and from the team's decisions on roles, record kinds and the cell's two stores.

## Goals / Non-Goals

**Goals:**

- A shared space for 0..n members.
- Everything a member writes reaches every member, from any member, with the author's authorship enforced on every honest device.
- Reuse: the swarm, the content-free topic, the ingest hook, the shape of the pairing dialogue that establishes a connection, multi-identity hosting with identity-scoped replicas and their in-process path, the directory as the carrier to a member's other devices.
- Every unanswered question written down, with its options.

**Non-Goals:**

- Signed claims and key rotation — the KERI roadmap; a join proves its `PdnId` through the key it derives from (D44).
- Identity-bound, revocable access — UWill.
- Content encryption — a separate layer; every member holds the plaintext by definition.
- Recall of delivered content — Invariant 2 governs acquisition, not retention.
- Chat — a later change of its own, on a sync shape of its own rather than the store's reconciliation.
- A name for a cell: the cell id is its one address, and a cell carries no name.
- Defence against a member's device contradicting its own member's history — acts under a point the member has lost, rewrites of its own entries, two events at one point: it rests on anchored signatures over the platform's key event logs (D34).
- The merge of a mergeable-document's operations into one document, their encoding and the editing UX: cells store, admit and reconcile the operations and hand them back with their writers (D17).
- Deleting or replacing a record: a record placed stays for every member (D14).
- Tuning for scale — a cached fingerprint tree, swarm parameters, payloads on demand, quotas: every payload replicates with its entry, the fork's defaults hold, and load tests measure them; the cell stores' pass takes the cadence D45 sets, whose numbers load tests revisit.
- Shedding a member entirely: a kick takes admission away, and what a kicked member keeps stays with it (D20, D28).
- A listed device's consent to its listing: a member's device statement names any node id the member's announcement key signs for, and member devices dial it (D7, D16).
- Versions of entries, of the fold or of the folded membership, and moving a cell from one build's rules to another's (D40).

## Decisions

### D1. A cell has no key pair — only an identifier

The cell id is a 16-byte identifier derived at creation from the creator's announcement key and a random nonce (D25). A cell signs nothing: no grant is issued by a cell, no claim is issued by a cell, and no dialogue proves "this is cell X". Every act inside a cell is a member's act — signed by that member's device author key, and, with KERI, by the member's identity. Consequence: there is nothing to steal and nothing to rotate — a cell's security is its members' security — and the KERI roadmap needs no group identifier and no multi-signature key set built from members' keys.

**Example:** who signs what in the cell "Family", which Alice created on her phone a1 and invited Bob into; Bob's phone is b1.

| act | signed by |
|---|---|
| the founding event | Alice's announcement key, in an entry by a1's author |
| Bob's joined event, written by Alice's invite act | a1's author; Bob's join statement inside it, signed by Bob's announcement key on b1 |
| Bob's claim | b1's author |
| Alice's kick of Bob | a1's author |
| the cell id `9cbcbe4da7cc35a44360d64e45621957` | nothing: 16 bytes derived from Alice's announcement key and a nonce, with no key pair behind them |

**Rejected alternatives:**

- The cell as an identity with its own key set — a multi-signature autonomic identifier.
  - **Pros:** a totally ordered membership log.
  - **Cons:** a group key to manage; a rotation on every membership change; a second identity kind in the KERI roadmap.

### D2. No connections "each with each"

Membership rests on the cell: a member joins on one member's invitation and sees everyone.

**Example:** Dave joins "Family" — Alice, Bob and Carol — from his phone d1 on Carol's invitation while every device of Alice and Bob is offline; Carol's phone is c1.

| step | what happens |
|---|---|
| Dave presents Carol's invite to c1 | c1 writes Dave's joined event; Dave holds a connection with nobody |
| d1's first session, with c1 | brings every record, Alice's and Bob's among them |
| Alice's phone a1 comes online and syncs with c1 | a1 lists Dave, and Alice did nothing |

**Rejected alternatives:**

- The cell as a fan-out of pairwise connections.
  - **Cons:** n×(n−1)/2 pairing ceremonies; adding a member is work for every existing member; no relay — content comes only from its author's devices, since a grantee never re-serves a third party.

### D3. One cell is two stores: the membership store and the record store

A cell is served by two stores, each a pdn-store namespace addressed through the cell id and held as a replica of its own by every member identity on each device that hosts it — a node hosting two members holds each store twice, and the two copies converge inside the process (ADR-0013). The **membership store** is the cell's authority: who is a member, with what role, on which devices. It holds, per member, one append-only sequence of **membership events** — joined (the join statement of D16, binding the member to its announcement key), left, kicked, promoted, demoted — each an immutable entry under its own key with the sequence number inside the signed bytes, and the member's device-list statements (D16), each version an immutable entry of its own. Honest devices overwrite and delete nothing in the membership store — what a member's own device does to its member's entries is D34 — a kick is an event, not a deletion, and the store holds no tombstones. The **record store** is what the authority governs: the records — claims, mergeable-documents and immutable-documents (D4). The fold reads the membership store into the membership every device serves sessions by and the record view reads records by, walking each member's events in sequence order: a join makes it a member and a plain one, a promotion an owner, a demotion a plain member again, a leave or a kick no member, a later join a plain member again — a member that joins again joins as a newcomer does (D11); a member's devices come from its join event and its device statements (D16), and an entry counts only when its author is among the devices of the member its key names (D43). By sequence, never by timestamp, so the order in which the events arrived does not matter; each event names its actor's sequence and is verified against the actor's chain at that point (D23). Membership state and role are events in one sequence, so that the flips a member goes through — promoted and demoted (D11), leaving and rejoining (D13) — order unambiguously against each other and, later, against records (D22), without trusting the timestamp the author sets (D13). A member's sequence is a small key event log of its membership state in the cell — the slot KERI fills. The two shapes — the act a device writes and the event a chain holds — are defined in the cell stores spec. Each store is the authorization unit (who may sync it), the swarm topic and the reconciliation unit, exactly the roles ADR-0009 keeps for a namespace, and ADR-0009's case against a shared namespace — a set that is never quiescent, and work spent on entries the filter discards — does not apply inside a cell, since every member wants every entry and nothing is discarded; the two stores share the audience — every member device — and differ in what they are: the membership store governs, the record store is governed, as the grants in a connection metadata store govern a data store. The price is a second store per cell — a topic, a ticket, and a replica with its reconcile pass for every member identity a device hosts — a fixed cost per cell, which load tests measure.

**Example:** the two stores of "Family" once Alice has created it on a1 and invited Bob, Bob has placed a claim from b1, and Alice has promoted him; `<alice>`, `<bob>`: 64 lowercase hex chars of each `PdnId`; `<id>`: the id `put_record` minted; a membership key ends in the actor and the actor's sequence, and `…` stands for the founding event's.

```
membership store
member/<alice>/1/founded/<alice>/0    Alice's founding event: Alice a member and an owner
member/<alice>/devices/1              Alice's device statement, version 1: a1
member/<bob>/1/joined/<alice>/1       Alice's invite act at her sequence 1, Bob's join statement inside: Bob a plain member
member/<bob>/devices/1                Bob's device statement, version 1: b1
member/<bob>/2/promoted/<alice>/1     Alice's promotion of Bob at her sequence 1: Bob an owner
record store
by/<bob>/claim/<id>/1                 Bob's claim, written at his sequence 1

every member device folds the same, whatever order the entries arrived in: Alice an owner, Bob an owner
```

**Rejected alternatives:**

- One store for all of an identity's cells.
  - **Cons:** a store is the authorization unit, the swarm topic and the reconciliation unit (ADR-0009), and cells differ in all three.
- One store, the membership material under a key prefix reconciled first.
  - **Cons:** the store orders entries by namespace, author, key, so a key prefix is a filter across every author's partition, not a range — reconciling it is subset-rbsr, whose fingerprint (`SessionStore::get_fingerprint`) walks every entry per round, on every session, before any record is judged; a cached fingerprint tree does not help a prefix.
- One role log for the whole cell under a single sequence.
  - **Pros:** orders events across members.
  - **Cons:** neither the record view (D22) nor the membership fold (D23) needs that order; two events at one number resolve by precedence (D38).
- Membership state and role as last-writer-wins values.
  - **Cons:** a flip's order against another flip, or against a record, would rest on the timestamp the author sets (D13).

### D4. A record is a claim, a mergeable-document or an immutable-document

A **record** is what a member places into a cell, of one of three kinds chosen when it is placed. A **claim** is an assertion by an issuer about a subject — a driver's license, a parent's statement of a child's blood type. A **mergeable-document** is content the members edit — a note. An **immutable-document** is content placed once — a file. Every member reads every record: inside a cell there is no narrower audience, and "share with Carol and Dave but not Bob" is a different cell (D9). A claim and an immutable-document differ in what the record is — an assertion or content — and an immutable-document and a mergeable-document in mutability (D17); no two kinds differ in payload format: payloads stay opaque below pdn-layer, and a record's kind picks how its entries are laid out and who writes them, not what they contain. Membership events and device statements are the cell's bookkeeping, not records in this sense.

**Example:** three records in "Family", one of each kind; `<alice>`, `<bob>`: 64 lowercase hex chars of each `PdnId`; `<id>`: the id `put_record` minted; `<op>`: the writer's `PdnId`, its author key, membership sequence and operation sequence.

| record | kind | written by | its entries |
|---|---|---|---|
| Alice's statement of her son Tom's blood type | claim | Alice's devices, once | `by/<alice>/claim/<id>/1` |
| the shopping list Alice started | mergeable-document | any member's device, one entry per operation | `by/<alice>/mergeable-document/<id>/<op>`, one per operation |
| Bob's scan of the lease, a PDF | immutable-document | Bob's devices, once | `by/<bob>/immutable-document/<id>/1` |
| Every member reads all three, and below pdn-layer each payload is opaque bytes, whatever the kind. | | | |

**Rejected alternatives:**

- One kind for the claim and the immutable-document, which share a shape on the platform (D17).
  - **Cons:** the two are expected to diverge as the product's UX is tested and its requirements redefined; one kind would then be split under content already placed.

### D5. Claims are immutable and written only by their issuer

A claim does not change after it is written — a changed assertion is a new claim. A claim placed in a cell is written only by its issuer.

**Example:** acts on Alice's claim of Tom's blood type, `by/<alice>/claim/<id>/1`; `<alice>`: 64 lowercase hex chars of Alice's `PdnId`; `<id>`: the id `put_record` minted; a1 and a2 are Alice's phone and laptop, b1 Bob's phone.

| act | outcome |
|---|---|
| Alice places the claim on a1 | every member reads it |
| Alice addresses a write at it on a2 | refused on a2 with a typed error; her corrected assertion is a new claim at a new id |
| a modified b1 writes an entry at the claim's key | held on every honest member device and read by none; Alice's claim reads unchanged |

### D6. Every member edits a mergeable-document

A mergeable-document is edited by every member — each operation is an entry signed by the device that wrote it, so who edited what is read from the entries themselves (D15) — and a claim or an immutable-document by no one (D5, D17). There is no sharing mode per record: no record is "shared read-only" or "shared read-write", and no act flips such a mode; and ownership (D11) changes nothing about editing — it changes the acts on membership. What takes editing away is a leave or a kick: an operation is read against the writer's membership state at the membership sequence the operation names (D22), so a member's operations from while it was a member stand on every device whenever they arrive, and an operation naming a sequence at which the writer was no member is held and read by none. The rights by role, one table per record kind, are in the pdn-node cells spec.

**Example:** operations on the shopping list under Alice's name; Bob and Carol are plain members, on b1 and c1, and Alice kicks Carol at Carol's sequence 2.

| operation | its `<op>` names | on every member device |
|---|---|---|
| Bob adds "milk" | Bob, b1's author, Bob's sequence 1, b1's operation 1 | read as Bob's |
| Carol adds "eggs" before the kick | Carol, c1's author, Carol's sequence 1, c1's operation 1 | read as Carol's, on a device that catches up after the kick too |
| Carol adds "cake" naming her sequence 2 | Carol, c1's author, Carol's sequence 2, c1's operation 2 | held and read by none: at her sequence 2 Carol is no member |

**Rejected alternatives:**

- A sharing mode per record — read-only or read-write — flipped over its life.
  - **Cons:** needs an encoding that survives the flip and a rule for who flips; a second access structure beside the roles.
- Editing another member's mergeable-document reserved to owners.
  - **Cons:** two plain members cannot write one note together; the per-operation signature already keeps every edit under its writer's name; a spoiled mergeable-document is repaired by further operations.

### D7. Inside a cell, gossip replaces subset-rbsr

No egress filter: both stores are served whole to member devices, the membership store before the record store (D19); the members' devices are the swarm; a write becomes a content-free announcement that neighbours pull through reconciliation and pass on; catch-up after an outage is one session with any neighbour. A store's contacts are the devices the current members' statements list (D16), each dialed as the member it belongs to, and the holding identity's own other devices, dialed as that identity (D32), derived afresh whenever the membership store changes and at each run of the store's pass (D45) — a departed member's devices drop out — save while the replica holds nothing, when its ticket's contacts stay, and each peer of either store dialed as the member that derivation pairs it with; a contact naming this node's own address is reached inside the process, and a write announces to a co-located member's replica directly, since a node's own gossip broadcast never reaches its other subscribers — so two members hosted on one node reach each other as members on two nodes do. With 100 members on 2 devices each — 200 nodes — an announcement reaches everyone in 3–4 hops of HyParView's active view, and catch-up costs one reconciliation of the difference. Subset-rbsr keeps its place for connections and personal namespaces.

**Example:** the contacts of Alice-leisure's replica of the record store of "Wedding" on Alice's tablet a3, which hosts both of Alice's identities, Alice-leisure and Alice-work, both members of "Wedding"; Erin's devices are e1 and e2, Bob's b1, Alice-leisure's a1 and a3, Alice-work's a3 alone.

| contact | dialed as | reached |
|---|---|---|
| e1, e2 | Erin | over the network |
| b1 | Bob | over the network |
| a1 | Alice-leisure, the replica's own identity | over the network |
| a3 | Alice-work | inside the process: Alice-work's replica on this node |
| Alice-leisure places a claim on a3: the content-free announcement goes out on the store's topic to the swarm, and a3 announces it to Alice-work's replica directly, since its own broadcast never reaches Alice-work's subscription on a3. | | |

**Rejected alternatives:**

- A replica per member inside the cell, the cell as the grant audience — "share without copying".
  - **Pros:** data stays with its issuer; grants stay per claim.
  - **Cons:** every member's content is a replica the reader reaches separately; grantees stay outside the swarm, so a live update needs a grant republish per item; a stream grows the grant record with every message.

### D9. Several cells with the same members are ordinary

The member set does not identify a cell.

**Example:** Alice and Bob share two cells, "Household" and "Taxes", and Bob places his lease scan in "Taxes".

| cell | its stores | the lease scan |
|---|---|---|
| Household: Alice, Bob | a membership store and a record store | absent |
| Taxes: Alice, Bob | a membership store and a record store of its own | present |

### D10. The platform knows no ontology

Below pdn-layer a cell entry is a key and opaque bytes. The platform reads from the key what it enforces: the cell, the member under whose name the record sits and the record's kind. What a payload says and what the application derives from it are the application's. This is the existing layering — the data layer treats tokens and payloads as opaque, the domain lives in pdn-layer — applied to cells.

**Example:** one entry of "Family" and who reads what in it; `<alice>`: 64 lowercase hex chars of Alice's `PdnId`; `<id>`: the id `put_record` minted.

```
key:       by/<alice>/claim/<id>/1
payload:   the application's bytes for "Tom's blood type is A+"
platform:  the member Alice, the kind claim, the membership sequence 1, the entry's author
above it:  what the bytes say about Tom, and whatever the application derives from it
```

### D11. A cell has owners

The creator is the cell's first owner — its founding event (D23). An owner promotes any member to owner, and an owner is demoted only by another owner — no other act takes ownership from a member that stays one. An owner kicks any other member out of the cell — an owner or a plain member alike: a member that is no owner kicks nobody, so an owner is kicked only by another owner. The invite act, a kick and a demotion always have a subject other than their actor, on the writing device and in the fold alike (D23). Inviting stays every member's act — a newcomer always joins as a plain member, and only an owner's promotion makes it an owner — and leaving stays the member's own (D13), except that the one owner of a cell with other members leaves only once another member is an owner: its leave is refused on the writing device with a typed error until it promotes one, while the one member of a cell leaves as any member does. The refusal runs on the writing device, so the last two owners leaving at once, disconnected from each other, each still see the other and both leave: the cell then stays without an owner — its members read and edit, nobody kicks a member or promotes one — and a new cell is the way out. The last owner losing every device leaves the same state: no event is written, the owner stays listed and nobody acts as one, until recovery through the identity arrives with KERI, and for good where a KERI backup is lost too; the application encourages every shared cell to keep at least two owners. A member that joins again is a plain member until an owner promotes it anew, whatever role it held before. Ownership is a role inside membership: an owner is a member, and losing ownership does not touch membership. Editing is every member's (D6), and no role deletes a record (D14). Members become owners and stop being owners repeatedly over a cell's life — an operating condition, not an edge case. The owner set lives in the membership store as promoted and demoted events in each member's sequence (D3, D21).

**Example:** roles in "Family" over its first year.

| step | act | Alice | Bob | Carol |
|---|---|---|---|---|
| 1 | Alice creates the cell | owner | — | — |
| 2 | Alice invites Bob; Bob invites Carol | owner | member | member |
| 3 | Alice promotes Bob | owner | owner | member |
| 4 | Bob demotes Alice | member | owner | member |
| 5 | Bob kicks Carol | member | owner | — |
| 6 | Alice invites Carol again | member | owner | member |
| After step 4 Alice kicks and demotes nobody, and Bob, the one owner, can neither demote nor kick himself. | | | | |

**Example:** leaves by the last owners of "Family", where Bob is a plain member.

| leaves | on every member device afterwards |
|---|---|
| Alice, the one owner, leaves | refused on her phone with a typed error; she promotes Bob, and then her leave is written |
| Alice and Carol, the two owners, leave the same evening, their phones disconnected from each other | both leaves stand and the cell has no owner: Bob reads and edits, and his kick of anyone or promotion of himself is refused; a new cell is the way out |
| Alice, the one owner, loses her phone a1 and her laptop a2 in one fire | Alice stays listed as the one owner, and nobody acts as one |

**Rejected alternatives:**

- Equal-rank membership, no roles.
  - **Cons:** no repair channel — membership states nobody may fix (D14).
- The last owner's leave allowed, a member becoming an owner by rule.
  - **Cons:** ownership appears without an owner's promotion; and every member joins at its own sequence 1, so the rule needs an order among members that no event gives — the lowest `PdnId`, say, which means nothing.
- The last two owners' concurrent leaves each completing only once another owner's device has acknowledged it.
  - **Cons:** the two leaves wait on each other, and an owner whose devices never come online again blocks the other's leave for good.
- An owner silent past a bound losing the role to the longest-standing member.
  - **Cons:** silence is measured by time, which the fold never reads (D23), so each device would judge the bound by its own clock and devices would disagree on when.
- A member becoming an owner by rule when concurrent leaves empty the owner set.
  - **Cons:** ownership appears without an owner's promotion, and the rule needs an order among members that no event gives.
- An invite, a kick or a demotion of oneself.
  - **Cons:** an invite of oneself readmits a departed member with no current member's act; a kick of oneself is a leave that bypasses the refusal the last owner's leave meets and keeps both stores on the member's devices; a demotion of oneself lets the last owner empty the owner set (D14).

### D13. Acting on a record does not depend on its member's membership state

The rights to act on a record are the same whether the member that placed it in the cell is a current member or a departed one — one that left or was kicked. Leaving and a kick change access alone — the record store refused, the membership store served up to the departure (D36), entries naming a sequence at which the member was no longer a member read by none (D22) — and change nothing about what is in the cell or what members may do to it: the member's own records stay, its operations on other members' mergeable-documents stay, no power over a member's records appears at its departure, and none disappears — the members edit a departed member's mergeable-documents as they do a current member's. A member that joins again writes again — new records, new operations, naming its new sequence — as any member, and its earlier records, naming its earlier sequence, resolve to it as they always did (D22). Members leave, rejoin and are kicked over a cell's life, and the rules for its records read the same throughout.

**Example:** Carol's records in "Family" as her membership changes; Bob is a plain member.

| Carol | Bob edits her note | her claim from her sequence 1 |
|---|---|---|
| a member, from her sequence 1 | read | read as Carol's |
| left, at her sequence 2 | read | read as Carol's |
| invited again, at her sequence 3 | read | read as Carol's; her new records name her sequence 3 |

### D14. Every reachable membership state is repairable by owners

No sequence of acts — joins, leaves, kicks, promotions, demotions — leaves the cell's membership in a state its owners cannot repair from inside, and a mergeable-document spoiled by edits is repaired by further edits. Recreating the cell — a new store, re-invited members, re-uploaded content — is never the only way out of a membership state. A record placed stays: no member and no owner deletes or replaces one, so a claim or an immutable-document placed by mistake, a member's junk and a departed member's records stay for every member for as long as the cell lives. The converse holds too: no operation deletes a cell for every member, owners included — a cell ends by its members leaving, each forgetting its own copy of the records and keeping the membership store as the cell's tombstone (D36), and a device that holds the record store keeps it anyway (Invariant 2). The cell after its last leave — every member's chain ending in a left or kicked event — needs no form of its own: every former member's devices hold the tombstone, and no record store is left to observe. Every rule in this design is measured against this invariant; two edges strand it, both of which D11 accepts: the last two owners leaving at once, and the last owner losing every device.

**Example:** states "Family" reaches and how its owner Alice repairs each from inside; Bob and Carol are plain members.

| state | repair |
|---|---|
| Bob filled the shopping list with junk operations | any member appends operations that take the junk out |
| Carol, kicked, left claims nobody wants | none: a record placed stays |
| Bob was promoted by mistake | Alice demotes him |
| Alice, the one owner, loses every device | none: nobody acts as an owner, an edge D11 accepts |

### D15. Authorship is forged by no one

A record's authorship is cryptographic — the author signature on its entries — and no role weakens it: a member edits another member's mergeable-document and an owner kicks another member, and each such entry carries its actor's own signature, so a mergeable-document's history reads who wrote what, and every act in a cell reads as the signed act of its actor. Where a record sits — the member under whose name it is placed — and who wrote each entry in it are two different things, and only the second is a statement about authorship. Which authors write for a member stays what the member publishes (D16), each hosted identity writes with its own author (ADR-0013), and every entry names in its key the member it is written as, its author counting only among that member's devices (D43); signed claims per the KERI roadmap strengthen the same property.

**Example:** entries in "Wedding" written from Alice's tablet a3, which hosts Alice-leisure and Alice-work, both members, and from Erin's phone e1, Erin being the cell's owner.

| entry | under whose name | its author | reads as |
|---|---|---|---|
| an operation adding a table to the seating plan | Erin | a3's author for Alice-leisure | Alice-leisure's edit |
| an operation moving that table | Erin | a3's author for Alice-work | Alice-work's edit |
| the kicked event in Alice-work's chain | Alice-work | e1's author | Erin's kick, as an owner |

### D16. A member's devices are announced by the member itself, under its announcement key

Each identity holds a device-announcement key pair, minted with the identity, and its `PdnId` derives from the pair's public key (D44). The secret lives in its private metadata store at a fixed path and reaches every new device at linking, beside the store tickets; the cell's own write tickets sit there under per-cell kinds, beside the records of each cell that the identity's joining writes and its leave tombstones, keyed by the identity's membership sequence (D35). The identity's other devices open on demand every cell whose record is live, and a restarted runtime re-derives its hosted cells from the same records, as it re-derives connections from theirs (private metadata store spec). The cell holds two things about a member's devices: a join statement binding the member's `PdnId` to its announcement public key — signed by the announcement secret on the joining device, carried in the join dialogue, written by the inviter in its invite act (D44), and for the creator the founding event (D25) — and the member's device-list statements: each of the member's devices with its node id and the author the member writes with on it — one author per hosted identity on a device (ADR-0013), so a node hosting two members appears under one node id with two authors — a version counter inside the signed bytes, the whole statement signed by the announcement key over the prefix `pdn/cell-devices/v1` followed by the statement, the prefix keeping it apart from the founding event and the join statement the same key signs (D25, D44).

A statement is self-contained proof, so who writes it into the store does not matter: the fold counts an entry in the membership device area by the embedded signature against the announcement key from the join statement, once its payload has arrived (D41), never by the entry's author. A freshly linked device therefore registers itself — it holds the write ticket and the announcement secret, writes the next version, the member's device list with itself added, into its local replica of every cell the identity is a member of, and ordinary sync spreads it through the identity's own devices, which serve the new device by the identity's own directory before any statement lists it (D32), and from them through any member, with no waiting on another member being online. Before syncing a cell replica, each of the identity's devices checks that the member's device list names it with the author its identity writes with there, and when it does not, writes the next version: that list with itself added. The sweep heals an interrupted fan-out, a cell joined after a linking and a device linked before the join; only the device itself knows the author it writes with, so only it puts itself back (D32).

Resolution never reads an entry timestamp: statements coexist, one key per version (D21), and the member's device list is the union of every validly signed statement a device holds, whatever its version — two siblings that each link a device while out of reach of each other both write the next version, under two authors, and both new devices are listed, and a device that a later version, written from a view that missed it, leaves out stays listed by the version that named it. The version orders the member's statements, the shape KERI's key event log takes over. The fold and the record view check an entry's author against the list of the member its key names (D43). The union names no device the announcement key did not sign, and it follows from the statements alone, whatever order they arrived in and whoever wrote them. A device writes only a version above the highest its replica holds. A second statement at one version from the same author replaces the first, the store keeping one entry per author at a key; an honest device never writes one, so it is the member's own contradiction, which D34 takes on its word. The list only grows, so taking a device off it takes a new announcement key, the rotation KERI brings. A statement that never left a dying device dies with the device it described; the converged list is the surviving devices' own. The announcement key with its versioned statements is the slot KERI's key event log fills later: KERI replaces the key, not the scheme.

**Example:** Bob links his laptop b2 while Alice's devices and Carol's phone c1 are offline; `<bob>`: 64 lowercase hex chars of Bob's `PdnId`.

| step | b1, Bob's phone | b2, just linked into Bob | c1, Carol's phone |
|---|---|---|---|
| 1 | holds `member/<bob>/devices/1`: b1 | receives Bob's directory: the announcement key pair, Family's two tickets | offline |
| 2 | | opens "Family" and writes `member/<bob>/devices/2`: b1 and b2, signed by Bob's announcement key over `pdn/cell-devices/v1` and the statement | |
| 3 | serves b2 by Bob's directory, before any statement lists b2, and takes version 2 | | |
| 4 | | | comes online and syncs with b1: counts version 2 on its embedded signature, though b2's author wrote it, and serves b2 from then on |

**Example:** Bob's phone b1 and laptop b2 hold version 2, listing both, and lose touch with each other while each links a device; `<bob>`: 64 lowercase hex chars of Bob's `PdnId`.

| step | writes | a member device holding every statement so far resolves Bob's devices to |
|---|---|---|
| b3, linked through b1 | `member/<bob>/devices/3`: b1, b2, b3 | b1, b2, b3 |
| b4, linked through b2 | `member/<bob>/devices/3`: b1, b2, b4, under another author | b1, b2, b3, b4: the union of both version-3 statements |
| b5, linked through b1 before b1 sees b4's statement | `member/<bob>/devices/4`: b1, b2, b3, b5 | all five: b4 stays listed by its version 3 |
| b4's first sweep after version 4 reaches it | nothing: a statement names it already | all five |

**Rejected alternatives:**

- The union of the statements at the highest version alone.
  - **Cons:** a version written from a view that missed a device leaves it out until its own sweep, and a device that never syncs again — a phone lost the day after its linking — loses its member's own entries on every device that folds after that version.
- A tie-break among the statements at one version — the lowest author key, or the lowest hash of the signed bytes.
  - **Cons:** deterministic and meaningless, the luck of the key, and it leaves out a device the member linked until that device's own sweep runs, which needs it online.
- The first statement a device sees at a version.
  - **Cons:** devices that received the two in different orders keep different lists for good, and the verdict stops following from the statements alone (D23).
- A statement per device, with no version.
  - **Pros:** no two statements ever conflict.
  - **Cons:** the list stops being a sequence of versions, the shape KERI's key event log takes over.
- The newest statement kept in the identity's directory as the sweep's reference.
  - **Cons:** the directory holds no such copy, and a copy written from one sibling's view carries the device it missed out of every cell.
- A per-identity metadata store polled by acquaintances.
  - **Cons:** a replica tracked per acquaintance restores the topology D2 rejects and the per-store reconcile cost ADR-0009 counts; read tickets, once handed out, leak the device list to kicked members forever.
- A private-store contact book as the fold's authority.
  - **Cons:** a binding asserted in one cell would judge entries in another, carrying the inviter's word beyond the cell it was spoken in.
- Announcements handed to a live member device.
  - **Cons:** in a two-member cell the other member sleeps for weeks, and a waiting announcement survives nowhere.
- The announcement key pair minted lazily, when the identity first creates or joins a cell.
  - **Cons:** two devices of the identity doing so while disconnected mint two key pairs, and the identity's cells then disagree on which key signs its device statements; at identity creation there is one device, so there is no race.

### D17. A mergeable-document keeps concurrent edits; an immutable-document is placed once

A mergeable-document is content whose concurrent edits are meant to be kept — a markdown note, a rich text as a JSON tree of text nodes: every edit is an operation, each operation an immutable entry under its own key signed by its writer. Cells hold, reconcile, relay and read the operations and hand them back with their writers; the merge that makes them one document, the operation encoding and the editing UX sit above the data layer, and cells compute no document state. An immutable-document is content placed once — a PDF file uploaded into the cell: one entry under one key, written by the member under whose name it sits and updated afterwards by no one, that member included; a changed file is a new record. On the platform an immutable-document has the shape of a claim (D5) — placed once and never changed — and differs from it in what it is to the product: content rather than an assertion (D4). Below pdn-layer a record's kind decides the key layout — one key for a claim or an immutable-document, one key per operation for a mergeable-document — and the rule the record view reads it by: a claim or an immutable-document from the member under whose name it sits, a mergeable-document's operation from any member (D6); the merge algorithm and the payload encoding live above (D10).

**Example:** Bob and Carol, disconnected from each other on b1 and c1, act on two records; Alice is an owner, on a1.

| act | outcome on every member device |
|---|---|
| Bob adds "milk" to the shopping list, Carol "eggs" | two entries under two keys, one naming b1's author, the other c1's; both held, and `read_ops` returns both with their writers |
| Bob writes his lease scan again | refused on b1 with a typed error; a changed file is a new record |
| a1 writes at the lease scan's key | held on every member device, a1 included, and read on none |

**Rejected alternatives:**

- A record kind overwritten in place by the last writer.
  - **Cons:** loses one of two concurrent edits; an owner's overwrite leaves the member's name on the owner's content.

### D19. The membership store is reconciled before the record store, and no filter runs inside a cell

A session between two member devices reconciles the membership store to convergence first, folds it, and only then reconciles the record store; both by plain, unfiltered reconciliation — no capability filter (subset-rbsr) runs on either store between member devices, and none on the record store for any peer. The one narrowed session is a former member's, on the membership store alone: it takes and keeps the departure's past — the departure event and every entry it depends on — and nothing written after it, while the record store is refused to it as a store not hosted (D32, D36). Two members hosted on one node reconcile inside the process in the same order: an announced write, a dialed contact and the periodic pass each reconcile the membership store before the record store, and the pass opens both when either store of either identity has moved. The order serves the record store's session by the membership the same pair of sessions brings: a newcomer whose joined event reaches the serving device in the membership store's session is served the record store in the session after it, and a member whose departure that session brings is refused the record store at once (D32). What the record store holds does not depend on the order: it holds every entry a member device's session carries (D42), and the record view reads each by the membership folded over everything the device holds, so a record that reaches a device ahead of the membership event authorizing its author reads once that event arrives.

**Example:** Carol's phone c1 holds neither Dave's joined event nor Dave's first claim, and sessions with Bob's phone b1, which holds both; `<bob>`, `<dave>`: 64 lowercase hex chars of each `PdnId`; `<id>`: the id `put_record` minted; Dave joined on Bob's invitation, and `…` is Bob's sequence.

| step of the session | c1 |
|---|---|
| 1. the membership store reconciled to convergence | takes `member/<dave>/1/joined/<bob>/…` and, after it, `member/<dave>/devices/1`, listing d1 |
| 2. the membership folded | Dave a member at his sequence 1, writing on d1 |
| 3. the record store reconciled | takes `by/<dave>/claim/<id>/1` from d1's author, which the record view reads at Dave's sequence 1 at once |

**Rejected alternatives:**

- No order between the stores.
  - **Cons:** a record store's session served by stale membership refuses a newcomer until a later session brings its joined event, and serves a departed member once more.
- A capability filter on the record store per session peer.
  - **Cons:** the audience is every member device, so the filter removes nothing and costs the linear fingerprint (D3).

### D20. Every member device holds the write ticket of both stores

Every member device holds both stores whole and holds their write tickets; what an entry counts for inside a cell is the fold's and the record view's, judged per entry (D6, D17, D42), never the ticket's mode. Any member edits other members' mergeable-documents (D6), and every member relays what it holds (D7). A kicked member keeps the write tickets it held: honest devices refuse it the record store, serve it the membership store only up to its kick (D36), and read none of the entries it authors under a sequence at which it was no longer a member (D13, D22), which is the whole of a kick under bearer tickets — an entry it authors afterwards under an earlier sequence, a membership act among them, counts (D34).

**Example:** what the write tickets decide in "Family", where Alice is an owner, Bob a plain member, and Carol was kicked at her sequence 2; each holds both write tickets.

| | Alice | Bob | Carol |
|---|---|---|---|
| both write tickets | held | held | held still |
| sessions with member devices | served | served | the record store refused from the first session after the kick reaches the serving device, the membership store served up to the kick (D36) |
| an operation on the shopping list | read | read | held and read by none when it names her sequence 2; read when, written after the kick, it names her sequence 1 (D34) |

**Rejected alternatives:**

- A read-only ticket for plain members.
  - **Cons:** editing other members' mergeable-documents and relaying what one holds are every member's, and a read-only ticket allows neither.
- A ticket per role.
  - **Cons:** re-cut at every role change (D11).

### D21. The key layout of both stores

The membership store: `member/<pdnid>/<seq>/<kind>/<actor>/<aseq>` — the member's membership events (D3): founded, joined, left, kicked, promoted, demoted, with `<actor>` the actor's `PdnId` and `<aseq>` its own sequence at the time (D23, D43), so the fold reads the kind, the actor and the actor's point from the key as the record view reads a record's from its key; `member/<pdnid>/devices/<version>` — the device-list statements (D16), one key per version, resolved by the union of every validly signed statement, whatever its version. Events at one sequence of one subject all stand, whoever wrote them, and resolve by precedence (D38). The membership store holds no tombstones. The record store: `by/<pdnid>/claim/<id>/<mseq>` — a claim; `by/<pdnid>/immutable-document/<id>/<mseq>` — an immutable-document, one entry; `by/<pdnid>/mergeable-document/<id>/<op>` — one entry per operation of a mergeable-document, where `<op>` is one segment, `<writer>.<author>.<mseq>.<opseq>`: the writer's `PdnId`, its author key, its membership sequence and its own operation sequence (D43), so two writers' operations never share a key and one writer's never collide. `<mseq>` is the sequence of the writer's own membership events at the time of writing — the state the entry is judged against (D22). Every segment is text: a number is decimal with no leading zeros, a `PdnId` or an author key is 64 lowercase hexadecimal characters, and a record id — 16 random bytes `put_record` mints — is 32, the size of the cell id. The founding event's `<aseq>` is `0`, the creator holding no point of its chain before its first event. An operation sequence counts one author's operations on one mergeable-document from 1, the writing device taking the one above the highest its replica holds under its author, so a restart continues the count. The store orders keys byte by byte, and `10` sorts before `9`, so the fold and the record view parse every number they order. A record's identity is its key without its last segment, whatever its kind, and a record is addressed by the cell id and that key — member, kind and id — never by a store's namespace id, which is the read capability (Invariant 3). `<pdnid>` is the member under whose name the record sits — the identity, not a device, so the key outlives the devices that write under it. The record view reads from the key what it enforces (D10): the member, the record's kind and, for an operation, its writer; it reads from the entry only its author, which counts only among the devices of the member the key names (D43). Everything else — a record's title, a link to another record — is payload. An entry whose key fits neither layout, or fits one only in part, is kept and used by nothing (D27).

**Example:** keys in the two stores of "Family" and what the fold and the record view read from each; `<alice>`, `<bob>`, `<carol>`: 64 lowercase hex chars of each `PdnId`; `<id>`: 32 lowercase hex chars of the id `put_record` minted; `<b2-author>`: 64 lowercase hex chars of the author Bob writes with on his laptop b2.

```
membership store
member/<alice>/1/founded/<alice>/0                          Alice's founding event: her sequence 1, no point of her chain before it
member/<carol>/1/joined/<bob>/2                             Carol's sequence 1, joined by Bob at his sequence 2, from b1, one of Bob's devices
member/<carol>/devices/1                                    Carol's device statement, version 1
record store
by/<carol>/claim/<id>/1                                     a claim under Carol's name, written at her sequence 1
by/<carol>/immutable-document/<id>/1                        an immutable-document, its one entry
by/<carol>/mergeable-document/<id>/<bob>.<b2-author>.2.7    one operation: Bob, b2's author, Bob's sequence 2, that author's operation 7
ext/anything                                                fits neither layout: kept, used by nothing (D27)
```

**Rejected alternatives:**

- The writer's author key as the key prefix.
  - **Cons:** devices come and go while the member stays — a record keyed by a device moves with every linking; the author-to-member map already bridges the two.
- `<op>` as four segments.
  - **Cons:** a record's identity becomes its key without its last four segments for a mergeable-document and without its last one otherwise, so the cut depends on the kind.
- Numbers as fixed-width big-endian hex, 16 characters for a 64-bit number.
  - **Pros:** keys sort in number order under the store's byte order.
  - **Cons:** the fold reads a member's chain whole and needs no such order; every key holding a number grows, and no key reads as the examples print it.

### D22. A record names the membership state it was authored under, and is judged against it

Every content entry in the record store names, in its key (D21), the sequence of its writer's own membership events at the time of writing. The record view reads the entry against the writer's event log folded up to that sequence: a claim or an immutable-document reads if the writer was a member at that sequence, a mergeable-document's operation likewise, and an entry naming a sequence the device does not yet hold reads once the events arrive (D42). The question the record view asks is "was this allowed at that point", never "is it allowed now", so an entry is judged the same on every device whenever it arrives: a departed member's entries from while it was a member reach a device that catches up after the departure, and a member's entries resolve to it across leaving and rejoining (D13). Sessions stay as of the session — a departed member's devices are refused (D20).

The reference proves that the entry is after the named event, not that it is before the next one: a departed member can author a new entry naming a sequence at which it was a member and have a member relay it, and the record view reads it — the retrograde direction of anchored signatures, which D34 leaves open. Judging every entry the same on every device is taken at that price.

**Example:** entries Carol wrote reach Alice's laptop a2, linked after all of them were written; Carol joined at her sequence 1, left at 2, and was invited again at 3.

| Carol's entry | names | Carol there | on a2 |
|---|---|---|---|
| a claim, written while a member | 1 | a member | read |
| an operation on the shopping list, written after the leave by a modified c1 | 1 | a member | read: the reference proves after, not before (D34) |
| an operation written after the leave by a modified c1, naming her sequence 2 | 2 | no member | held and read by none |
| a claim, written after she joined again | 3 | a member | read, and resolved to Carol like her claim at 1 |

**Rejected alternatives:**

- Judging a record as of the session.
  - **Pros:** keeps a departed member's new writes out.
  - **Cons:** its old ones stop reading on every device at its departure.
- The membership reference in the payload.
  - **Cons:** the payload is the application's opaque bytes (D10), and a record's reference would wait for its payload before the record view could place it.

### D23. A membership event names its actor's sequence, and the store verifies from the founding event

Every membership event names, in its key (D21), the sequence of its actor's own events at the time of acting, and counts as the actor's chain folded up to that point allows: a joined event needs the actor a member other than its subject, a promoted event an owner, a kicked or demoted event an owner other than its subject, a left event the subject itself; the founding event — the creator's first, self-authored, making the creator a member and an owner at once (D11) — needs only to derive the cell id (D25) and is the root every verification ends at. The writing device picks both numbers from what it holds, reading each chain only as far as the first sequence at which it holds no entry: the event goes at that sequence of the subject's chain, and names as its actor's point the last sequence before it in the actor's own chain; two actors disconnected from each other can therefore write at one sequence of one subject, which D38 resolves. The verdict is a function of the event set and the cell id alone, so every device reaches the same membership from the same events whatever order they arrived in, and a device holding nothing — a newcomer's, a freshly linked one — verifies the whole store from the founding event in its first session, whatever order the entries arrive in. What an event rests on need not arrive first: an event counts once the device holds its actor's chain up to the point it names — a sequence being held once any entry at it is, whatever that entry counts for — and a member's state follows its chain as far as the first sequence at which the device holds no entry, an event beyond it waiting until the sequences below it arrive; an entry a modified device places far beyond a chain therefore waits for good and moves no writer. An event whose transition the state before its sequence does not allow counts for nothing without waiting on its actor's point, and events left waiting on each other's outcome in a loop, which only a modified device writes, count for nothing. A device statement counts once the device holds the event that carries its member's announcement key, and an entry whose author only a statement lists once that statement counts, whatever order the entries arrive in (D42). The date in an entry is written by its author and shown to people; the fold and the record view never read it, now or later — order is the sequence, and an anchored log (D34) proves order, not dates.

What the reference proves is, as for records (D22), that the event is after the actor's named point, not before the point at which the actor lost the state the event needs; an act a narrowed member writes under its old point counts (D34).

**Example:** Carol's new laptop c2, freshly linked, holds `9cbcbe4da7cc35a44360d64e45621957` from Carol's directory and nothing of the membership store; Alice founded the cell on a1, invited and promoted Bob, and Bob invited Carol from b1, and c2's first session brings the store in this order; `<alice>`, `<bob>`, `<carol>`: 64 lowercase hex chars of each `PdnId`; `…`: the founding event's actor sequence.

| arrives | needs | verdict on c2 |
|---|---|---|
| `member/<alice>/1/founded/<alice>/0` | to derive the cell id c2 holds, and a signature under the announcement key it names | counts |
| `member/<alice>/devices/1`, listing a1 | a signature under the announcement key of Alice's founding event | counts |
| `member/<bob>/1/joined/<alice>/1`, by a1's author | Alice a member at her sequence 1 | counts |
| `member/<bob>/devices/1`, listing b1 | a signature under the announcement key in Bob's joined event | counts |
| `member/<carol>/1/joined/<bob>/2`, by b1's author | Bob a member at his sequence 2 | held, not yet counting: c2 holds Bob's chain up to 1 |
| `member/<bob>/2/promoted/<alice>/1`, by a1's author | Alice an owner at her sequence 1 | counts, and Carol's joined event with it, in this session |
| c2 lists Alice and Bob as owners and Carol as a plain member, as every member device does. A device statement arriving before the event that carries its key counts once that event is held, the same way. | | |

**Rejected alternatives:**

- The entry's timestamp as the point it is judged at.
  - **Cons:** each writer's clock sets it, and clocks disagree and step back — the store admits an entry dated up to 10 minutes ahead — so an act written after another, and knowing it, can carry the earlier time, and a chain folds out of the order its writers saw; a device never knows it holds every event with an earlier time, so a verdict would change with every event that arrives late; and a key event log proves order, not time, so no anchoring closes it later.
- Membership events judged as of the session.
  - **Cons:** what an owner did while an owner stops counting at its demotion — its promotions and its invites undone — and what a member did while a member stops counting at its departure (D13).
- The next event after the highest sequence held, whatever lies below it.
  - **Cons:** one entry a modified device places far ahead — at a member's sequence 1,000,000 — moves every honest writer past a gap no event fills, and the member's acts and the events on it wait for good.

### D25. The cell id is derived from its creator's announcement key and a random nonce

At creation the creator's device draws a 16-byte random nonce and derives the cell id as the first 16 bytes of BLAKE3 in its key-derivation mode, under the context string `pdn/cell-id/v1`, over the creator's `PdnId`, the creator's announcement public key (D16) and the nonce — BLAKE3 being the hash iroh and pdn-store already use, and the context keeping this derivation apart from any other hash of the same bytes. The founding event carries those three fields and a signature by the announcement secret over the prefix `pdn/cell-founding/v1` followed by the three, the prefix keeping it apart from the device-list statements the same key signs (D16). A device holding the cell id — from its identity's directory, an invite or a link in a note — counts a founding event only when its three fields derive that id, its announcement key derives its `PdnId` (D44) and its signature verifies under that key, and counts no other founding event, whatever order it arrives in; a device holding nothing checks the root of the membership store against the id it already holds (D23). A newcomer learns the id from its inviter, as it learns everything else at join (D26). Without the founding event, which only member devices hold, the id reveals nothing of its creator. The id is 16 bytes, the size of a UUID, written as text as 32 lowercase hexadecimal characters, and the byte-id type in pdn-types is defined to that size. The id travels in notes to other cells' members, so it never equals either store's namespace id, the read capability (Invariant 3). With KERI the creator's autonomic identifier takes the announcement key's place in the derivation.

**Example:** Alice's laptop a2, freshly linked, holds `9cbcbe4da7cc35a44360d64e45621957` from Alice's directory and nothing of the membership store; its first session is with a modified b1 that withholds Alice's founding event and serves one in Bob's chain instead. Alice's and Bob's `PdnId`s derive from their announcement keys (D44).

| founding event a2 is served | its fields derive | on a2 |
|---|---|---|
| by b1: Bob's `PdnId`, Bob's announcement key `d759793b…25ad2c48`, nonce `5a5a…5a5a` | `211891a43656908e3d5804f5c25a38f4` | held and counted for nothing, and so is every event of the chain b1 invents |
| by c1, next: Alice's `PdnId`, her announcement key `17cb79fb…e18080ce`, nonce `5a5a…5a5a`, signed by that key | `9cbcbe4da7cc35a44360d64e45621957` | counts, and the rest of the store is verified from it |

**Rejected alternatives:**

- A random cell id, such as a UUID v4.
  - **Pros:** embeds nothing.
  - **Cons:** a device holding nothing takes the root from whoever serves its first session — a member's freshly linked device that catches up first from a modified member device is handed an invented founder, and once the real founding event arrives too, nothing tells which of the two roots the store.
- A random cell id beside a founding event signed by the creator.
  - **Cons:** anyone signs a founding event naming the same id under their own key, and the id names no key to tell the two apart.
- The creator's key and the nonce as the id, unhashed.
  - **Cons:** every link names the creator; three times the size.
- The creator's signature over the nonce as the id.
  - **Cons:** rests on a property the signature scheme does not promise — that no other key verifies the same signature over some message; 64 bytes.
- The hash of the whole founding event.
  - **Cons:** how every id is derived follows the founding event's encoding, so a change of its format changes the derivation.
- The full hash, uncut.
  - **Pros:** a creator cannot prepare two founding events under one id.
  - **Cons:** substitution by another member is out of reach at 16 bytes already; the creator sits inside the trust boundary (D28).

### D26. A newcomer joins through a one-time-secret dialogue with a member device

Any member's device mints an invite — a QR code or an invite link carrying the inviting device's address, a one-time short-lived secret and the cell id, no ticket; minting writes nothing to either store. The newcomer's device dials the inviting device on a dedicated ALPN and presents the secret; the inviting device verifies and burns it before any state changes, names the sequence the newcomer's joined event takes and the version and device list its device statement extends — the member's own, for an identity the cell has listed before — receives the newcomer's join statement signed over that sequence and its device statement (D16, D44), writes the invite act — held in the newcomer's chain as its joined event, carrying the join statement — beside the device statement, and hands over both stores' write tickets — the shape of the pairing dialogue that establishes a connection (ADR-0011). The statement lets the inviting device serve the newcomer's first session (D32), so the join returns caught up. The inviting device writes the joined event before it hands over the tickets, as linking registers a newcomer before it replies, and the newcomer's device records both tickets and the cell's directory entry (D35) before it catches up, so the armer's next sweep finishes a catch-up that a dropped connection, a dropped `join` future or a restart interrupts. A secret presented by an identity the cell already lists as a member — one whose earlier join lost the inviting device's reply — runs the same dialogue and writes no joined event: the inviting device hands over both tickets again and writes the device statement the dialogue carries when the member's list does not name that device. The pending secret records the identity it was minted for, and the invite act goes into that identity's replica — a node hosting two members holds the cell twice. Between two identities of one node the dialogue runs inside the process, as pairing does between them, with the secret verified and burned the same way; the dialogue is written once, generic over its streams. Both devices are online at once and reach each other through iroh relays, since two devices on different networks without a relay and without DNS do not reliably reach each other; the stack binds relays through `Connectivity` in `SpawnOptions`, and the product is expected to run relays of its own. Whoever presents a live secret first joins, under a `PdnId` its join statement proves its own (D44): the invite is a bearer one, and whom it reaches is the inviter's choice. Inviting a party that is offline is pending-invite machinery with polling, which ADR-0011 leaves possible and a later change builds.

**Example:** Carol joins "Family" on Bob's invitation; Bob's phone b1 mints the invite, and Carol's phone c1 presents it.

| step | b1, inviting as Bob | c1, joining as Carol |
|---|---|---|
| 1 | mints the invite: b1's address, a one-time secret, `9cbcbe4da7cc35a44360d64e45621957`, no ticket; writes nothing into either store | reads it from a QR code |
| 2 | | dials b1 on the join dialogue's own ALPN, beside `/pdn/pairing/0` and `/pdn/linking/0`, and presents the secret |
| 3 | verifies and burns the secret, before any state changes, and names Carol's sequence 1 | |
| 4 | | sends Carol's join statement, signed by her announcement key over her `PdnId`, the key, the cell id and her sequence 1, and her first device statement, listing c1 |
| 5 | writes into Bob's replica the invite act — Carol's joined event, her join statement inside — and her device statement, and hands c1 both stores' write tickets | |
| 6 | serves c1's first session, since Carol's statement lists c1 | catches up, and the join returns |

**Example:** the dialogue above is interrupted at one of two moments.

| the connection drops | on every member device | c1 |
|---|---|---|
| before b1's reply reaches c1 | Carol listed | holds nothing; a second invite from Bob writes no joined event and hands c1 both tickets |
| after c1 recorded both tickets and `cells/9cbcbe4da7cc35a44360d64e45621957/1`, during the catch-up or across a restart | Carol listed | the armer opens the cell and catches up |

**Rejected alternatives:**

- An invite record carried over an existing channel with the newcomer — a connection or a common cell — the stores' tickets inside an Invariant-3 store as data tickets travel.
  - **Pros:** no simultaneous presence; addressed to the newcomer's identity, so there is no secret to intercept.
  - **Cons:** reaches only a party already connected or sharing a cell, so a first contact needs the dialogue anyway; the join completes only when a member device next sees the newcomer's answer.
- Both paths.
  - **Cons:** two join paths to build, test and keep in step, where pending invites give the dialogue the same reach to an offline party.
- The inviting device writing the joined event once the newcomer acknowledges the tickets.
  - **Cons:** a round trip more on every join; a lost acknowledgement leaves a newcomer holding both tickets that no member lists, refused every session and receiving the stores' content-free announcements — when members write, and how often — until a second invite writes its joined event.

### D27. An entry outside the key layout is kept, used by nothing, and surfaced

An entry in either store whose key fits neither layout of D21 — or fits one only in part, such as `by/<pdnid>/` alone — is held like every entry a member device's session carries (D42), and reconciled and relayed like any entry. A key longer than the store's bound of 8,192 bytes never reaches this question: the store drops it at ingest on every honest device, because a replica holding it would send a first message too large for any peer to read, so a record's id and every layout of D21 fit under that bound. Nothing on the platform reads it: no fold, no record view. The record store lists such entries with their authors, and the application shows that the cell holds entries it does not understand. Because no entry affects another key — the store keeps no relation between keys — holding one harms nothing else in the store, and every member device converges on the same set.

**Example:** entries outside the key layout offered to Carol's phone c1 in the record store of "Family"; `<bob>`: 64 lowercase hex chars of Bob's `PdnId`.

| entry | its author | on c1 and every member device |
|---|---|---|
| `ext/anything` | b1's | held, relayed, listed with b1's author; no record changes |
| `by/<bob>/`, a layout in part | b1's | the same |
| `ext/` and 8,188 bytes more, 8,192 in all | b1's | the same |
| `ext/` and 8,189 bytes more, 8,193 in all | b1's | dropped at ingest, before any layout is read |
| `ext/anything`, relayed by b1 | one no member's statement lists | held, and listed with that author |

**Rejected alternatives:**

- Dropping it at ingest.
  - **Cons:** the replicas never converge — every session with a device that holds the entry reconciles the same difference again, each round a linear fingerprint scan; a cell whose devices run two versions of the layout drops on the older what the newer writes.
- Failing the session.
  - **Cons:** the session fails again every time, and the peer's other entries — its own and those it relays — stop with it; a two-member cell stops syncing; honest devices hold no such entry, so it reaches a device only from the device that holds it, and failing protects nothing that dropping does not.

### D28. Every member is trusted with the whole cell

A member reads every record, holds both stores and their write tickets, and relays what it holds; what it does under its own name — what it leaks, the storage it fills, the entries it keeps outside the key layout (D27), the entries it writes into either store under any name and the time every member device's fold and record view spend reading them (D42) — no rule of the platform limits. The fold and the record view protect honest members from a dishonest member's forgeries — an entry under another member's name, an act its role does not allow — which every member device holds and relays and none counts, and from nothing else. Real expulsion under bearer tickets is a new cell (D20).

**Example:** what Bob, a plain member of "Family", does from a modified b1, and what the honest member devices do with it.

| a modified b1 | honest member devices |
|---|---|
| copies every record out of the cell | cannot tell |
| places 10,000 claims under Bob's name | hold them all, as any member's records |
| writes 100,000 acts into other members' chains | hold them all, and the fold reads every one each time it folds, counting none |
| writes entries outside the key layout | hold and relay them (D27) |
| places a claim under Alice's name | hold it and read none of it |
| writes a promoted event for Bob | hold it and count none of it: Bob is no owner |

### D30. Cells stand beside connections, grants and per-issuer namespaces, and touch none of them

Cells are built in parallel with what exists. Connections, grants, subset-rbsr and per-issuer namespaces keep working as they do, and nothing in a cell rests on them: a cell's stores carry no grant, a grant names no cell as its audience, and cell content never flows into a personal namespace or out of one through a grant. A two-member cell and a connection coexist, one a copy into a common space and the other a grant on one's own data. Once cells prove themselves in practice — the mobile application's integration included — connections go entirely, with the machinery that serves only them; until then both stay.

**Example:** Alice and Bob hold a connection and share the two-member cell "Household".

| | Alice's connection to Bob | the cell "Household" |
|---|---|---|
| Alice's phone number | her own namespace at `contact/phone`, under a grant to Bob | — |
| the shopping list | — | the cell's record store, under Alice's name |
| Alice withdraws the grant | Bob stops receiving `contact/phone` | nothing changes |
| Bob leaves the cell | nothing changes | Bob's devices forget the record store and keep the membership store as the cell's tombstone |

**Rejected alternatives:**

- Connections as two-member cells now.
  - **Cons:** replaces a working path with one not yet tried in the product, before the mobile application runs on it.
- The cell as an audience of grants on personal namespaces — "share without copying".
  - **Cons:** ties the new primitive to the machinery it may replace, and carries a grant's per-claim bookkeeping into every cell.

### D31. The debug surface covers the cells service whole

The HTTP host serves every operation of the cells service under `/debug/`, one route each, each delegating to one call and adding no orchestration — the rules the host already keeps for identity, connections and data. A cell the calling identity is no member of is 409, as an issuer the identity holds nothing of is (`UnknownIssuer`); a refusal by role is 403, as a write outside a grant is (`WriteNotGranted`); an absent record is 404. A client reads the cells routes as it reads every other route, and a test that expects a refusal by role fails when the service does not take the caller for a member at all. No route writes a raw entry, hands over a store ticket or forces reconciliation, so what a modified node does — a forged entry, an entry outside the key layout — is exercised in the data layer's own tests, what D34 leaves undefended nowhere, and the container stand exercises what the product path reaches: a three-member cell with its paired denials, a kick and a restart.

The routes take this shape; the host spec leaves paths free to change:

| Route                                     | Operation      |
| ----------------------------------------- | -------------- |
| `POST /debug/identities/{id}/cells`       | `create`       |
| `GET /debug/identities/{id}/cells`        | `list`         |
| `GET …/cells/{cell}/members`              | `members`      |
| `POST …/cells/{cell}/invites`             | `invite`       |
| `POST /debug/identities/{id}/cells/join`  | `join`         |
| `POST …/cells/{cell}/acts`                | `act`          |
| `POST …/cells/{cell}/records`             | `put_record`   |
| `GET …/cells/{cell}/records`              | `list_records` |
| `GET …/records/{member}/{kind}/{id}`      | `read`         |
| `POST …/records/{member}/{kind}/{id}/ops` | `append_op`    |
| `GET …/records/{member}/{kind}/{id}/ops`  | `read_ops`     |
| `GET …/cells/{cell}/unknown`              | `list_unknown` |

**Example:** requests to the host on Alice's tablet a3, which hosts Alice-leisure, the owner of "Family" (`9cbcbe4da7cc35a44360d64e45621957`), and Alice-work, a plain member of "Wedding" (`f942dfc21acd0218d48f61f714ddfff3`) and no member of "Family"; `<alice-leisure>`, `<alice-work>`, `<bob>`: 64 lowercase hex chars of each `PdnId`.

```
POST /debug/identities/<alice-work>/cells/f942dfc21acd0218d48f61f714ddfff3/acts   Kick(<bob>)
→ 403, a refusal by role; Bob stays a member
GET /debug/identities/<alice-work>/cells/9cbcbe4da7cc35a44360d64e45621957/members
→ 409, Alice-work being no member of "Family"
GET /debug/identities/<alice-leisure>/cells/9cbcbe4da7cc35a44360d64e45621957/records/<bob>/claim/<an id the cell does not hold>
→ 404
```

**Rejected alternatives:**

- A subset of the cell operations for the demo.
  - **Cons:** a scenario the surface cannot drive is tested across containers nowhere, and the host spec already asks the surface to cover the runtime's operations.
- A route that writes raw entries, to exercise forgeries over HTTP.
  - **Cons:** a path the runtime's own callers lack, against the host's rule; forgeries belong to the data layer's tests, where the stores are written directly.
- 403 for a cell the identity is no member of, as for a refusal by role.
  - **Pros:** the cell answers a non-member by its rules, as it answers a plain member's attempt at an owner's act.
  - **Cons:** a client tells no member from no role by the body alone, and a test that expects a refusal by role passes when the service does not take the caller for a member. It hides nothing the chosen statuses reveal: the body still tells the two apart, and a session on the cell's store already refuses a non-member as it refuses a store not hosted (D32).

### D32. A session names two members, and the caller is looked up in the serving identity's own records

Every session on a cell's store names, as every session under identity-scoped replicas does, the member whose replica it addresses and the member its caller acts as, and is served only when the member the caller names is a current member whose records list the caller's node id, or, on the membership store alone and up to its departure, a former member whose records list it (D36). Which records follow from who serves. Where the caller names the identity the serving replica belongs to — a sibling device of that identity — its node id is looked up in that identity's own directory, as for every other store of the identity. Where it names another member, it is looked up in that member's device statements in the membership store (D16), whether the session crosses the network or runs inside the process between two identities of one node. A freshly linked device is therefore served by its siblings at once, before any statement lists it, and its statement reaches the other members through them. A caller naming an identity that is no member is refused indistinguishably from the store not being hosted — a co-located identity on a member's own node included, though it shares that member's node id — and so is a caller naming a member whose records do not list it. A node hosting members B and D is served as B in a session naming B and as D in one naming D, never as both.

**Example:** callers ask Bob's phone b1 for a session on the record store of "Family", addressing Bob's replica. Bob's laptop b2 was linked a minute ago and no statement lists it yet; Alice's tablet a3 hosts Alice-leisure, a member, and Alice-work, no member; no statement of Dave's lists a3; `<b2-hex>`: 64 lowercase hex chars of b2's `NodeId`.

| caller | names as its member | b1 looks it up in | b1 |
|---|---|---|---|
| b2 | Bob, the replica's own identity | Bob's directory, which holds `devices/<b2-hex>` | serves it |
| c1 | Carol | Carol's device statements, which list c1 | serves it as Carol |
| a3 | Alice-leisure | Alice-leisure's device statements, which list a3 | serves it as Alice-leisure, never as Alice-work too |
| a3 | Alice-work | nowhere: Alice-work is no member | refuses with `00 00 00 02 02 00`, the answer for a store b1 does not host |
| a modified a3 | Dave | Dave's device statements, which do not list a3 | refuses with the same frame |

**Rejected alternatives:**

- The member's device statements alone, siblings included.
  - **Cons:** a freshly linked device is refused by every device until a statement lists it, and the statement lists the author the member writes with on that device, which only that device knows until it writes it.
- Naming only the caller's member and leaving the serving node to pick the replica.
  - **Cons:** a node hosting two members holds the cell twice, and the pick is ambiguous exactly there.

### D34. A member's own history is taken on its word

Cells serve load testing first, and the defence of a cell against a member's device that contradicts its own member's history rests on anchored signatures over the platform's key event logs, which cells do without. Without them both stores take on the member's word what a member's devices write as that member — records under its name and acts in any member's chain — in four ways: an act or a record naming a point in the member's chain after which the member lost the state it names — a demoted owner acting as an owner, a kicked member placing a record — counts, since a reference proves only that the entry is after the point it names (D22, D23); an entry the member's own author writes at a key it wrote before replaces the earlier one wherever it is the newer, the store keeping one entry per author at a key; two events the member's devices write at one point of a chain stand side by side, resolved by precedence as two owners' events at one point are (D38); and two entries of one of the member's claims or immutable-documents — from two of its devices at one key, or under two membership sequences — stand side by side, and a read of the record returns the one with the newest timestamp. What counts for nothing is what no state of the member's own ever allowed: a record under another member's name, an entry by an author that resolves to no member's device, an act naming a point at which its actor lacks the state the act needs, a device statement not signed by the member's announcement key, a founding event that does not derive the cell id. Every reachable membership state stays repairable against honest members' acts (D14); a member's device that contradicts its member's history undoes an owner's repair as often as the owner makes it. These paths are specified by what honest devices do, and no scenario and no test pins what the fold does with a member's contradictions. The defect a modified member device reaches through them obliges a fix, as every lever a modified node has against honest nodes does; the fix is deferred, this decision is its record, and a review reports none of it anew. The deferral holds while no cell carries data people depend on: it ends before connections go (D30).

**Example:** in "Family", Alice demoted Bob, an owner since his sequence 2, at his sequence 3, and kicked Carol at her sequence 2; Bob's phone b1 and Carol's phone c1 are modified.

| what a modified device writes | on every honest member device |
|---|---|
| b1 promotes Bob himself, naming his sequence 2 | counts, and Bob is an owner again |
| c1 places a claim under Carol's name, naming her sequence 1, relayed by a member device the kick has not reached | read |
| b1 promotes Bob himself, naming his sequence 3 | counts for nothing: at his sequence 3 Bob is a plain member |
| b1 places a claim under Alice's name | read by none |

**Rejected alternatives:**

- Act numbers and narrowing marks in the membership store, ahead of the logs.
  - **Pros:** a narrowed member's acts under its old point stop counting in the membership store, with no cryptography and no cost at run time, since the fold reads the whole store.
  - **Cons:** a mechanism of its own — act numbers, gapless counting, marks, a fold that ignores what rests on an ignored act — built, specified and tested before cells can serve load testing, and replaced when anchored signatures arrive; it leaves the record store open all the same.
- Hash-linked membership sequences, ahead of the logs.
  - **Cons:** the logs' duplicity handling built a second time, in a format the logs' own encoding then replaces.

### D35. A cell's record in the directory follows the identity's membership sequence

The identity's directory records each cell under `cells/<cell-id-hex>/<seq>`, where `<seq>` is the sequence, in the identity's own chain in the cell's membership store, of the event the entry mirrors: the founding event or a joined event writes a non-empty entry at its sequence, and a left event, or a kicked event its device learns of, writes a pdn-store tombstone at its own. The identity holds the cell when the entry at the highest sequence, across all authors, is non-empty, a tombstone outweighing a non-empty entry at one sequence; entry timestamps are never read, so a leave from a device whose clock runs behind still ends holding on every device, and a join after it holds the cell again. The device that acts writes both with one number: the leaving device places its left event at the first sequence of its own chain at which it holds no entry (D23) and the tombstone at the same one, and a joining device writes its entry at the sequence the inviting device named in the join dialogue, before it catches up (D26, D44). The record sits in the directory, the identity's own store, because a departed member's devices are served no session on the cell's stores (D32), its siblings' included, so the left event may never reach them, while the directory syncs between them always; a restart re-derives the held cells from the same entries (D16). pdn-store's delete removes its own key alone, so a tombstone at `cells/<cell-id-hex>/1` leaves `cells/<cell-id-hex>/10` standing. A kick reaches the kicked member's directory through the first of its devices that learns of it (D36).

**Example:** Bob acts on his membership of "Family" from his phone b1, whose clock is right, and his laptop b2, whose clock runs 80 minutes behind.

| real time | device | writes | entry timestamp | Bob's devices hold "Family" |
|---|---|---|---|---|
| 10:00 | b1 | `cells/9cbcbe4da7cc35a44360d64e45621957/1`, non-empty: joined at his sequence 1 | 10:00 | yes |
| 11:00 | b2 | `cells/9cbcbe4da7cc35a44360d64e45621957/2`, the tombstone: left at his sequence 2 | 09:40 | no, once the directory syncs |
| 12:00 | b1, on a new invite | `cells/9cbcbe4da7cc35a44360d64e45621957/3`, non-empty: joined at his sequence 3 | 12:00 | yes |

**Rejected alternatives:**

- One entry per cell at `cells/<cell-id-hex>`, the newest across authors by entry timestamp.
  - **Cons:** a leave written from a device whose clock runs behind the one that wrote the join loses to the join, and the identity's other devices go on holding a cell whose members refuse them.
- The identity's own chain in the membership store, read directly.
  - **Cons:** a departed member's siblings are served no session on the cell's stores, so the left event may never reach them.
- A counter of the directory's own beside the cell id.
  - **Cons:** a second number for what the membership chain already numbers, which two disconnected devices of the identity bump alike.

### D36. A departed member's devices keep the cell's membership store as its tombstone

A member that leaves, and a member whose device learns that it was kicked, forget the record store and keep the membership store for good, on every device of the identity, as the cell's tombstone. The tombstone holds the departure's past: the departure event — the member's left event, or the kicked event in its chain — and every entry that event depends on, followed back through the earlier events of its subject's chain, its actor's chain up to the point it names, and, for each of these in turn, the same, with the joined events and device statements that resolve their authors, down to the founding event. A member device serves a session naming a former member on the membership store alone and over the departure's past alone, in both directions, and refuses it the record store as it refuses any caller that is no member (D32); a sibling device serves the tombstone whole, it being the identity's own. The departed device holds its own sessions with member devices to the same past, both ways, so a member device that has not yet learned of the departure sends it nothing outside that past, and takes beside the past the events of its own chain after the departure, so a join after it reaches the device. The past follows from the event set alone, so every member device serves the same one, and nothing written outside it — a later record, a later member, a later device statement — reaches a former member. A left event written with no member reachable therefore reaches the members at the leaving device's first session with any of them, and a device offline during its member's kick learns of the kick at its first session, turns the cell into its tombstone, and writes the directory's tombstone at the kicked event's sequence (D35), which carries the departure to the identity's other devices. A tombstone is reconciled with member devices, outside the store's swarm, until one session with a member device has converged over the departure's past, and is then kept and reconciled with the identity's own devices alone; a device linked after the departure takes it from a sibling. A join after the departure turns the tombstone back into the cell's membership store (D35). Without an anchored log a former member's device is taken on its word within the departure's past, as every member's own history is (D34). The forgotten record store's payloads leave the device once no other replica on it references them (D37).

**Example:** Carol leaves "Family" on her phone c1 while c1 is offline, her laptop c2 holds the cell too, and an hour later c1 reaches Bob's phone b1; meanwhile Bob invited Dave, and nothing in Carol's departure depends on Dave's join.

| step | Carol's devices | b1 |
|---|---|---|
| Carol leaves on c1 | c1 writes her left event at her sequence 3 and `cells/9cbcbe4da7cc35a44360d64e45621957/3` as the directory's tombstone, forgets the record store, keeps the membership store; c2 does the same once Carol's directory syncs | — |
| an hour later c1 reaches b1 | a session on the membership store over the past of Carol's left event: c1 sends the left event and takes what of that past it lacks | takes the left event; Dave's joined event, outside that past, is not sent |
| c1 asks b1 for the record store | refused with `00 00 00 02 02 00` | |
| Alice places a record | receives nothing | receives it |
| had Alice kicked Carol while c1 was offline instead | c1 takes the kicked event and the past it rests on in its first session, forgets the record store and writes the directory's tombstone at the kicked event's sequence | serves that past, and nothing after it |

**Rejected alternatives:**

- Both stores forgotten at the leave.
  - **Cons:** a left event written with no member reachable exists nowhere once the device forgets, and every member device lists the member for good; a device offline during a kick learns nothing of it and keeps writing entries nobody receives.
- Both stores forgotten once another member's device has acknowledged the left event.
  - **Cons:** an acknowledgement of its own, and a device offline during a kick still learns nothing.
- Both stores forgotten after a bound.
  - **Cons:** a bound that passes before a member device is reached loses the left event.
- The former member's own chain alone as the tombstone's past.
  - **Cons:** a kicked event is written by an owner, and the owner's chain up to the point the event names is what makes it verifiable, so the former member's device could judge its own kick by nothing.
- Every entry the serving device held when the departure reached it.
  - **Cons:** entries of different chains carry no order between them, so each member device would serve a different set, fixed by what it happened to hold.

### D37. A node removes the payloads no replica it holds references

The node runs blob collection over its one blob store, whose single protect callback answers with the union of what every hosted identity's engine references, so a payload stays while any replica of any identity the node hosts references it and leaves the device at the next run once none does. A payload replicates with its entry, so every device of a member downloads every payload of the cell; a forgotten record store, a forgotten data replica or a withdrawn grant's replica frees its payloads without anything to delete by hand. The collection runs at an interval `SpawnOptions` sets.

**Example:** Carol leaves "Family" on her phone c1, which hosts Carol alone; its record store held Bob's lease scan and a photo whose bytes Carol also keeps in her own data namespace.

| payload | referenced after the record store is forgotten by | on c1 after the next run |
|---|---|---|
| Bob's lease scan | nothing | removed |
| the photo | Carol's data namespace | kept |
| On Alice's tablet a3, where Alice-work leaves "Wedding" and Alice-leisure stays a member, every payload of the cell stays: Alice-leisure's replica of the record store references each. | | |

**Rejected alternatives:**

- No collection: payloads stay until the device's storage is reset.
  - **Cons:** every payload a device ever downloaded stays on its disk for good, a departed member's and a withdrawn grant's among them, and keeps being served by hash to any caller.
- A collection per identity.
  - **Cons:** the blob store is one per node, so one identity's run would remove a payload a co-located identity's replica still references.

### D38. Events at one point of one chain resolve by precedence, the narrowest first

Two owners disconnected from each other can write at one sequence of one subject (D23), and a member's own devices can too (D34). Every such event persists, and among those whose transition the subject's state before that sequence allows — the founding or a join of no member, a leave, a kick or a promotion of a member, a demotion of an owner — the fold takes effect with the one that ranks highest: kicked, then left, then demoted, then promoted, then joined, the founding event above a joined event at the creator's sequence 1. An event whose transition that state does not allow counts for nothing, and the same event written twice counts once, so the sequence at which a member joins takes no kick, leave or demotion placed beside the join, and the creator's first sequence takes none beside the founding event. The order runs from the narrowest state to the widest: a kick and a leave take the member out, a kick recording an owner's act; a leave outranks a demotion, since a member that left has forgotten the record store (D36) and would otherwise stay listed while holding none of the records; a demotion outranks a promotion. A wrong kick is undone by an invite, and a wrong demotion by a promotion. Where a left and a kicked event share a point, the kicked event is the departure a tombstone's past follows (D36). The rule reads the event set alone, so every device reaches the same membership whatever order the events arrived in, and no author's key decides.

**Example:** events at one of Bob's sequences in "Family", where Alice and Carol are owners, each written while its writer was disconnected from the other.

| Bob's sequence | events at it | Bob on every member device |
|---|---|---|
| 5 | Alice promotes him, Carol kicks him | kicked; a member invites him again if the kick was wrong |
| 5 | Carol demotes him, an owner, while Bob leaves | no member: the leave outranks the demotion |
| 5 | Alice and Carol both promote him | an owner, the promotion counted once |
| 1 | Alice's invite act brought him in, and a modified phone of Carol's writes a kick beside it | a member: before his sequence 1 Bob is no member, so the kick counts for nothing |

**Rejected alternatives:**

- The lower author key wins.
  - **Cons:** deterministic and meaningless: the luck of a key decides whether a member is an owner or out.
- Both applied in author-key order.
  - **Cons:** the same luck in another form: a promotion beside a demotion ends at the event of the higher key.
- The fork left unresolved, the member in the conservative state until a later event supersedes both.
  - **Cons:** a later event names its actor's point, not a branch of the subject's chain, so nothing ever settles the fork, and choosing the conservative state is a precedence all the same.
- A demotion outranking a leave.
  - **Cons:** a member demoted and leaving at one point stays listed as a plain member while its devices hold nothing but the tombstone.
- Every event at a point competing, whatever the state before it.
  - **Cons:** a kick or a leave placed at the sequence where a member joined outranks the join and applies to no member, so the member never joined: everything it did stops counting and the members it invited are out with it, and placed at the creator's first sequence it empties the cell.

### D39. A demotion that would leave a cell without an owner is ignored

Two owners disconnected from each other can demote each other at once: two events on two subjects, each valid at its actor's named point, and together they empty the owner set, which a fold walking one member's chain at a time does not see. The fold therefore runs one guard over all chains. When the folded membership holds no owner and the roles of some of its former owners ended in demotions, the fold takes those demotions in the order of their actors' `PdnId`, lowest first, each against the former owners it has not yet removed, and ignores every one that would remove the last of them; the subject of an ignored demotion stays an owner. The guard reads the event set alone, so every device reaches the same owners, and a member whose demotion it ignored is demoted again by an owner's later act. An owner set emptied by leaves or by a lost device is outside it, as D11 accepts.

**Example:** owners Alice and Carol, disconnected from each other, demote each other in "Family", where Bob is a plain member; Carol's `PdnId` sorts below Alice's.

| demotion, in the guard's order | the former owners it has not yet removed | on every member device |
|---|---|---|
| Carol demotes Alice | Alice, Carol | stands: Carol remains |
| Alice demotes Carol | Carol | ignored: it would remove the last of them |
| Carol is the one owner. | | |

**Rejected alternatives:**

- A member that cannot be demoted — the creator as a root owner.
  - **Cons:** a role no act takes away, against D11.
- The owner set left empty.
  - **Cons:** nobody kicks a member or promotes one again, and the cell has no repair from inside (D14).

### D40. Nothing in a cell carries a version

No entry of either store, no fold and no folded membership carries a version: every device reads every entry of a cell by the one set of rules its build holds, and a build that reads entries otherwise — a new event kind, a new record kind, a fold that resolves differently — reads the cells it finds by its own rules as well. Devices of one cell on two such builds can then reach two memberships and two sets of readable records from the same entries, and a cell that splits so is recreated, its content lost. This holds while cells run inside the company alone and a lost cell costs nothing beyond itself; it ends before a cell carries data people outside the company depend on. The `v1` in the context strings of D16 and D25 keeps the signatures a key makes apart and names no rules; the invite's format version is the one the pairing and linking payloads carry.

**Example:** a later build adds an act that suspends a member's editing, and Alice's phone a1, on that build, suspends Bob at his sequence 3, writing `member/<bob>/3/suspended/<alice>/1`; Carol's phone c1 runs the build this design describes; `<alice>`, `<bob>`: 64 lowercase hex chars of each `PdnId`.

| | a1 | c1 |
|---|---|---|
| `member/<bob>/3/suspended/<alice>/1` | Bob suspended from his sequence 3 | an entry outside the key layout: kept, used by nothing (D27) |
| Bob's operation on the shopping list naming his sequence 3 | not counted | counted |
| The two devices read the shopping list differently for good; the cell is recreated on one build. | | |

**Rejected alternatives:**

- A version in each entry, each build reading an entry by its own version's rules and the folds of every shipped version kept side by side.
  - **Pros:** one set of entries stays the only source of truth; an older build answers "unknown" where a newer one knows, never otherwise.
  - **Cons:** the answer "unknown", the rules for how far it spreads, and tests holding every fold to the ones before it, built before cells serve load testing.
- A version per cell, fixed in its founding event, a new version being a new cell.
  - **Cons:** the recreation this decision accepts, with the machinery that carries members and records into the new cell built first.

### D41. The fold verifies what a membership entry's payload carries, once it has arrived

The membership fold reads a membership entry's payload once the payload has arrived, and counts the entry only when what it carries verifies: a founding event when its `PdnId`, announcement key and nonce derive the cell id, its announcement key derives its `PdnId` and its signature verifies under that key (D25, D44), a joined event when its announcement key derives its member's `PdnId` and its join statement verifies under that key (D44), a device statement when its signature verifies under the announcement key its member's joined or founding event carries (D16); an entry whose author only a statement lists reads once that statement counts. An entry whose payload has not arrived counts for nothing yet, and one whose material does not verify counts for nothing for good; either is held like every entry (D42). Every key stays as D21 lays it out, with nothing of the signed material in it. The fold works as the validation of a key event log does: an event waits until what it rests on is held and counts then, and a member contradicting itself shows only while both versions of an event are held side by side — the fold a member's entries go through once they anchor in the member's log (D34).

**Example:** Bob's laptop b2, just linked, writes version 2 of Bob's device statement into "Family" and places a claim, and Carol's phone c1 takes both from Bob's phone b1 in one session.

| on c1 | the statement | b2's claim |
|---|---|---|
| before the statement's payload arrives | held, counting for nothing yet | held, read by none yet |
| once the payload arrives and its signature verifies under Bob's announcement key | counts: b2 is Bob's device | read as Bob's |
| had b1 carried a statement signed under another key | held, counting for nothing for good | held, read by none |

**Rejected alternatives:**

- The material in the key, verified at ingest.
  - **Pros:** a verdict in the session that brings the entry; the ingest check reads keys alone, as on every other store.
  - **Cons:** a key grows with its material, which caps a member's device list at about 60 devices under the store's bound of 8,192 bytes; and a check at ingest drops the second version of an event, which a key event log needs held to show a member contradicting itself, so it would be rebuilt once entries anchor in the logs.
- Payloads carried inline by the fork and handed to the ingest check.
  - **Cons:** a change to the fork's sync protocol and its wire format, and the same drop at ingest.

### D42. A cell store holds whatever a session it serves carries; the fold and the record view judge it

Either store of a cell holds every entry a session carries from a caller it serves — a member device's session whole, a former member's over its departure's past (D36) — bounded by what pdn-store drops on its own: a key over 8,192 bytes, a timestamp more than 10 minutes ahead, an entry whose signature does not verify. No entry is judged at ingest by its author, its key or the membership, and nothing waits there. What an entry counts for follows from the whole set a device holds, whatever order its entries arrived in: the membership fold counts an event when its actor held the state it needs at the point it names, precedence and the guard over demotions included (D23, D38, D39), and the record view reads a record's entry when its author is a device of the member it is written as, that member a member at the sequence the entry names (D5, D6, D17, D22). Every member device therefore holds the same entries, and every list and read follows from them alone; a forged entry — one under another member's name, or an act its actor's role does not allow — is held and relayed by every member device and counts on none. A session is served by the membership as of its setup (D32). For a cell, an entry that counts against its author's state is what an entry admitted past the ingest gate is for a data replica: the defect a review names.

**Example:** in "Family", Alice and Carol are owners and Bob a plain member since his sequence 1; disconnected from each other, Alice promotes Bob and Carol kicks him, both at his sequence 2; Bob's phone b1 takes the promotion first and invites Dave, writing `member/<dave>/1/joined/<bob>/2`; Alice's laptop a2 takes the promotion, then Dave's joined event, then the kick, and Carol's phone c1 takes the kick and the promotion, then Dave's joined event; `<bob>`, `<dave>`: 64 lowercase hex chars of each `PdnId`.

| | a2 | c1 |
|---|---|---|
| Dave's joined event | held; counts until the kick arrives, then counts for nothing, the kick outranking the promotion at Bob's sequence 2 | held, counting for nothing |
| once each holds all three | lists Dave as no member | lists Dave as no member, and a later session with a2 finds no difference |

**Rejected alternatives:**

- Verdicts at ingest, deferred within the session until what they rest on arrives.
  - **Cons:** a verdict is taken over what the device holds when the entry arrives, and a later event reverses it — a concurrent event at the point the entry names, a late promotion that switches off the guard over demotions, the departure of an entry's author — so the device that took the entry keeps it, the device that saw the later event first drops it, and every session between the two offers it again for good; and pdn-store's ingest check accepts or drops and holds nothing back, so a deferral is a buffer of the data layer's own.
- Admission by what no later event reverses — a key that fits a layout and an author that resolves to a member's device.
  - **Pros:** a forgery under another member's name stops at the first honest device that resolves its author.
  - **Cons:** an author resolves only once its statement's payload has arrived (D41), so a freshly linked device's first entries are dropped and offered again by a later session.

### D43. An act names its actor, and an operation its writer, in its key

A membership act's key names its actor beside the actor's sequence — `member/<pdnid>/<seq>/<kind>/<actor>/<aseq>` — and an operation's `<op>` names its writer beside the author that signed it (D21); a claim's and an immutable-document's key names its member already. The fold and the record view read the member an entry is written as from its key, and count the entry only when its author is among that member's devices as the member's own statements list them (D16). An operation counts only when the author that signs it is the one its `<op>` names, so an operation's id names one entry. The members' statements say which authors write for each member and never decide who wrote an entry, so an author that a second member's statement lists as well counts, under that second member's name, only what its device wrote there — nothing, since only its device holds it — and no entry reads as anyone but the member its key names.

**Example:** Bob's modified phone b1 writes version 2 of Bob's device statement, listing b1 and the author Alice writes with on her phone a1, signed by Bob's announcement key, and Alice then appends an operation to the shopping list from a1; `<alice>`: 64 lowercase hex chars of Alice's `PdnId`; `<a1-author>`: 64 lowercase hex chars of the author she writes with on a1.

| on Carol's phone c1 | |
|---|---|
| Bob's statement | counts: it lists what Bob's key signed |
| Alice's operation, its `<op>` naming `<alice>` and `<a1-author>` | read as Alice's: `<a1-author>` is among Alice's devices |
| an operation naming Bob as its writer beside `<a1-author>` | would read as Bob's, and only a1 can sign one, which it never does |

**Rejected alternatives:**

- The author countersigning its listing: each device in a statement carrying a signature by the author it lists, over the cell id and the member's `PdnId`.
  - **Pros:** each author resolves to one member, and keys keep their length.
  - **Cons:** a signature per listed device, verified by the fold and carried into every later version, for what the member's name in the key settles with no check at all.
- The writer resolved from the author, the defence deferred with a member's own history (D34).
  - **Cons:** it touches entries other members wrote: a member's modified device reads another member's edits as its own member's, and an owner's kick by a plain member's role.

### D44. A member's `PdnId` derives from its announcement key, and its join statement proves it

An identity's `PdnId` is the 32 bytes of BLAKE3 in its key-derivation mode, under the context string `pdn/pdn-id/v1`, over the identity's announcement public key. It is derived when the identity and its announcement key pair are minted (D16). This is the cell id's hash (D25) without a nonce, since every identity mints a key pair of its own; the key pair does not rotate before KERI (D16), so the name stays the identity's for its life. The join statement is a signature by the newcomer's announcement secret over the prefix `pdn/cell-join/v1` followed by the newcomer's `PdnId`, its announcement key, the cell id and the sequence of its chain that the joined event takes; the prefix keeps it apart from the founding event and the device-list statements the same key signs (D16, D25). In the join dialogue the inviting device, once it has burned the secret, names that sequence — the first of the newcomer's chain at which it holds no entry (D23) — and the newcomer's device signs over it (D26). The fold counts a founding or joined event only when the announcement key it carries derives the `PdnId` its key names, and a joined event only when its join statement verifies under that key as well (D41). A `PdnId` therefore has one announcement key in every cell, a member joins and returns only through a statement its own devices sign, and a statement copied from an earlier join verifies at no other sequence. With KERI, `PdnId` names the autonomic identifier, which derives from the identity's inception event, and the fold verifies the join statement against the identity's key event log (ADR-0003).

**Example:** Carol left "Family" at her sequence 2 and Dave has never been in it; Bob's modified phone b1 writes every entry but the last; `<carol>`, `<dave>`: 64 lowercase hex chars of each `PdnId`, derived from their announcement keys `<k-carol>` and `<k-dave>`; `<k-b1>`: a key b1 minted; `…`: the actor's sequence.

| entry | on every honest member device |
|---|---|
| `member/<carol>/3/joined/<bob>/…`, carrying `<k-b1>` | counts for nothing: `<k-b1>` does not derive `<carol>` |
| `member/<carol>/1/joined/<bob>/…`, carrying `<k-b1>`, beside Alice's invite at Carol's sequence 1 | counts for nothing, likewise; Carol's sequence 1 stands on Alice's invite |
| `member/<carol>/3/joined/<bob>/…`, carrying `<k-carol>` and Carol's join statement from her sequence 1 | counts for nothing: the statement signs sequence 1 |
| `member/<dave>/1/joined/<bob>/…`, carrying `<k-b1>` | counts for nothing: no key b1 holds derives `<dave>` |
| `member/<carol>/3/joined/<alice>/…`, from Carol's own join dialogue with Alice's phone a1 | counts: Carol a plain member again |

**Rejected alternatives:**

- The key of the member's first joined event binding it, the `PdnId` random.
  - **Cons:** the fold reads no order but the sequence, so a modified member device writes a second joined event at the member's first sequence under a key of its own, and every rule for two keys at one point hands the member over: both keys counting lets that device write as the member, a tie-break by key lets it mint a key that wins, and neither counting takes the member out of the cell.
- The inviter's word: the join statement dropped, the key of the member's latest joined event verifying its statements.
  - **Cons:** a modified member device writes as any departed member, and, through a second joined event at a member's latest point, as any member.
- The announcement public key itself as the `PdnId`.
  - **Cons:** a `PdnId` that is also a verifying key invites code to verify with it directly, skipping the derivation that KERI's autonomic identifier replaces.
- A join statement signing no sequence.
  - **Cons:** a modified member device copies a departed member's statement from its earlier join into a new invite act and readmits the member without its consent.

### D45. A cell store's periodic pass runs every 5 minutes and reaches at most 5 peers drawn at random

Inside a cell a write reaches the member devices through the swarm — a content-free announcement and the pull it triggers (D7) — and a device that comes back catches up in the session its first swarm neighbour opens; the periodic reconcile pass is the safety net under both, for an announcement gossip lost. For each of a cell's two stores the pass runs at an interval of its own, `SpawnOptions::cell_reconcile_interval`, 5 minutes by default, and each run reconciles with at most 5 peers drawn at random, afresh on every run, from the store's contacts and the peers the engine recorded. Any member device serves the cell whole, so an entry a device missed reaches it from whichever drawn device holds it, and draws that differ from run to run spread a missed entry through the cell in a handful of runs. Data namespaces, directories and connection metadata stores keep `SpawnOptions::reconcile_interval` and every contact, a grantee's only data path being the reconciliation it initiates; the pass between two co-located members opens its sessions when something has moved, as the in-process sessions spec states. A run costs a device at most 5 sessions per store of every cell it holds, whatever the cell's size, and the load tests of cells revisit both numbers.

**Example:** Bob's phone b1 holds 50 cells, each of 100 members on 2 devices, beside Bob's data namespace, which his laptop b2 holds too.

| replica on b1 | one run reaches | runs per hour |
|---|---|---|
| each store of the 50 cells, 199 contacts each | at most 5 of them, drawn afresh | 12 |
| Bob's data namespace | b2, its one contact | 360 |
| At most 6,000 cell sessions an hour on b1, where every contact every 10 s would be 7,164,000; a write in "Family" whose announcement b1 missed reaches it at the first run whose draw holds a device that took the write. | | |

**Rejected alternatives:**

- The pass of every other replica: every 10 s, over every contact.
  - **Cons:** every device reconciles with every device of every cell it holds, so a cell's sessions grow with the square of its devices, each a linear fingerprint scan — 39 ms a pass over a quiet store of 100,000 entries.
- A longer interval over every contact.
  - **Cons:** each run still reaches every device of the cell; only the rate falls.
- No periodic pass for a cell's stores.
  - **Cons:** an announcement gossip lost waits for the next write or the next neighbour met, which a quiet two-member cell may not see for weeks.
- One peer drawn per run.
  - **Cons:** a draw that lands on an offline device wastes the run, and a missed entry spreads through the cell in more runs.

## Risks / Trade-offs

- [Every member holds the whole cell in plaintext] → accepted by definition; content encryption is a separate layer; the trust boundary is the member set (D28).
- [A kicked member keeps both stores' write tickets and topic ids] → honest devices refuse it the record store, serve it the membership store only up to its kick (D36), and read none of the entries it authors under a sequence at which it was no longer a member; an entry it authors afterwards under an earlier sequence, a membership act among them, counts (D34); it retains what it received and still sees content-free announcements; real expulsion under bearer tickets is a new cell, accepted while cells serve load testing (D20, D28).
- [A cell can be left without an owner] → the last two owners leaving at once, disconnected from each other, both leave, since the refusal of the last owner's leave runs on each writing device; accepted: the members read and edit, nobody kicks or promotes, and a new cell is the way out (D11); the last owner losing every device leaves the same state until recovery through the identity arrives with KERI, and for good where a KERI backup is lost too (D11).
- [Membership is a multi-writer set] → its events order by per-member sequence numbers, never by timestamp (D3, D21); two owners' concurrent events on one member at one sequence — a kick beside a promotion or a demotion — resolve by precedence, the narrowest first (D38); a member-signed founding chain gives membership a root but no total order.
- [Authorship is a transport-level binding] → author keys are held per hosted identity on a device (ADR-0013); the binding of an author key to a member is what the member publishes under its announcement key (D16), verifiable by anyone holding the join statement; the fold and the record view enforce it on every honest device; a modified member device can forge entries under the name of a member it does not host, which every honest device holds and counts for nothing, while a node acts as every identity it hosts, holding the secrets of each (threat model); what it can still do under its own name after departing is D34. Signed claims come with KERI.
- [Range fingerprints are linear scans] → a record store with 100 writers is never quiescent, so every catch-up session scans it per round; a cached fingerprint tree in pdn-store is the fix, outside this change, and the membership store's convergence does not wait for it (D3).
- [An announcement gossip loses waits for the pass] → the entry reaches a member device at the first 5-minute run whose draw holds a device that took it, a handful of runs across a cell of 200 devices; accepted: the swarm carries live delivery, and the pass bounds how long a lost announcement delays it (D45).
- [An owner's act placed at a point another member's chain has passed] → a modified owner's device writes a kick or a demotion at a sequence where the subject was a member, beside what the chain holds there, and precedence gives it effect from that point: what the subject did from its own point there on stops counting, the members it invited then with it, and a later invite brings the subject back without what it did; an honest act written concurrently with the one it outranks produces the same entries, and only anchored logs tell the two apart; accepted while cells serve load testing (D23, D38).
- [Events waiting on each other in a loop] → a modified device writes an event naming an actor point that a later event resting on the first one's outcome fills, and both, the honest one among them, count for nothing, and what waited on them settles after; only such a device closes a loop; accepted while cells serve load testing (D23).
- [A member's own history is taken on its word] → a departed or demoted member's new entries under its old point count in both stores, whichever member device relays them, a member's device rewrites the entries its author wrote, and two events of one member at one point stand as D38 resolves them; accepted while cells serve load testing, untested, its fix deferred (D22, D23, D34).
- [Dates in entries are self-asserted] → written and shown, never judged (D3, D22, D23); order is the sequence, and "provably before" is the anchored log D34 waits for.
- [The membership store only grows] → events are never deleted; a member's sequence is a handful of events over a cell's life, and the store stays tiny beside the records (D3).
- [Storage per device grows with every cell] → records and their payloads replicate to every member device, and no quota bounds a cell; load tests measure it.
- [Reachability] → two devices on different networks without a relay and without DNS do not reliably reach each other, so a join and a swarm across networks rest on iroh relays — without them a join fails and a swarm fragments; the stack binds relays, the product is expected to run relays of its own, and the test suites and the container stand run on direct paths (D26).
- [Concurrent editing loses edits] → a mergeable-document keeps every operation under its own key and so no edit is lost below the merge that shows them as one document, which sits above the data layer (D17); an immutable-document is never edited.
- [The join is bearer-level] → the invitation carries no ticket and the secret burns on first use, but whoever presents it first joins, under a `PdnId` its join statement proves its own; whom the invite reaches is the only check of who joins (D26, D44).
- [A member's device lists any node id] → the fold counts a device statement by the announcement signature alone, so a member's modified device lists the node id of a node outside the cell, and every member device dials that node as the member on every reconcile pass — with address lookup bound, any node on the network; the node refuses each session, and the dials go on. A modified node reaching a denial of service against a node outside the cell obliges a fix; it is deferred while cells serve load testing (D7, D16, D28).
- [Forgeries are held and relayed] → a member's modified device can write entries under another member's name, or acts its role does not allow, and every member device holds and relays them and spends the fold's and the record view's time reading them, while none counts them; accepted, as the storage a member fills under its own name is (D28, D42).
- [A later build reads a cell otherwise] → devices of one cell on two builds whose rules differ can reach two memberships and two sets of readable records from the same entries; accepted while cells run inside the company alone: a cell that splits is recreated and its content lost (D40).
- [A record placed stays] → no member and no owner deletes or replaces a record: a mistake, a member's junk and a departed member's records stay for every member, and a corrected claim sits beside the old one; accepted while cells serve load testing (D14).
- [Any member edits any mergeable-document] → accepted: every member is trusted with the whole cell already (D28), each operation carries its writer's signature (D15), and a spoiled mergeable-document is repaired by further operations.
- [Payload bytes are served by hash to any caller] → the blob store is the node's and its egress is ungated (ADR-0013), so a party that learns a record's hash fetches its payload from any member device; a kicked member's device that stays in the store's swarm learns the hash of every new payload as it spreads, since a member device that finishes a download announces the hash to its swarm neighbours (`Op::ContentReady` in the fork), and so fetches what is placed after the kick as well as before it; accepted while cells serve load testing; iroh-blobs offers a hook for a gate over payload bytes.
- [A node hosting two members holds the cell twice] → each member identity holds replicas of its own, stored twice and walked twice on every reconcile pass; accepted as the price of separation, at the 1 to 10 identities a device is sized for (ADR-0013, D3, D32).
- [Linkability] → a member carries one `PdnId` into every cell it joins, and two identities hosted on one node list the same node id in their device statements, so whoever shares cells with them sees one member in both, or two identities on one device; accepted, since the network links them regardless — one address, one relay, online together (ADR-0013) — and neither per-cell identities nor an endpoint per identity removes that link.

## Migration Plan

Additive: no existing store, ticket, grant or record changes shape — the directory gains the cell kinds and the announcement key pair — and a runtime without cells behaves as before. Rollback is forgetting cell stores; nothing else depends on them. No migration: the platform has no real users, so an identity created before this change, which holds no announcement key pair, is not carried over.

## Open Questions

None remain: each question answered since its posing left the list, its answer recorded as a decision.
