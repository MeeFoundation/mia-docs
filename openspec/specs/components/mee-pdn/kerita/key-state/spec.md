# Kerita key state

## Purpose

How kerita folds a [KEL](../../../../architecture/language/kel.md) into [key state](../../../../architecture/language/key-state.md), as keripy, the reference implementation, does for the subset [ADR-0017](../../../../architecture/adr/0017-keri-identity-layer.md) uses, and what it answers for every event that does not advance the key state. The rules ADR-0017 sets on top of KERI — the roles a role statement gives, the weight each role carries, the limits on a KEL, the old [witness](../../../../architecture/language/witness.md)'s [receipt](../../../../architecture/language/receipt.md) on a change of witness, the fork rule for devices (DR-22) — are not here: the crate hands the layers above what those rules read. For the fork rule that is a rival event answered as likely duplicitous, its signatures unchecked: the crate proves no duplicity, and the layer applying the rule proves the rival against the key state at its position before it acts.

## Requirements

### Requirement: Key state is a fold of the KEL
The key state of an [AID](../../../../architecture/language/aid.md) SHALL be determined by its KEL's accepted events, in order, together with the receipts and the delegator's KEL those events need. The crate SHALL keep nothing between calls: folding the same events again, each in the context it was accepted in, SHALL reach the same key state. `fold` in `src/state.rs` folds a KEL as a remote validator checks it; a controller or a witness folds its KEL through `KeyState::accept`, each event checked as it was. An accepted event SHALL leave in the key state what the layers above read from it: each index into its keys whose key signed it, once, with the prior next-key slot a rotation's signature at that index exposed, as checked against the digest committed in that slot and never as the signature's code claims it; the seals it anchors; and the witness list it sets.

**Example:** Alice's phone restarts with her identity's KEL of 10 events in its store.

| | before the restart | after it |
|---|---|---|
| what the phone holds | events 0 to 9, accepted | the same 10 events, read from its store |
| key state | sequence number 9, the keys and next-key digests event 9 set, witness W-tellipod | the fold of events 0 to 9 reaches the same |

#### Scenario: A fold of a stored KEL reaches the key state accepted before
- **WHEN** the accepted events of a KEL are folded again from the first one, each in the context it was accepted in
- **THEN** the fold reaches the key state that accepting them one by one reached

#### Scenario: An accepted event exposes what the layers above read
- **WHEN** a rotation is accepted
- **THEN** the key state names the slots that signed it, the seals it anchors and the witness list it sets

#### Scenario: A copy of a signature claims no slot
- **WHEN** a relay attaches to an accepted rotation copies of its signatures, one of them re-encoded to claim another prior next-key slot
- **THEN** the key state names each index that signed once, with the slot its key was committed in

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

#### Scenario: Another key under a basic prefix is refused
- **WHEN** an inception names a basic prefix and lists a key other than the prefix
- **THEN** the crate refuses it, and accepts the inception that lists the prefix's own key

### Requirement: A rotation exposes committed keys and meets both thresholds
A `rot` or `drt` SHALL follow the last accepted event: its sequence number one higher, its prior digest that event's SAID. Each signature SHALL verify under the key at its index into the rotation's own current keys, and SHALL count toward the rotation's current threshold. A signature SHALL count toward the prior establishment event's next threshold only when its key matches, by its digest, the next-key digest at its index into the prior next keys; one that does not match, or that carries no such index, SHALL count toward the current threshold alone, as keripy counts it, since a rotation may add keys that were never committed. The signatures SHALL meet both thresholds. The crate SHALL accept next-key digests carried over unchanged from the prior establishment event, as a controller carries them for keys that do not sign. A delegated AID SHALL rotate by `drt` alone, and its `rot` SHALL be refused; a `drt` of an AID nothing delegates SHALL be accepted as its rotation, needing no approval, as keripy accepts it.

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

#### Scenario: A key never committed does not count toward the prior next threshold
- **WHEN** a rotation's signatures meet its current threshold, one of them by a key that does not match the next-key digest at its prior-next index, and the committed keys among them fall short of the prior next threshold
- **THEN** the crate answers that the rotation waits for more signatures

#### Scenario: A key never committed counts toward the current threshold
- **WHEN** a rotation is signed by the paper's committed key at its prior-next index and by a key never committed, their weights together meeting the current threshold and the paper's alone the prior next threshold
- **THEN** the crate accepts the rotation

#### Scenario: A plain rotation of a delegated AID is refused
- **WHEN** a delegated AID's next event is a `rot`
- **THEN** the crate refuses it

#### Scenario: A delegated rotation of an AID nothing delegates is its rotation
- **WHEN** an AID incepted by an `icp` rotates by a `drt`
- **THEN** the crate accepts the `drt` as its rotation, asking no delegator's approval

### Requirement: An AID that commits to no next key takes no further event
An AID whose latest establishment event lists no next-key digest — abandoned by a rotation that commits to none, or incepted under a non-transferable prefix — SHALL take no further event: a rotation and an interaction event SHALL both be refused, as keripy refuses them, whoever signs them. An event SHALL belong to the AID whose key state it follows: one naming another AID SHALL be refused.

**Example:** an AID abandoned by its rotation 1, and an AID whose next threshold is 0 over one committed digest.

| the AID's latest establishment event | next event | outcome |
|---|---|---|
| rotation 1: `n` empty, `nt` 0 | a rotation to a thief's key, signed by it | refused |
| rotation 1: `n` empty, `nt` 0 | an interaction event signed by the AID's current key | refused |
| inception: `n` one digest, `nt` 0 | a rotation to a thief's key, signed by it | waits for signatures: a count of 0 is met by no signature |

#### Scenario: A rotation of an abandoned AID is refused
- **WHEN** an AID whose rotation committed to no next key receives a rotation signed by the keys it lists
- **THEN** the crate refuses it

#### Scenario: An interaction event of an abandoned AID is refused
- **WHEN** an AID whose rotation committed to no next key receives an interaction event signed by its current key
- **THEN** the crate refuses it

#### Scenario: A rotation of a non-transferable AID is refused
- **WHEN** an AID incepted under a non-transferable basic prefix receives a rotation
- **THEN** the crate refuses it

#### Scenario: An event of another AID is refused
- **WHEN** a rotation follows an AID's latest event and is signed by the key that event committed to, but names another AID
- **THEN** the crate refuses it

### Requirement: Thresholds are numeric or weighted
A threshold SHALL be either a number of keys, written in hexadecimal, or a list of weight clauses, each weight a fraction from 0 to 1. A count of 0 SHALL be met by no signature, as keripy's is. A weighted threshold SHALL be met when, in every clause, the weights of the signing keys within that clause add up to at least 1. A clause list of one clause SHALL be met as one clause. A clause whose weights add up to less than 1, which no signers can meet, SHALL be refused, as keripy refuses it. Any other threshold form, such as nested weight maps, SHALL be refused as unsupported.

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

#### Scenario: A count of 0 is met by no signature
- **WHEN** an AID whose next threshold is 0 over one committed digest receives a rotation
- **THEN** the crate answers that the rotation waits for more signatures, whatever signs it

#### Scenario: A clause no signers meet is refused
- **WHEN** an inception's current or next threshold is the one clause `["1/2"]`
- **THEN** the crate refuses the event

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
A `dip` or `drt` SHALL be accepted only when an accepted event of the delegator's KEL anchors a [key event seal](../../../../architecture/language/key-event-seal.md) of it — the delegated AID, the delegated event's sequence number and its SAID. The approving event MAY be an establishment event or an interaction event. A [digest seal](../../../../architecture/language/digest-seal.md) of the delegated event SHALL approve nothing. Until such an event is accepted in the delegator's KEL, the crate SHALL answer that the delegated event waits for its delegator's approval, naming the delegator — unless the caller says the event is checked by its controller or by a witness of its AID, as keripy then accepts the event, so that the delegate can ask for its approval. A `drt` SHALL take its delegator from its AID's `dip`.

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
An event of a KEL that lists witnesses SHALL be accepted only with valid receipts from at least as many of its witnesses as the witness threshold demands. For an inception, the witnesses SHALL be those it lists. For a rotation, they SHALL be the prior list without the witnesses the rotation cuts and with those it adds, and the threshold SHALL be the rotation's. A receipt by an AID outside that list SHALL count for nothing. A witness list SHALL hold no witness twice, and its threshold SHALL be at least 1 and at most the number of witnesses, or 0 when the list is empty; an event breaking either SHALL be refused. A witness's receipt SHALL verify under the key its prefix is, and an event listing a witness whose prefix is no key, such as a self-addressing one, SHALL be refused, as keripy refuses it. Until enough receipts are attached, the crate SHALL answer that the event waits for receipts. The caller SHALL say who checks the event: its controller, the node that created it for an AID it controls; a witness of its AID, given the event by its controller to receipt; or a remote validator, any validator given the event from another node, the validator's own AID's event included, a sibling device's among them. A controller or a witness SHALL accept the event without receipts, as keripy does, so that a witness can give its own; a remote validator SHALL ask for them. keripy holds apart an event of a validator's own, witnessed or delegated AID that arrives from another source; that rule is the caller's, whose transport knows the source, and the crate does not apply it.

**Example:** rotation 9 of Alice's identity KEL moves her from W-tellipod to W-home, with witness threshold 1.

| receipts attached | outcome |
|---|---|
| W-home's | accepted |
| W-tellipod's alone | waits for receipts: W-tellipod is cut by rotation 9 |
| none | waits for receipts |
| none, checked by W-home as the witness Alice's phone gave it to receipt | accepted |
| none, checked by Alice's laptop, which received it from her phone | waits for receipts: the laptop checks it as a remote validator |

#### Scenario: Receipts from the witnesses the rotation sets are enough
- **WHEN** a rotation that cuts one witness and adds another carries the added witness's receipt alone, under witness threshold 1
- **THEN** the crate accepts it

#### Scenario: A receipt from a cut witness counts for nothing
- **WHEN** the same rotation carries the cut witness's receipt alone
- **THEN** the crate answers that it waits for receipts

#### Scenario: A witness accepts the event it is to receipt
- **WHEN** a witness of Alice's identity is given her rotation by her controller to receipt, with no receipt attached, and the caller says a witness checks it
- **THEN** the crate accepts the rotation

#### Scenario: A witness whose prefix is no key is refused
- **WHEN** an inception lists a self-addressing AID as its witness and carries a valid signature
- **THEN** the crate refuses it

#### Scenario: A witness threshold above the list is refused
- **WHEN** an inception or a rotation sets witness threshold 2 over one witness
- **THEN** the crate refuses it

#### Scenario: A witness list that breaks its rules is refused
- **WHEN** an inception lists one witness twice, or a rotation cuts a witness not listed or adds one already listed
- **THEN** the crate refuses it, and accepts the event that keeps the rules

### Requirement: The first accepted event at a position stays
An event at a position where an event is already accepted SHALL leave the key state unchanged. The same event again SHALL be answered as a duplicate. A different event at that position SHALL be answered as likely duplicitous, as keripy answers it before checking the rival's signatures, carrying the accepted event's SAID and the rival message with its signatures and receipts. The answer SHALL claim no [duplicity](../../../../architecture/language/duplicity.md): an unsigned rival gets it as much as a validly signed one. No event SHALL replace an accepted one, and so no rotation supersedes an accepted event.

**Example:** Alice's identity KEL at sequence number 8, and 2 rotations at sequence number 9.

| arrives | answer | key state |
|---|---|---|
| rotation A at 9, signed and receipted | accepted | 9, from A |
| rotation A at 9 again | duplicate | 9, from A |
| rotation B at 9, signed or not | likely duplicitous: A accepted, B the rival | 9, from A |

#### Scenario: A repeated event is a duplicate
- **WHEN** an accepted event arrives again
- **THEN** the crate answers that it is a duplicate, and the key state is unchanged

#### Scenario: A rival event is likely duplicitous and replaces nothing
- **WHEN** a different event arrives at the position of an accepted one
- **THEN** the crate answers that it is likely duplicitous, with the accepted event's SAID and the rival, and the key state keeps the accepted one

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
