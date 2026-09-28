# Proposal: cells-anchored-history

## Why

A cell's membership store holds, per member, a chain of membership events under `member/<pdnid>/<seq>/<kind>/<aseq>`, each naming its actor's point — the sequence of the actor's own chain it was written at — and judged against the actor's state there; every content entry of the record store names its writer's membership sequence the same way ([cell stores](../../specs/components/mee-pdn/data-layer/cell-store/spec.md)). The reference proves that an entry is after the point it names, not that it is before the next one. A member's device can therefore write, as its member — records under the member's name and acts in any member's chain — entries every honest device takes on the member's word: an act or a record naming a point the member has since lost — a demoted owner acting as an owner, a kicked member placing a record — an entry replacing one the member's own author wrote at the same key, the store keeping one entry per author at a key, two events of the member's at one point of a chain, and two entries of one of its records from two of its devices. What no state of the member's own ever allowed — a record under another member's name, an act naming a point at which its actor lacks the state the act needs — stays refused.

The named point is a logical clock, a Lamport-style reference into the author's own chain, and that is the limit of every logical clock with no cryptographic binding, a vector clock included: the author writes the reference, and nothing ties it to what the author had seen. Linking each event to its predecessors' hashes stops history being rewritten, but not backdating, equivocation — two versions sent to two parties — or withholding ([Kleppmann, Making CRDTs Byzantine Fault Tolerant](https://martin.kleppmann.com/papers/bft-crdt-papoc22.pdf)); a key event log with anchored signatures closes backdating and equivocation, and withholding stays outside what a log can prove.

A departed member's devices keep the cell's membership store as its tombstone and reconcile with every member device the part of it that precedes the departure — the departure event and every entry it depends on — and nothing after ([cell stores](../../specs/components/mee-pdn/data-layer/cell-store/spec.md)). What a former member's device sends within that part is taken on its word, as every member's own history is. Anchoring bounds it: with each entry anchored in its author's log, an entry of the former member's anchored after the position its departure holds in that log does not count, and what precedes a departure becomes a position in the log rather than the set of entries the departure depends on.

The platform takes a member's own history on its word while cells serve load testing: it specifies what honest devices do on these paths, no scenario or test pins what the gate does with a member's contradictions, and a review reports none of it anew, since this change records it. Under [defect-reachability](../../specs/code-practices/defect-reachability.md) these paths are reachable over the network: a modified member device takes ownership back and kicks the owners that demoted it, which ends honest members' sessions. That obliges a fix, and this change is where the fix sits. The deferral ends before any cell carries data people depend on: this change lands before connections are removed from the platform.

The direction is set: anchored signatures. A key event log commits to its owner's events in order and cannot be appended to in the past, and an anchored signature ties a signed entry to a position in its signer's log, so a narrowing that names the position it saw in the narrowed member's log tells an act written after it from one written before it. Key event logs arrive with the platform's own KERI implementation.

**Example:** in "Family", Alice demoted Bob, an owner since his sequence 2, at his sequence 3, and kicked Carol at her sequence 2; Bob's phone b1 and Carol's phone c1 are modified, and Bob's device statements list b1 alone.

| entry | names | on every honest member device |
|---|---|---|
| b1 promotes Bob himself | Bob's sequence 2, at which he is an owner | admitted: Bob is an owner again |
| b1 then kicks Alice | Bob's sequence 2 | admitted: Alice is out of the cell, and her devices are refused from their next session |
| c1 places a claim under Carol's name, which a member device the kick has not reached takes and relays | Carol's sequence 1 | admitted |
| b1 promotes Bob himself naming his sequence 3, at which he is a plain member | Bob's sequence 3 | dropped |
| b1 places a claim under Alice's name | — | dropped |

## What Changes

The change settles how a cell's entries anchor in their authors' logs, and whether a defence lands ahead of the logs, and then specifies and builds the answer. Neither is decided; the options stand under Open Questions, strongest first.

## Open Questions

### What a member's log anchors

- Membership acts and record-store entries alike. Both stores stop taking a member's contradictions: an act or a record anchored past the position a narrowing saw does not count, a rewritten entry no longer matches the digest its anchor holds, and one member contradicting itself is duplicity the log detects. Each entry costs its author an event in its log, and a mergeable-document's operations are many.
- Membership acts alone. The membership store stops taking a member's contradictions at one log event per act, and acts are few; a departed member's record-store entries under its old sequence still pass, content signed as its own.

With several parties, the first-seen rule the KERI roadmap applies between two parties does not detect duplicity, so duplicity detection moves earlier in that roadmap under either option.

KERI's own shape for an anchored record is an Authentic Chained Data Container (ACDC) with a transaction event log (TEL): the record is the container, its issuance and revocation are events of the log, and each event is committed by a seal — its sequence number and digest — in an event of the issuer's key event log, which makes it verifiable and orders it against the issuer's rotations, while the date the event carries is the issuer's word ([ACDC](https://trustoverip.github.io/kswg-acdc-specification/), [TEL](https://trustoverip.github.io/tswg-ptel-specification/draft-pfeairheller-ptel.html)). Record-store entries anchored under the first option would take the same shape, and a cell's claim presented to a party outside the cell would travel by the Issuance and Presentation Exchange protocol (IPEX), whose messages disclose a container to a party that signs its acceptance ([IPEX](https://www.ietf.org/archive/id/draft-ssmith-ipex-00.html)).

**Example:** the cases of Why, under each option.

| option | b1 promotes Bob under his sequence 2 | c1's claim under Carol's sequence 1 |
|---|---|---|
| acts and entries anchored | ignored: anchored past the position Alice's demotion saw in Bob's log | dropped: anchored past the position the kick saw in Carol's log |
| acts alone | ignored, as above | admitted |

### Whether a defence lands before the logs

- Act numbers and narrowing marks in the membership store. Every membership act carries in its key its author's own act number in the cell: 1 for the author's first act, one more for each next, and an act is admitted only once the device holds every lower number of the same author, so a device holding an act holds every earlier act of its author. Every event that narrows a member — demoted, kicked, left — carries a mark: for each author the member's device statements list, the highest number of that author's acts the writing device holds; the event is admitted only once the device holds the acts its mark names, so a mark names nothing that did not exist when it was written. An act of the member naming a point before a narrowing that forbids it — any act before a kick or a leave, an owner's act before a demotion — counts only if its number is within that narrowing's mark for its author: the first such narrowing after the named point decides, and at a sequence holding several, the highest of their marks. An act beyond the mark was written after the narrowing, or before it and unseen by the narrowing's writer, and the two are not told apart: a concurrent act loses to its actor's narrowing. Two acts of one author under one number are both ignored. The rule is the fold's: the fold that lists members, serves sessions and judges the record store ignores an act beyond the mark and every event resting on it, while the gate judges an event's named point by the membership folded without the rule, so every member device holds the same entries whatever order they arrived in. The mark never withdraws what the narrowing rests on: the writing device held every event its own authority depends on, and with them every earlier act of their authors. The whole membership store is in the write admission, so every check costs nothing at run time; the cost is the mechanism itself, built and tested before the logs replace it, and it leaves the record store open.
  - Weaker forms fall short. A mark on promotions alone leaves a demoted or kicked owner kicking and demoting others under its old point. A mark only in the invite act that readmits a member never reaches a demoted owner, who stays a member and is never readmitted. An event in the actor's own chain naming the point right before it lets a former owner promote a colluding member under its old point and be promoted back. A list of the acts the writer holds says what one number per author says once admission is gapless, and grows with every act.
  - At the gate instead of the fold, a device that learns of the narrowing first drops what rests on the ignored act while a device that learned later holds it, and every session between them offers the difference again.
  - The option brings a question of its own: what the record store admitted meanwhile on an act the fold later ignores — the records of a newcomer the act invited, and, where records can be deleted, the deletions of a member it promoted. Either the record store removes the entries that named the membership the ignored act gave, and every device converges on their absence, or they stay where they landed, and every session offers them again to the devices that drop them.
  - It also makes two owners' narrowings of each other depend on each other: each is an owner's act of its actor naming a point before the other, beyond the other's mark, so each counts only if the other does not, and the fold needs a rule for that — whether an act the fold ignores still narrows by its mark, or a tie-break.
- A kick that commits to the departed member's record-store entries: a per-author high-water mark on the operation sequence, or a Merkle root over the author's range. The high-water mark counts operations and does not reach a claim or an immutable-document, and needs a uniqueness the gate cannot check without the record store; the Merkle root needs a cached fingerprint tree in pdn-store.
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
| act numbers and marks | ignored: beyond the demotion's mark | admitted | replaces the original: the key, act number included, is the same |
| a kick that commits to record-store entries | counts | dropped, under the Merkle-root variant | replaces the original |
| hash-linked membership sequences | counts | admitted | shows once a later event of Dave's chain names the original's digest |
| witnessing | counts: every honest device accepted it | admitted on the commitment of the member device that relayed it | shows against the commitments made to the original |
| none | counts | admitted | replaces the original |

## Operating conditions

An unstable connection is what puts the gap within reach of ordinary timing: an entry reaches a device the narrowing has not yet reached, and any member device relays it from there. Clocks do not close it: an entry's timestamp is set by its author, and a key event log proves order, not time, so a point stays a position in a chain under every option. Placing a logged event against a wall-clock time takes evidence from outside the log: a witness's signed and dated record of the log's state shows that an event happened no later than that date, while that an event happened after a given time rests on its author's word alone ([ToIP dossier specification, issue 35](https://github.com/trustoverip/kswg-dossier-specification/issues/35)); a cell has no witnesses, so it keeps relative order only. A capability-bound write does not close it alone either, since an entry signed under a since-revoked capability poses the same question.

## Out of Scope

- Two owners writing at one point of one member's chain while disconnected from each other: a race among honest owners, which the cell's membership rules settle.
- The identity proof at join and device statements signed under the identity's key: steps of the KERI roadmap of their own.
- Real expulsion of a member, whose tickets stay valid under bearer tickets: a question of its own.

## Capabilities

None is settled. Every option touches `components/mee-pdn/data-layer/cell-store`, where the membership fold and the gate are specified, and `components/mee-pdn/pdn-node/cells`, where acts are written.

## Impact

- **`crates/data-layer`**: the membership fold and the gate of both cell stores.
- **`crates/pdn-node`**: the membership acts the cells service writes, and their anchors.
- **The KERI implementation**: the key event log each member's entries anchor in.
