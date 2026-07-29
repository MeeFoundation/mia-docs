# Write retraction

## Purpose

The writer-side discipline that keeps a refused foreign write from breaking the writer forever. A write into a granted namespace is provisional until the issuer keeps it: [capability-gated ingest](capability-gated-ingest.md) refuses an out-of-scope entry and signals that refusal back to the sender on the reconciliation reply — a withdrawal race or an adversarial client reaches here. The writer, on the issuer's rejection, physically removes the entry, replicates the verdict to its sibling devices as a marker, and surfaces the outcome, so acquisition stays capability-covered (Invariant 2) on the write side and no honest writer wedges. The marker is an accelerator for a sibling that has not itself reached the issuer, not the enforcement.

## Requirements

### Requirement: A foreign write is provisional until the issuer keeps it

An own entry in a granted (audience-postured) namespace is provisional until the issuer keeps it. Acceptance is locally unobservable — an accepted and a refused write leave the writer's replica identical — so the issuer's gate SHALL signal its refusal back to the writer: when the gate refuses an entry at ingest for lack of a write capability, the reply of that reconciliation session SHALL carry the refused entry's identity — author, path, timestamp — to the sender. The gate SHALL signal only an entry its replica does not hold, so a rejection states that the refusing device lacks the named entry; one that device admitted in an earlier session is refused silently however the grant reads now. On an issuer of several devices that statement is narrower than the issuer lacking the entry, and the requirement on a rejection carrying one device's knowledge states the bound that leaves. A writer that receives such a rejection from a peer resolving as a device of the issuer (the same published-device-set resolution the read side uses), for an entry of its own author, SHALL judge that entry not accepted — one session, no counting. A rejection from any other peer, or for an entry the writer did not author, SHALL be ignored, so a forged rejection cannot make a writer discard data it holds legitimately. A rejection's fields are the refusing peer's word and retraction is irreversible, so the writer SHALL confirm them against its own replica before judging: the named author, path, timestamp and content hash SHALL match a record it holds at that moment. A name matching no local record SHALL retract nothing — a fabricated timestamp addresses no entry of the writer's, and a version already replaced by a newer own write is not the one the rejection judged. A refusal for any other reason SHALL NOT be signalled: a bad signature or a timestamp outside the window is transient, and a live marker or a session the gate cannot resolve is the receiving node's own state rather than a verdict on the sender's authority. Signalling either would make an honest writer destroy an entry it holds legitimately. A lost rejection is self-healing: the refused entry stays in the set difference and is re-offered in a later session, carrying the rejection again.

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

A rejection states that the refusing device lacks the named entry, which on an issuer of several devices is narrower than the issuer lacking it. A device that admitted an entry can go offline before that entry replicates to its siblings, and a sibling the writer reaches afterwards — judging by a grant narrowed meanwhile — lacks the entry honestly and signals. The writer then retracts a write the issuer holds and keeps, marks it, refuses its re-ingest until the marker is superseded or ages out, and surfaces a retraction event for a write that was in fact accepted. This is the accepted window, bounded by the marker's retention: no device can establish what its siblings hold without asking them, and asking would put sibling availability back into the path this discipline exists to keep clear of it. Two guards SHALL therefore stand: the writer's confirmation against its own replica, which establishes that the named entry is one the writer holds and never that the issuer lacks it, and the content hash the marker records, since a wrongly retracted entry has no other address to be recovered from.

Three ways to close the window are open and none is chosen. Leaving it as it stands costs nothing further and relies on the recovery surface the recorded content hash seeds, at the price of a wrong verdict shown to the writer's user. Signalling only from a device that can vouch for its identity — one that knows itself caught up with its siblings — is exact, and it returns the sibling availability this design took out of the path. Making retraction reversible, so that later sight of the entry at the issuer restores it, keeps availability out of the path and turns the guarantee from prevention into repair, at the cost of a recovery mechanism the writer does not have. Choosing between them wants a measurement this spec does not carry: how often an admitting device goes offline before it replicates.

#### Scenario: A stale sibling's rejection retracts an accepted write

- **WHEN** one device of the issuer admits a write, goes offline before the entry replicates, and the writer afterwards reaches a sibling that lacks the entry and holds a grant narrowed meanwhile
- **THEN** the sibling signals, the writer retracts and marks the entry, and the issuer goes on holding it — the divergence standing until the marker is superseded or ages out

### Requirement: Retraction restores the issuer's accepted state locally

A rejected entry SHALL be physically removed from the local replica — never tombstoned: a tombstone is one more entry the gate refuses, and it shadows the issuer's entries locally instead of restoring them. After removal, the issuer's entry is the latest for the path again and later sessions re-offer nothing.

#### Scenario: The local view returns to the issuer's value

- **WHEN** retraction runs on an own entry at a claim the issuer refused
- **THEN** reading that path locally returns the issuer's value, and subsequent reconciliations with the issuer re-send nothing for it

### Requirement: The verdict replicates to sibling devices as a directory marker

The rejection reaches only the writer device that was in the session, so a sibling that holds the entry but has not itself reached the issuer would not learn of it; the verdict SHALL therefore also be recorded at `retractions/<issuer-hex>/<author-hex>/<path>`, with a bounding timestamp inside, in the private metadata store of every identity this node hosts that holds a grant on that issuer. One replica per issuer serves every identity granted by it, and a marker reaches only the devices of the identity whose directory carries it, so recording it in one of them would leave the others' devices holding the retracted entry. Every device of the identity, on reading the marker, SHALL remove matching entries — that author, that path, timestamp at or below the bound — from its copy of the granted replica and SHALL refuse their re-ingest, so a retraction cannot flap back from a sibling that still holds the entry. That refusal SHALL be silent: the marker states what this identity already retracted, and the peer offering the entry is often the issuer itself, which kept it and is entitled to hold it. One live entry per author and path exists in a replica at a time, so the bound also covers a value rewritten while the marker travelled, and a newer own write dated above the bound is never matched. The marker is an accelerator and a durability aid, not the enforcement — a device that reaches the issuer with an entry of its own authorship earns its own rejection regardless. It is not backed up that way for a copy authored elsewhere: a rejection names one author, and a device honors only rejections naming an author it writes with, so the retention window has to outlast replication of the marker to the identity's own devices. Markers SHALL carry the writing device's node id, the content hash, and the timestamp of what was retracted, as provenance for the event and a future recovery surface. A marker SHALL be dropped once the entry it addresses can no longer win — superseded by a newer own entry at that author and path, or aged out by a retention window — and in bulk when the granted namespace is forgotten. Dropping a marker SHALL take down the ingest refusal it armed: arming only ever widens, so a refusal that outlived its marker would go on answering for as long as the node runs, past the window that is supposed to bound it. Restoring write on the claim SHALL NOT drop the marker: a re-grant does not validate the old refused entry, and it removes the issuer-gate backstop, so the marker holds until the entry is superseded or aged out.

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
- **THEN** the marker stands until a newer own write supersedes the retracted entry or the retention window elapses — the re-grant alone drops nothing

#### Scenario: Markers age out and leave with the grant binding

- **WHEN** a marker's retention window elapses, or the granted namespace is forgotten
- **THEN** the marker is pruned from the directory, and the ingest refusal it armed stops refusing

### Requirement: The retraction outcome is observable

Retraction SHALL emit a log record and a runtime-consumable event carrying the issuer, the path, the author, the timestamp, the content hash, and the deciding device — the refusal is never silent at the writer, and the marker is the durable half of the same record. The payload blob is not copied: it stays in the blob store as long as the store lives, so the marker's address is the seed of a later recovery surface.

#### Scenario: A verdict produces an event

- **WHEN** an entry is retracted
- **THEN** a subscriber to the retraction events observes one event naming that issuer, path, author, timestamp, and content hash
