# Proposal: pods-anchored-history

## Why

A pod's membership store holds, per member, a chain of membership events under `member/<pdnid>/<seq>/<kind>/<actor>/<aseq>`, each naming its actor and the actor's point — the sequence of the actor's own chain it was written at — and judged against the actor's state there; every content entry of the record store names its writer's membership sequence the same way ([pod stores](../../specs/components/mee-pdn/data-layer/pod-store/spec.md)). The reference proves that an entry is after the point it names, not that it is before the next one. A member's device can therefore write, as its member — records under the member's name and acts in any member's chain — entries every honest device takes on the member's word: an act or a record naming a point the member has since lost — a demoted owner acting as an owner, a removed member placing a record — an entry replacing one the member's own author wrote at the same key, the store keeping one entry per author at a key, two events of the member's at one point of a chain, and two entries of one of its records from two of its devices. What no state of the member's own ever allowed — a record under another member's name, an act naming a point at which its actor lacks the state the act needs — stays refused.

The named point is a logical clock, a Lamport-style reference into the author's own chain, and that is the limit of every logical clock with no cryptographic binding, a vector clock included: the author writes the reference, and nothing ties it to what the author had seen. Linking each event to its predecessors' hashes stops history being rewritten, but not backdating, equivocation — two versions sent to two parties — or withholding ([Kleppmann, Making CRDTs Byzantine Fault Tolerant](https://martin.kleppmann.com/papers/bft-crdt-papoc22.pdf)); a key event log with anchored signatures closes backdating and equivocation, and withholding stays outside what a log can prove.

A departed member's devices keep the pod's membership store as its tombstone and reconcile with every member device the part of it that precedes the departure — the departure event and every entry it depends on — and nothing after ([pod stores](../../specs/components/mee-pdn/data-layer/pod-store/spec.md)). What a former member's device sends within that part is taken on its word, as every member's own history is. Anchoring bounds it: with each entry anchored in its author's log, an entry of the former member's anchored after the position its departure holds in that log does not count, and what precedes a departure becomes a position in the log rather than the set of entries the departure depends on.

The platform takes a member's own history on its word while pods serve load testing: it specifies what honest devices do on these paths, no scenario or test pins what the fold does with a member's contradictions, and a review reports none of it anew, since this change records it. Under [defect-reachability](../../specs/code-practices/defect-reachability.md) these paths are reachable over the network: a modified member device takes ownership back and removes the owners that demoted it, which ends honest members' sessions. That obliges a fix, and this change is where the fix sits. The deferral ends before any pod carries data people depend on: this change lands before connections are removed from the platform.

The direction is set: anchored signatures. A key event log commits to its owner's events in order and cannot be appended to in the past, and an anchored signature ties a signed entry to a position in its signer's log, so a narrowing that names the position it saw in the narrowed member's log tells an act written after it from one written before it. Key event logs arrive with the platform's own KERI implementation.

**Example:** in "Family", Alice demoted Bob, an owner since his sequence 2, at his sequence 3, and removed Carol at her sequence 2; Bob's phone b1 and Carol's phone c1 are modified, and Bob's device statements list b1 alone.

| entry | names | on every honest member device |
|---|---|---|
| b1 promotes Bob himself | Bob's sequence 2, at which he is an owner | counts: Bob is an owner again |
| b1 then removes Alice | Bob's sequence 2 | counts: Alice is out of the pod, and her devices are refused from their next session |
| c1 places a claim under Carol's name, which a member device the removal has not reached takes and relays | Carol's sequence 1 | read |
| b1 promotes Bob himself naming his sequence 3, at which he is a plain member | Bob's sequence 3 | counts for nothing |
| b1 places a claim under Alice's name | — | read by none |

## What Changes

The change settles how a pod's entries anchor in their authors' logs, where a member's log is held for the pod's other members, what one log shows across the pods of its identity, and whether a defence lands ahead of the logs, and then specifies and builds the answers. None is decided; the options stand under Open Questions, strongest first.

## Open Questions

### What a member's log anchors

- Membership acts and record-store entries alike. Both stores stop taking a member's contradictions: an act or a record anchored past the position a narrowing saw does not count, a rewritten entry no longer matches the digest its anchor holds, and one member contradicting itself is duplicity the log detects. Each entry costs its author an event in its log, and a mergeable-document's operations are many.
- Membership acts alone. The membership store stops taking a member's contradictions at one log event per act, and acts are few; a departed member's record-store entries under its old sequence still pass, content signed as its own.

With several parties, the first-seen rule the KERI roadmap applies between two parties does not detect duplicity, so duplicity detection moves earlier in that roadmap under either option.

A log is validated as KERI validates one: an event whose predecessors have not arrived waits in escrow and is judged once they do, and a member's two versions of one event are caught only while both are held side by side. The pod's stores hold every entry a session they serve carries and leave what counts to the fold, so under either option a second version of an event sits beside the first on every member device, where the log's validation finds it.

KERI's own shape for an anchored record is an Authentic Chained Data Container (ACDC) with a transaction event log (TEL): the record is the container, its issuance and revocation are events of the log, and each event is committed by a seal — its sequence number and digest — in an event of the issuer's key event log, which makes it verifiable and orders it against the issuer's rotations, while the date the event carries is the issuer's word ([ACDC](https://trustoverip.github.io/kswg-acdc-specification/), [TEL](https://trustoverip.github.io/tswg-ptel-specification/draft-pfeairheller-ptel.html)). Record-store entries anchored under the first option would take the same shape, and a pod's claim presented to a party outside the pod would travel by the Issuance and Presentation Exchange protocol (IPEX), whose messages disclose a container to a party that signs its acceptance ([IPEX](https://www.ietf.org/archive/id/draft-ssmith-ipex-00.html)).

**Example:** the cases of Why, under each option.

| option | b1 promotes Bob under his sequence 2 | c1's claim under Carol's sequence 1 |
|---|---|---|
| acts and entries anchored | ignored: anchored past the position Alice's demotion saw in Bob's log | read by none: anchored past the position the removal saw in Carol's log |
| acts alone | ignored, as above | read |

### Where a member's log is held for the other members

A member's anchored entry verifies only against the member's key event log up to the anchor's position, each event of the log committing to the one before it, so every member device that judges the member's entries holds the member's log from its inception. The KERI roadmap keeps an identity's log in its private metadata store (PMS), which only the identity's own devices sync; a pod's other members are served neither the PMS nor any other store of the identity.

- A copy in the membership store of each pod. The member's devices write every event of its log into every pod they hold, as a device statement reaches every pod of the identity, and a newcomer's log arrives with its join. Each pod holds the member's whole log, the events from before the member joined included, and a member of many pods writes each event into each of them.
- A store of the identity's log that every member of its pods reads. One copy per identity, at the price of a replica more for every device to reconcile per identity it shares a pod with, and of every serving device classifying a caller by the pods the two share, so that a member removed from the last pod they shared stops receiving the log's later events, its devices among them.

**Example:** Bob is a member of "Family" and "Taxes"; his log holds its inception, a rotation adding his laptop b2 and three interaction events, each some hundreds of bytes, about 1.5 KB in all; Carol is a member of "Family" alone.

| option | what holds Bob's log | what Carol's phone c1 holds of it |
|---|---|---|
| a copy in each pod | the membership store of "Family" and that of "Taxes" | the copy in "Family": all five events |
| a store every member reads | one store of Bob's log, with a replica on every device of every member of either pod | its replica of that store, all five events |

### What one log shows the members of its identity's other pods

An identity keeps one log for every pod it is a member of, and a log verifies only whole up to a position, so the members of a pod that hold a member's log hold every event of it, the interaction events anchoring the member's acts in its other pods among them. A seal is a digest and shows no content; how many acts the member anchored elsewhere, and in what order against its acts here, the members of each of its pods see.

- An identifier delegated per pod. At join the member's identity delegates an identifier for the pod, one seal in its own log per pod joined, and its acts in the pod anchor in the delegated log, which only that pod's members hold. The identity's own log shows how many pods it joined and when, and nothing of what it did in them; the cost is a log per member per pod, and KERI's cooperative delegation — the delegator's seal on the delegate's inception and the delegate's reference to the delegator — at every join.
- Few events, several seals in one. Only membership acts anchor, several of them in one interaction event where they come together, so the log shows little of any pod; record-store entries stay unanchored, as the first question's second option leaves them.
- One log for every pod, the view accepted: the members of each pod see the count and the order of the member's anchored acts in the others.

**Example:** one evening Bob places 40 claims in "Taxes" and removes Dave there; Carol, on her phone c1, is a member of "Family" alone, which Bob is a member of too.

| option | what c1 holds of Bob's evening |
|---|---|
| an identifier delegated per pod | nothing: the claims and the removal anchor in the log delegated for "Taxes", which "Family" does not hold |
| few events, several seals in one | one interaction event, carrying the removal's seal: the claims are not anchored |
| one log for every pod | 41 interaction events where record-store entries anchor as the first question's first option has them, one where only acts do |

### Whether a defence lands before the logs

- Act numbers and narrowing marks in the membership store. Every membership act carries in its key its author's own act number in the pod: 1 for the author's first act, one more for each next, and an act counts only once the device holds every lower number of the same author, so a device holding an act holds every earlier act of its author. Every event that narrows a member — demoted, removed, left — carries a mark: for each author the member's device statements list, the highest number of that author's acts the writing device holds; the event counts only once the device holds the acts its mark names, so a mark names nothing that did not exist when it was written. An act of the member naming a point before a narrowing that forbids it — any act before a removal or a leave, an owner's act before a demotion — counts only if its number is within that narrowing's mark for its author: the first such narrowing after the named point decides, and at a sequence holding several, the highest of their marks. An act beyond the mark was written after the narrowing, or before it and unseen by the narrowing's writer, and the two are not told apart: a concurrent act loses to its actor's narrowing. Two acts of one author under one number are both ignored. The rule is the fold's: the fold that lists members, serves sessions and reads the record store ignores an act beyond the mark and every event resting on it, while every member device holds the same entries whatever order they arrived in. The mark never withdraws what the narrowing rests on: the writing device held every event its own authority depends on, and with them every earlier act of their authors. The fold reads the whole membership store, so every check costs nothing at run time; the cost is the mechanism itself, built and tested before the logs replace it, and it leaves the record store open.
  - Weaker forms fall short. A mark on promotions alone leaves a demoted or removed owner removing and demoting others under its old point. A mark only in the invite act that readmits a member never reaches a demoted owner, who stays a member and is never readmitted. An event in the actor's own chain naming the point right before it lets a former owner promote a colluding member under its old point and be promoted back. A list of the acts the writer holds says what one number per author says once admission is gapless, and grows with every act.
  - What rests on an act the fold ignores — the records of a newcomer the act invited, and, where records can be deleted, the deletions of a member it promoted — stops reading on every device at once, since the record view reads by the fold; a record read yesterday is gone today when the mark that ignores the act arrives, and the application shows its person why.
  - It also makes two owners' narrowings of each other depend on each other: each is an owner's act of its actor naming a point before the other, beyond the other's mark, so each counts only if the other does not, and the fold needs a rule for that — whether an act the fold ignores still narrows by its mark, or a tie-break.
- A removal that commits to the departed member's record-store entries: a per-author high-water mark on the operation sequence, or a Merkle root over the author's range. The high-water mark counts operations and does not reach a claim or an immutable-document, and needs a uniqueness the gate cannot check without the record store; the Merkle root needs a cached fingerprint tree in pdn-store.
- Hash-linked membership sequences, each event carrying the digest of the one before it, for the rewrite. Detecting one member contradicting itself is the logs' duplicity handling, built here a second time, in a format the logs' own encoding then replaces.
- Witnessing: a current member's signed commitment to the entries it accepted. History then travels under the witness's authority, a trust structure of its own beside membership, and a member device that accepted an entry before a narrowing reached it commits to it all the same.
- None: the deferral stands until the logs.

**Example:** the marks at work. Alice demotes Bob, an owner since his sequence 2, at his sequence 3; Bob's statements list b1 alone, and a1 holds acts of b1's author up to number 5, so the demotion's mark gives b1's author 5; b1 had not received the demotion when it wrote acts 6 and 7.

| act of b1's author | its number | names Bob's point | the fold on every member device |
|---|---|---|---|
| promotes Carol | 5 | 2 | counts: within the mark, and Carol is an owner |
| demotes Carol | 6 | 2 | ignored: an owner's act beyond the mark, and Carol stays an owner |
| invites Dave | 7 | 2 | counts: a demotion forbids no invite, and Dave is a plain member |
| a modified b1 promotes Bob himself | 8 | 2 | ignored: beyond the mark, and Bob stays a plain member |
| Every member device holds all four entries. | | | |

**Example:** the cases of Why, under each option.

| option | b1 promotes Bob under his sequence 2 | c1's claim under Carol's sequence 1 | b1 rewrites Bob's earlier invite of Dave at the same key |
|---|---|---|---|
| act numbers and marks | ignored: beyond the demotion's mark | read | replaces the original: the key, act number included, is the same |
| a removal that commits to record-store entries | counts | read by none, under the Merkle-root variant | replaces the original |
| hash-linked membership sequences | counts | read | shows once a later event of Dave's chain names the original's digest |
| witnessing | counts: every honest device accepted it | read on the commitment of the member device that relayed it | shows against the commitments made to the original |
| none | counts | read | replaces the original |

### How the last owner who lost every device returns

The last owner losing every device writes no event: the owner stays listed and nobody acts as one, which pods accept until KERI arrives and for good where the identity's KERI backup is lost too. KERI's pre-rotated keys restore control of the identity on a new device, which signs its device statement under the rotated key in the announcement key's slot; the owner's chain holds no left event, so the role stands. The PMS that held the pod's tickets is lost with the devices, so the return needs a path by which any member hands the pod's tickets to a device of an identity proven through KERI, writing no joined event, since a join makes a plain member. Open: which member's device hands the tickets over, and what it checks of the proof.

**Example:** Alice, the one owner of "Family", loses her phone a1 and her laptop a2 in one fire; Bob and Carol are plain members.

| with KERI | the pod afterwards |
|---|---|
| Alice restores her identity on a new phone a4 with her pre-rotated keys; a4 signs its device statement under the rotated key, and Bob's phone hands a4 the pod's tickets without writing a joined event | Alice acts as an owner again |
| Alice's KERI backup is lost too | Alice stays listed as the one owner, and nobody acts as one |

## Operating conditions

Several identities on one node keep a log each: Alice-leisure's and Alice-work's acts in "Wedding" anchor in two logs, as their entries sit under two authors. An unstable connection is what puts the gap within reach of ordinary timing: an entry reaches a device the narrowing has not yet reached, and any member device relays it from there. Clocks do not close it: an entry's timestamp is set by its author, and a key event log proves order, not time, so a point stays a position in a chain under every option. Placing a logged event against a wall-clock time takes evidence from outside the log: a witness's signed and dated record of the log's state shows that an event happened no later than that date, while that an event happened after a given time rests on its author's word alone ([ToIP dossier specification, issue 35](https://github.com/trustoverip/kswg-dossier-specification/issues/35)); a pod has no witnesses, so it keeps relative order only. A capability-bound write does not close it alone either, since an entry signed under a since-revoked capability poses the same question.

## Out of Scope

- Two owners writing at one point of one member's chain while disconnected from each other: a race among honest owners, which the pod's membership rules settle.
- The identity proof at join and device statements signed under the identity's key: steps of the KERI roadmap of their own.
- Real expulsion of a member, whose tickets stay valid under bearer tickets: a question of its own.

## Capabilities

None is settled. Every option touches `components/mee-pdn/data-layer/pod-store`, where the membership fold and the record view are specified, and `components/mee-pdn/pdn-node/pods`, where acts are written; where a member's log is held touches `components/mee-pdn/data-layer/private-metadata-store` as well.

## Impact

- **`crates/data-layer`**: the membership fold and the record view of both pod stores.
- **`crates/pdn-node`**: the membership acts the pods service writes, and their anchors.
- **The KERI implementation**: the key event log each member's entries anchor in, and delegation, if a pod anchors in an identifier delegated for it.
