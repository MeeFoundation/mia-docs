# Proposal: pods-record-deletion

## Why

A pod's record store holds claims, immutable-documents and mergeable-documents under `by/<pdnid>/<kind>/<id>/…`, and no record leaves it: the pods service places records and appends operations, and nothing deletes one ([pod stores](../../specs/components/mee-pdn/data-layer/pod-store/spec.md), [pdn-node pods](../../specs/components/mee-pdn/pdn-node/pods/spec.md)). Every record's blob lands on every member device and stays there for as long as the device holds the pod: the node's blob collection frees a blob once no replica references it ([node assembly](../../specs/components/mee-pdn/data-layer/node-assembly/spec.md)), and in a pod that happens only when a device forgets the whole record store, on a leave or a removal. A device's storage grows with everything ever placed — content placed by mistake, a member's junk, a departed member's records, a file a corrected one replaced — and with every entry the record view counts for nothing: no pod store sets a download policy, so a member device downloads the blob of every entry it holds, though no member reads such an entry and no one can delete it, since it reads as no record. The owners have no way to delete content either, and a claim or an immutable-document is never replaced: a corrected one sits beside the old one. The store beneath does not supply the deletion: an entry, empty or not, affects only its own key, the store keeps one entry per author at a key, and a record's content is spread over keys and authors — one key per operation of a mergeable-document, one author per device that wrote.

**Example:** in "Family", Bob places a 20 MB lease scan by mistake, Carol, since removed, left 200 claims nobody wants, Alice, an owner, has a corrected claim of her son Tom's blood type after a new test, and a modified phone of Dave's places a 50 MB file under Bob's name.

| | in the pod | on every member device |
|---|---|---|
| Bob's scan | stays, read by every member | its 20 MB blob |
| Carol's 200 claims | stay | their 200 blobs |
| Alice's corrected claim | placed beside the old one: both read, and nothing says which is current | both blobs |
| the file under Bob's name | held and relayed, counts for nothing: its author is no device of Bob's | its 50 MB blob, which no member reads and no one can delete |

## What Changes

Who deletes and how a record is replaced are set. What a deletion takes off a device, and which blobs a device keeps at all, are open, and the change leans toward one rule for both: a device keeps the blob of an entry the record view counts and of no other, so no device holds a blob the record view rejects. Six questions stand open under Open Questions.

### Who deletes

A member deletes the records under its own name because they are its own. An owner deletes records of any member — its own, another current member's, a departed member's alike, since the rights to act on a record do not depend on its member's membership state — because it is an owner. Deletion is the owners' repair power over content, and every reachable state becomes repairable by the owners, content included. Neither power writes under another member's name: the tombstone carries its writer's own signature, the deletion is the owner's own signed act and forges nothing, and a hostile owner sits inside the trust boundary already. A tombstone is an entry like every other, held by every member device whoever wrote it ([pod stores](../../specs/components/mee-pdn/data-layer/pod-store/spec.md)); whether it counts is the record view's, over everything a device holds: it counts when its author is a device of the record's member or of an owner, and at which point the writer is judged is an open question. A tombstone that counts for nothing — a plain member's on another member's record — deletes nothing.

**Example:** tombstones in "Family", where Alice is an owner, Bob and Carol are plain members, and Dave left.

| tombstone on | by Alice | by Bob | by Carol |
|---|---|---|---|
| Bob's claim | counts | counts | counts for nothing |
| Carol's lease scan | counts | counts for nothing | counts |
| Dave's note | counts | counts for nothing | counts for nothing |

The rights tables of the pods service gain, for each record kind, "Delete own …" — every member — and "Delete another member's …" — an owner alone; the service gains `delete`, and the HTTP host its route, `DELETE …/records/{member}/{kind}/{id}`, whose refusal by role is a client error.

### Replacing a claim or an immutable-document

Neither is updated in place by anyone. A member replaces its own record because it is its own; an owner replaces any member's record because it is an owner: the old record is deleted, and the new one is placed under the replacer's name — a new record with a new id, its issuer or placing member the replacer, so a member's record replaced by an owner becomes the owner's. References to the old record — links inside notes — stay on the old record and do not follow the new one; that such references break is accepted, since a record's id names the member under whose name it sits. A mergeable-document is edited in place and its id stays. Two members replacing one record at once leave two new records under two names, visible to everyone and resolved by people. A replacement is two entries the store carries apart — the tombstone and the new record — so a device catching up reads, for a moment, both records or neither, and converges on the new one alone once both have arrived, with no act from anyone.

**Example:** Alice, an owner, replaces Bob's lease scan; `<alice>`, `<bob>`: 64 lowercase hex chars of each `PdnId`; `<lease>`, `<new-lease>`: the ids `put_record` minted for the old scan and the new one.

```
before     by/<bob>/immutable-document/<lease>/1           Bob's scan
Alice      by/<bob>/immutable-document/<lease>             the tombstone: empty, a1's author
           by/<alice>/immutable-document/<new-lease>/1     her new scan, a new record under her name
after      Bob's scan reads as deleted and its blob leaves every member device; the new scan reads as Alice's; a note linking <lease> links a deleted record
c1         Carol's phone takes the new scan in one session and the tombstone in the next: reads both scans in between, then Alice's alone
```

### A tombstone marks a record deleted

A tombstone is the store's empty entry at a record's key — `…/<kind>/<id>`, the key of its content entries without their last segment. The record store knows its key layout and maps a content entry to its record by dropping the last segment of its key. Once a tombstone counts, the record view reads the record as deleted on every device, whatever the timestamps of its content entries, and the record's blob leaves the device at the node's next blob collection; whether the content entries leave with it, and how the blob stays out from then on, are open questions. The read of a record's tombstone takes every author's entries at the record's key, empty ones included, never the newest entry across authors: a later non-empty entry at the record's key from another author would be the newest. A mergeable-document's operations are deleted with it. The tombstone entry itself stays, as the element of the set reconciliation compares: a peer that missed the deletion converges on it instead of reading the record again. The blob store is the node's, one under every hosted identity's replicas, so a blob leaves only once no record store of any identity the node hosts keeps it: a co-located member's copy of the record keeps it until that replica takes the tombstone too, which the in-process path brings at once.

The rule belongs to the record store alone: the store beneath keeps carrying no relation between keys, so a private metadata store (PMS) tombstone at `connections/<P>` leaves that key open for a later connect, and an entry outside the record layout touches nothing.

**Example:** in "Wedding", Erin, an owner, deletes Bob's scan of the venue contract from her phone e1, and Alice's tablet a3, hosting Alice-leisure and Alice-work, both members, takes the tombstone.

| step on a3 | Alice-leisure's replica | Alice-work's replica | the scan's blob |
|---|---|---|---|
| before | reads the scan | reads the scan | kept |
| Alice-leisure's replica takes the tombstone from e1 | reads the scan as deleted | reads the scan | kept: Alice-work's replica reads it |
| the in-process path brings the tombstone to Alice-work's replica | reads the scan as deleted | reads the scan as deleted | freed at the next blob collection |
| Bob's phone b1, which missed the tombstone, syncs with a3 | reads the scan as deleted | reads the scan as deleted | stays freed |
| b1 takes the tombstone from a3 and frees its own copy of the scan's blob. | | | |

**Rejected alternatives:**

- The store's own deletion alone — an empty entry replaces only its own author's older entry at its key, other authors' entries stay and are hidden on read by the newest timestamp across authors.
  - **Cons:** deleted content and its blob stay on disk until a collection nobody schedules; a content entry with a newer self-set timestamp brings a deleted record back.
- Prefix semantics in the store — an empty entry removing every author's entries under its key, a dead prefix admitting nothing more.
  - **Cons:** an entry at a short key or at a key a later layout gives meaning — `by/`, `by/<M>/` — reaches entries it was never meant for; a non-empty entry at a record's key erases its own author's operations under it; the rule holds in every replica, so a dead `connections/<P>` in a PMS forbids a reconnect.
- A tombstone at every content key.
  - **Cons:** deleting a mergeable-document is one tombstone per operation, and an operation written while disconnected after the deletion arrives later and brings back a fragment of the document.
- A signed deletion record with a key of its own, judged at its actor's point.
  - **Pros:** gives a deletion a membership reference; the question on the point at which a tombstone's writer is judged reopens it.
  - **Cons:** a second entry kind for what an empty entry at the record's key already says, where every device looks for it.

The tests pair each access in one place: an owner's tombstone deleting a record and freeing its blob on every device beside a plain member's counting for nothing; a member deleting its own beside another member's refused on the writing device; a removed member's record deleted by an owner beside a plain member's tombstone and the removed member's own counting for nothing, and an outsider served nothing; a content entry with a newer timestamp still read as deleted; a peer that missed the tombstone converging on the deletion; a mergeable-document's operations deleted with it; a tombstone whose writer's role does not allow it counting for nothing whatever order it and the role change arrive in; an immutable-document replaced concurrently by two members leaving two records under two names; an empty entry at `by/<B>/` deleting nothing, and a non-empty entry at a mergeable-document's key deleting none of its operations; if blobs follow the record view, an entry that counts for nothing leaving no blob on any member device beside one that counts keeping its blob. The container stand's paired denial gains the creator's deletion of its own claim beside a plain member's deletion of another member's.

## Open Questions

### Which blobs a device keeps

Today a device keeps the blob of every entry it holds: no pod store sets a download policy, so the fork's default downloads everything, and blob collection keeps every blob a replica references (`protect_hosted` in `crates/data-layer/src/node.rs`). An entry that counts for nothing — written by an author its member's device statements do not list, or naming a membership sequence at which its writer is no member — lands its blob on every member device, and nothing frees it: it reads as no record, so no tombstone reaches it.

- The record view decides, which the change leans toward: a device keeps the blob of an entry the record view counts and of no other — no blob for a deleted record, an entry that counts for nothing or an entry outside the layout — so a device's storage follows what its members can read, and a deletion is that rule applied to one record. Three things follow from it. The fetch is decided without the blob: `judge` in `crates/data-layer/src/pod/record_view.rs` checks the writer's chain, the author and the writer's state, and waits for the blob last (`NotYet(Awaiting::Payload)`), so the decision is the verdict on everything before the blob. A refusal is not always final: a member's devices are the union of its counted device statements, so an entry from a device that no counted statement lists yet counts for nothing until one does, and an entry ahead of its writer's chain waits for it (`NotYet(Awaiting::ActorChain)`); such a blob is fetched once the verdict turns, from any device that holds it, the writer's own among them. And while its verdict stands, a device relays such an entry without its blob, so a member device that reaches only it waits for a device that counts the entry. The membership store stays outside the rule: the membership view judges an event by the signatures in its blob, so a membership-store blob is fetched to be judged.
- Every blob of every held entry, as today, a deletion freeing the deleted record's blob alone: the download stays as it is, and a counted-for-nothing entry's blob stays on every member device for as long as the pod lives.

**Example:** in "Family", Bob links his new laptop b2 and places a 20 MB scan from it, whose entry reaches Carol's phone c1 while the blob of Bob's new device statement is still on its way; a modified phone of Dave's placed a 50 MB file under Bob's name earlier.

| option | the 50 MB file under Bob's name, on c1 | b2's scan on c1 |
|---|---|---|
| the record view decides | never downloaded | downloaded once the statement counts, from b2 or any device that counts the scan |
| every blob, as today | 50 MB, kept for as long as c1 holds the pod | downloaded at once |

### What a deletion takes off a device

- The blob alone, which the leaning on which blobs a device keeps implies: the record's content entries stay, the record view reads the record as deleted, and its blob leaves. The entries a pod store holds only grow: pdn-store removes nothing, the stores keep holding whatever a session carries with no exception at ingest, the record view reads a tombstone through a query that includes empty entries (`Query::include_empty` in `crates/pdn-store/src/store.rs`), and reconciliation needs nothing new — a peer that missed the deletion holds the same content entries, offers nothing back, and takes the tombstone. Where a tombstone stops counting, as one answer to the question on its writer's point allows, the blob comes back from any device that kept it. A later build reads every record that ever stood, with its author, hash, length and timestamp. The cost: entries never leave, so a pod store's size and the linear-scan fingerprint over it (`get_fingerprint` in `crates/pdn-store/src/store/fs.rs`) grow with every record ever placed; and the hash and length of deleted content stay on every member device, a member that joins after the deletion included, so whoever holds the same file can confirm it was placed in the pod.
- The record's entries with its blob: once a tombstone counts, the record store removes every author's content entries of that record, its blob leaves at the next blob collection, and the store keeps every content entry of that record out from then on. Removing every author's entries is safe because a record's content keys are written once and a replacement is a new key. A member that joins after the deletion finds the tombstone alone — the record's member, kind and id — and no hash. The cost: pdn-store gains two primitives — removing every author's entries at one key, and reading every author's entries at one key at ingest, empty ones included — which changes the fork and brings the stress pass of the flaky-tests practice with it; a deleted record's content has to be kept out of stores that hold whatever a session carries, the next question; and a deletion that later stops counting finds content again only on a device that never took the tombstone.
- Nothing: the record view reads the record as deleted, and its entries and blob stay on every device. Content placed by mistake keeps taking storage and keeps being served by hash.

**Example:** Alice, an owner, deletes Bob's 20 MB lease scan in "Family"; Carol's phone c1 holds the tombstone, and Bob's phone b1 missed it.

| option | on c1 after the deletion | b1 syncs with c1 | a member who joins later finds |
|---|---|---|---|
| the blob alone | the scan's entry, read as deleted, and no blob | b1 offers nothing new and takes the tombstone | the scan's entry: its hash and its 20 MB length |
| the entries with the blob | the tombstone alone | b1 offers the scan's entry, which c1 keeps out | the tombstone: Bob's immutable-document `<lease>` |
| nothing | the scan's entry and its 20 MB blob, read as deleted | b1 offers nothing new and takes the tombstone | the scan whole, read as deleted |

### How a deleted record's content stays out

A deleted record takes no content back, and how depends on what a deletion takes off a device.

Where the entries stay, the blob is what has to stay out. `park_missing_content` in `crates/pdn-store/src/engine/live.rs` queues, on every open of a replica, the blob of every entry the download policy wants and the blob store lacks, and every finished sync retries what is queued; the download policy is a list of key patterns (`DownloadPolicy` in `crates/pdn-store/src/store.rs`), and blob collection keeps every blob a replica references, a deleted record's entry still referencing its blob.

- The record view answers per entry: the fork asks data-layer whether to fetch an entry's blob, as blob collection asks which blobs to keep, and data-layer answers both from the record view. One rule for both, holding no state of its own, so a restart rebuilds the answer from the held entries. The fork's download path changes, and its stress pass comes with it.
- A download policy pattern per deleted record: the fork stays as it is; the policy grows with every deletion and has to be stored, and a counted-for-nothing entry needs a pattern of its own, taken back when its verdict turns.

Where the entries leave, a pod store holds every entry a session it serves carries, judged at ingest by nothing beyond what pdn-store drops on its own ([pod stores](../../specs/components/mee-pdn/data-layer/pod-store/spec.md)), and a peer that missed the tombstone offers the record's content in every session until it takes the tombstone itself, in the same session as a rule.

- Refused at ingest, the one exception to holding whatever a session carries: the record store keeps a content entry out when the record's tombstone counts, one read of every author's entries at the record's key beside the membership view. No blob of a deleted record is downloaded again. The refusal follows the record view: where a tombstone stops counting, the record's content is taken again from any device that still holds it.
- Removed once held: the content entry is held as every entry is and removed at once, its blob with it. The rule for holding stays whole, at the price of a download and a freeing of a deleted record's blob for every peer that offers it before taking the tombstone.

**Example:** Erin, an owner of "Wedding", deleted Bob's scan of the venue contract, Alice's tablet a3 holds the tombstone and has freed the scan's blob, and Bob's phone b1, which missed the tombstone, syncs with a3; then a3 restarts.

| option | b1 syncs with a3 | a3 restarts |
|---|---|---|
| the record view answers per entry | a3 holds the scan's entry and asks for no blob | `park_missing_content` skips the scan |
| a pattern per deleted record | the same | the same, the policy one pattern longer |
| refused at ingest | a3 keeps the scan's entry out | nothing to skip |
| removed once held | a3 holds the scan's entry, downloads its blob, then removes both | nothing to skip |

### At which point a tombstone's writer is judged

A tombstone carries no membership reference, and every verdict in a pod follows from the whole set of entries a device holds, so the record view reads a tombstone by its writer's role — the question is at which point. It matters where an owner deletes while cut off from the owner that demotes it: the writing device, and every device that took the tombstone before the demotion arrived, have freed the record's blob — and its content entries, if a deletion takes them — by the time the demotion reaches them.

- (a) A tombstone names its writer's membership sequence and counts at that point, as a content entry does: every device reaches one verdict whatever arrives later, and a deletion is never undone. It is the signed deletion record set aside above, and it inherits the gap a member's own history leaves open: a demoted owner deletes under its old sequence.
- (b) A tombstone counts while its writer's role allows it in the current membership view: once the demoted event arrives, the tombstone counts for nothing, and the record reads again, its blob — and its content entries, if a deletion took them — taken from any device that still holds them. Every device converges on the record's presence, but every deletion the owner made while an owner is undone wherever the content survives, and lost where no device kept it.

**Example:** in "Family", Bob, an owner, demotes Alice at her sequence 2; her phone a1, cut off from Bob's devices but not from Dave's phone d1, places a tombstone on Carol's claim, and d1 takes it before the demotion reaches d1; Carol's phone c1 takes the demotion first.

| option | a1 and d1 | c1 |
|---|---|---|
| (a) the tombstone judged at the sequence it names | the claim deleted | the claim deleted: the tombstone names Alice's sequence 1, at which she is an owner |
| (b) a tombstone counts while its writer's role allows it | the claim comes back once the demotion arrives, fetched from c1 | the claim stays: the tombstone counted for nothing when it arrived |

### A second version of a claim or an immutable-document at a record the pod holds

Placing on top of a record is refused on the writing device, and a version under another member's name reads on no device; two sources remain — a modified device of the member itself, and two of its devices placing one id while disconnected from each other, which happens only when the id is not a fresh one the service mints.

- Today: nothing checks whether the record is taken. The store keeps one entry per author at a key. An entry from the same device at the same key with a newer timestamp replaces the older on every device and keeps the id, so references to the record silently show the new content; an entry from another device of the member is another author's, so both stand at the key, and a version at the same id under another membership sequence is another key, so both stand there too; a read returns the one with the newest timestamp.
- (a) Contested: while a record holds content of two hashes, the record view reads it as two versions and neither as the record, until a deletion — the member's own or an owner's — takes one away. Every device converges on the same view, an honest collision stays visible and loses nothing, and claims and immutable-documents never silently change under a reference; a modified device of the member can make its own records contested, which its member's own history already allows.
- (b) Last writer wins on reconciliation: within one record, the newest timestamp from any device of its member wins, and older versions go with their blobs; the membership sequence in the key stays. Every device converges on one version, and only the member's own devices contend over timestamps. But an honest collision silently loses one version, "a record's key is written once" — which removing a deleted record's content entries rests on — needs rewriting, and a departed member naming its old sequence rewrites its old records in place. The access tables would then read: no update on the writing device, and the newest version winning on reconciliation, so a modified device of a member rewrites that member's own claims and immutable-documents.
- What the choice turns on is the form of a record's id: with a fresh id the service mints, as `put_record` does, two devices of one member never meet at one id, there is no honest collision, and (b) rests on convergence alone; with an id that is a file path or a well-known name, the collision is real — one file placed from a phone and a laptop while disconnected — and (b) resolves it by losing one version.

**Example:** Bob places his lease scan at the well-known id `lease.pdf` from his phone b1 at 10:00 and from his laptop b2 at 10:05, the two disconnected from each other; both entries sit at `by/<bob>/immutable-document/lease.pdf/1`, `<bob>` being 64 lowercase hex chars of Bob's `PdnId`.

| | every member device once both versions have reached it |
|---|---|
| today | holds both, one per author; a read shows b2's |
| (a) contested | holds both, and reads the record as two versions until Bob or an owner deletes one |
| (b) last writer wins | holds b2's; b1's goes with its blob |

### A non-empty entry at a record's own key

A record's own key is its content keys without their last segment, the key its tombstone takes; an entry outside the key layout is held like every entry, and the store keeps one entry per author at a key, the newer replacing the older.

- Today: a device of the author that wrote the tombstone — a modified one, since honest code writes nothing there — writes a non-empty entry at the record's key with a newer timestamp, and it replaces the tombstone on every device that takes it. A device that missed the deletion then never receives the tombstone, finds no empty entry at the record's key, and reads the record again. Another author's non-empty entry at that key leaves the tombstone standing, and the read of every author's entries finds it.
- (a) The record's key holds only empty entries: the record store refuses a non-empty entry there at ingest, reading the key and whether the entry is empty only — an exception to holding whatever a session carries. A deletion is final, against the member that wrote it too, and every entry at the record's key is a tombstone. A device that holds such an entry — only a modified one — offers it on every session, and every session refuses it.
- (b) Taken on its writer's word: the tombstone's own author rewrites its own entry, as a member's own history is taken on its word, and the record reads again wherever its content survives, until an owner deletes it again. Nothing is refused at ingest, and the defence waits with the rest of a member's own history for the anchored logs.

**Example:** Alice, an owner, deleted Bob's claim from her phone a1 at 10:00, and a modified a1 writes a non-empty entry at the record's key `by/<bob>/claim/<id>` at 10:05; Bob's phone b1 holds the tombstone, and Carol's phone c1 missed the deletion and still reads the claim. `<bob>`: 64 lowercase hex chars of Bob's `PdnId`; `<id>`: the claim's id.

| | c1 syncs with a1, then with b1 | c1 syncs with b1, then with a1 |
|---|---|---|
| today | takes a1's entry; the tombstone b1 offers is an older entry of the same author at that key, so c1 never takes it and keeps the claim | takes the tombstone and reads the claim as deleted; a1's newer entry then replaces the tombstone, and c1 reads the claim again, its blob fetched from any device that holds it |
| (a) only empty entries at a record's key | refuses a1's entry, takes the tombstone from b1 and reads the claim as deleted | the same |
| (b) taken on its writer's word | as today | as today |

## Operating conditions

An unstable connection splits a replacement into two halves that arrive apart, puts a demoted owner's tombstone on both sides of its demotion (the question on a tombstone's writer), and, if blobs follow the record view, leaves a device holding an entry whose blob waits until the device statement that lets the entry count arrives. Several identities on one node share one blob store, which is why a blob leaves only once no hosted identity's record store keeps it. A restart is a state the change specifies: where a deletion removes content entries, the removal it starts completes after the restart; where blobs follow the record view, the answer is rebuilt from the held entries on every open, since `park_missing_content` asks again for every missing blob. A disk that fills is what the leaning answers: a device stores what its members can read. Clocks decide nothing: a deleted record stays deleted whatever the timestamps of its content entries.

## Capabilities

`components/mee-pdn/data-layer/pod-store` (the deletion rule, the tombstone's verdict, which blobs a device keeps), `components/mee-pdn/data-layer/node-assembly` (blob collection keeping what the record view counts), `components/mee-pdn/pdn-node/pods` (the `delete` operation, the rights tables, replacement), `components/mee-pdn/pdn-store/crate` (the download decision or the two primitives), `components/mee-pdn/pdn-node-http/host` and `components/mee-pdn/pdn-node-http/container-stand` (the route and the stand's paired denial).

## Impact

- **`crates/pdn-store`**: where the entries stay, a download decision data-layer answers per entry; where they leave, removing every author's entries at one key with their blobs, and reading every author's entries at one key, empty ones included, at ingest.
- **`crates/data-layer`**: the record view reading a deleted record, and telling an entry kept without its blob from one whose blob is on its way; blob collection keeping the blobs the record view counts; or the record store's removal of a deleted record's content entries and how it keeps them out.
- **`crates/pdn-node`**: `delete`, and replacement as a deletion followed by a placement.
- **`crates/pdn-node-http`**: the delete route and the stand's deletion step.
