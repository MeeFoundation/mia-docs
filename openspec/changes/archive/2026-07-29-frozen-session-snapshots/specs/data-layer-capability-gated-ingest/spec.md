# Delta: data-layer-capability-gated-ingest

## MODIFIED Requirements

### Requirement: Ingest into a hosted issuer's replica is capability-gated

On a replica data-bound to an identity the node hosts, an entry arriving over sync SHALL be admitted only when the session peer resolves as a device of the issuer, or the entry's derived claim identity is in the write set of the sender identity's recorded grant. An admitted entry is persisted; a refused entry SHALL be dropped before persisting, leaving the replica unchanged. A capability refusal SHALL be signalled back to the sender on the reconciliation reply, carrying the refused entry's identity, so the writer can retract it at once; the refused entry is still not remembered, so a lost signal self-heals as reconciliation re-offers it in a later session. Only a capability refusal SHALL be signalled. Every other reason the gate keeps an entry out — a live retraction marker, a peer whose session it cannot resolve, its own records unreadable — SHALL refuse silently, because a signalled refusal makes the sender destroy its own entry, and none of those reasons is a verdict on that sender's authority. A rejection SHALL name only an entry the replica would newly store: an entry it already holds was admitted when it arrived, so refusing that one is silent however the grant reads now. Two things bring such an entry back to the gate, and both work the same way: the session's view hides an entry the replica holds, so the sender reads the two sets as divergent and re-offers what the issuer keeps. Narrowing a grant hides it because the entry leaves the egress filter; a session snapshot hides it when the entry lands after session setup ([subset reconciliation](subset-reconciliation.md)). Signalling in either case would destroy the sender's copy of data both sides hold, so the check behind a rejection SHALL read the replica's live state, never the session's frozen view. The writer-side discipline is [write retraction](write-retraction.md). Local inserts are not gated: the issuer's own writes carry its authority.

#### Scenario: A write on a write-granted claim is admitted

- **WHEN** an audience granted read-write on a claim writes that claim and reconciles with a device of the issuer
- **THEN** the issuer's devices converge on the audience's entry

#### Scenario: A write outside the write set is refused

- **WHEN** the same audience produces an entry at a claim its grant covers read-only, or not at all, and reconciles with the issuer's devices
- **THEN** no device of the issuer ever persists it, and the issuer's own value at that path survives unchanged

#### Scenario: A read-only audience's entry is refused

- **WHEN** an audience whose grant carries no write produces an entry in the issuer's namespace and reconciles
- **THEN** the entry is refused, and the issuer's replica is unchanged

#### Scenario: Withdrawal refuses from the next session

- **WHEN** the issuer withdraws a grant carrying write and the tombstone reaches a device's copy of the pair
- **THEN** that device admits nothing from the withdrawn audience in sessions set up afterwards, although the audience still holds the write ticket

#### Scenario: A refusal that is not a capability verdict is silent

- **WHEN** the gate keeps an entry out for a reason other than the sender's write capability
- **THEN** the entry is not persisted and the reply carries no rejection for it, so the sender keeps its entry and re-offers it in a later session

#### Scenario: An entry the replica already holds draws no rejection

- **WHEN** a grant narrows so that a claim leaves the write set, and the audience re-offers an entry at that claim which the issuer admitted before the narrowing
- **THEN** the issuer keeps its stored entry, the reply carries no rejection for it, and the audience retracts nothing

#### Scenario: An entry hidden by the session snapshot draws no rejection

- **WHEN** an entry lands on the issuer's replica after a session's setup, so the frozen egress hides it and the audience re-offers it, and the gate refuses that audience
- **THEN** the issuer keeps its stored entry, the reply carries no rejection for it, and the audience retracts nothing

