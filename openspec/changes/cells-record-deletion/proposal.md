# Proposal: cells-record-deletion

## Why

A cell's record store holds claims, immutable-documents and mergeable-documents under `by/<pdnid>/<kind>/<id>/…`, and no record leaves it: the cells service places records and appends operations, and nothing deletes one ([cell stores](../../specs/components/mee-pdn/data-layer/cell-store/spec.md), [pdn-node cells](../../specs/components/mee-pdn/pdn-node/cells/spec.md)). Content placed by mistake, a member's junk and a departed member's records stay for every member for as long as the cell lives, the owners have no way to remove content, and a claim or an immutable-document is never replaced: a corrected one sits beside the old one. The store beneath does not supply the deletion: an entry, empty or not, affects only its own key, the store keeps one entry per author at a key, and a record's content is spread over keys and authors — one key per operation of a mergeable-document, one author per device that wrote.

**Example:** in "Family", Bob places a lease scan by mistake, Carol, since kicked, left 200 claims nobody wants, and Alice, an owner, has a corrected claim of her son Tom's blood type after a new test.

| | in the cell |
|---|---|
| Bob's scan | stays for every member, its blob on every member device |
| Carol's 200 claims | stay |
| Alice's corrected claim | placed beside the old one: both read, and nothing says which is current |

## What Changes

The direction is set, and the change specifies and builds it; three questions stand open under Open Questions.

### Who deletes

A member deletes the records under its own name because they are its own. An owner deletes records of any member — its own, another current member's, a departed member's alike, since the rights to act on a record do not depend on its member's membership state — because it is an owner. Deletion is the owners' repair power over content, and every reachable state becomes repairable by the owners, content included. Neither power writes under another member's name: the tombstone carries its writer's own signature, the deletion is the owner's own signed act and forges nothing, and a hostile owner sits inside the trust boundary already. A tombstone is judged as of the session: it carries no membership reference, so the gate asks whether its author's device is the record's member's or an owner's in the write admission the session was set up with. A session reconciles the membership store before the record store, so a role change the session brings is applied before the deletions that follow it are judged: a tombstone written after a demotion that the same session brings is dropped in that session.

**Example:** tombstones in "Family", where Alice is an owner, Bob and Carol are plain members, and Dave left.

| tombstone on | by Alice | by Bob | by Carol |
|---|---|---|---|
| Bob's claim | admitted | admitted | dropped |
| Carol's lease scan | admitted | dropped | admitted |
| Dave's note | admitted | dropped | dropped |

The rights tables of the cells service gain, for each record kind, "Delete own …" — every member — and "Delete another member's …" — an owner alone; the service gains `delete`, and the HTTP host its route, `DELETE …/records/{member}/{kind}/{id}`, whose refusal by role is a client error.

### Replacing a claim or an immutable-document

Neither is updated in place by anyone. A member replaces its own record because it is its own; an owner replaces any member's record because it is an owner: the old record is deleted, and the new one is placed under the replacer's name — a new record with a new id, its issuer or placing member the replacer, so a member's record replaced by an owner becomes the owner's. References to the old record — links inside notes — stay on the old record and do not follow the new one; that such references break is accepted, since a record's id names the member under whose name it sits. A mergeable-document is edited in place and its id stays. Two members replacing one record at once leave two new records under two names, visible to everyone and resolved by people. A replacement is two entries the store carries apart — the tombstone and the new record — so a device catching up holds, for a moment, both records or neither, and converges on the new one alone once both have arrived, with no act from anyone.

**Example:** Alice, an owner, replaces Bob's lease scan; `<alice>`, `<bob>`: 64 lowercase hex chars of each `PdnId`; `<lease>`, `<new-lease>`: the ids `put_record` minted for the old scan and the new one.

```
before     by/<bob>/immutable-document/<lease>/1           Bob's scan
Alice      by/<bob>/immutable-document/<lease>             the tombstone: empty, a1's author
           by/<alice>/immutable-document/<new-lease>/1     her new scan, a new record under her name
after      Bob's scan gone with its blob; the new scan read as Alice's; a note linking <lease> links a deleted record
c1         Carol's phone takes the new scan in one session and the tombstone in the next: holds both scans in between, then Alice's alone
```

### Deleting a record kills it

A tombstone is the store's empty entry at a record's key — `…/<kind>/<id>`, the key of its content entries without their last segment. The record store knows its key layout and maps a content entry to its record by dropping the last segment of its key. Once a tombstone is admitted, the record store removes every author's content entries of that record, whose blobs leave the device at the node's next blob collection once nothing references them, and from then on refuses at ingest every content entry of that record, whatever its timestamp — one read of every author's entries at the record's key, empty ones included, apart from the gate, which stays synchronous and reads no replica. The read takes every author's entries, never the newest entry across authors: a later non-empty entry at the record's key from another author would be the newest. That is safe because a record's content keys are written once and a replacement is a new key, and a mergeable-document's operations die with the document. The blob store is the node's, one under every hosted identity's replicas, so a blob is released once no replica of any identity the node hosts references it: a co-located member's copy of the record keeps it until that replica takes the tombstone too, which the in-process path brings at once. The tombstone entry itself stays, as the element of the set reconciliation compares: a peer holding the content and not the tombstone converges on the deletion instead of offering the content back.

The rule belongs to the record store alone: the store beneath keeps carrying no relation between keys, so a directory's tombstone at `connections/<P>` leaves that key open for a later connect, and an entry outside the record layout touches nothing. pdn-store gains the two primitives the rule builds on — removing every author's entries at one key, and reading every author's entries at one key, empty ones included, at ingest — which changes the fork and brings the stress pass of the flaky-tests practice with it.

**Example:** in "Wedding", Erin, an owner, deletes Bob's scan of the venue contract from her phone e1, and Alice's tablet a3, hosting Alice-leisure and Alice-work, both members, takes the tombstone.

| step on a3 | Alice-leisure's replica | Alice-work's replica | the scan's blob |
|---|---|---|---|
| before | holds the scan | holds the scan | kept |
| Alice-leisure's replica takes the tombstone from e1 | removes the scan, keeps the tombstone | holds the scan | kept: Alice-work's replica references it |
| the in-process path brings the tombstone to Alice-work's replica | tombstone | removes the scan, keeps the tombstone | released |
| Bob's phone b1, which missed the tombstone, offers the scan, whatever its timestamp | refuses it at ingest | refuses it at ingest | stays released |
| b1 then takes the tombstone from a3 and removes its own copy of the scan. | | | |

**Rejected alternatives:**

- The store's own deletion alone — an empty entry replaces only its own author's older entry at its key, other authors' entries stay and are hidden on read by the newest timestamp across authors.
  - **Cons:** deleted content and its blob stay on disk until a collection nobody schedules; a content entry with a newer self-set timestamp brings a deleted record back.
- Prefix semantics in the store — an empty entry removing every author's entries under its key, a dead prefix admitting nothing more.
  - **Cons:** an entry at a short key or at a key a later layout gives meaning — `by/`, `by/<M>/` — reaches entries it was never meant for; a non-empty entry at a record's key erases its own author's operations under it; the rule holds in every replica, so a dead `connections/<P>` in a directory forbids a reconnect.
- A tombstone at every content key.
  - **Cons:** deleting a mergeable-document is one tombstone per operation, and an operation written while disconnected after the deletion arrives later and brings back a fragment of the document.
- A signed deletion record with a key of its own, judged at its actor's point.
  - **Pros:** gives a deletion a membership reference; the first open question below reopens it.
  - **Cons:** a deletion is a repair act judged when it lands, and the empty entry is what reconciliation already carries.

The tests pair each access in one place: an owner's tombstone removing a record, its content and its blob on every device beside a plain member's dropped; a member deleting its own beside another member's refused; a kicked member's record deleted by an owner beside a plain member, the kicked member itself and an outsider dropped; a content entry with a newer timestamp refused for a deleted record; a peer that missed the tombstone converging on the deletion; a mergeable-document's operations gone with it; a role change applied before a deletion the same session brings is judged; an immutable-document replaced concurrently by two members leaving two records under two names; an empty entry at `by/<B>/` deleting nothing, and a non-empty entry at a mergeable-document's key erasing none of its operations. The container stand's paired denial gains the creator's deletion of its own claim beside a plain member's deletion of another member's.

## Open Questions

### A tombstone its writer placed before learning of its demotion

A tombstone is judged as of the session: a device that already holds the writer's demoted event drops it, while the writing device, which applied it on writing, and every device that took it before the demotion arrived have removed the record's content and released its blob, and refuse the content at ingest from then on. The cell splits for good into devices that hold the record and devices that refuse it, so a member whose devices are on the second side never reads a record every other member reads; a current owner's repeat deletion brings every device to the record's absence, but the demoted owner's tombstone stays dropped on the devices that refused it and is offered to them in every session. An unstable connection is enough: an owner deletes while cut off from the owner that demotes it.

- (a) A tombstone names its writer's membership sequence and is judged at that point, as a content entry is: every device reaches one verdict whenever it arrives. It is the signed deletion record set aside above, and it inherits the gap a member's own history leaves open: a demoted owner deletes under its old sequence.
- (b) A tombstone counts only while its writer's role allows it in the device's current fold: once the demoted event arrives, the record store admits the record's content again from any device that still holds it. Every device converges on the record's presence, but every deletion the owner made while an owner is undone wherever the content survives.
- (c) Accepted: the split stands until a current owner deletes the record again, which leaves the demoted owner's tombstone offered for ever.

**Example:** in "Family", Bob, an owner, demotes Alice at her sequence 2; her phone a1, cut off from Bob's devices but not from Dave's phone d1, places a tombstone on Carol's claim, and d1 takes it before the demotion reaches d1; Carol's phone c1 takes the demotion first.

| option | a1 and d1 | c1 |
|---|---|---|
| (a) the tombstone judged at the sequence it names | the claim deleted | the claim deleted: the tombstone names Alice's sequence 1, at which she is an owner |
| (b) a tombstone counts only while its writer's role allows it | the claim comes back once the demotion arrives, fetched from c1 | the claim stays |
| (c) accepted | the claim deleted, its content refused for good | the claim stays, and a1's tombstone is offered to c1 in every session |

### A second version of a claim or an immutable-document at a record the cell holds

Placing on top of a record is refused on the writing device, and a version under another member's name is dropped at the gate; two sources remain — a modified device of the member itself, and two of its devices placing one id while disconnected from each other, which happens only when the id is not a fresh one the service mints.

- Today: nothing on reconciliation checks whether the record is taken. The store keeps one entry per author at a key. An entry from the same device at the same key with a newer timestamp replaces the older on every device and keeps the id, so references to the record silently show the new content; an entry from another device of the member is another author's, so both stand at the key and a read shows the newer. A version at the same id under another membership sequence is another key: both stand, and which one reads is undefined.
- (a) Refused everywhere: the record store refuses content for a record that already holds content with another hash. Claims and immutable-documents become truly immutable, and both paths close. But a member that placed two versions leaves one on some devices and the other on the rest, for good — every session offers the other version again and has it refused, the cost of an entry dropped at ingest — repaired only by a deletion, the member's own or an owner's.
- (b) Last writer wins on reconciliation: within one record, the newest timestamp from any device of its member wins, and older versions go with their blobs; the membership sequence in the key stays. Every device converges on one version, and only the member's own devices contend over timestamps. But an honest collision silently loses one version, "a record's key is written once" — which the deletion rule rests on — needs rewriting, and a departed member naming its old sequence rewrites its old records in place. The access tables would then read: no update on the writing device, and the newest version winning on reconciliation, so a modified device of a member rewrites that member's own claims and immutable-documents.
- What the choice turns on is the form of a record's id: with a fresh id the service mints, as `put_record` does, two devices of one member never meet at one id, there is no honest collision, and (b) rests on convergence alone; with an id that is a file path or a well-known name, the collision is real — one file placed from a phone and a laptop while disconnected — and (b) resolves it by losing one version.

**Example:** Bob places his lease scan at the well-known id `lease.pdf` from his phone b1 at 10:00 and from his laptop b2 at 10:05, the two disconnected from each other; both entries sit at `by/<bob>/immutable-document/lease.pdf/1`, `<bob>` being 64 lowercase hex chars of Bob's `PdnId`.

| | every member device once both versions have reached it |
|---|---|
| today | holds both, one per author; a read shows b2's |
| (a) refused everywhere | holds whichever version arrived first and refuses the other, which every session offers again, until Bob or an owner deletes the record |
| (b) last writer wins | holds b2's; b1's goes with its blob |

### A non-empty entry at a record's own key

A record's own key is its content keys without their last segment, the key its tombstone takes; an entry outside the key layout is admitted from a member's device and kept, and the store keeps one entry per author at a key, the newer replacing the older.

- Today: a device of the author that wrote the tombstone — a modified one, since honest code writes nothing there — writes a non-empty entry at the record's key with a newer timestamp, and it replaces the tombstone on every device that admits it. A device that missed the deletion then never receives the tombstone, finds no empty entry at the record's key, and admits the record's content again. Another author's non-empty entry at that key leaves the tombstone standing, and the read of every author's entries finds it.
- (a) The record's key admits only empty entries: the gate drops a non-empty entry there silently, as an entry from the wrong author, reading the key and whether the entry is empty only. A deletion is final, against the member that wrote it too, and every entry at the record's key is a tombstone. A device that holds such an entry — only a modified one — offers it on every session, and every session drops it.
- (b) A non-empty entry at a deleted record's key is dropped: the record store reads every author's entries at the key, empty ones included, and drops a non-empty entry at the key of a record holding an admitted tombstone; at a key without one, it is an entry outside the layout. The rule reads the replica's state rather than the key alone, which a later edit breaks more easily. It also closes the case only on a device that takes the tombstone before the non-empty entry: a device that missed the deletion and meets the entry first admits it as an entry outside the layout, never takes the older tombstone of the same author, and keeps the record, while the devices holding the tombstone drop the entry, so the two offer each other the difference in every session and never converge.
- What the choice turns on: both options leave an entry offered for ever to devices that drop it; under (a) every honest device converges on the deletion whatever the arrival order, under (b) the arrival order decides whether a device that missed the deletion converges at all, and (a) keeps the record's key a slot the gate judges by its shape alone.

**Example:** Alice, an owner, deleted Bob's claim from her phone a1 at 10:00, and a modified a1 writes a non-empty entry at the record's key `by/<bob>/claim/<id>` at 10:05; Bob's phone b1 holds the tombstone, and Carol's phone c1 missed the deletion and still holds the claim. `<bob>`: 64 lowercase hex chars of Bob's `PdnId`; `<id>`: the claim's id.

| | c1 syncs with a1, then with b1 | c1 syncs with b1, then with a1 |
|---|---|---|
| today | admits a1's entry; the tombstone b1 offers is an older entry of the same author at that key, so c1 never takes it and keeps the claim | takes the tombstone and removes the claim; a1's newer entry then replaces the tombstone, and c1 admits the claim again from any device that offers it |
| (a) only empty entries at a record's key | drops a1's entry, takes the tombstone from b1 and removes the claim | the same |
| (b) a non-empty entry dropped at a deleted record's key | admits a1's entry, since c1 holds no tombstone yet; then never takes the tombstone and keeps the claim, as today, while b1 stays deleted and drops a1's entry, so the two offer each other the difference in every session | takes the tombstone and removes the claim, then drops a1's entry |

## Operating conditions

An unstable connection splits a replacement into two halves that arrive apart, and puts a demoted owner's tombstone on both sides of its demotion (the first open question). Several identities on one node share one blob store, which is why a blob is released only once no hosted identity's replica references it. A restart between a tombstone's admission and the removal of the content it kills is a state the change specifies, so that the removal completes after the restart. Clocks decide nothing: a content entry is refused for a deleted record whatever its timestamp.

## Capabilities

`components/mee-pdn/data-layer/cell-store` (the deletion rule, the tombstone's admission, blob release), `components/mee-pdn/pdn-node/cells` (the `delete` operation, the rights tables, replacement), `components/mee-pdn/pdn-store/crate` (the two primitives), `components/mee-pdn/pdn-node-http/host` and `components/mee-pdn/pdn-node-http/container-stand` (the route and the stand's paired denial).

## Impact

- **`crates/pdn-store`**: removing every author's entries at one key with their blobs; reading every author's entries at one key, empty ones included, at ingest.
- **`crates/data-layer`**: the record store's deletion rule and its refusal of content for a deleted record.
- **`crates/pdn-node`**: `delete`, and replacement as a deletion followed by a placement.
- **`crates/pdn-node-http`**: the delete route and the stand's deletion step.
