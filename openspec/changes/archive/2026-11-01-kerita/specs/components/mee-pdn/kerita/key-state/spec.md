# KERI key state

## Purpose

How the KERI crate folds a [KEL](../../../../architecture/language/kel.md) into [key state](../../../../architecture/language/key-state.md), as keripy, the reference implementation, does for the subset [ADR-0017](../../../../architecture/adr/0017-keri-identity-layer.md) uses, and what it answers for every event that does not advance the key state. The rules ADR-0017 sets on top of KERI — the roles a role statement gives, the weight each role carries, the limits on a KEL, the old [witness](../../../../architecture/language/witness.md)'s [receipt](../../../../architecture/language/receipt.md) on a change of witness — are not here: the crate hands the layers above what those rules read.

## ADDED Requirements

### Requirement: Key state is a fold of the KEL
The key state of an [AID](../../../../architecture/language/aid.md) SHALL be determined by its KEL's accepted events, in order, together with the receipts and the delegator's KEL those events need. The crate SHALL keep nothing between calls: folding the same events again SHALL reach the same key state. An accepted event SHALL leave in the key state what the layers above read from it: the keys that signed it and their slots, the seals it anchors, and the witness list it sets.

**Example:** Alice's phone restarts with her identity's KEL of 10 events in its store.

| | before the restart | after it |
|---|---|---|
| what the phone holds | events 0 to 9, accepted | the same 10 events, read from its store |
| key state | sequence number 9, the keys and next-key digests event 9 set, witness W-tellipod | the fold of events 0 to 9 reaches the same |

#### Scenario: A fold of a stored KEL reaches the key state accepted before
- **WHEN** the accepted events of a KEL are folded again from the first one
- **THEN** the fold reaches the key state that accepting them one by one reached

#### Scenario: An accepted event exposes what the layers above read
- **WHEN** a rotation is accepted
- **THEN** the key state names the slots that signed it, the seals it anchors and the witness list it sets

### Requirement: An inception establishes the key state
An `icp` or `dip` SHALL establish the AID's key state: its current keys and their threshold, the digests of its next keys and their threshold, its witness list and witness threshold, and its configuration traits. A self-addressing prefix SHALL be the event's SAID, and a basic prefix SHALL be the event's one key. The event SHALL be signed by current keys meeting the current threshold.

**Example:** the inception of Alice's identity on her phone, with a paper sheet and no co-signer.

```
k:   [phone's key (P-256), paper's key]            kt: ["1","1"]
n:   [digest of phone's next key, digest of paper's next key]   nt: ["1","1"]
b:   [W-tellipod]                                  bt: 1
c:   ["EO"]
prefix: the event's SAID
signed by the phone alone: 1 >= 1, accepted once W-tellipod's receipt is attached
```

#### Scenario: An inception meeting its threshold is accepted
- **WHEN** an inception is signed by current keys whose weights reach its threshold, and its witnesses' receipts reach its witness threshold
- **THEN** the crate establishes the key state the event sets

#### Scenario: An inception whose prefix does not derive from it is refused
- **WHEN** an inception carries a self-addressing prefix other than its SAID
- **THEN** the crate refuses it

### Requirement: A rotation exposes committed keys and meets both thresholds
A `rot` or `drt` SHALL follow the last accepted event: its sequence number one higher, its prior digest that event's SAID. Each signature's key SHALL match, by its digest, the next-key digest at the signature's index into the prior establishment event's next keys, and SHALL be the key at its index into the rotation's own current keys. The signatures SHALL meet both the rotation's current threshold and the prior establishment event's next threshold. The crate SHALL accept next-key digests carried over unchanged from the prior establishment event, as a controller carries them for keys that do not sign. A signature that fails to match SHALL count for nothing.

**Example:** Alice's laptop and the co-signer link her tablet in rotation 5; her desktop is off.

| | rotation 4 (prior) | rotation 5 |
|---|---|---|
| next-key digests | 0 paper, 1 co-signer, 2 phone, 3 laptop, 4 desktop | the co-signer's and laptop's new ones, phone, desktop and paper carried over, the tablet's |
| next threshold | `["1","1/2","1/2","1/2","1/2"]` | |
| current keys | | co-signer's key, laptop's key, `kt` `["1/2","1/2"]` |
| signatures | | co-signer: current index 0, prior-next index 1; laptop: current index 1, prior-next index 3 |
| outcome | | prior next threshold 1/2 + 1/2 = 1, current threshold 1/2 + 1/2 = 1: accepted |

#### Scenario: A rotation signed by committed keys meeting both thresholds is accepted
- **WHEN** a rotation is signed by 2 keys whose digests sit at their indices in the prior next keys, and their weights reach both thresholds
- **THEN** the crate accepts the rotation and the key state takes its keys and next-key digests

#### Scenario: One signer short, the rotation waits for signatures
- **WHEN** the same rotation carries the co-signer's signature alone
- **THEN** the crate answers that the rotation waits for more signatures, and the key state stays at rotation 4

#### Scenario: A key that was never committed counts for nothing
- **WHEN** a signature's key does not match the next-key digest at its prior-next index
- **THEN** the crate counts that signature for nothing toward either threshold

### Requirement: Thresholds are numeric or weighted
A threshold SHALL be either a number of keys, written in hexadecimal, or a list of weight clauses, each weight a fraction from 0 to 1. A weighted threshold SHALL be met when, in every clause, the weights of the signing keys within that clause add up to at least 1. A clause list of one clause SHALL be met as one clause. Any other threshold form, such as nested weight maps, SHALL be refused as unsupported.

**Example:** keripy's threshold `[["1/2","1/2","1/2"],["1","1"]]` over 5 keys, the first clause covering keys 0 to 2 and the second keys 3 and 4.

| signers | first clause | second clause | met |
|---|---|---|---|
| 0, 1, 3 | 1/2 + 1/2 = 1 | 1 | yes |
| 0, 1 | 1 | 0 | no |
| 0, 3, 4 | 1/2 | 2 | no |

#### Scenario: Every clause met, the threshold is met
- **WHEN** an event is signed by keys 0, 1 and 3 under `[["1/2","1/2","1/2"],["1","1"]]`
- **THEN** the crate counts the threshold as met

#### Scenario: One clause short, the threshold is not met
- **WHEN** the same event is signed by keys 0 and 1 alone
- **THEN** the crate counts the threshold as not met

#### Scenario: A nested weight map is refused as unsupported
- **WHEN** an event carries a threshold written as a nested weight map
- **THEN** the crate refuses the event as unsupported

### Requirement: An establishment-only KEL takes no interaction event
An `ixn` in a KEL whose inception carries the `EO` trait SHALL be refused. The `EO` trait SHALL take effect from the inception alone. A configuration trait other than `EO` in an inception, and any configuration trait in a rotation, SHALL be refused as unsupported.

**Example:** Alice's identity KEL, incepted with `"c":["EO"]`, receives an `ixn` at sequence number 4 signed by her phone and laptop; the crate refuses it, and the key state stays at rotation 3.

#### Scenario: An interaction event in an establishment-only KEL is refused
- **WHEN** an `ixn` arrives for a KEL whose inception carries `EO`
- **THEN** the crate refuses it, whatever signs it

#### Scenario: An interaction event in a KEL without the trait is accepted
- **WHEN** an `ixn` signed by current keys meeting the current threshold arrives for a KEL whose inception carries no trait
- **THEN** the crate accepts it and the key state names the seals it anchors

#### Scenario: Another trait is refused as unsupported
- **WHEN** an inception carries the `DND` trait
- **THEN** the crate refuses it as unsupported

### Requirement: A delegated event is accepted once the delegator's KEL approves it with a key event seal
A `dip` or `drt` SHALL be accepted only when an accepted event of the delegator's KEL anchors a [key event seal](../../../../architecture/language/key-event-seal.md) of it — the delegated AID, the delegated event's sequence number and its SAID. The approving event MAY be an establishment event or an interaction event. A [digest seal](../../../../architecture/language/digest-seal.md) of the delegated event SHALL approve nothing. Until such an event is accepted in the delegator's KEL, the crate SHALL answer that the delegated event waits for its delegator's approval, naming the delegator — unless the caller says the validator controls the delegated AID or witnesses it, as keripy then accepts the event, so that the delegate can ask for its approval. A `drt` SHALL take its delegator from its AID's `dip`.

**Example:** rotation 3 of Alice's identity KEL, which is establishment-only, approves the inception of her laptop's device AID.

```
rotation 3, a:  [{"i": "E-laptop", "s": "0", "d": "E-laptop"}]    a key event seal
E-laptop's dip: d = i = E-laptop, di = Alice's AID
outcome:        accepted once rotation 3 is accepted
had rotation 3 carried [{"d": "E-laptop"}] instead, a digest seal:
                the dip waits for its delegator's approval
```

#### Scenario: A delegated inception approved by a rotation is accepted
- **WHEN** a `dip` arrives and an accepted rotation of its establishment-only delegator anchors a key event seal of it
- **THEN** the crate accepts the `dip`

#### Scenario: A digest seal approves nothing
- **WHEN** the delegator's KEL anchors only a digest seal of the `dip`
- **THEN** the crate answers that the `dip` waits for its delegator's approval

#### Scenario: A delegated rotation is approved like a delegated inception
- **WHEN** a `drt` arrives and an accepted event of the delegator named by its AID's `dip` anchors a key event seal of it
- **THEN** the crate accepts the `drt`

### Requirement: An event of a witnessed KEL needs receipts from the witness list it falls under
An event of a KEL that lists witnesses SHALL be accepted only with valid receipts from at least as many of its witnesses as the witness threshold demands. For an inception, the witnesses SHALL be those it lists. For a rotation, they SHALL be the prior list without the witnesses the rotation cuts and with those it adds, and the threshold SHALL be the rotation's. A receipt by an AID outside that list SHALL count for nothing. A witness list SHALL hold no witness twice, and its threshold SHALL be at least 1 and at most the number of witnesses, or 0 when the list is empty; an event breaking either SHALL be refused. A witness's receipt SHALL verify under the key its prefix is, and an event listing a witness whose prefix is no key, such as a self-addressing one, SHALL be refused, as keripy refuses it. Until enough receipts are attached, the crate SHALL answer that the event waits for receipts. When the caller says the validator controls the event's AID or is one of its witnesses, the crate SHALL accept the event without receipts, as keripy does, so that a witness can give its own.

**Example:** rotation 9 of Alice's identity KEL moves her from W-tellipod to W-home, with witness threshold 1.

| receipts attached | outcome |
|---|---|
| W-home's | accepted |
| W-tellipod's alone | waits for receipts: W-tellipod is cut by rotation 9 |
| none | waits for receipts |

#### Scenario: Receipts from the witnesses the rotation sets are enough
- **WHEN** a rotation that cuts one witness and adds another carries the added witness's receipt alone, under witness threshold 1
- **THEN** the crate accepts it

#### Scenario: A receipt from a cut witness counts for nothing
- **WHEN** the same rotation carries the cut witness's receipt alone
- **THEN** the crate answers that it waits for receipts

#### Scenario: A witness accepts the event it is to receipt
- **WHEN** a witness of Alice's identity is given her rotation with no receipt attached, as the validator the rotation names among its witnesses
- **THEN** the crate accepts the rotation

#### Scenario: A witness whose prefix is no key is refused
- **WHEN** an inception lists a self-addressing AID as its witness and carries a valid signature
- **THEN** the crate refuses it

#### Scenario: A witness threshold above the list is refused
- **WHEN** an inception lists one witness under witness threshold 2
- **THEN** the crate refuses it

### Requirement: The first accepted event at a position stays
An event at a position where an event is already accepted SHALL leave the key state unchanged. The same event again SHALL be answered as a duplicate. A different event at that position SHALL be answered as [duplicity](../../../../architecture/language/duplicity.md), carrying the accepted event's SAID and the rival message with its signatures and receipts as evidence, as keripy answers it before checking the rival's signatures. No event SHALL replace an accepted one, and so no rotation supersedes an accepted event.

**Example:** Alice's identity KEL at sequence number 8, and 2 rotations at sequence number 9.

| arrives | answer | key state |
|---|---|---|
| rotation A at 9, signed and receipted | accepted | 9, from A |
| rotation A at 9 again | duplicate | 9, from A |
| rotation B at 9, validly signed | duplicity: A accepted, B the rival | 9, from A |

#### Scenario: A repeated event is a duplicate
- **WHEN** an accepted event arrives again
- **THEN** the crate answers that it is a duplicate, and the key state is unchanged

#### Scenario: A rival event is duplicity and replaces nothing
- **WHEN** a different event arrives at the position of an accepted one
- **THEN** the crate answers duplicity with both events, and the key state keeps the accepted one

### Requirement: An event that cannot be validated yet is answered with what it waits for
For an event that cannot be validated yet, the crate SHALL answer with what it waits for: the prior event at a named sequence number, more signatures, its delegator's approval, or more receipts. The crate SHALL keep nothing of such an event: its caller holds it, and the same event given again once the awaited input is there SHALL be accepted.

**Example:** Bob's phone receives Alice's rotation 7 before her rotation 6.

| step | given | answer | key state |
|---|---|---|---|
| 1 | rotation 7 | waits for the prior event at sequence number 6 | 5 |
| 2 | rotation 6 | accepted | 6 |
| 3 | rotation 7 again | accepted | 7 |

#### Scenario: An event ahead of its prior waits for it
- **WHEN** an event arrives whose prior event is not yet accepted
- **THEN** the crate answers that it waits for the prior event, naming its sequence number, and the key state is unchanged

#### Scenario: The waiting event is accepted once its prior is
- **WHEN** the prior event is accepted and the waiting event is given again
- **THEN** the crate accepts it
