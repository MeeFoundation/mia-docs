# Design: cells

## Context

A cell is a space its members share: sharing a cell gives every member a complete live copy of its content, the relationship with one other person is a two-member cell, and a cell is expected to stay well under 100 members.

This design records the decisions taken for the platform side of cells and the questions left open. It works from the team's working note on cells and from the team's decisions on roles, record kinds and the cell's two stores.

## Goals / Non-Goals

**Goals:**

- A shared space for 0..n members.
- Everything a member writes reaches every member, from any member, with the author's authorship enforced on every honest device.
- Reuse: the swarm, the content-free topic, the ingest hook, the linking-shaped dialogue, multi-identity hosting, the directory as the carrier to a member's other devices. One change in pdn-store: no entry affects another key (D24).
- Every unanswered question written down, with its options.

**Non-Goals:**

- Identity proof at join, signed claims, key rotation — the KERI roadmap.
- Identity-bound, revocable access — UWill.
- Content encryption — a separate layer; every member holds the plaintext by definition.
- Recall of delivered content — Invariant 2 governs acquisition, not retention.
- Chat — a later change of its own, on a sync shape of its own rather than the store's reconciliation.

## Decisions

### D1. A cell has no key pair — only an identifier

The cell id is a 16-byte identifier derived at creation from the creator's announcement key and a random nonce (D25). A cell signs nothing: no grant is issued by a cell, no claim is issued by a cell, and no dialogue proves "this is cell X". Every act inside a cell is a member's act — signed by that member's device author key, and, with KERI, by the member's identity. Consequence: there is nothing to steal and nothing to rotate — a cell's security is its members' security — and the KERI roadmap needs no group identifier and no multi-signature key set built from members' keys.

**Rejected alternatives:**

- The cell as an identity with its own key set — a multi-signature autonomic identifier.
  - **Pros:** a totally ordered membership log.
  - **Cons:** a group key to manage; a rotation on every membership change; a second identity kind in the KERI roadmap.

### D2. No connections "each with each"

Membership rests on the cell: a member joins on one member's invitation and sees everyone.

**Rejected alternatives:**

- The cell as a fan-out of pairwise connections.
  - **Cons:** n×(n−1)/2 pairing ceremonies; adding a member is work for every existing member; no relay — content comes only from its author's devices, since a grantee never re-serves a third party.

### D3. One cell is two pdn-store replicas: the membership store and the record store

A cell is served by two replicas, each addressed through the cell id. The **membership store** is the cell's authority: who is a member, with what role, on which devices. It holds, per member, one append-only sequence of **membership events** — join (the join record of D16, binding the member to its announcement key), leave, removal, made-owner, unmade-owner — each an immutable entry under its own key with the sequence number inside the signed bytes, and the member's device-list statements (D16), each version an immutable entry of its own. Nothing in the membership store is overwritten or deleted: a removal is an event, not a deletion, and the store holds no tombstones. The **record store** is what the authority governs: the records — claims, mergeable-documents and immutable-documents (D4). The classifier folds the membership store into the write admission the gate judges both stores by, walking each member's events in sequence order: a join makes it a member and a plain one, made-owner an owner, unmade-owner a plain member again, leave and removal no member, a later join a plain member again — a member that joins again joins as a newcomer does (D11); the author-to-member map comes from the join events and the device statements by highest version. By sequence, never by timestamp, so the order in which the events arrived does not matter; each event names its actor's sequence and is verified against the actor's chain at that point (D23). Membership state and role are events in one sequence, so that the flips a member goes through — made an owner and unmade (D11), leaving and rejoining (D13) — order unambiguously against each other and, later, against records (D22), without trusting the timestamp the author sets (D13). A member's sequence is a small key event log of its membership state in the cell — the slot KERI fills. The two shapes — the act a device writes and the event a chain holds — are defined in the cell stores spec. Each replica is the authorization unit (who may sync it), the swarm topic and the reconciliation unit, exactly the roles ADR-0009 keeps for a namespace, and ADR-0009's case against a shared namespace — a set that is never quiescent, and work spent on entries the filter discards — does not apply inside a cell, since every member wants every entry and nothing is discarded; the two replicas share the audience — every member device — and differ in what they are: the membership store governs, the record store is governed, as the grants in a connection metadata store govern a data store. The price is a second replica per cell — a topic, a ticket, a reconcile pass — a fixed cost per cell, measured with D1'.

**Rejected alternatives:**

- One replica for all of an identity's cells.
  - **Cons:** a replica is the authorization unit, the swarm topic and the reconciliation unit (ADR-0009), and cells differ in all three.
- One replica, the membership material under a key prefix reconciled first.
  - **Cons:** the store orders entries by namespace, author, key, so a key prefix is a filter across every author's partition, not a range — reconciling it is subset-rbsr, whose fingerprint (`SessionStore::get_fingerprint`) walks every entry per round, on every session, before any record is judged; a cached fingerprint tree (D2') does not help a prefix.
- One role log for the whole cell under a single sequence.
  - **Pros:** orders events across members.
  - **Cons:** neither the record gate (D22) nor the membership gate (D23) needs that order; two events at one number still need a tie-break (B10).
- Membership state and role as last-writer-wins values.
  - **Cons:** a flip's order against another flip, or against a record, would rest on the timestamp the author sets (D13).

### D4. A record is a claim, a mergeable-document or an immutable-document

A **record** is what a member places into a cell, of one of three kinds chosen when it is placed. A **claim** is an assertion by an issuer about a subject — a driver's license, a parent's statement of a child's blood type. A **mergeable-document** is content the members edit — a note. An **immutable-document** is content placed once — a file. Every member reads every record: inside a cell there is no narrower audience, and "share with Carol and Dave but not Bob" is a different cell (D9). A claim and an immutable-document differ in what the record is — an assertion or content — and an immutable-document and a mergeable-document in mutability (D17); no two kinds differ in payload format: payloads stay opaque below pdn-layer, and a record's kind picks how its entries are laid out and who writes them, not what they contain. Membership events and device statements are the cell's bookkeeping, not records in this sense.

**Rejected alternatives:**

- One kind for the claim and the immutable-document, which share a shape on the platform (D17).
  - **Cons:** the two are expected to diverge as the product's UX is tested and its requirements redefined; one kind would then be split under content already placed.

### D5. Claims are immutable and written only by their issuer

A claim does not change after it is written — a changed assertion is a new claim. A claim placed in a cell is written only by its issuer.

### D6. Every member edits a mergeable-document

A mergeable-document is edited by every member — each operation is an entry signed by the device that wrote it, so who edited what is read from the entries themselves (D15) — and a claim or an immutable-document by no one (D5, D17). There is no sharing mode per record: no record is "shared read-only" or "shared read-write", and no act flips such a mode; and ownership (D11) changes nothing about editing — it changes deletion (D12). What takes editing away is removal: an operation is judged against the writer's membership state at the membership sequence the operation names (D22), so a member's operations from while it was a member stand on every device whenever they arrive, and an operation naming a sequence at which the writer was no member is dropped. The rights by role, one table per record kind, are in the pdn-node cells spec.

**Rejected alternatives:**

- A sharing mode per record — read-only or read-write — flipped over its life.
  - **Cons:** needs an encoding that survives the flip and a rule for who flips; a second access structure beside the roles.
- Editing another member's mergeable-document reserved to owners.
  - **Cons:** two plain members cannot write one note together; the per-operation signature already keeps every edit under its writer's name; a spoiled mergeable-document is repaired by an owner's deletion (D12).

### D7. Inside a cell, gossip replaces subset-rbsr

No egress filter: both stores are served whole to member devices, the membership store before the record store (D19); the members' devices are the swarm; a write becomes a content-free announcement that neighbours pull through reconciliation and pass on; catch-up after an outage is one session with any neighbour. With 100 members on 2 devices each — 200 nodes — an announcement reaches everyone in 3–4 hops of HyParView's active view, and catch-up costs one reconciliation of the difference. Subset-rbsr keeps its place for connections and personal namespaces.

**Rejected alternatives:**

- A replica per member inside the cell, the cell as the grant audience — "share without copying".
  - **Pros:** data stays with its issuer; grants stay per claim.
  - **Cons:** every member's content is a replica the reader reaches separately; grantees stay outside the swarm, so a live update needs a grant republish per item; a stream grows the grant record with every message.

### D8. A cell has a human-readable name that is not an identifier

Names repeat, including among one identity's cells. Only the cell id addresses a cell. The name is shared: the cell carries one name every member sees, set at creation and renamed by an owner; there is no per-member name on the platform. The name is a cell-level record (C8).

### D9. Several cells with the same members are ordinary

The member set does not identify a cell.

### D10. The platform knows no ontology

Below pdn-layer a cell entry is a key and opaque bytes. The platform reads from the key what it enforces: the cell, the member under whose name the record sits and the record's kind. What a payload says and what the application derives from it are the application's. This is the existing layering — the data layer treats tokens and payloads as opaque, the domain lives in pdn-layer — applied to cells.

### D11. A cell has owners

The creator is the cell's first owner — its founding event (D23). An owner makes any member an owner, and ownership is taken from a member only by another owner — no other act narrows the owner set. Removing a member from the cell — an owner or a plain member alike — is an owner's act: a member that is no owner removes nobody, so an owner is removed only by another owner. Inviting stays every member's act — a newcomer always joins as a plain member, and only an owner's grant makes it an owner — and leaving stays the member's own (D13). Ownership is a role inside membership: an owner is a member, and losing ownership does not touch membership. Beside the acts on membership, an owner deletes any record (D12); editing is every member's (D6). Members become owners and stop being owners repeatedly over a cell's life — an operating condition, not an edge case. The owner set lives in the membership store as made-owner and unmade-owner events in each member's sequence (D3, D21); the edges of the role are B10.

**Rejected alternatives:**

- Equal-rank membership, no roles.
  - **Cons:** no repair channel — records nobody may delete, states nobody may fix (D12, D14).

### D12. A member deletes its own records; an owner deletes any member's

A member deletes the records under its own name because they are its own. An owner deletes records of any member — its own, another current member's, a removed member's alike (D13) — because it is an owner. Deletion is the owners' repair power over content, and a deletion followed by a new record is how a claim or an immutable-document is replaced (D18); the mechanics are D24: the tombstone kills the record, its content and blobs go at once. Neither power writes under another member's name (D15).

### D13. Acting on a record does not depend on its member's membership state

The rights to act on a record are the same whether the member that placed it in the cell is a current member or a removed one. Leaving and removal change admission alone — sessions refused, entries naming a sequence at which the member was no longer a member dropped (D22) — and change nothing about what is in the cell or what members and owners may do to it: the member's own records stay, its operations on other members' mergeable-documents stay, no power over a member's records appears at its removal, and none disappears — the members edit and the owners delete a removed member's records as they do a current member's. A member that joins again writes again — new records, new operations, naming its new sequence — as any member, and its earlier records, naming its earlier sequence, resolve to it as they always did (D22). Members leave, rejoin and are removed over a cell's life, and the rules for its records read the same throughout.

### D14. Every reachable state is repairable by owners

No sequence of acts — joins, leaves, removals, ownership changes, edits, deletions — leaves the cell in a state its owners cannot repair from inside. Recreating the cell — a new store, re-invited members, re-uploaded content — is never the only way out. The converse holds too: no operation deletes a cell for every member, owners included — a cell ends by its members leaving, each forgetting its own copy, and a device that holds the store keeps it anyway (Invariant 2). The cell after its last leave — every member's chain ending in a left or removed event — needs no form of its own, and no device observes it, since leaving forgets both stores. Every rule in this design is measured against this invariant; the act that could strand it — the last owner gone — is the open edge (B10).

### D15. Authorship is forged by no one

A record's authorship is cryptographic — the author signature on its entries — and no role weakens it: a member edits another member's mergeable-document and an owner deletes another member's record, and each such entry carries its actor's own signature, so a mergeable-document's history reads who wrote what, and every act in a cell reads as the signed act of its actor. Where a record sits — the member under whose name it is placed — and who wrote each entry in it are two different things, and only the second is a statement about authorship. The binding of author keys to members stays what the member publishes (F2); signed claims per the KERI roadmap strengthen the same property.

### D16. A member's devices are announced by the member itself, under its announcement key

Each identity holds a device-announcement key pair, minted with the identity. The secret lives in its private metadata store at a fixed path and reaches every new device at linking, beside the store tickets; the cell's own write tickets sit there under per-cell kinds, which the identity's other devices open on demand (private metadata store spec). The cell holds two things about a member's devices: a join-time record binding the member's `PdnId` to its announcement public key — signed by the joining device, carried in the join dialogue, written by the inviter, its root the inviter's word exactly as D26 states, and for the creator the founding event (D25) — and the member's device-list statements: the member's devices with their author keys, a version counter inside the signed bytes, the whole statement signed by the announcement key over the prefix `pdn/cell-devices/v1` followed by the statement, the prefix keeping it apart from the founding event the same key signs (D25).

A statement is self-contained proof, so who writes it into the store does not matter: the gate judges an entry in the membership device area by the embedded signature against the announcement key from the join record, never by the entry's author. A freshly linked device therefore registers itself — it holds the write ticket and the announcement secret, writes the newest statement into its local replica of every cell the identity is a member of, and ordinary sync spreads it through the identity's own devices and through any member, with no waiting on anyone being online. Before syncing a cell replica, each of the identity's devices compares the replica's newest statement version against the private metadata store's and writes the newer one in — the sweep that heals an interrupted fan-out, a cell joined after a linking, and a device linked before the join.

Resolution is by the statement's version, never by entry timestamp: statements coexist, one entry per version (D21), the classifier builds the author-to-member map from the highest validly signed version, and a device writes only when its version exceeds the replica's — a lagging sibling neither displaces a newer list nor is displaced while it catches up. A statement that never left a dying device dies with the device it described; the converged list is the surviving devices' own. The announcement key with its versioned statements is the slot KERI's key event log fills later: KERI replaces the key, not the scheme (F2).

**Rejected alternatives:**

- A per-identity metadata store polled by acquaintances.
  - **Cons:** a replica tracked per acquaintance restores the topology D2 rejects and the per-store reconcile cost ADR-0009 counts; read tickets, once handed out, leak the device list to removed members forever.
- A private-store contact book as the gate's authority.
  - **Cons:** a binding asserted in one cell would judge entries in another, carrying the inviter's word beyond the cell it was spoken in.
- Announcements handed to a live member device.
  - **Cons:** in a two-member cell the other member sleeps for weeks, and a waiting announcement survives nowhere.
- The announcement key pair minted lazily, when the identity first creates or joins a cell.
  - **Cons:** two devices of the identity doing so while disconnected mint two key pairs, and the identity's cells then disagree on which key signs its device statements; at identity creation there is one device, so there is no race.

### D17. A mergeable-document keeps concurrent edits; an immutable-document is placed once

A mergeable-document is content whose concurrent edits are meant to be kept — a markdown note, a rich text as a JSON tree of text nodes: every edit is an operation, each operation an immutable entry under its own key signed by its writer, and the operations are merged by a CRDT above the data layer. An immutable-document is content placed once — a PDF file uploaded into the cell: one entry under one key, written by the member under whose name it sits and updated afterwards by no one, that member included; a changed file is a new record (D18). On the platform an immutable-document has the shape of a claim (D5) — placed once, deleted (D12), replaced by a new record — and differs from it in what it is to the product: content rather than an assertion (D4). Below pdn-layer a record's kind decides the key layout — one key for a claim or an immutable-document, one key per operation for a mergeable-document — and the admission rule: a claim or an immutable-document from the member under whose name it sits, a mergeable-document's operation from any member (D6); the merge algorithm and the payload encoding live above (D10).

**Rejected alternatives:**

- A record kind overwritten in place by the last writer.
  - **Cons:** loses one of two concurrent edits; an owner's overwrite leaves the member's name on the owner's content.

### D18. Replacing a claim or an immutable-document is deleting it and placing a new one

A claim (D5) and an immutable-document (D17) are updated in place by no one. A member replaces its own record because it is its own; an owner replaces any member's record because it is an owner (D12): the old record is deleted, and the new one is placed under the replacer's name — a new record with a new id, its issuer or placing member the replacer, so a member's record replaced by an owner becomes the owner's. References to the old record — links inside notes — stay on the old record and do not follow the new one. That such references break is accepted: a record's id names the member under whose name it sits (C10), so a record replaced under another name is another id. A mergeable-document is edited in place (D6) and its id stays. A replacement is two entries the store carries apart — the tombstone and the new record — so a device catching up holds, for a moment, both records or neither, and converges on the new one alone once both have arrived, with no act from anyone; that is the expected behaviour of a replacement under an unstable connection, not a fault.

### D19. The membership store is reconciled before the record store, and no filter runs inside a cell

A session between two member devices reconciles the membership store to convergence first, folds it into the write admission, and only then reconciles the record store under it; both by plain, unfiltered reconciliation — no capability filter (subset-rbsr) runs on either store, whatever the session peer. The order makes the common case exact: a newcomer's first records name a sequence the same session brings, so they are judged in that session (D22), and a role change the session brings is applied before the deletions that follow it are judged. The order does not remove the residue — membership still spreads through the swarm, so a record may reach a device before the membership event authorizing its author — and the residue heals as before: the entry is dropped and offered again by a later session. The gate stays synchronous and reads no replica: everything it needs is in the write admission folded at session setup.

**Rejected alternatives:**

- No order between the stores.
  - **Cons:** a record judged under stale membership is dropped and re-offered — a session of latency per newcomer write.
- A capability filter on the record store per session peer.
  - **Cons:** the audience is every member device, so the filter removes nothing and costs the linear fingerprint (D3).

### D20. Every member device holds the write ticket of both stores

Every member device holds both stores whole and holds their write tickets; write authority inside a cell is the gate's, judged per entry (D6, D12, D17), never the ticket's mode. Any member edits other members' mergeable-documents (D6), an owner deletes other members' records (D12), and every member relays what it holds (D7). A removed member keeps the write tickets it held: honest devices refuse its sessions and drop the entries it authors under a sequence at which it was no longer a member (D13, D22), which is the whole of removal under bearer tickets — an entry it authors afterwards under an earlier sequence is the retrograde case D29 accepts; UWill takes write authority out of the ticket (D28, F3).

**Rejected alternatives:**

- A read-only ticket for plain members.
  - **Cons:** editing other members' mergeable-documents and relaying what one holds are every member's, and a read-only ticket allows neither.
- A ticket per role.
  - **Cons:** re-cut at every role change (D11).

### D21. The key layout of both stores

The membership store: `member/<pdnid>/<seq>/<kind>/<aseq>` — the member's membership events (D3): founded, joined, left, removed, made-owner, unmade-owner, with `<aseq>` the actor's own sequence at the time (D23), so the gate reads the kind and the actor's point from the key as it reads a record's from its key; `member/<pdnid>/devices/<version>` — the device-list statements (D16), one entry per version, resolved by the highest validly signed version. Every membership-store entry is written once: an entry under a subject sequence the write admission already shows held by the same author is dropped — the whole store is in the write admission, so the check costs nothing — and two authors' events at one sequence both stand until B10's tie-break. The membership store holds no tombstones. The record store: `by/<pdnid>/claim/<id>/<mseq>` — a claim; `by/<pdnid>/immutable-document/<id>/<mseq>` — an immutable-document, one entry; `by/<pdnid>/mergeable-document/<id>/<op>` — one entry per operation of a mergeable-document, where `<op>` is the writer's author key, the writer's membership sequence and the writer's own operation sequence, so two writers' operations never share a key and one writer's never collide. `<mseq>` is the sequence of the writer's own membership events at the time of writing — the state the entry is judged against (D22). A record's identity is its key without that trailing sequence (C10). `<pdnid>` is the member under whose name the record sits — the identity, not a device, so the key outlives the devices that write under it. The gate reads from the key what it enforces (D10): the member and the record's kind; it reads from the entry only its author and whether it is empty — a tombstone (D24) is the store's empty entry at a record's key — the content keys without their last segment — and so carries no membership reference (D22). Everything else — a record's title, a replacement's reference to what it replaced — is payload. An entry whose key fits neither layout, or fits one only in part, is kept and used by nothing (D27).

**Rejected alternatives:**

- The writer's author key as the key prefix.
  - **Cons:** devices come and go while the member stays — a record keyed by a device moves with every linking; the author-to-member map already bridges the two.

### D22. A record names the membership state it was authored under, and is judged against it

Every content entry in the record store names, in its key (D21), the sequence of its writer's own membership events at the time of writing. The gate judges the entry against the writer's event log folded up to that sequence, held in the write admission: a claim or an immutable-document is admitted if the writer was a member at that sequence, a mergeable-document's operation likewise, and an entry naming a sequence the device does not yet hold is dropped and offered again once the events arrive (D19). The question the gate asks is "was this allowed at that point", never "is it allowed now", so an entry is judged the same on every device whenever it arrives: a departed member's entries from while it was a member reach a device that catches up after the departure, and a member's entries resolve to it across leaving and rejoining (D13). Sessions stay as of the session — a departed member's devices are refused (D20). Tombstones are the exception: the store's empty entry carries no reference, so a deletion is judged as of the session (D13); a deletion by an owner whose ownership was taken meanwhile is dropped, the record stays, and a current owner deletes it again.

The reference proves that the entry is after the named event, not that it is before the next one: a departed member can author a new entry naming a sequence at which it was a member and have a member relay it, and the gate admits it — the retrograde direction of anchored signatures, accepted until KERI (D29). Judging every entry the same on every device is taken at that price.

**Rejected alternatives:**

- Judging a record as of the session.
  - **Pros:** keeps a departed member's new writes out.
  - **Cons:** loses its old ones on every device that was not there.
- The membership reference in the payload.
  - **Cons:** the gate reads no payload — content arrives apart from the entry, possibly later — and a tombstone has none.

### D23. A membership event names its actor's sequence, and the store verifies from the founding event

Every membership event names, in its key (D21), the sequence of its actor's own events at the time of acting, and is judged against the actor's chain folded up to that point: a joined event needs the actor a member there, a removed, made-owner or unmade-owner event an owner, a left event the subject itself; the founding event — the creator's first, self-authored, making the creator a member and an owner at once (D11) — needs only to derive the cell id (D25) and is the root every verification ends at. The writing device picks both numbers from what it holds: the event goes at the sequence after the highest it holds in the subject's chain, and names as its actor's point the highest sequence it holds in the actor's own chain; two actors disconnected from each other can therefore write at one sequence of one subject, the case B10 settles. The verdict is a function of the event set and the cell id alone, so every device reaches the same membership from the same events whatever order they arrived in, and a device holding nothing — a newcomer's, a freshly linked one — verifies the whole store from the founding event in its first session. Within a session the gate re-judges an event it had to defer once the events it depends on are admitted, so a session that brings a dependency brings what depends on it; what a session cannot resolve is offered again by the next (D19). The date in an entry is written by its author and shown to people; the gate never reads it, now or later — order is the sequence, and an anchored log (D29) proves order, not dates.

What the reference proves is, as for records (D22), that the event is after the actor's named point, not before the point at which the actor lost its membership: the retrograde direction stays open until the KERI roadmap gives each actor a hash-linked log that commits to its own acts (D29).

**Rejected alternatives:**

- Membership events judged as of the session.
  - **Cons:** a device holding nothing has nothing to judge by, so a newcomer's first session drops every event; a device catching up after an owner's demotion drops what that owner did while an owner — memberships diverge.

### D24. Deleting a record kills it: its content goes at once, and no content for it is admitted again

A tombstone is the store's empty entry at a record's key — `…/<kind>/<id>`, the key of its content entries without their last segment (D21) — admitted from a device of the record's member or of an owner (D12), as of the session (D22). The record store knows its key layout and maps a content entry to its record by dropping the last segment of its key. Once a tombstone is admitted, the record store removes every author's content entries of that record and releases their blobs the moment nothing references them, and from then on refuses at ingest every content entry of that record, whatever its timestamp — one lookup of the record's key, apart from the gate, which stays synchronous and reads no replica (D19). That is safe because a record's key is written once and a replacement is a new key (D17, D18), and a mergeable-document's operations die with the document. The tombstone entry itself stays, as the element of the set that reconciliation compares: a peer holding the content and not the tombstone converges on the deletion instead of offering the content back.

The rule belongs to the record store alone. The store beneath carries no relation between keys: an entry, empty or not, affects only its own key, in every replica — so a directory's tombstone at `connections/<P>` leaves that key open for a later connect, a non-empty entry at a record's key erases nothing, and an entry outside the record layout touches nothing (D27). The store offers the two primitives the rule builds on: removing every author's entries at one key with their blobs, and looking one key up at ingest. This is the change in pdn-store this design makes.

**Rejected alternatives:**

- The store's read-side deletion as it is today — an empty entry removes only its own author's older entries under the prefix, other authors' entries stay and are hidden on read by the newest timestamp across authors.
  - **Cons:** deleted content and its blob stay on disk until a collection nobody schedules; a content entry with a newer self-set timestamp resurrects a deleted record (D13).
- Prefix semantics in the store — an empty entry removing every author's entries under its key, a dead prefix admitting nothing more.
  - **Cons:** an entry at a short key or at a key a later layout gives meaning — `by/`, `by/<M>/` — reaches entries it was never meant for; a non-empty entry at a record's key erases its own author's operations under it; the rule holds in every replica, so a dead `connections/<P>` in a directory forbids a reconnect.
- A tombstone at every content key.
  - **Cons:** deleting a mergeable-document is one tombstone per operation, and an operation written while disconnected after the deletion arrives later and brings back a fragment of the document.
- A signed deletion record with a key of its own, judged at its actor's point (D22).
  - **Pros:** gives a deletion a membership reference.
  - **Cons:** a deletion is a repair act judged when it lands; the empty entry is what reconciliation already carries.

### D25. The cell id is derived from its creator's announcement key and a random nonce

At creation the creator's device draws a 16-byte random nonce and derives the cell id as the first 16 bytes of BLAKE3 in its key-derivation mode, under the context string `pdn/cell-id/v1`, over the creator's `PdnId`, the creator's announcement public key (D16) and the nonce — BLAKE3 being the hash iroh and pdn-store already use, and the context keeping this derivation apart from any other hash of the same bytes. The founding event carries those three fields and a signature by the announcement secret over the prefix `pdn/cell-founding/v1` followed by the three, the prefix keeping it apart from the device-list statements the same key signs (D16). A device holding the cell id — from its identity's directory, an invite or a link in a note — admits a founding event only when its three fields derive that id and its signature verifies under the key it names, and drops every other founding event whatever order it arrives in; a device holding nothing checks the root of the membership store against the id it already holds (D23). A newcomer learns the id from its inviter, as it learns everything else at join (D26). Without the founding event, which only member devices hold, the id reveals nothing of its creator. The id is 16 bytes, the size of a UUID, written as text as 32 lowercase hexadecimal characters, and the byte-id type in pdn-types is defined to that size. The id travels in notes to other cells' members, so it never equals either store's namespace id, the read capability (Invariant 3). With KERI the creator's autonomic identifier takes the announcement key's place in the derivation.

**Rejected alternatives:**

- A random cell id, such as a UUID v4.
  - **Pros:** embeds nothing.
  - **Cons:** a device holding nothing takes the root from whoever serves its first session — a member's freshly linked device that catches up first from a modified member device is handed an invented founder, drops the real founding event as a second one on arrival, and stays in the invented cell for good, deleting records on the invented owner's tombstones (D24).
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

Any member's device mints an invite — a QR code or an invite link carrying the inviting device's address, a one-time short-lived secret and the cell id, no ticket. The newcomer's device dials the inviting device on a dedicated ALPN and presents the secret; the inviting device verifies and burns it before any state changes, receives the newcomer's signed join record (D16), writes the joined event and hands over both stores' write tickets — the shape of the linking dialogue (ADR-0012). Both devices are online at once and reach each other through iroh relays, which the stack takes on in a change of its own: two devices on different networks without a relay and without DNS do not reliably reach each other. Whoever presents a live secret first joins under the `PdnId` it names; the `PdnId` is the inviter's word, and proving it is the invited identity is KERI's proof step — challenge-response and an exchange of key event logs — in the same dialogue, the slot pairing and linking keep for it; until then that gap is accepted. Inviting a party that is offline is pending-invite machinery with polling, which ADR-0011 leaves possible and a later change builds.

**Rejected alternatives:**

- An invite record carried over an existing channel with the newcomer — a connection or a common cell — the stores' tickets inside an Invariant-3 store as data tickets travel.
  - **Pros:** no simultaneous presence; addressed to the newcomer's identity, so there is no secret to intercept.
  - **Cons:** reaches only a party already connected or sharing a cell, so a first contact needs the dialogue anyway; the join completes only when a member device next sees the newcomer's answer.
- Both paths.
  - **Cons:** two join paths to build, test and keep in step, where pending invites give the dialogue the same reach to an offline party.

### D27. An entry outside the key layout is kept, used by nothing, and surfaced

An entry in either store whose key fits neither layout of D21 — or fits one only in part, such as a mergeable-document key without its operation segment — is admitted when its author resolves to a member device, as of the session, and then reconciled, held and relayed like any entry. Nothing on the platform reads it: no fold, no gate verdict, no record view. The record store lists such entries with their authors, and the application shows that the cell holds entries it does not understand. Because no entry affects another key (D24), holding one harms nothing else in the store, and every member device converges on the same set.

**Rejected alternatives:**

- Dropping it at ingest.
  - **Cons:** the replicas never converge — every session with a device that holds the entry reconciles the same difference again, each round a linear fingerprint scan; a cell whose devices run two versions of the layout drops on the older what the newer writes.
- Failing the session.
  - **Cons:** the session fails again every time, and the peer's other entries — its own and those it relays — stop with it; a two-member cell stops syncing; honest devices hold no such entry, so it reaches a device only from the device that holds it, and failing protects nothing that dropping does not.

### D28. Every member is trusted with the whole cell

A member reads every record, holds both stores and their write tickets, and relays what it holds; what it does under its own name — what it leaks, the storage it fills, the entries it keeps outside the key layout (D27) — no rule of the platform limits. The gate protects honest members from a dishonest member's forgeries — an entry under another member's name, an act its role does not allow — and from nothing else. Real expulsion under bearer tickets is a new cell (D20).

### D29. Provably before comes with KERI; until then the retrograde direction is accepted

A record's membership reference (D22) and a membership event's actor reference (D23) prove that the entry comes after the point it names; nothing proves that it comes before the point at which its writer or actor lost its membership. A departed member therefore authors new entries under its old sequence and has any member relay them, and the governance case follows: a demoted or removed owner, with a plain member relaying, rejoins and re-promotes itself by naming a sequence at which it was an owner — a plain member and a former owner together do what the rules reserve to an owner. A rewrite of an actor's own past event that reaches a device before the original stays there, and that device then refuses the original. The self-asserted timestamp does not close the direction (D13, D23), and capability-bound writes do not close it alone, since an entry signed under a since-revoked capability poses the same question. What closes it is an actor's log that commits to the actor's own acts and cannot be appended to in the past — KERI's hash-linked key event log, with its detection of one actor contradicting itself (F4). Until KERI the direction is accepted, as real expulsion under bearer tickets is already a new cell (D28). A fork several actors write at one sequence of one subject is outside what KERI settles and keeps the rule of B10. The cell stores spec pins what the gate does meanwhile, in scenarios named after this decision.

**Rejected alternatives:**

- A removal that commits to the departed member's contributions — a per-author high-water mark on the operation sequence, or a Merkle root over the author's range.
  - **Cons:** the high-water mark needs a uniqueness the gate cannot check without the record store; the Merkle root needs the cached fingerprint tree (D2').
- Witnessing — a current member's signed commitment to the entries it accepted.
  - **Cons:** history then travels under the witness's authority, a trust structure of its own beside membership.
- Hash-linked membership sequences built ahead of KERI.
  - **Cons:** detecting one actor contradicting itself is KERI's duplicity handling, taken with its key event log rather than built twice; concurrent events at one sequence are ordinary and stay with B10 either way.

### D30. Cells stand beside connections, grants and per-issuer namespaces, and touch none of them

Cells are built in parallel with what exists. Connections, grants, subset-rbsr and per-issuer namespaces keep working as they do, and nothing in a cell rests on them: a cell's stores carry no grant, a grant names no cell as its audience, and cell content never flows into a personal namespace or out of one through a grant. A two-member cell and a connection coexist, one a copy into a common space and the other a grant on one's own data. Once cells prove themselves in practice — the mobile application's integration included — connections go entirely, with the machinery that serves only them; until then both stay.

**Rejected alternatives:**

- Connections as two-member cells now.
  - **Cons:** replaces a working path with one not yet tried in the product, before the mobile application runs on it.
- The cell as an audience of grants on personal namespaces — "share without copying".
  - **Cons:** ties the new primitive to the machinery it may replace, and carries a grant's per-claim bookkeeping into every cell.

## Risks / Trade-offs

- [Every member holds the whole cell in plaintext] → accepted by definition; content encryption is a separate layer; the trust boundary is the member set (D28).
- [A removed member keeps both stores' write tickets and topic ids] → honest devices refuse its sessions and drop the entries it authors under a sequence at which it was no longer a member; an entry it authors afterwards under an earlier sequence passes until KERI closes the retrograde direction (D29); it retains what it received and still sees content-free announcements; real expulsion under bearer tickets is a new cell. UWill takes write authority out of the ticket (D13, D28, F3).
- [Membership is a multi-writer set] → its records order by per-member sequence numbers, never by timestamp (D3, D21); a concurrent add and remove, or grant and revoke, at one sequence needs a tie-break (B10); a member-signed founding chain gives membership a root but no total order.
- [Authorship is a transport-level binding] → author keys are node-local; the binding of an author key to a member is what the member publishes under its announcement key (D16), verifiable by anyone holding the join record; an honest gate enforces it; a modified member device can forge locally but cannot pass honest gates under another member's name; what it can still do under its own name after departing is D29. Signed claims come with KERI (F2).
- [Range fingerprints are linear scans] → a record store with 100 writers is never quiescent, so every catch-up session scans it per round; a cached fingerprint tree in pdn-store is the fix (D2'), and the membership store's convergence does not wait for it (D3).
- [A membership reference proves after, not before] → a departed member's new entries under its old sequence pass through a relaying member (D29); accepted as the price of judging every entry the same on every device (D22).
- [Dates in entries are self-asserted] → written and shown, never judged (D3, D22, D23); order is the sequence, and "provably before" is D29.
- [The membership store only grows] → events are never deleted; a member's sequence is a handful of events over a cell's life, and the store stays tiny beside the records (D3).
- [Storage per device grows with every cell] → records replicate everywhere; payloads can follow a download policy (D5').
- [Reachability] → the stack is relay-free today, and two devices on different networks without a relay and without DNS do not reliably reach each other — a join fails and a swarm fragments; iroh relays come in a change of their own (D3', D26).
- [Concurrent editing loses edits] → a mergeable-document keeps every operation under its own key and merges them above the data layer (D17); an immutable-document is never edited, and two members replacing one at once leave two new records under two names, visible to everyone and resolved by people (D18).
- [The join is bearer-level] → the invitation carries no ticket and the secret burns on first use, but whoever presents it first joins under the `PdnId` it names — asserted, not proven; accepted until KERI's proof step slots into the same dialogue (D26).
- [An owner deletes another member's records] → accepted as the repair channel (D12, D14); the deletion is the owner's own signed act and forges nothing (D15), and a hostile owner sits inside the trust boundary already (D28).
- [Any member edits any mergeable-document] → accepted: every member is trusted with the whole cell already (D28), each operation carries its writer's signature (D15), and a spoiled mergeable-document is repaired by further operations or by an owner's deletion (D12).
- [A replaced record breaks references to the old one] → accepted (D18); the deletion and the new record are two signed acts of the replacer (D15).

## Migration Plan

Additive: no existing store, ticket, grant or record changes shape — the directory gains the cell kinds and the announcement key pair — and a runtime without cells behaves as before. The store's prefix deletion goes (D24): every existing delete already addresses one key, and the directory's pruning of an issuer's retraction markers deletes them one by one. Rollback is forgetting cell stores; nothing else depends on them. No migration: the platform has no real users, so an identity created before this change, which holds no announcement key pair, is not carried over.

## Open Questions

Grouped; each names its options and, where the team leans somewhere, the leaning — none is decided; a question answered since its posing leaves the list, its answer recorded as a decision.

### B. Membership

- B10. Ownership at the edges. Every rule here has to be one every device reaches from the events alone, in any arrival order, never from timestamps (D3, D23).
  - Two owners' events at one point of one subject — a made-owner and a removed at B's sequence 5. A concurrent add and remove of one member is this case.
    - (a) Narrowing wins: among the events at one point, the most restrictive state takes effect — removed over unmade-owner over left over made-owner over joined. A concurrent removal and promotion leave B removed, and a re-invite undoes it if it was wrong. Fail-closed, the gate's own habit, and no author's key decides. **Leaning.**
    - (b) The lower author key wins: deterministic, meaningless, luck of the key.
    - (c) Both stand and the fold applies them in author-key order: (b) in another form, since a made-owner after a removal is a transition of no member and is ignored.
    - (d) The fork stands unresolved, and B's state is the conservative one until a later event supersedes both: a later event names its actor's point, not a branch of B's chain, so nothing ever picks a branch.
  - The last owner leaving a one-owner cell that has other members.
    - (a) Refused with a typed error until the owner makes another member an owner. Explicit; a one-member cell's owner leaves by forgetting, and the cell ends with it, D14 having no subject left to protect. **Leaning.**
    - (b) Allowed, the member with the lowest join sequence becoming an owner by rule: repairability kept, but ownership appears without an owner's hand, against D11.
  - Mutual demotion — owners A and C unmake each other at once. Two events on two subjects, each valid at its actor's named point, no collision at one number, and the owner set empties; a fold that walks one member's chain at a time cannot see a cell-wide count.
    - A fold-time guard over all chains: an unmade-owner that would leave the cell with no owner is ignored, and when two would jointly do so, the one whose actor has the lower key stands. **Leaning.**
    - A member that cannot be unmade — the creator as a root owner, which D11 rejects.
  - The same event twice at one point from two owners — two made-owners of B at sequence 5: the same transition, applied once.
  - The last two owners leaving at once, while disconnected from each other. The refusal of the second case runs on the writing device, and each device still sees the other owner, so both left events stand and the owner set empties. Ignoring one of them does not help: that member has forgotten both stores and would stay an owner who holds nothing.
    - (a) An owner's leave completes only once another owner's device has acknowledged it, so two concurrent leaves wait on each other; an owner that is never online again blocks the other's leave.
    - (b) When the owner set empties through concurrent left events, the member with the lowest join sequence becomes an owner by rule: against D11, as in the second case, but only for this race.
    - (c) Accepted: the cell stays without an owner — members read and edit, nobody removes a member or deletes another's record — and a new cell is the way out, against D14 for this edge.
  - The last owner losing every device. No event is written, the owner stays listed, and nobody acts as an owner.
    - (a) Recovery through the identity: KERI's pre-rotated keys restore control of the identity on a new device, which signs its device statement under the rotated key in the announcement key's slot (D16); the owner's chain holds no left event, so the role stands. The directory holding the cell's tickets is lost with the devices, so this also needs a path by which any member hands the cell's tickets to a device of an identity proven through KERI, writing no joined event — a rejoin makes a plain member (D11).
    - (b) An owner silent past a bound loses the role to the longest-standing member: silence is measured by time, which the fold never reads (D23), so no device derives this from the events alone.
    - (c) Accepted, as in the concurrent leave: the application encourages every shared cell to keep at least two owners.
- B12. A member removed while its devices were offline learns nothing of it. Honest devices refuse its sessions as for an unhosted store and hand it no removal event (cell stores spec), and once no member is left there is nobody even to refuse; either way its device shows a cell whose members seem offline, and it keeps writing entries nobody receives. Options: serve a removed member's device its own removal event before refusing — the cell's existence is no secret to it; or leave it to the application, which shows a cell unsynced for long as stale.
- B13. A leave reaching the leaving member's own devices. Leaving forgets both stores on the member's devices, but a device offline at the time learns of the leave only by syncing, and the cell's stores may have no member left to sync with; the left event itself has to reach another member before the leaving device forgets, or it exists nowhere and the member stays listed. Options: the leave also tombstones the cell's ticket kinds in the identity's directory, so a sibling forgets the cell when the directory syncs; the leaving device forgets only once another member's device has acknowledged the left event, or after a bound; or both.

### C. Content

- C5. The merge of a mergeable-document: which CRDT serves markdown and which the rich-text JSON tree, whether pdn-layer or the application runs the merge, and the operation encoding.
- C6. Files: attachments as blobs; lazy payloads through the fork's download policy; size limits; a rename or move as a new key plus a tombstone.
- C8. The cell's name (D8): a cell-level entry outside every member's `by/<pdnid>/` prefix, written by owners — its key, the store it sits in, and how two owners' concurrent renames resolve.
- C10. Record identity: derived from the cell id, the member under whose name the record sits and the path inside the cell without the trailing membership sequence (D21) — the form D18 assumes, a record replaced under another name being another id — or from the replica and the key as in data stores. It matters if a one-member cell is ever promoted from a personal namespace (D1').
- C13. A second version of a claim or an immutable-document at a record the cell already holds. Placing on top of a record is refused on the writing device, and a version under another member's name is dropped at the gate; two sources remain — a modified device of the member itself, and two of its devices placing one id while disconnected from each other, which happens only when the id is not a fresh one the service mints (C10).
  - Today: nothing on reconciliation checks whether the record is taken. An entry at the same key with a newer timestamp replaces the older on every device and keeps the id, so references to the record silently show the new content. A version at the same id under another `<mseq>` is another key: both stand, and which one reads is undefined.
  - (a) Refused everywhere: the record store refuses content for a record that already holds content with another hash. Claims and immutable-documents become truly immutable, and both paths close. But a member that placed two versions leaves one on some devices and the other on the rest, for good — every session offers the other version again and has it refused (D27's case against dropping) — repaired only by an owner's deletion.
  - (b) Last writer wins on reconciliation: within one record, the newest timestamp from any device of its member wins, and older versions go with their blobs; `<mseq>` stays. Every device converges on one version, and only the member's own devices contend over timestamps. But an honest collision silently loses one version; the rejected alternative of D17 and D24's "a record's key is written once" need rewriting; and D29's gap widens — a departed member naming its old sequence rewrites its old records in place. The access tables would then read: no update on the writing device, and the newest version winning on reconciliation, so a modified device of a member rewrites that member's own claims and immutable-documents.
  - What the choice turns on is C10: with a fresh id the service mints, as `put_record` does, two devices of one member never meet at one id, there is no honest collision, and (b) rests on convergence alone; with an id that is a file path or a well-known name, the collision is real — one file placed from a phone and a laptop while disconnected — and (b) resolves it by losing one version.

### D. Sync and scale

- D1'. One-member cells: a pair of replicas from birth — D3 read literally, hundreds of pairs per device for a full personal tree, each replica its own swarm and its own reconcile pass — or key prefixes in the identity's own namespace promoted to a replica at the second member, which is a data move and raises C10. Leaning: from birth; measure.
- D2'. The linear-scan range fingerprint in the fork: when to replace it with a cached fingerprint tree; with two stores per cell the tree serves each store over its own order (D3).
- D3'. Reachability beyond relays (D26): always-on member devices as de-facto hubs.
- D4'. Swarm and cadence parameters for 200 nodes: active and passive view sizes, the reconcile interval, churn of mobile devices.
- D5'. The download policy default for record stores: records everywhere, payloads on demand.
- D6'. Clocks: chat ordering by writer timestamps under the fork's 10-minute future window.
- D7'. Storage: a quota per cell on a device; a disk that fills mid-sync.

### F. Security

- F2. The author-key-to-member binding: published by the member itself (D16); what a device does when two members claim one author key, or when two validly signed statements of one member conflict at one version. Two members claim one author key whenever one node hosts both: every store on a node writes with the node's one author (`SyncNode::default_author`), so both members' device statements list that key. An entry the node writes under either member's name then passes as that member's, and a membership act, whose actor is resolved from its author key, resolves to two members — an owner's act can be judged as a plain member's and dropped. The node holds both identities' secrets, so the question is attribution on honest devices, not a defence against the node. Options: an author key per hosted identity, at least for cell stores; or the actor named in a membership act's key beside `<aseq>`, the author key checked against that actor's statements.
- F3. Each store's topic id equals its namespace id, known to removed members forever: content-free announcements leak activity; a cell that must shed a member entirely moves to a new store.
- F4. Equivocation among members: with n parties the pairwise "first seen wins" of the KERI roadmap is not enough; duplicity detection moves earlier in that roadmap. A member rewriting its own past event is the same problem inside the membership store (D29).
- F5. Linkability: one `PdnId` across cells; per-cell pairwise identities (the KERI roadmap's later step).

### G. Operations

- G1. Restart: cells re-derived from each hosted identity's directory, or recorded beside the hosted identities.
- G2. Observability: metrics for cell sessions, drops at the gate, swarm size; and the deferred membership events with the point each waits on, listed per cell — the only way anyone learns that an act has to be made anew by a current owner (D23, cell stores spec).
- G3. The HTTP host and the container stand: which cell operations the demo surface exposes.
