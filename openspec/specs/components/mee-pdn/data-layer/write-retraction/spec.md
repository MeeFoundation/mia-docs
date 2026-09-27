# Write retraction

## Purpose

The writer-side discipline that keeps a refused foreign write from breaking the writer forever. A write into a granted namespace is provisional until the issuer keeps it: [capability-gated ingest](../capability-gated-ingest/spec.md) refuses an out-of-scope entry and signals that refusal back to the sender on the reconciliation reply — a withdrawal race or an adversarial client reaches here. The writer, on the issuer's rejection, physically removes the entry, replicates the verdict to its sibling devices as a marker, and surfaces the outcome, so acquisition stays capability-covered (Invariant 2) on the write side and no honest writer wedges. The marker is an accelerator for a sibling that has not itself reached the issuer, not the enforcement.

## Requirements

### Requirement: A foreign write is provisional until the issuer keeps it

An own entry in a granted (audience-postured) namespace is provisional until the issuer keeps it. Acceptance is locally unobservable — an accepted and a refused write leave the writer's replica identical — so the issuer's gate SHALL signal its refusal back to the writer: when the gate refuses an entry at ingest for lack of a write capability, the reply of that reconciliation session SHALL carry the refused entry's identity — author, path, timestamp — to the sender. The gate SHALL signal only an entry its replica does not hold, so a rejection states that the refusing device lacks the named entry; one that device admitted in an earlier session is refused silently however the grant reads now. On an issuer of several devices that statement is narrower than the issuer lacking the entry, and the requirement on a rejection carrying one device's knowledge states the bound that leaves. A writer that receives such a rejection from a peer resolving as a device of the issuer (the same published-device-set resolution the read side uses), for an entry written by the author of the identity the session belongs to, SHALL judge that entry not accepted — one session, no counting. A rejection from any other peer, or for an entry the writer did not author, SHALL be ignored, so a forged rejection cannot make a writer discard data it holds legitimately. A rejection's fields are the refusing peer's word and retraction is irreversible, so the writer SHALL confirm them against its own replica before judging: the named author, path, timestamp and content hash SHALL match a record it holds at that moment. A name matching no local record SHALL retract nothing — a fabricated timestamp addresses no entry of the writer's, and a version already replaced by a newer own write is not the one the rejection judged. A refusal for any other reason SHALL NOT be signalled: a bad signature or a timestamp outside the window is transient, and a live marker or a session the gate cannot resolve is the receiving node's own state rather than a verdict on the sender's authority. Signalling either would make an honest writer destroy an entry it holds legitimately. A lost rejection is self-healing: the refused entry stays in the set difference and is re-offered in a later session, carrying the rejection again.

**Example:** Bob's phone b1 offers its entry at `contact/phone` to Alice's device a1 over reconciliation; what a1's gate answers.

| at a1 | gate outcome | rejection to b1 |
|---|---|---|
| Bob holds no write on `contact/phone`, a1 lacks the entry | `ValidateOutcome::Reject` | author, key, timestamp, content hash |
| the same, but a1 already holds that entry | `Reject`, not echoed: a1 holds the entry | none |
| the signature does not verify | `ValidationFailure::BadSignature` | none |
| the timestamp is over 10 minutes ahead of a1's clock | `ValidationFailure::TooFarInTheFuture` | none |
| a1 dialed b1 and cannot resolve it to Bob | `ValidateOutcome::Drop` | none |

#### Scenario: An accepted write draws no rejection

- **WHEN** the audience writes a write-granted claim and the issuer's devices admit it
- **THEN** no rejection is returned, the sets converge, and no retraction occurs

#### Scenario: A refused write draws a rejection in one session

- **WHEN** an own entry is refused by the issuer's gate for lack of write on its claim
- **THEN** the issuer's reply carries the rejection, and the writer judges the entry not accepted in that session

#### Scenario: A forged rejection from a non-issuer peer is ignored

- **WHEN** a peer that is not a device of the issuer returns a rejection for an entry the writer authored
- **THEN** the writer retracts nothing and the entry stands

#### Scenario: A rejection naming an entry the writer does not hold is ignored

- **WHEN** a device of the issuer returns a rejection whose timestamp matches no record the writer holds at that author and path
- **THEN** the writer retracts nothing, records no marker, and the entry stands

### Requirement: A rejection carries one device's knowledge, not the issuer's

A rejection states that the refusing device lacks the named entry, which on an issuer of several devices is narrower than the issuer lacking it. A device that admitted an entry can go offline before that entry replicates to its siblings, and a sibling the writer reaches afterwards — judging by a grant narrowed meanwhile — lacks the entry honestly and signals. The writer then retracts a write the issuer holds and keeps, marks it, refuses its re-ingest until the marker is superseded or ages out, and surfaces a retraction event for a write that was in fact accepted. This is the accepted window. On the writer device the marker's retention bounds it. On a sibling that armed the refusal from the writer's marker it lasts until the sibling restarts or forgets the issuer's namespace after the marker has aged out, and the marker of a writer device that never runs again ages out on no device, so there the window has no bound. It stays open because no device can establish what its siblings hold without asking them, and asking would put sibling availability back into the path this discipline exists to keep clear of it. Two guards SHALL therefore stand: the writer's confirmation against its own replica, which establishes that the named entry is one the writer holds and never that the issuer lacks it, and the content hash the marker records, since a wrongly retracted entry has no other address to be recovered from.

Three ways to close the window are open and none is chosen. Leaving it as it stands costs nothing further and relies on the recovery surface the recorded content hash seeds, at the price of a wrong verdict shown to the writer's user. Signalling only from a device that can vouch for its identity — one that knows itself caught up with its siblings — is exact, and it returns the sibling availability this design took out of the path. Making retraction reversible, so that later sight of the entry at the issuer restores it, keeps availability out of the path and turns the guarantee from prevention into repair, at the cost of a recovery mechanism the writer does not have. Choosing between them wants a measurement this spec does not carry: how often an admitting device goes offline before it replicates.

**Example:** Alice (issuer) on devices a1 and a2; Bob, write grant on `contact/phone`, on his phone b1.

| step | b1 | a1 | a2 |
|---|---|---|---|
| 1 | writes `contact/phone` "+7-999-0001" | | |
| 2 | session with a1 | admits the entry | |
| 3 | | goes offline before a2 has it | narrows Bob's grant to read-only |
| 4 | session with a2 | | lacks the entry, Bob has no write: rejection |
| 5 | retracts, records the marker, emits the event | | |
| 6 | refuses the entry until the marker ages out | back online | takes the entry from a1: Alice holds it |

#### Scenario: A stale sibling's rejection retracts an accepted write

- **WHEN** one device of the issuer admits a write, goes offline before the entry replicates, and the writer afterwards reaches a sibling that lacks the entry and holds a grant narrowed meanwhile
- **THEN** the sibling signals, the writer retracts and marks the entry, and the issuer goes on holding it — the divergence standing until the marker is superseded or ages out

### Requirement: Retraction restores the issuer's accepted state locally

A rejected entry SHALL be physically removed from the local replica — never tombstoned: a tombstone is one more entry the gate refuses, and it shadows the issuer's entries locally instead of restoring them. After removal, the issuer's entry is the latest for the path again and later sessions re-offer nothing. A session already open when the retraction runs is not a later one: it serves the store as of its own setup ([subset reconciliation](../subset-reconciliation/spec.md)), so it goes on offering the retracted entry until it ends, and what it handed over is removed by the marker rather than by the removal.

**Example:** Bob's phone b1 writes `contact/phone` as Alice narrows his grant to read-only; `t1 < t2 < t3` are entry timestamps.

| b1's replica | entries at `contact/phone` | b1 reads |
|---|---|---|
| before the rejection | Alice's author t1 "+1-555-0100", b1's author t2 "+7-999-0001" | "+7-999-0001" |
| after `retract_entry` | Alice's author t1 "+1-555-0100" | "+1-555-0100" |
| a tombstone instead | Alice's author t1, b1's author t3 empty | nothing; Alice's gate refuses the tombstone too |

#### Scenario: The local view returns to the issuer's value

- **WHEN** retraction runs on an own entry at a claim the issuer refused
- **THEN** reading that path locally returns the issuer's value, and subsequent reconciliations with the issuer re-send nothing for it

### Requirement: The verdict replicates to sibling devices as a directory marker

The rejection reaches only the writer device that was in the session, so a sibling that holds the entry but has not itself reached the issuer would not learn of it; the verdict SHALL therefore also be recorded at `retractions/<issuer-hex>/<author-hex>/<path>`, with a bounding timestamp inside, in the private metadata store of the identity that holds the replica the entry was written into — the identity the verdict's author names, one author per identity. The replica belongs to that identity alone, so no device of another identity holds the entry, and a marker in a co-located identity's directory would address what that identity obtained under its own grant. Every device of the identity, on reading the marker, SHALL remove matching entries — that author, that path, timestamp at or below the bound — from its copy of the granted replica and SHALL refuse their re-ingest, so a retraction cannot flap back from a sibling that still holds the entry. That refusal SHALL be silent: the marker states what this identity already retracted, and the peer offering the entry is often the issuer itself, which kept it and is entitled to hold it. One live entry per author and path exists in a replica at a time, so the bound also covers a value rewritten while the marker travelled, and a newer own write dated above the bound is never matched. The marker is an accelerator and a durability aid, not the enforcement — a device that reaches the issuer with an entry of its own authorship earns its own rejection regardless. It is not backed up that way for a copy authored elsewhere: a rejection names one author, and a device honors only rejections naming an author it writes with, so the retention window has to outlast replication of the marker to the identity's own devices, and a session open across the retraction, which can hand the entry to a sibling after the marker was recorded. Markers SHALL carry the writing device's node id, the content hash, and the timestamp of what was retracted, as provenance for the event and a future recovery surface. A marker SHALL be dropped only by the device that recorded it: each device ages out the markers it recorded at its first marker sweep after their retention window (14 days) elapses, judged by the marker entry's own timestamp, and when the grant binder unbinds the issuer's withdrawn grant, forgetting the namespace it imported, each device drops every marker it recorded for that issuer. A sibling's markers therefore stay listed until the sibling drops them, and the marker of a device that never runs again is dropped by no device. An unbind whose pruning is cut short — the process ends, or a delete is refused — leaves the rest of that device's markers for the issuer until they age out, since the binder does not retry it. A newer own write at that author and path is not matched by the marker, since the bound is the retracted entry's timestamp: writing again after a retraction is the way back, and the marker stays until it ages out. Arming only ever widens, so a device SHALL take a refusal down at three moments and no others: when its own age-out drops the marker that armed it, when the issuer's replica is forgotten, which takes down every refusal on that replica, and at a restart, since refusals live in memory. A refusal armed from a sibling's marker therefore outlives that marker's age-out on the sibling until the device restarts or forgets the issuer's replica, and every marker still listed arms its refusal again at the next sweep that finds the issuer's namespace bound. Restoring write on the claim SHALL NOT drop the marker: a re-grant does not validate the old refused entry, and it removes the issuer-gate backstop, so the marker holds until it ages out.

**Example:** Bob's laptop b2 reads the marker `retractions/<alice-hex>/<b1-author-hex>/contact/phone`, bound t2; `t1 < t2 < t3`.

| entry held by b2 or offered to it | matched | b2 |
|---|---|---|
| b1's author, `contact/phone`, t2 or t1 | yes | removes it, and refuses its re-ingest silently |
| b1's author, `contact/phone`, t3 | no | admits it: a newer own write |
| Alice's author, `contact/phone`, t1 | no | admits it: another author |
| b1's author, `contact/email`, t2 | no | admits it: another path |

**Example:** b1 records `retractions/<alice-hex>/<b1-author-hex>/contact/phone`, bound t2, on day 0, and b2 arms its refusal from it; is b1's entry at `contact/phone`, timestamp t2, refused at ingest?

| moment | on b1 | on b2 |
|---|---|---|
| day 0, the marker lists on both | yes | yes |
| day 14, b1's marker sweep ages the marker out | no | yes, though b2 no longer lists the marker |
| day 15, b2 restarts or forgets Alice's replica | no | no |
| had b1 been lost before day 14, the marker would list for good, and b2 would arm it again at every restart and every fresh grant from Alice | | |

#### Scenario: A sibling converges on the retraction

- **WHEN** one device retracts an entry and the marker replicates to a sibling still holding it
- **THEN** the sibling removes the entry too, and it reappears on neither device

#### Scenario: A marker never suppresses the issuer's entries

- **WHEN** a retraction marker exists for an own author at a path
- **THEN** the issuer's entries at that path — other authors — replicate unaffected

#### Scenario: The issuer's later write at a marked path is read

- **WHEN** the issuer narrows a claim to read-only, a racing own write is retracted and marked, and the issuer later writes that path itself
- **THEN** the issuer's newer value — its own author — reaches the audience and is read, unaffected by the live marker

#### Scenario: Restoring write does not drop the marker

- **WHEN** the issuer restores write on a claim that has a live retraction marker
- **THEN** the marker stands until the retention window elapses or the binding is forgotten — the re-grant alone drops nothing, and a newer own write at the path is admitted past it

#### Scenario: Markers age out and leave with the grant binding

- **WHEN** a marker a device recorded outlives the retention window, or the grant binder on that device unbinds the issuer's withdrawn grant
- **THEN** that device drops the marker from the directory and takes down the ingest refusal it armed, and a sibling's marker for the same issuer stays listed

#### Scenario: A co-located identity's directory carries no marker

- **WHEN** one hosted identity's write into a granted namespace is retracted while a co-located identity holds a grant of the same issuer
- **THEN** the marker is recorded in the writing identity's directory alone, and the co-located identity's directory and replica are unchanged

### Requirement: The retraction outcome is observable

Once the writer has recorded the verdict's marker, it SHALL emit a log record at WARN carrying the issuer, the path and the timestamp, and a runtime-consumable event, `RetractionEvent`, carrying the issuer, the path, the author, the timestamp, the content hash, and the deciding device — the refusal is never silent at the writer, and the marker is the durable half of the same record. A marker that fails to be written SHALL be logged at WARN and emit no event: the removal runs from the marker, so nothing was retracted, and the entry draws its rejection again in a later session. The payload blob is not copied: it stays in the blob store as long as the store lives, so the marker's address is the seed of a later recovery surface.

**Example:** Bob's phone b1 retracts its entry at `contact/phone` in Alice's namespace; t2 is the entry's timestamp.

```
log, WARN   "write not accepted by the issuer; local copy retracted to the issuer's state", fields issuer, path, timestamp
event       RetractionEvent { issuer: Alice, path: contact/phone, author: b1's author, timestamp: t2,
                              content_hash: blake3 of "+7-999-0001", decided_by: b1 }
marker      retractions/<alice-hex>/<b1-author-hex>/contact/phone in Bob's directory, the durable half
```

#### Scenario: A verdict produces an event

- **WHEN** an entry is retracted
- **THEN** a subscriber to the retraction events observes one event naming that issuer, path, author, timestamp, content hash, and deciding device
