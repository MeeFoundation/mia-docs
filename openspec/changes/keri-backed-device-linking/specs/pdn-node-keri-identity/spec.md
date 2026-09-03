# KERI-backed identity on the runtime

An identity becomes a root autonomic identifier and each of its devices a delegated identifier under it, so that "this device belongs to this identity" is a chain of key events a stranger can check rather than a claim a store repeats. This capability covers the model, the key material behind it, the accepted-history state a device keeps, the ceremony proof that binds a confirmed device identifier to its authenticated transport endpoint, and the durable attempt state that makes a retried linking converge. The ceremony binding is immutable and sufficient only for access classification of this identity's confirmed devices; resolving a device identifier to a later endpoint and superseding a confirmed binding remain the following endpoint-statement change. The ceremony that creates the delegation and binding is [device-linking](../pdn-node-device-linking/spec.md); the storage layout of key events is [kel-store](../data-layer-kel-store/spec.md).

Every requirement below that says durable presupposes the active `durable-runtime-storage` change. That change SHALL land before implementation of this change begins. The durable half of this capability — pinned heads surviving a restart, startup recovery of creation records, a stable endpoint key, and an attempt record a same-endpoint retry reads back — is mandatory and SHALL NOT be removed to create an in-process subset.

## ADDED Requirements

### Requirement: An identity is a root identifier and its devices are delegates
An identity SHALL be a transferable root autonomic identifier, and every device of it SHALL hold its own delegated identifier whose delegator is the identifier of the device that linked it — the root for the first device. The delegator of a device identifier is fixed at inception and SHALL NOT change: a device is moved under another delegator only by incepting a new device identifier. A device identifier is therefore not a permanent name for the device in the domain: no durable _domain_ record — a claim, a grant, a capability token, a connection record — SHALL be keyed by it, and anything that must outlive a device names the identity instead. The identity's own key material is the exception by construction: key events and ceremony state are keyed by the device identifier, because they are the record of that identifier and nothing else — as is any later statement about that identifier, such as the endpoint binding a following change introduces.

A delegated inception SHALL name its delegator, and SHALL be accepted only when the delegator's key event log carries a seal over that inception. Neither half alone establishes the delegation.

That accepted chain is the authority statement. A directory device record is the transport association and confirmation half; it SHALL NOT substitute for the chain, and full identity-device access SHALL require the authenticated endpoint's confirmed record to carry a complete tagged `DeviceBindingProof`. A linked device's proof SHALL contain the device-signed request, inviter-signed manifest, and a second newcomer signature confirming that it verified the reply, store commitments, and tickets for that exact endpoint. The founding device, for which there was no network ceremony, SHALL instead carry a creation-specific statement signed by its device identifier and countersigned by the root. This preserves record-level listing without letting a directory writer mint identity authority by promoting a pending offer, writing a path, or copying another device's payload.

#### Scenario: A device's chain reaches its identity
- **WHEN** a device of an identity is asked for its authority
- **THEN** its delegated inception names its delegator, the delegator's log carries the seal over that inception, and following the delegators arrives at the identity's root identifier

#### Scenario: An unanchored inception establishes nothing
- **WHEN** a delegated inception names a delegator whose log carries no seal over it
- **THEN** the delegation is not accepted, and the device is not a device of that identity

#### Scenario: A record cannot manufacture delegation authority
- **WHEN** a confirmed directory record has no accepted anchored chain to the identity, or copies another device's valid proof under an endpoint the signed transcripts do not name
- **THEN** the record does not make that endpoint an authorized device of the identity

#### Scenario: Every device can delegate the next
- **WHEN** a device that was itself linked into an identity links a further device
- **THEN** the further device's delegated inception is anchored in the linking device's own log, with no key material of the root or of any other device involved

#### Scenario: The founding device has a verifiable endpoint binding
- **WHEN** identity creation accepts the founding device's delegated inception and the root event that seals it
- **THEN** the founder's confirmed record carries a creation-specific proof signed by both the founding device identifier and the root over the founder's exact local node id

### Requirement: Key material is durable, protected, and purpose-bounded
A device SHALL durably hold its current and pre-rotated private keys, and the device that creates an identity SHALL durably hold the root's keys. Every such private key SHALL be written through the protected versioned secret-record facility of `durable-runtime-storage`, separate from non-secret catalog and diagnostic data. Before creating the first key record, identity creation or linking SHALL persist an outer creation/attempt intent containing every preallocated secret handle, secret type, and the non-secret inputs needed to resume or roll back that owner. Each generic secret registration SHALL name that outer intent. The creation or attempt record becomes active only after all of its required handles are registered; recovery SHALL either complete the recorded owner and all missing secret transitions or delete every registered handle it owns. A registered KERI secret with no committed active owner or unfinished outer intent is invalid and SHALL be removed during recovery rather than admitted or adopted. On platforms with owner-only permissions, a failure to establish or retain them SHALL fail initialization or reopen before any KERI key is used. Missing, malformed, unreadable, or permission-invalid key material SHALL NOT be regenerated, skipped, logged, or replaced with an in-memory key.

What losing the root keys costs SHALL NOT be overstated: in this delegation shape the root delegates only the first device, and every further device is delegated by the device that invited it, so an identity whose root keys are gone goes on linking devices exactly as before. What is lost is the future: the root cannot be rotated, no ancestor can recover the root or the first device, and the identity's fixed identity-store set cannot be extended. All 3 operations are outside this change, which is why root keys are required to be durable and a recovery copy of them is not: an export whose only user is a rotation that does not exist yet belongs to the change that adds it, together with the security decision about where such an export may live.

Pre-rotated keys of a device SHALL be generated and held by that device, and a delegator SHALL NOT hold them. An ordinary delegated rotation therefore requires both halves — the device signs it, its delegator anchors it — so neither side performs that ordinary rotation alone, and an attacker holding only the device's keys cannot rotate it away from its owner.

This SHALL NOT be written as "no party can ever act on a device without it" or "lost device keys are unrecoverable under every topology". The mechanism this change builds on permits more than this change implements: a superseding rotation higher in a delegation chain can recover signing or pre-rotated keys at lower levels, which in a tree of devices means an ancestor holds a recovery path over its subtree. No such path is implemented here — rotation, revocation, and recovery are all outside this change — so loss of non-root device keys requires a new device identifier in this runtime while remaining recoverable by a future ancestor-recovery implementation. The root is different because it has no ancestor.

#### Scenario: Keys survive a restart
- **WHEN** a runtime restarts after creating an identity
- **THEN** it still holds the identity's root keys and its device's current and pre-rotated keys

#### Scenario: KERI key protection fails closed
- **WHEN** a root or device secret record is missing, malformed, unreadable, or has broader permissions than the platform policy permits
- **THEN** reopen fails before service admission and does not log or generate replacement key bytes

#### Scenario: Linking does not use the root keys
- **WHEN** a device links a further device into an identity
- **THEN** the delegation is anchored in the linking device's own log with its own keys, and the root keys are not used

#### Scenario: A delegator alone cannot rotate a device
- **WHEN** the delegator of a device attempts to rotate that device's identifier without it
- **THEN** the attempt produces no accepted establishment event, because the rotation is signed by keys the delegator does not hold, and the runtime offers no other path to the same effect

### Requirement: The identity's history names its own store set
An identity's inception SHALL seal exactly 2 role-tagged commitments: one to its private-metadata directory and one to its data namespace. Their exact BLAKE3-256 preimage, role octets, CESR encoding, and order SHALL be those of `pdn-node-keri-wire-profile`; no implementation-selected `H`, label encoding, concatenation, or ordering is permitted. A raw namespace identifier is itself a read capability and SHALL NOT appear in the key event log or cross the `data-layer` boundary during this check.

The term identity store set SHALL mean only those 2 device-replicated stores. Per-connection metadata replicas created by pairing are discovered through the already verified directory and SHALL NOT count as extensions of this set. A cross-identity replica imported through the existing grant path is authorized by that grant and likewise SHALL NOT be treated as a store of the hosted identity.

During this change's own-identity linking bootstrap, a device SHALL NOT bind either offered store to the identity on the strength of an unverified field. Before either import, the runtime SHALL submit both exact canonical ticket byte strings, both expected role-tagged commitments, and the authenticated inviter fallback to the single pair-verification operation defined by `data-layer-identity-store-bootstrap`. Only 2 internal `MatchWritable` verdicts SHALL return a `VerifiedBootstrapPair`, and the runtime SHALL import only by consuming that opaque byte-bound pair. A failed pair SHALL return the complete typed role/verdict mapping and no import handle; no single-ticket pass/fail API, remembered verdict, or caller-supplied ticket SHALL authorize import. This rule SHALL NOT alter `import_namespace_granted` or any other independently authorized grant path. Without the bootstrap comparison, a chain that verifies down to the last event still leaves the answering device free to hand over any store it likes — another identity's, or one it created for the occasion — and have it hosted under the verified identity's name.

The 2-commitment set SHALL be fixed for the lifetime of this change. A commitment establishes ownership and not access level, so a ticket matching a sealed commitment SHALL still be checked for the capability the operation needs.

#### Scenario: The sealed set is what the identifier commits to
- **WHEN** an identity is created
- **THEN** its inception seals the role-tagged commitments to its directory and data namespace, and the identifier derived from that inception changes if either commitment is altered

#### Scenario: A store outside the sealed set is not adopted
- **WHEN** linking offers a ticket whose internally recomputed role-tagged commitment is absent from the identity's history
- **THEN** the device refuses it and binds nothing, whatever else about the offer verified

#### Scenario: A sealed namespace still needs the right capability
- **WHEN** a device holds a read-only ticket whose store commitment the identity's history seals, and an operation needs to write
- **THEN** the write is refused, because the seal establishes ownership and not access

#### Scenario: Pairing metadata does not extend the identity store set
- **WHEN** a device pairs with another identity and creates a per-connection metadata replica
- **THEN** the identity still has exactly the same 2 sealed store commitments

#### Scenario: A grant remains independently authorized
- **WHEN** `import_namespace_granted` binds a cross-identity replica under a valid grant
- **THEN** that import is not rejected for absence from the hosted identity's 2 store commitments and does not add a commitment to them

#### Scenario: Namespace capabilities stay below the data layer
- **WHEN** the runtime creates the identity's store commitments or jointly verifies both bootstrap tickets
- **THEN** it receives opaque commitments, a consuming `VerifiedBootstrapPair`, or the complete typed role/verdict failure mapping — never either raw namespace identifier, a decoded ticket, or a single-ticket Boolean

### Requirement: Identifiers are self-addressing, and the derivation is pinned
An identity's root identifier and every device identifier SHALL be self-addressing: the identifier is the qualified digest of its own inception event, so the whole inception configuration — the keys, the thresholds, the witness fields, and for a delegate the delegator — is bound into the identifier and cannot be restated without changing it. A device identifier SHALL NOT depend on where its delegation is anchored, which is what makes a retried linking converge on one identifier.

The derivation SHALL be exactly the profile-1 SAIDification pipeline and no other digest operation: construct the size-correct canonical inception JSON with both `d` and `i` replaced by 44 ASCII `#` bytes, BLAKE3-256 those dummy bytes, qualify the digest with CESR code `E`, then place that identical value in `d` and `i`. Hashing the final JSON containing the claimed identifier is invalid. `PdnId` is the unqualified 32 bytes of that SAID digest; adding or removing the `E` qualification is the sole mapping at the KERI boundary. The inception SHALL explicitly encode empty witnesses and threshold `"0"` because those bytes enter the identifier.

#### Scenario: The identifier is the digest of its inception
- **WHEN** an identity or a device is incepted
- **THEN** reconstructing the profile-1 size-correct dummy inception and applying SAIDification reproduces the identifier, while hashing the final event bytes does not define it

#### Scenario: A restated inception is a different identifier
- **WHEN** an inception event is re-encoded with any configuration field altered
- **THEN** the identifier it derives differs from the original

#### Scenario: The witness configuration is explicit and empty
- **WHEN** an inception is written by this change
- **THEN** it names an empty witness set and a threshold of zero, rather than leaving the fields unstated

### Requirement: KERI runtime security state has one durable transactional home

The runtime SHALL use the durable catalog's `runtime-security/keri-v1/` facility for exactly these non-secret local record families:

- `accepted-head/<identity>/<aid>`: the accepted SAID, sequence number, key state, record generation, and complete verified reconstruction set described below;
- `ceremony/<identity>/<attempt>`: the exact signed request, manifest, optional confirmation, anchor, commitments, and accepted-head snapshot required by the attempt boundary, containing `{aid, sequence, SAID}` plus the generation used as its commit-time conditional-write guard;
- `pending-observation/<identity>/offer/<offer-digest>` and `pending-observation/<identity>/active/<device-aid>/<node-id>`: respectively the verified offer's first-observed lifecycle record and the subject's sole active-offer index;
- `kel-problem/<identity>/<aid>/<sequence>/<content-digest>`: the enumerable typed discrepancy or malformed-content-address facts.

Every payload SHALL carry KERI security-state schema version `1`; these records SHALL be local and unreplicated and SHALL contain no private key or raw namespace identifier. Each `accepted-head` payload SHALL durably retain the exact canonical `KEL1` bytes for every signed event needed to verify that identifier from inception through the accepted head, plus a seal index mapping each accepted delegated inception to the exact accepted delegator event location and seal-list position that authorizes it. The reconstruction set SHALL be ordered, content-digested, free of duplicate event locations, and sufficient to recompute every signature, prior-digest link, key state, SAID, and delegation decision without waiting for a directory payload. When a head advances, the replacement reconstruction set SHALL retain every exact event byte of the prior accepted branch as a byte-identical prefix and append only the newly accepted extension. Arrival or later disappearance of the same payload in the replicated directory SHALL NOT erase the durable evidence.

A ceremony's stored head generation SHALL be used only to make its original acceptance batch conditional; it SHALL NOT be a permanent foreign key to the current `accepted-head` generation. On startup and whenever the ceremony is used for authorization, the runtime SHALL locate each snapshotted `{aid, sequence, SAID}` in the current verified reconstruction set and require the exact bytes through that event to equal the accepted prefix. A current head at a later sequence is valid for the older ceremony only under that prefix rule. A missing snapshot event, a different SAID at its position, or different prefix bytes SHALL fail the ceremony and affected identity closed. Implementations SHALL NOT retain every old head record merely to preserve its catalog generation.

A required malformed, missing, incomplete, or unsupported record SHALL fail the affected identity closed before identity, linking, or session-classification admission. Startup SHALL replay every `keri-v1` intent, load these records, verify each reconstruction set again from exact bytes, reconstruct the accepted view and problem projection, and only then publish the identity's services. It SHALL NOT derive a first-seen accepted branch from current replica arrival order when a required head or its evidence is absent.

Accepting a reply SHALL conditionally write every advanced `accepted-head` and the corresponding `ceremony` record in one catalog batch. Extending the ceremony with confirmation SHALL likewise be one conditional update. A KEL evaluation that advances a head and creates or clears related `kel-problem` records SHALL commit one batch against the generations it evaluated. Any transition that changes identity-device authorization SHALL additionally drive the generation-bound `IdentityAccessProjection` contract in `data-layer-private-metadata-store`: a granting projection follows its durable KERI state, while a potentially revoking transition closes old device-derived access before publishing the new verdict. Forget SHALL name and delete the identity's entire `keri-v1` prefix through the outer forget intent. Any transition involving a directory pending/confirmed write or an access-projection generation SHALL use a `keri-v1` write-ahead intent with exact catalog generations and its data-layer target, then replay closed before admission.

#### Scenario: Reply acceptance cannot tear heads from its ceremony

- **WHEN** storage stops during the transition that accepts a verified reply
- **THEN** reopen observes both the complete previous head/ceremony set or both the complete new set, never new heads without their exact ceremony or the reverse

#### Scenario: Missing pinned state is not reconstructed from arrival order

- **WHEN** an identity's hosted records require an accepted head but its required `accepted-head` record is missing or malformed
- **THEN** that identity fails closed before session classification and the runtime does not select whichever KEL candidate arrived first

#### Scenario: Verified reply evidence survives before replica payload arrival

- **WHEN** a reply advances accepted heads, the process stops before those exact KEL payloads arrive through directory replication, and the profile reopens
- **THEN** startup re-verifies the accepted branch from the durable reconstruction sets and admits no identity until that succeeds

#### Scenario: An older ceremony survives a legitimate head extension

- **WHEN** device B is confirmed, B later anchors device C so B's accepted head and catalog generation advance, and the runtime restarts
- **THEN** B's older ceremony remains valid because its snapshotted `{aid, sequence, SAID}` and exact bytes are a verified prefix of B's current reconstruction set; equality with the old catalog generation is not required

#### Scenario: Forget removes every local KERI security family

- **WHEN** forgetting an identity is interrupted between deleting different KERI security families
- **THEN** startup keeps the identity non-admissible and replays the outer intent until heads, ceremonies, observations, problems, keys, replicas, and their references are consistently removed

### Requirement: Accepted history is pinned, and pinning outlives the attempt
On accepting an identity's history, a device SHALL durably record the accepted head of the root identifier and of every identifier on the chain it verified together with each head's complete exact-byte reconstruction set. A later replay that contradicts a pinned head SHALL be refused rather than accepted, whether it arrives in a retried ceremony or through replication. Completion of a sync session without the corresponding entry payloads SHALL NOT weaken or substitute for this evidence.

A pinned head SHALL advance, and the rule for advancing it SHALL be stated rather than left to a reader: an event extends the accepted branch when it chains from the pinned head — its prior digest is that head's digest, its sequence number is the next one, and its signatures verify under the key state that head establishes — and every external authorization prerequisite also verifies. In particular, a delegated establishment event remains outside the accepted branch until the accepted branch of its fixed delegator carries the matching seal. The head then becomes that event. Advancing is the ordinary case, not an exception: in this delegation shape every linking appends an anchoring event to the inviting device's log, so a device that could not advance a head would call a legitimate anchor a discrepancy after the very next device joined. An event that claims a position the accepted branch already holds, with a different digest, contradicts it and SHALL be refused as above.

An event beyond the next position SHALL be retained without advancing the head and without being classified as a discrepancy, then re-evaluated as the gap closes. A valid delegated establishment event whose matching seal is not yet on the accepted delegator branch SHALL likewise be retained as awaiting delegation. It SHALL be re-evaluated when that branch advances; a matching seal present only on a competing, unaccepted delegator branch authorizes nothing. Records whose payload bytes have not arrived provide no validation input and SHALL NOT change any verdict.

A pinned head SHALL survive a failed linking, a rollback, and a restart, and SHALL be removed only by an explicit act of forgetting an identity. Rollback of a linking attempt therefore leaves no replicas, no bindings, and no hosted identity, but it does leave the pinned heads — without which an inviter could present a different branch on the retry and have it accepted as the first one seen.

#### Scenario: A contradicting branch is refused after a failed attempt
- **WHEN** a linking fails after its history was verified, and a retry presents a different history for the same identity
- **THEN** the retry is refused, and the head recorded by the first attempt still stands

#### Scenario: A pinned head advances on a chaining event
- **WHEN** a device of an identity anchors a further device, and that event reaches a device whose head is the event's predecessor
- **THEN** the head advances to the new event, and the anchor is not treated as a discrepancy

#### Scenario: An out-of-order event waits for its gap
- **WHEN** an event 2 positions beyond the accepted head arrives before the event between them
- **THEN** it is retained without advancing the head or becoming a discrepancy, and is re-evaluated when the missing event arrives

#### Scenario: A delegated inception waits for its accepted seal
- **WHEN** a valid delegated inception arrives before the matching seal is present on the delegator's accepted branch
- **THEN** it remains awaiting delegation, establishes no accepted head, and is re-evaluated when that branch advances

#### Scenario: A seal on a competing branch authorizes nothing
- **WHEN** the matching seal exists only on a delegator event that contradicts the accepted delegator branch
- **THEN** the delegated event remains outside the accepted history

#### Scenario: A record without payload changes no verdict
- **WHEN** a key-event record is present but its payload bytes have not arrived
- **THEN** the accepted head and awaiting-delegation state remain unchanged until the bytes are readable

#### Scenario: Pinning survives a restart
- **WHEN** a runtime restarts after pinning an identity's heads
- **THEN** the pinned heads are still in force, and a replay that contradicts them is refused

#### Scenario: Forgetting is explicit
- **WHEN** an identity is explicitly forgotten
- **THEN** its pinned heads are removed, and no ordinary failure path removes them

### Requirement: An interrupted linking attempt is resumed, not repeated
Before dialing, a device SHALL durably record the attempt: the delegated inception it assembled, the keys behind it, the identity it is joining, the inviting device identifier that inception names, and the exact local `NodeId` whose endpoint the proof will bind. A retry SHALL reuse that record only while the runtime still has that node id, so that repeated attempts against the same inviting device and endpoint yield exactly 1 device identifier and exactly 1 anchoring seal.

If an explicit endpoint reset or profile migration changes the local node id before completion, the runtime SHALL abandon the endpoint-specific attempt, its inception, device keys, and local proof before dialing, and SHALL assemble a new inception for the new endpoint. The identity's already pinned heads SHALL remain. The old inviter-side pending offer grants no access and expires normally. Presenting the old inception from the new endpoint SHALL NOT be treated as a retry.

Because a delegated inception names its delegator, the record SHALL be reusable only with the same inviting device. An invite minted by a different device of the identity SHALL start a new attempt with a new device identifier, and the abandoned identifier SHALL remain in the earlier delegator's log without conferring anything.

An abandoned attempt record SHALL NOT be immortal. A completed linking for an identity SHALL discard the attempt records of that identity that its own attempt superseded, together with their keys: they name inceptions that will never be anchored, and forgetting the identity is not available as the cleanup path once the identity is legitimately hosted.

#### Scenario: 3 interrupted attempts leave 1 device
- **WHEN** a device links against the same inviting device after 2 connection failures and a restart
- **THEN** the identity's device set gains exactly 1 device, and the inviting device's log carries exactly 1 seal for it

#### Scenario: A changed local endpoint starts a fresh inception
- **WHEN** an unfinished attempt names one local node id and the runtime is explicitly restarted under another
- **THEN** the old endpoint-specific attempt and device keys are discarded before dialing, a new delegated inception is assembled, and the pinned identity heads remain

#### Scenario: A superseded attempt and its keys are discarded
- **WHEN** a device abandons an attempt against one inviting device and completes a linking into the same identity against another
- **THEN** the abandoned attempt record and its keys are gone, while the identity stays hosted

#### Scenario: Another inviter starts a new attempt
- **WHEN** a device abandons an attempt against one device of an identity and links from an invite minted on another device of the same identity
- **THEN** it incepts a new device identifier under the new inviter, and the abandoned identifier is not part of the completed link

### Requirement: A confirmed endpoint binding is immutable in profile 1
This change SHALL NOT silently repair, migrate, or supersede a confirmed binding when the runtime no longer controls the endpoint key whose `NodeId` its proof names. Reopen of the original profile already fails closed when that key is missing. Starting another profile or explicitly resetting the endpoint produces another `NodeId` and SHALL NOT cause an existing `Created` or `Linked` proof to authorize it.

A linked device MAY be forgotten locally and linked again as a new device identifier only when another live device can invite it. The founder has no equivalent self-recovery in this change: forgetting the hosted identity removes its root keys, while using those root keys to incept and confirm a replacement founder endpoint is endpoint supersession and recovery, which is deliberately deferred. A sole founder that loses its confirmed endpoint secret therefore cannot restore `SessionAccess::Full` from another node id under this profile.

#### Scenario: Confirmed binding does not follow a reset endpoint
- **WHEN** a device with a confirmed proof starts under a different node id
- **THEN** the old proof grants that endpoint no full access and no automatic replacement proof is written

#### Scenario: Founder endpoint loss has no hidden repair path
- **WHEN** the founding endpoint key is lost after confirmation and no endpoint-supersession change is implemented
- **THEN** reopen fails or the replacement endpoint remains unauthorized; the runtime does not forget the identity, re-incept a founder, or consume root keys as an implicit repair

### Requirement: Forgetting an identity is an explicit operation
The runtime SHALL offer one explicit operation to forget an identity, and it SHALL be the only path that removes that identity's pinned heads, its ceremony context, and its key material. It SHALL be distinguishable in the service surface from the rollback of a failed linking, which removes replicas and bindings and deliberately keeps all three.

Forgetting SHALL leave the runtime as it was before the identity was ever known to it: operations addressed to that identity are refused as unknown, and a later linking into it starts with no pinned history — which is exactly why the operation is explicit rather than a consequence of any failure.

#### Scenario: Rollback and forgetting are different acts
- **WHEN** a linking fails and rolls back, and separately the identity is explicitly forgotten
- **THEN** the first leaves the pinned heads and the attempt in place, and the second removes them

#### Scenario: Forgetting clears the pinned history
- **WHEN** an identity is forgotten and later linked into again
- **THEN** the new linking pins the history it verifies, with no earlier head standing in its way

### Requirement: Key material of several identities stays separate
A runtime hosting several identities SHALL keep each identity's key material, creation record, and in-flight attempt state separate from every other's. An interruption, a rollback, or a forgetting of one identity SHALL leave the others' material untouched.

#### Scenario: Forgetting one identity keeps the other's keys
- **WHEN** a runtime hosts two identities and one is forgotten
- **THEN** the other's root and device keys are intact and it can still anchor a delegation

#### Scenario: A device holds one identifier per identity
- **WHEN** one runtime is a device of two identities
- **THEN** it holds a distinct device identifier under each, with distinct keys, and neither is used in the other's ceremonies

### Requirement: A key-event problem is durable and observable
A competing event or malformed content address SHALL be recorded in the `kel-problem` runtime-security family and readable through the runtime's own surface — durable across reopen, enumerable per identity, and carrying a typed kind, the identifier and position involved, and the claimed and observed digests that apply. Creating or clearing it SHALL share the conditional catalog batch with any accepted-head verdict made from the same evaluated input. A problem nobody can read back is unverifiable and therefore not a requirement; nothing in this change resolves a competing branch, and the surface is what makes the difference between "detected" and "claimed".

#### Scenario: A recorded discrepancy can be read back
- **WHEN** two events claiming one position of an identifier are present
- **THEN** the runtime reports a competing-event problem for that identifier and position, with both digests, and the accepted head is unchanged

#### Scenario: A recorded discrepancy survives reopen

- **WHEN** a discrepancy is recorded and the runtime reopens before the competing replica entry is read again
- **THEN** the problem remains enumerable from its durable record and the accepted head remains unchanged

#### Scenario: A malformed content address can be read back
- **WHEN** an entry's payload identifier, sequence number, or recomputed digest does not match its key
- **THEN** the runtime reports a malformed-content-address problem with the claimed and observed values, and the accepted head is unchanged

#### Scenario: A clean history reports nothing
- **WHEN** an identity's history is consistent
- **THEN** the runtime reports no discrepancy for it
