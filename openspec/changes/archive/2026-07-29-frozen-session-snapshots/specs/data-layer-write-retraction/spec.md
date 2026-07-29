# Delta: data-layer-write-retraction

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: A rejection carries one device's knowledge, not the issuer's

A rejection states that the refusing device lacks the named entry, which on an issuer of several devices is narrower than the issuer lacking it. A device that admitted an entry can go offline before that entry replicates to its siblings, and a sibling the writer reaches afterwards — judging by a grant narrowed meanwhile — lacks the entry honestly and signals. The writer then retracts a write the issuer holds and keeps, marks it, refuses its re-ingest until the marker is superseded or ages out, and surfaces a retraction event for a write that was in fact accepted. This is the accepted window, bounded by the marker's retention: no device can establish what its siblings hold without asking them, and asking would put sibling availability back into the path this discipline exists to keep clear of it. Two guards SHALL therefore stand: the writer's confirmation against its own replica, which establishes that the named entry is one the writer holds and never that the issuer lacks it, and the content hash the marker records, since a wrongly retracted entry has no other address to be recovered from.

Three ways to close the window are open and none is chosen. Leaving it as it stands costs nothing further and relies on the recovery surface the recorded content hash seeds, at the price of a wrong verdict shown to the writer's user. Signalling only from a device that can vouch for its identity — one that knows itself caught up with its siblings — is exact, and it returns the sibling availability this design took out of the path. Making retraction reversible, so that later sight of the entry at the issuer restores it, keeps availability out of the path and turns the guarantee from prevention into repair, at the cost of a recovery mechanism the writer does not have. Choosing between them wants a measurement this spec does not carry: how often an admitting device goes offline before it replicates.

#### Scenario: A stale sibling's rejection retracts an accepted write

- **WHEN** one device of the issuer admits a write, goes offline before the entry replicates, and the writer afterwards reaches a sibling that lacks the entry and holds a grant narrowed meanwhile
- **THEN** the sibling signals, the writer retracts and marks the entry, and the issuer goes on holding it — the divergence standing until the marker is superseded or ages out

