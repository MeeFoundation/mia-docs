---
status: proposed
date: 2026-10-27
---
# KERI identity layer — architectural decisions

Draft for review. Each numbered item, such as DR-1 or DR-5, states one decision and why it was taken, and it usually gives an example. A "To verify" line marks a point that still has to be checked against the KERI specification, against a platform or against the sync engine. The numbers run through the whole document, and the headings only group related decisions. The topics that are deferred are listed at the end.

## Terms

- **PDN** — Private Data Network: the platform. Data moves between devices over iroh.
- **Tellipod** — the product: the PDN together with the Android, iOS and desktop apps.
- **Pod** — a shared space with many members. A pod is usually about one topic, such as "planning a trip to Tokyo".
- **Identity** — a person, known to others by one KERI identifier.
- **AID** — KERI's autonomic identifier: a self-certifying identifier that is bound to a key event log.
- **KEL** — key event log: the signed, hash-chained sequence of an AID's key events.
- **Establishment event** — an inception event or a rotation. An establishment event sets the current keys and commits to the digests of the next keys. This commitment in advance is called pre-rotation.
- **Interaction event** — a KEL event that changes no keys and anchors data, such as a digest.
- **Weight and threshold** — each key carries a weight. An event is valid when the weights of the keys that signed it add up to at least the threshold. In this design the threshold is 1.
- **Partial rotation** — a rotation that uses some of the committed next keys, and carries the commitments to the other next keys forward unchanged.
- **Digest seal** — a digest of some data, carried inside a KEL event. The event is signed, so the seal fixes the data without putting the data itself in the KEL. An event that carries a digest seal of some data is said to anchor that data.
- **Escrow** — a place where a validator holds an event that it cannot validate yet, such as an event that arrived before the event that precedes it.
- **Delegation** — a relation between 2 AIDs, a delegator and a delegated AID. The inception and the rotations of the delegated AID are valid only when the delegator anchors them in the delegator's own KEL.
- **Fork** — 2 different items, both validly signed, at the same position of one sequence that a single party signs. The 2 items are either 2 events of one KEL, or 2 records of one device's chain in a pod. From that position on, the sequence has 2 branches.
- **Duplicity** — KERI's name for a fork of a KEL. KERI treats duplicity as the mark of a compromised key.
- **Superseding recovery** — KERI's mechanism by which a rotation replaces the interaction events that came after the last establishment event. For a delegated AID, superseding recovery can also replace the latest rotation, if the delegator approves. This design does not use superseding recovery (DR-3).
- **Relay** — an iroh relay server. A relay carries traffic between devices that cannot reach each other directly. It sees which devices talk to each other, but not what they say.
- **Witness** — a server that receipts an AID's events, which means that it signs a receipt for each of them. A witness refuses to receipt a second event at a position where it has already receipted one. In this design, a witness also issues stamps. An AID's witnesses are the ones listed in the AID's inception event, and a later establishment event can change that list. A validator accepts an event of the AID only once enough of the AID's witnesses have receipted the event. The witness threshold in the KEL sets how many witnesses are enough. An AID whose list of witnesses is empty has no witnesses, and its events are accepted on their signatures alone.
- **Keys of a device** — a device has 4 kinds of keys:
  - Its key in the identity's key set. It is a P-256 key, kept in hardware if the device has any, and it signs rotations.
  - The keys of its device AID. They are P-256 keys, kept in hardware if the device has any, and they sign records and the binding of the device's iroh endpoint key.
  - Its iroh endpoint key, which is the device's network identity. It is an Ed25519 key, held in memory while the node runs. It is stored wrapped, which means encrypted under the wrapping key.
  - A wrapping key, kept in hardware. Its type follows the platform, and its only job is to encrypt the iroh endpoint key while that key is stored.
- **Device AID** — a device's own AID, delegated by the identity's AID. A device has one device AID for each identity that it hosts.
- **Record** — an item of a pod's store. One device signs each record in the name of the device's identity. A record is pod data, never a KEL event.
- **Second party** — whoever signs a rotation together with a device: another device of the user, or the external co-signer.
- **External co-signer** — a party that is not a device of the user and that holds a key of weight 1/2 in the identity's key set. An external co-signer is either the Tellipod co-signer or a co-signer node that the user hosts. In this document, "the co-signer" always means the external co-signer.
- **Recovery key** — a key of weight 1, held by the Tellipod recovery service or written on a paper sheet.
- **Role statement** — a public statement, anchored in every establishment event, that gives the role of each key: recovery, external co-signer or device.
- **ACDC and TEL** — ACDC (Authentic Chained Data Container) is KERI's format for verifiable credentials. A TEL (Transaction Event Log) is the log that tracks whether each credential is issued or withdrawn, which ACDC calls revoked.
- **History of a record** — the record itself, together with every earlier record of the same device in the same pod that the record's hash chain leads back to.
- **Replica** — a device's copy of a pod's store.
- **Sync session** — an exchange of records between 2 devices. A sync session is different from a signing session, which is a period during which the user's presence lets a device sign records (DR-23).
- **Stamp** — a statement that an identity's witness signs at the request of one of that identity's own devices. A stamp names the identity's AID, and it gives the latest position of the identity's KEL that the witness has receipted, with the digest of the event at that position. It also gives a digest that the requesting device supplied, and that digest covers some of the requesting device's own records. Whatever a stamp covers existed before any event after the stamp's position was accepted (DR-20). A stamp travels in each pod whose records it covers. In such a pod, the stamp is pod data that no device signs, so a stamp is not a record.
- **Admission** — a record that a linked device writes on the user's explicit act. An admission names a record of a revoked device of the same identity, and it accepts the revoked device's records up to the named record (DR-20).
- **Enclave** — a hardware-protected area of a server's processor. The server's operator cannot read or change the enclave's memory and code. The trust that remains lies with the chip vendor and with the machine's physical security.

## KERI and its implementation

### DR-1. KERI is the identity layer, in its standard encoding

**Decision.** Every identity is a KERI AID. The identity's KEL and the KELs of its device AIDs use KERI's standard encoding, CESR (Composable Event Streaming Representation), so that existing KERI implementations can verify them. For P-256 signatures, the implementations that can verify them are the ones that follow keripy (DR-2). Each addition of this design is one of 3 things: data carried inside conformant events, a rule applied on top of those events, or a message outside the KELs. Role statements are data of the first kind, and a stamp is a message of the third kind (DR-20). No addition changes the encoding of a KEL. Every signature of this design covers a domain tag that names its purpose. So a record never parses as a KERI event, a stamp never verifies as a receipt, and a request to the recovery service or the co-signer carries its purpose, the identity's AID, the KEL position, a nonce and an expiry, so that it cannot be replayed.

**Why.** A self-certifying identifier makes an identity independent of any server. The standard encoding keeps every KEL checkable by tools that the project did not write.

**Example.** Given Alice's KEL, keripy computes the same current keys as Bob's phone does. keripy parses Alice's role statement as data and ignores what the statement means.

### DR-2. Hardware-bound keys on P-256

**Decision.** A device's key in the identity's key set and the keys of its device AID are P-256 keys. They are bound to the device's hardware if the device has any, and they are never exported from the device. Their access rule survives changes to the fingerprints or faces that the user enrolls. On iOS and macOS, the keys ask for `userPresence`, never for `biometryCurrentSet`. On Android, the keys are created with `setInvalidatedByBiometricEnrollment(false)`. Recovery keys are software keys. For P-256 signatures, the implementation conforms to keripy. The CESR specification has a gap for these signatures, and that gap is tracked or pushed upstream. A virtual TPM, as a virtual machine provides it, counts as no hardware. The record-signing key lives in the platform's trusted execution environment, not in StrongBox. Where StrongBox exists, it holds only the device's key in the identity's key set.

**Why.** P-256 is the curve that the Secure Enclave of iOS and macOS, Android StrongBox and TPMs have in common. The Secure Enclave offers no Ed25519. The CESR specification defines P-256 keys and plain P-256 signatures. However, KERI controllers use indexed signatures, and the specification's table of indexed signatures lists no P-256 code. keripy, the reference implementation, defines indexed P-256 signatures. Binding keys to hardware outweighs conformance with the specification's table. A recovery key is typed into whichever device carries out the recovery, so a recovery key cannot be bound to one device. Suppose that a key's access rule depends on the enrolled fingerprints. When the user adds or deletes a fingerprint, that key becomes permanently unusable, and so does its pre-committed next key. The device would then have to be revoked and linked again. Enrolling a new fingerprint must never cost the user a linking. A snapshot of a virtual machine copies its virtual TPM, keys included. StrongBox takes about 100 to 500 ms for each signature, which is too slow for a burst of records but fine for a rare rotation.

**Example.** Alice's laptop keeps its P-256 keys in its TPM. The recovery key of Alice's paper sheet is derived from the sheet's 24 words, on the device that carries out the recovery.

**To verify.** The exact key-creation flags on each platform: that a Secure Enclave key with `userPresence` stays usable after the user adds or deletes a fingerprint or a face, that an Android key created with `setInvalidatedByBiometricEnrollment(false)` survives a new biometric enrollment, and what a TPM-backed Windows Hello key does when the user changes the enrolled fingerprints.

### DR-3. Our own KERI implementation, limited to the subset in use

**Decision.** The project writes its own KERI implementation, under the Apache 2.0 license. The implementation includes only what this design uses: inception and rotation with partial rotation and weighted thresholds, the establishment-only configuration, delegated inception and delegated rotation, interaction events and digest seals in the KELs of device AIDs, witness receipts, and the escrows in which a device holds events that it cannot validate yet. It also includes the witness software, which receipts the identity's events and issues stamps (DR-15, DR-20). The witness orders every stamp of an identity against that identity's receipts, so that no stamp gives a position below an event that the witness has already receipted. The witness keeps its state durable and linearizable for each identity, and never restores it backward. Receipts never wait behind stamps, and the witness limits request rates for each connection, never for each identity. The identity's KEL needs no interaction events. Neither the identity's KEL nor the KELs of device AIDs need KERI's superseding recovery. ACDC registries (TELs) are out of scope. Conformance is checked in both directions against test vectors generated with keripy, the reference implementation, which is also under Apache 2.0. keripy serves as an outside test oracle: the tests compare our implementation's results with keripy's results, and keripy's code never enters the product.

**Why.** keriox, an existing KERI implementation, is under the EUPL, and an Apache 2.0 project cannot take in code under the EUPL. The design needs only the subset that the decision lists. A witness restored from an old backup would stamp a thief's later records at an old position, and a limit for each identity would let a flood of requests block other devices' stamps.

**Example.** A test feeds a KEL that keripy produced into our validator, and a KEL that our implementation produced into keripy. For both KELs, our validator and keripy must reach the same key state.

### DR-4. Every device does the full KERI work itself

**Decision.** Each device validates KELs completely. Complete validation includes the escrows for events that arrive out of order, for events that do not yet carry enough signatures, and for events that wait for a delegator's approval. Each device is also reachable over iroh, and it checks the copies of KELs that it receives. There is no cloud agent of the kind that KERI's Signify client relies on. With Signify, the KERIA agent keeps the user's KELs and mailbox in the cloud. The escrow has an overall size limit. Inside it, each identity has a share, and inside an identity's share each sender has a part of its own, so that one sender's events never push out another sender's. The escrow admits only events that carry a valid receipt from the witness of the identity's latest validated event, and it indexes events by AID and position. Without these limits, events that cannot be validated until missing earlier events arrive could fill the device's storage.

**Why.** The platform is local-first, and KELs are small enough for a phone (DR-13). Doing all KERI work on the device costs a complete and correct KERI implementation there, not storage or computing power.

**Example.** Bob's phone receives Alice's rotation 7 before her rotation 6. The phone holds rotation 7 in an escrow until rotation 6 arrives, and then validates both. In another case, a pod member sends Bob's phone events for positions 900 to 5,000 of Alice's KEL. These events fill only that member's part of Alice's share, and Bob's phone drops the rest. A genuine event of Alice that Carol's phone sends out of order still finds room in Carol's part.

## Identity and devices

### DR-5. One identity across all of a person's devices

**Decision.** A person is one identity, with one AID on all of the person's devices. Linking a device, revoking a device and rotating keys never change the AID.

**Why.** Pod membership and records refer to the person, not to the hardware. A new phone must not turn Alice into a new member of every pod.

**Example.** Alice replaces her phone. Her pods still list the same AID for her, and Bob notices nothing.

### DR-6. Each device has its own delegated AID

**Decision.**

- Each identity on each device has an AID of its own, called the device AID. The identity's AID is the device AID's delegator. A phone that hosts 2 identities has 2 device AIDs.
- A device AID is created when its device is linked. Linking a device is a rotation of the identity's KEL that adds the device's key to the identity's key set (DR-8). That same rotation also carries a digest seal of the device AID's inception event. The seal is how the identity approves the new device AID, as delegation requires. The identity's first device is not linked by a rotation. The first device's device AID is sealed in a rotation that the identity makes right after the identity's inception. The first device signs that rotation, together with the external co-signer if the identity has one. The identity's inception event cannot carry that seal. A delegated inception names its delegator's AID. The identity's AID is the digest of the identity's own inception event. So each of the 2 inception events would need the other's digest.
- The device AID signs the device's records (DR-18), and it binds the device's iroh endpoint key to the identity (DR-7).
- Unlike the identity's KEL, the device AID's KEL may hold interaction events. The binding of the iroh endpoint key is one.
- The device AID's own keys change only with the identity's approval. A rotation of the device AID is valid only when a rotation of the identity's KEL carries a digest seal of it (DR-8). In practice, a device AID rotates only when the signature algorithm changes for all devices. A compromised device is revoked instead. A device whose keys became unusable is revoked and linked again, since its pre-committed next keys are lost together with its current keys. KERI's superseding recovery would not help a device AID either. The device AID's pre-committed next keys sit in the same hardware as its current keys. A thief who holds the device therefore holds both sets of keys.

**Why.** A device signs records all day, but its key in the identity's key set is single-use and changes at every rotation. The device therefore needs a key that it can use repeatedly. It also needs an identifier that stays the same across the identity's rotations, so that the device's records, the binding of its iroh endpoint key and its revocation can all refer to that identifier.

**Example.** Alice's rotation 3 adds her laptop's key to her key set, and anchors the inception of the laptop's device AID, `E-laptop`. When the laptop next signs a rotation of Alice's KEL, the laptop's key in her key set changes. `E-laptop` stays the same, and the laptop's records in the Hiking pod keep `E-laptop` as their author.

**To verify.** That KERI indeed rules out sealing a delegated inception in its delegator's own inception event. Also, that a rotation right after the identity's inception is the usual way to delegate the first device AID.

### DR-7. The iroh endpoint key is separate and bound by the device AID

**Decision.** A device's iroh endpoint key is an Ed25519 key, separate from the device's KERI keys. An interaction event in the device AID's KEL binds the iroh endpoint key to the device AID, and through the device AID to the identity. The secret part of the iroh endpoint key is stored encrypted under a separate wrapping key in the device's hardware: the Secure Enclave, the Android Keystore or a TPM. The wrapping key cannot be exported, its type follows the platform, and it signs nothing. The device unwraps the secret into memory when the node starts. Where the platform allows, the stored secret is kept out of backups. The wrapping key asks for no user presence, since background sync runs without the user. On a device with no such hardware, the secret is a file that is kept out of backups. The iroh endpoint key also signs its own binding, so no device can bind another device's endpoint key. Peers reject an endpoint key that is bound to 2 device AIDs. A new binding needs the user's presence for that act, and the identity's other devices tell the user about it. The device's replicas of its pods are kept out of backups as well, or stored encrypted under the wrapping key.

**Why.** If the iroh endpoint key were a KERI key, every rotation would change the device's network identity, and the tickets and peers that refer to that network identity would lose the device. Binding the iroh endpoint key in the device AID's KEL needs no second party. Pod sync authorizes a device by its iroh endpoint key. If the secret were a plain file in the app's data, the file would travel with every backup. Whoever stole a backup could then read every pod as that device, and nothing would signal that a second endpoint uses the same key. Without the endpoint key's own signature, a modified node could bind Bob's endpoint key to its device AID and so cut Bob's device off. Without presence and the notice, a thief or malware could bind an endpoint of its own during a signing session and read pods from elsewhere until the revocation.

**Example.** In the KEL of the device AID of Alice's laptop, the first interaction event binds the laptop's iroh endpoint key. Alice's later rotations do not change that binding. Mallory obtains the Time Machine backup of Alice's Mac. The wrapped secret is kept out of the backup, so the backup does not hold it. Even a copy of the wrapped secret would be useless without the Mac's Secure Enclave.

## The identity's key event log

### DR-8. The identity's KEL holds rotations only

**Decision.** The identity's KEL uses KERI's establishment-only configuration. The configuration is set in the identity's inception event, as `"c":["EO"]`, and KERI allows this setting nowhere else. The identity's KEL therefore holds an inception event and rotations, and no interaction events. Linking a device is a rotation that adds the device's key. Revoking a device is a rotation that drops the device's key. Each rotation is signed by any 2 parties, by a sole device (DR-10) or by a recovery key, and a rotation is final once it is accepted. While no second party is reachable, linking waits. Anything that has to be anchored in the identity's KEL costs a 2-party rotation. Records, including membership acts, are frequent, so they are never anchored in the identity's KEL.

**Why.** Apart from a sole device (DR-10), no single device writes to the identity's KEL. A thief who holds one of several devices therefore changes nothing in that KEL, and no single device can fork that KEL. KERI defines the configuration: "Only establishment events MUST appear in this KEL".

**Example.** Alice links a tablet from her phone. Her laptop shows "approve the tablet?", and she approves. The rotation that adds the tablet's key is final.

### DR-9. Any 2 parties can rotate

**Decision.** Every device carries weight 1/2. The external co-signer, whether it is Tellipod's or a self-hosted one, carries weight 1/2. Each recovery key carries weight 1. The threshold is 1. An identity without an external co-signer has no co-signer key in its key set, and a sole device of such an identity carries weight 1 (DR-10). Apart from that case, the weights do not depend on the number of devices. KERI expresses the weights as one clause of fractional weights, such as `["1/2","1/2","1/2","1","1"]`. The clause is satisfied when the weights of the signers add up to at least 1. No weight may exceed 1. Every validator and every second party enforces these weights, the recovery weight of 1 and the threshold of 1. It also enforces that a key's role never changes once a role statement gives it, and that a device AID that a rotation dropped is never listed again. With partial rotation, a validator matches each signature's key against the next-key digest at the signature's index, and takes the weight of that slot.

**Why.** No device is special. Any 2 parties together can agree on a change. With 3 or more parties, the other parties keep working after the loss of any one device. The external co-signer's operator alone, at weight 1/2, can never rotate an identity.

**Example.** Alice has a phone, a laptop, the Tellipod co-signer and a paper sheet. The phone and the laptop together reach 1, and so do the phone and the co-signer. The co-signer alone reaches only 1/2. The paper alone reaches 1.

**To verify.** Negative test vectors for each of these rules: a rotation that lowers the paper's weight, raises the threshold, relabels a role, lists a dropped device AID, or claims the recovery slot with a device's signature.

### DR-10. A sole device carries weight 1

**Decision.** While an identity has one device and no external co-signer, that device carries weight 1. The rotation that links a second device gives both devices weight 1/2. A revocation after which the identity has one device gives that device weight 1 again. Identities with an external co-signer need no special case.

**Why.** Every user without an external co-signer links a second device at some point. If a sole device carried only 1/2, that routine act would need the recovery key. Linking would then cost a paper user a new sheet, and it would expose the recovery key on a device. The risk of giving a sole device weight 1 is that whoever holds the sole device and its unlock secret owns the identity. That risk is accepted (DR-41). User presence for every rotation (DR-23) means that an unlocked phone lying on a table is not enough.

**Example.** Alice creates her identity on her phone, with a paper sheet and no external co-signer. The phone carries weight 1, and the paper carries weight 1. She then links her laptop: she scans the laptop's QR code and confirms on the phone. Now the phone carries 1/2, the laptop 1/2, and the paper 1.

### DR-11. The threshold of the current keys mirrors the threshold of the next keys

**Decision.** In every establishment event, each current key carries the weight that its role has under DR-9 and DR-10, and the threshold of the current keys is 1.

**Why.** KERI requires the signatures of a rotation to satisfy 2 thresholds: "the set of signatures on a Rotation event MUST satisfy two thresholds. These are the newly current threshold and the old prior next threshold from the most recent prior Establishment event." The list of current keys in a rotation holds the keys that the rotation exposes, and it may add keys that were never pre-rotated. The identity's current keys sign nothing but rotations. Because the current threshold mirrors the next threshold, any set of signers that satisfies one threshold also satisfies the other.

**Example.** Alice's laptop and the Tellipod co-signer link her tablet. The rotation lists the laptop's key and the co-signer's key as current keys, with weight 1/2 each. A recovery rotation signed with Alice's paper lists only the paper's key as a current key, with weight 1.

### DR-12. An offline device stays in the key set

**Decision.** A rotation carries forward, unchanged, the next-key commitment of every device that stays in the key set but does not sign the rotation.

**Why.** A rotation must not need every device to be present, and a switched-off desktop has to stay usable. A device's key in the key set signs rotations only, so carrying the device's commitment forward is all that the device needs to stay usable. KERI allows such a partial rotation: "A Partial rotation operation on a set of pre-rotated keys MAY hold back some as unexposed while exposing others as needed".

**Example.** Alice's desktop is switched off while her phone and laptop link a tablet. The rotation repeats the desktop's commitment unchanged. Later, the desktop signs another rotation with the key that it committed to.

### DR-13. KELs stay small and are stored once per identity

**Decision.** The identity's KEL holds identity acts only. These acts are device links, device revocations, recovery rotations, replacements of a recovery key, changes of the witness or of the external co-signer, and the seals of rotations of a device AID. The identity's KEL never holds pod membership, pod data or records. A device stores one copy of each KEL that it knows, and every pod that the device is in shares that copy. Every KEL has hard limits that are decided from its content alone: a number of device keys in each establishment event, a size of the identity's KEL, and a number of interaction events in a device AID's KEL. An identity whose KEL exceeds a limit is invalid. No device syncs with its devices, and no device stores or serves its KEL beyond the limit. A device caches its verdicts on records, and on a first sync it checks the newest records first.

**Why.** The identity's KEL then grows with device changes, not with activity. A device's storage grows with the number of people that the device knows, not with the number of pods. An estimate, to be replaced by measurement: a KEL holds about 16 KB after 3 years of ordinary use, and 64 KB for a heavy user. The KELs of 100 pod members then come to about 2 MB to 6 MB, and a phone checks them for the first time in under a second. A heavy user who knows about 900 identities holds about 14 MB to 58 MB of KELs, and a new device needs about 10 seconds to check them. Without the limits, a member with a witness of its own could make every member's device store and check millions of valid events.

**Example.** Bob is in 3 pods with Alice. His phone keeps one copy of Alice's KEL.

**To verify.** The values of the limits. Proposed: 32 device keys in each establishment event, 1 MB or 4,096 events for an identity's KEL, and 64 interaction events for a device AID's KEL.

### DR-14. Every establishment event states the role of each key

**Decision.** Every establishment event anchors a public role statement by a digest seal. The role statement gives the role of each key. The roles are recovery by paper, recovery by the service, external co-signer and device. The role statement is KERI self-addressing data, which means that it is CESR-encoded and carries its own digest. The role statement travels with the KEL. Revoking a device drops the device's key, and the role statement of that rotation no longer lists the device's device AID (DR-20). Wherever a rule of this design depends on the roles of a rotation's signers, the rule reads those roles from the previous establishment event. The role statement of the identity's inception event gives the role of the first device, but not the first device's device AID. In the rotation that seals the first device AID, the role statement adds that device AID (DR-6). The indices in a role statement count the next-key digests of the event that carries the role statement.

**Why.** KERI validation sees only the positions and weights of keys, and KERI defines no roles. The rules of this design need roles. A rotation signed with a recovery key may change the witness with only the new witness's receipt (DR-16). A sole device also carries weight 1, so a weight alone does not show which key is a recovery key. The external co-signer must also know which next-key commitment belongs to the recovery key. The roles are read from the previous establishment event so that a thief cannot relabel a key as a recovery key in the same rotation that uses that key for recovery. The role statement reveals nothing new, since the number of devices is visible anyway (DR-37).

**Example.** Event 8 of Alice's KEL anchors the role statement "key 0: recovery (paper), key 1: recovery (service), key 2: external co-signer, keys 3 and 4: devices `E-phone` and `E-laptop`". Event 9 may move Alice to another witness without a receipt from the old witness only if event 9 is signed with key 0 or key 1.

## Witnesses

### DR-15. Every identity has a witness

**Decision.**

- Every identity has exactly one witness, listed in the identity's KEL from the identity's inception event on. By default, the witness is Tellipod's. The user can instead choose another witness that runs the same witness software. Someone else may operate that witness, or the user may host it. A stock KERI witness does not qualify, since it issues no stamps (DR-20).
- The witness is not the co-signer. It holds no key of the identity and cannot rotate anything. Its only jobs are to receipt events and to issue stamps (DR-20).
- A rotation of the identity's KEL is accepted only after the witness has receipted it. The witness receipts only the first event that it sees at each position, so a second, different event at the same position is never accepted.
- Identities with different witnesses can share a pod. Changing the witness is itself a rotation (DR-16).
- A device gets the KELs of other identities from its pod peers, together with the receipts. The device checks the receipts itself, without contacting any witness. Every member's device stores the KELs of the members of its pods, serves those KELs to other devices, and compares the copies that it receives.
- A device contacts a witness to send the rotations that it signs, to fetch the latest KEL before it co-signs a rotation (DR-16), and during recovery. Apart from these, a device asks a witness for a KEL in only 3 cases:
  - Before it writes, and at least every 24 hours, it asks for its own identity's KEL (DR-21).
  - It asks for another identity's KEL when no source has confirmed the device's copy of that KEL within the last 24 hours. A confirmation from the device that it is about to sync with does not count. It sends such a query through a relay, in one batch with its other overdue queries. A device never puts queries of 2 identities that it hosts into one batch.
  - While it holds a removal of its identity from a pod, or a leave written in its identity's name, it asks, at most every 24 hours, for the KEL of the identity that wrote the removal or the leave. With that KEL, it checks the removal or the leave again (DR-19).
- A device also asks its own identity's witness for stamps for its own records (DR-20). A stamp request carries the identity's AID and a digest, so it shows the witness no pod. No device asks for stamps for another identity's records.
- When a device checks whether its copy of an identity's KEL is fresh, a confirmation from a device of that same identity does not count.

**Why.** Without a party that orders events, no rule for forks can both bring all devices to the same state and protect the events that were already accepted. Either every device falls back to the same state when it sees 2 rotations at one position, or each device keeps the event that it saw first. In the first case, a rival rotation that arrives late can undo events that were already accepted. It can do so even if it was signed a year later, by keys that were carried forward since then. In the second case, members disagree for good about which branch is valid. The witness provides the single order. A rival event is never accepted, and a thief cannot show different versions of the KEL to different members. Stamps need exactly one witness. With several witnesses, one of them might not yet have receipted a revocation, and that witness would still issue stamps at the old position. Within 24 hours, a revocation reaches every device that syncs with the identity's devices. This limit of 24 hours is called the freshness bound. A peer can withhold events but cannot forge them, since the witness receipts only the first event at a position. The freshness bound limits what a peer can achieve by withholding events. The witness sees the identity's KEL, and so it sees the identity's device changes, but it never sees pods. The design pays 2 costs. First, a witness is required even for users who run no other infrastructure. The user may choose any witness that runs the witness software, including a self-hosted one, and that choice softens this cost. Second, linking and revoking need the witness to be reachable, so 2 devices on a local network without internet access cannot link a third device. Records are unaffected. Every period in this design, such as these 24 hours, is measured on a monotonic clock, and a stored time that lies in the future counts as expired, so that a clock set back does not stretch a period.

If a device asked the witness before every sync session, the witness would learn who checks whom. Taking KELs from peers keeps the witness from learning this. A revoked device is itself a peer, and it can serve an old KEL that is still validly signed. The freshness bound keeps such a device from delaying a revocation for more than 24 hours.

**Example.** Alice's phone and the co-signer link a tablet. At the same time, her laptop and her desktop revoke an old phone that she no longer uses. Both rotations are at position 9 of Alice's KEL. The witness receipts only the rotation that reaches it first, and the other rotation is never accepted. In another case, Alice's phone is stolen. On Tuesday, her laptop and the co-signer revoke the stolen phone. Then the laptop goes offline, and so does Carol. Bob's phone keeps syncing the Tokyo pod with the stolen phone. The stolen phone cannot confirm that Bob's copy of Alice's KEL is fresh. The last copy of Alice's KEL that Bob's phone got from anyone else is 20 hours old. So 4 hours later, Bob's phone asks Alice's witness through the relay, learns of the revocation, and stops syncing with the stolen phone. In a third case, Alice uses no Tellipod co-signer, and she runs the witness software on her home server instead of using Tellipod's witness.

### DR-16. Changing the witness, retries and a misbehaving witness

**Decision.** A rotation that changes the witness needs receipts from both the old witness and the new witness. The exception is a rotation signed with a recovery key, which needs a receipt from the new witness only. Whether a signing key is a recovery key is read from the role statement of the previous establishment event (DR-14). Every signer stores the new keys and the signed event durably before it releases the event, and it resends the same event on a retry. Receipts by one witness for 2 different events at one position prove that the witness misbehaves. The identity then moves to another witness by a recovery rotation. A device that co-signs refuses a rotation unless the device holds the latest KEL. A rotation that changes the witness goes to the new witness first and to the old witness last. The old witness's receipt is the point at which the change takes effect.

**Why.** The exception for a recovery key is the way out from a witness that is down or that censors the identity. In every other case the old witness's receipt is required, so that a thief with 2 devices cannot move the identity to a witness of the thief's own without the old witness seeing the move. A device saves its new keys and the signed event before it sends the event. So if the device crashes after the witness has receipted its rotation, the device does not lose the keys that the rotation committed to, and it does not build a second, conflicting rotation. Because a device refuses to co-sign without the latest KEL, it does not sign a rotation that the witness will refuse. Sending to the old witness last keeps the old witness stamping until the change is final, and a new witness that never answers does not lock the identity.

**Example.** Alice's new phone signs recovery rotation 13, sends it to the witness, and crashes. On restart, the phone finds rotation 13 and its new keys saved. The phone resends the same rotation 13 instead of building a second, different rotation at position 13. In another case, Tellipod's witness is unreachable for a week. Alice uses her paper to sign a rotation that moves her identity to her home witness.

**To verify.** Which witnesses KERI requires receipts from for a rotation that changes the witness: the old witnesses, the new witnesses, or both.

## Records and revocation

### DR-17. Records form hash chains

**Decision.** Each device's records in a pod form a hash chain: every record carries its sequence number and the digest of the device's previous record. The history of a record is the record itself, together with every earlier record that its hash chain leads back to. Wherever this design says that something names a record, it names the record by the record's digest. A stamp's leaf, an admission, a removal and the first record of a new interval all name records in this way. A record of a revoked device is accepted only if it lies in the history of a record that a stamp or an admission names (DR-20). A record of a removed member is accepted only if it lies in the history of a record that the removal lists. This limit holds until a re-add starts a new interval (DR-40). A record's identity is the digest of its signed body, without the signature. The signed body carries a domain tag, the pod, the identity's AID, the device AID, the sequence number, the digest of the previous record and the record type. P-256 signatures use the low-S form. A verifier indexes records by device, branch and sequence number, so that checking whether one record lies in another record's history is a lookup, not a walk back through the chain.

**Why.** A signature or an anchor proves that a record existed, but never that another record did not exist. A record's position in its chain lets a verifier reject a record that was written later but claims to be older. Position also tells the branches of a fork apart. A stamp, an admission or a removal that names a record on one branch therefore does not extend to the other branch. In both cases, the honest records around the rejected record stay accepted. Because of the chain, a stamp or an admission that names a record covers that record's whole history. Because a record's identity leaves out the signature, nobody can make a second item at a position by changing a signature's encoding. Because the body names its pod, nobody can replay a record from one pod in another pod. Either would otherwise let any member make an honest device look forked.

**Example.** Alice's phone writes record #440 in the Tokyo pod, and #440 carries the digest of #439. A stamp whose leaf names #440 therefore covers #1 to #440. Malware on the phone later gives Bob a rival record at position 1. That rival record lies outside the history of #440, so the stamp does not cover it.

**To verify.** Whether the sync engine's records can carry a sequence number and the digest of the device's previous record.

### DR-18. A record is pod data, verified against 2 KELs

**Decision.** A record is signed by one device AID and stored as pod data, never as a KEL event. A verifier checks the record's signature against the device AID's KEL, at the key state that the record refers to. The verifier also checks in the identity's KEL that the device AID was linked. If the device has since been revoked, the verifier checks that a stamp from before the revocation, or an admission, covers the record (DR-20).

**Why.**

- A record cannot be an event of the identity's KEL. That KEL holds rotations only (DR-8), and each rotation needs 2 parties and a receipt from the witness (DR-15). A device writes records all day, often offline, and at the same time as the identity's other devices, while a KEL is a single sequence.
- A record cannot be signed with the device's key in the identity's key set either. Unless the device is the identity's sole device (DR-10), that key carries weight 1/2, below the threshold of 1, so a signature by one device alone is not valid for the identity. That key is also replaced every time the device signs a rotation. And because that key can rotate the identity, using it for every record would expose it many times a day.
- The device AID gives the device a key that it may use again and again, and a name that stays the same across the identity's rotations (DR-6). So every record has a stable author.
- Each of the 2 KELs answers its own question. The device AID's KEL shows which key the device AID held at the key state that the record refers to. The identity's KEL shows that the device AID belongs to the identity, because a rotation of the identity's KEL anchors the device AID's inception. Without the second check, anyone could create a device AID and sign records in Alice's name.
- Keeping records out of KELs keeps pod activity private and the KELs small (DR-13). Otherwise every holder of a KEL, including the witness, would see when and how often the identity writes. Records, by contrast, reach only the members of the pod.
- After a revocation, a signature alone cannot show when a record was signed, because there is no trusted clock. So after a revocation, the verifier relies on stamps and on admissions by the user (DR-20). The witness orders each stamp against the revocation.

**Example.** Alice's laptop writes a record in the Hiking pod. Bob's phone verifies the record against the KEL of `E-laptop`, the laptop's device AID, and against Alice's KEL. Alice's KEL anchors the inception of `E-laptop`, and it holds no rotation that drops the laptop's key.

### DR-19. A device syncs a pod only while it is linked and its identity is a member

**Decision.** A device may sync a pod only while its identity is a member of the pod and the device is linked to that identity. Every peer checks both conditions, for the devices of its own identity and for other members' devices alike. A revocation must therefore reach every device of every member of every pod that the identity is in. A device that holds a removal of its identity from a pod, or a leave written in its identity's name, stops syncing the pod but keeps its replica. The device checks the removal or the leave again whenever the KEL of the identity that wrote it changes. If the removal or the leave is no longer accepted, the device resumes syncing the pod.

**Why.** Membership lists identities, not devices (DR-38). Without the check that the device is linked, a revoked laptop would keep syncing with Bob's devices. A removal written by a revoked device is accepted only if a stamp from before the revocation, or an admission, covers it (DR-20). The revocation of the device that wrote the removal reaches the removed member through the KEL of that device's identity. The removed member's device gets that KEL from any peer or from the witness (DR-15). The revocation does not reach the removed member through records of the pod from which the member was removed. Without checking the removal again, a removal that a thief wrote after the revocation would cut honest members off for good. The cost is that a removed member's device keeps the pod's data until its check shows whether the removal is accepted.

**Example.** Alice revokes her laptop. Bob's phone stops syncing with the laptop once Bob's phone holds the revocation. In another case, a thief has Alice's phone, and the phone is revoked at 10:06. At 10:07, the thief uses the phone to write record #441 in the Tokyo pod, and that record removes Bob. At 10:08, Bob's phone holds #441 and stops syncing the Tokyo pod. At 10:10, Bob's phone receives Alice's KEL from Carol's phone, which is also in the Tokyo pod. Bob's phone sees the revocation, finds that no stamp from before the revocation and no admission covers #441, and resumes syncing the Tokyo pod.

### DR-20. A revoked device's records are accepted when its own stamp from before the revocation covers them

**Decision.**

- Revoking a device is a rotation of the identity's KEL that drops the device's key. The role statement of that rotation no longer lists the device's device AID (DR-14). From then on, the device AID's KEL has no authority. Whether a device is revoked is decided by the role statement. A device AID that a rotation dropped stays revoked, and every new linking uses a new device AID. Nothing about pods is anchored in the identity's KEL.
- A stamp is a statement that the identity's witness signs at the request of one of the identity's devices. The stamp names the identity's AID. It gives the position of the latest event of the identity's KEL that the witness has receipted, and the digest of that event. It also gives a digest that the requesting device supplied. That digest is the root of a Merkle tree. Each leaf of the tree names a pod, the requesting device's device AID and the digest of that device's newest record in the pod, together with a fresh random salt. The leaves are in random order, and the tree is padded to 256 leaves. Leaves and inner nodes carry distinct prefixes, and leaves have a fixed length. A device with more than 256 pods to cover requests several stamps.
- At the start of each signing session, together with the fetch of the identity's KEL (DR-21), a device requests one stamp for its own records. The stamp covers the device's newest record in every pod in which the device wrote since its previous stamp. The device publishes the stamp into each of those pods, together with the path from that pod's leaf to the root. A stamp covers the record that a leaf names, and every record in that record's history (DR-17). No write waits for a stamp, and a stamp request needs no user presence, since the device signs nothing to make it.
- Before a device signs a revocation of another device of the identity, it requests a stamp for the revoked device's records that it holds and that no published stamp covers yet. On each branch, that stamp covers the newest such record. The signer stores that stamp durably before it signs, and it publishes the stamp once the revocation is released, or after a restart if it stopped before publishing.
- After a device is revoked at a position of the identity's KEL, a record of that device is accepted only if a stamp or an admission covers it. The stamp must give a position below the position of the revocation. It must name the identity of the record's device, and the event digest that it gives must equal the digest of the accepted event of the identity's KEL at that position. It must be signed by the witness that the identity's KEL lists at that position, which is the witness that the event at that position lists. So at the position of a rotation that changes the witness, the KEL lists the new witness. A covered record is accepted on every branch of the revoked device's chains (DR-22).
- An admission is a record that another device of the same identity writes on the user's explicit act. It names a record of the revoked device, and it accepts the revoked device's records in the pod up to that named record. An admission counts only once the admission itself is accepted, and never through a record that it admits itself. A record's own reference to a key state never shows that its device was linked.
- Every member's device checks that the other members' devices keep requesting stamps. For each device and pod, it measures how long that device's records have stayed without a stamp, on its own monotonic clock from the moment it received them. After 7 days without a stamp, it shows the user that the device's records are not stamped, and it accepts no further records from that device in that pod until a stamp covers the waiting records. This is each device's sync policy, not part of the rule that decides which records are accepted.
- A replica stores stamps by their digest, so a stamp is never overwritten. For each device and each branch of its chain, the replica keeps the stamp that covers the highest record. It drops an older stamp only once it holds 3 things: a valid newer stamp that covers the same record or a later one on the same branch, the records that place the older stamp's record in the history of the newer stamp's record, and a KEL that shows that no event after the older stamp's position, up to and including the newer stamp's position, revokes that device. After a device is revoked, the replica drops the device's stamps at the position of the revocation and at higher positions.
- A replica keeps the records of a revoked device that nothing covers, marks them as not accepted, and passes them on to other devices. It keeps at most 1 MB of the headers of such records for each identity, and it fetches no record's content until the record is accepted. It keeps the lowest positions after the highest covered record on each branch first, taking branches and devices in turn. It accepts such a record once a stamp or an admission that covers it arrives.

**Why.**

- The goal is bounded non-repudiation. A user may disown her most recent records, but never a device's history. A user cannot disown older records by declaring the device stolen. Otherwise a promise made last year could be disowned today.
- There is no trusted clock. The witness is the only party that orders anything against the revocation, because the witness receipts the revocation itself. The witness receipts each position once and in order. So whatever a stamp covers existed before any event after the stamp's position was accepted, and so before any revocation after that position.
- Each device requests stamps for its own records, and the other members only check that it keeps doing so. So the records that a user can disown are at most those written since her device's last stamp. An honest user whose phone is stolen loses at most the records of the current signing session, unless she admits them. A dishonest user with a modified app that never requests stamps, or with a witness of her own that refuses them, can disown at most the records of the last 7 days. After that, the other members accept no further records from that device, and everything stamped before stands.
- Members do not request stamps for other identities' records. That would multiply the requests by the number of devices in each pod, and it would show each identity's witness who shares pods with whom.
- A stamp names the identity and the digest of its KEL event, so a stamp that an attacker obtains under an AID of the attacker's own covers no record of another identity.
- A record that no stamp from before the revocation covers cannot be told apart from a thief's record written after the revocation. No rule can accept the first and reject the second. Only the user may admit such a record.
- Because of the salts, the random order and the padding, the witness learns neither a pod nor the number of pods. A leaf and its path are published only in the leaf's pod, so pod members do not learn the identity's other pods.
- A revocation needs no statement of its own, and it reveals nothing about the identity's pods. KERI gives a delegator no event that revokes a delegated AID, so a revocation can only drop the device's key from the identity's key set. A thief who holds the device AID's keys can still sign records after the revocation. That is why stamps and admissions, not signatures, decide which of the device's records are accepted. The user repairs what a thief did by means of ordinary pod acts, and the thief's records stay in the pod.
- Storing stamps by digest keeps a thief from replacing an older stamp with a useless one. A newer stamp of a higher record on the same branch proves everything that an older one proved, unless a revocation lies between their positions, so the stamps that a replica keeps do not grow from day to day. The limit on unaccepted records keeps a revoked device from filling replicas, and peers stop syncing with a revoked device anyway (DR-19).

**Example.** Alice has a phone and a laptop, and Alice's KEL is at position 8.

- Bob is a member of the Tokyo pod. In that pod, the phone wrote records #1 to #430 by Monday afternoon. On Monday at 17:30 the phone starts a signing session, and its stamp at position 8 covers #430. At 17:40 the phone writes #437, "I'll pay the hotel deposit, 500 EUR", and by 17:55 it has written up to #440. The laptop syncs #431 to #440 at 17:56.
- Carol is a member of the Ginger pod. In that pod, the phone wrote #1 to #55, and the phone's latest stamp covers #55.
- Dave is a member of the Hiking pod. In that pod, the phone wrote #1 to #120, and in March it wrote Alice's leave. Stamps covered all of these records at the time.
- The phone is stolen on Monday at 18:00. On Tuesday at 10:00, the laptop and the co-signer revoke the phone. Before it signs, the laptop requests a stamp for the phone's #440, which it holds. The revocation is position 9 of Alice's KEL.
- At 10:30, the thief writes #441 in the Tokyo pod. No stamp below position 9 covers it, so #441 is rejected everywhere.
- In the Tokyo pod, #1 to #440 are accepted, including the promise. In the Ginger pod, #1 to #55 are accepted. In the Hiking pod, #1 to #120 and the leave are accepted.
- Suppose instead that the laptop had never synced #431 to #440. Then those records, written in the stolen phone's last signing session, are not accepted until Alice admits them from her laptop. Nothing older is lost.

**To verify.** That the sync engine can undo the effects of a record that is no longer accepted, redo them when a stamp or an admission arrives later, accept both branches of a fork, store stamps by digest, and keep the headers of unaccepted records without their content. Also, whether a KERI reply message or a key state notice can carry the requesting device's digest. Also, that a witness's AID is non-transferable, so that a verifier checks a stamp's signature against the witness that the KEL lists.

### DR-21. A revocation names no record, and a device fetches its KEL before writing

**Decision.** A revocation names none of the revoked device's records, so the revoking parties have no say in which of those records are accepted. Every record of the revoked device that a stamp from before the revocation covers is accepted, and so is every record that an admission covers. Before a device writes in a signing session, it tries to fetch its identity's KEL from the witness. In the same exchange, it requests stamps for its own newest records (DR-20). The device writes whether or not the witness answers. It syncs with the identity's other devices whether or not it has reached the witness.

**Why.** If the revoking parties named the last record that they accept, a dishonest user could disown records. That user would let a device that holds none of the revoked device's records carry out the revocation, and that device would name an early record. The fetch before writing lets a device learn of a revocation early. Writing and syncing while the witness is unreachable do not change which records are accepted. So devices on a local network without internet access can still sync with each other.

**Example.** In the first case, Alice is dishonest. She wants to disown her phone's record #200 in the Tokyo pod, written last month. She links a tablet, which holds none of the phone's records, and the tablet revokes the phone. But the phone's own stamp from a signing session after #200 covers it, so #200 stays accepted. In the second case, Alice is in a cabin, and her phone and laptop sync over a local network without internet access. The phone writes #451 to #500, and the laptop holds them. The phone is stolen before it reaches the internet. When the laptop revokes the phone, the laptop first requests a stamp for #500, so #451 to #500 are accepted.

### DR-22. Device AIDs have no witnesses, and a fork rejects no record

**Decision.**

- Device AIDs have no witnesses. A device AID's inception event lists no witnesses, so the device AID's events need no receipts. An interaction event is accepted on the device's signature alone. An inception or a rotation of the device AID also needs the identity's seal (DR-6).
- A fork of a device's chain of records in a pod (DR-17), or a fork of its device AID's KEL (DR-6), marks the device as compromised. Honest devices stop syncing with the compromised device, and the identity's other devices alert the user. The mark lasts until the identity revokes the device.
- The fork itself rejects no record. Until the revocation, the device's records on both branches are accepted, since the device is still linked. From the revocation on, stamps and admissions decide which of the device's records are accepted, and this holds on both branches (DR-20).
- After a device starts, and before it signs anything new, it finds out where its device AID's KEL and its own record chains end. Before it writes in a pod, it asks the pod's peers for its own newest record, and it writes anyway if no peer answers. Before it adds an interaction event, it asks for its device AID's KEL. A device whose stored positions match its data skips these questions.
- On iOS and macOS, a device also stores positions in the keychain. For each of its device AIDs and each pod, the device stores the position of that device AID's newest record in that pod. For each of its device AIDs, the device also stores the position of the newest event of that device AID's KEL. Each position is stored as a keychain item of class `WhenPasscodeSetThisDeviceOnly`. The device raises a stored position before it commits a new record or event to its store, once for each batch of records. For each device AID and pod, the device also stores whether any record of that chain was ever offered to a peer, and it sets that flag before the first offer. When its identity leaves a pod, the device deletes the stored positions and the flag for that pod. A restore does not change these items, so after a rollback they are ahead of the restored data. When a device AID is revoked, the device deletes that device AID's stored positions.
- When a stored position is ahead of the device's data, the device signs nothing more in that pod, or in its device AID's KEL, until it holds its own chain up to the stored position, which it gets from peers. While the flag shows that no record of that chain was ever offered to a peer, the device does not wait, since its lost records never reached another device. If the stored positions are missing while the device's keys exist, as after the user turns the device passcode off, the device treats its data as rolled back and waits. If no peer ever returns the chain up to the stored position, the only way out is to revoke the device and link it again. The app keeps what the user writes in the meantime as an unsigned draft, and signs the draft once the wait ends.
- A device writes at once, even when it reaches no peer, if its stored positions match its data or if it has no stored positions. Local-first operation requires this. The device catches up once a peer is reachable.
- Sometimes a device's data goes back to an older state while its hardware key survives. This is called a rollback. Suppose that the device's check of where its chains end misses a rollback, and that the device forks as a result. Then the device is revoked and linked again. Such a fork can happen only on devices that store no positions, such as Windows and Linux devices. On iOS and macOS, a rollback ends in a wait instead, as the bullets above describe.

**Why.**

- In a device AID's KEL, only the interaction events can fork. The device AID's keys change only with the identity's approval, in a rotation of the identity's KEL, and the identity's KEL has a witness (DR-15). Record chains fork far more easily than a device AID's KEL, because a device writes records all day but binds an iroh endpoint key only rarely. A witness of the device AID would see only the device AID's KEL, where forks are rare, and it would see none of the record chains. The fork rule applies to both the device AID's KEL and the record chains. A pod member's device notices a fork as soon as it holds both branches.
- A fork has one of 2 causes. In the first, a thief or malware shows different events or records to different members. In the second, an honest device's data goes back to an older state while its hardware key survives, which is a rollback. Nothing in the events or records tells the 2 causes apart, so both causes are handled the same way.
- The fork rule picks no branch. A rule that rejected one branch would let a dishonest user disown records. A modified phone would sign a rival record at an earlier position, and the honest branch would be lost. Both branches are the identity's, since the device signed both while it was linked.
- Asking peers works because everything that the device ever sent is held by some peer. An event or record that the device never sent can be replaced by a new one at the same position without harm, since no other copy of it exists for the new one to clash with.
- An honest rollback happens on desktop computers. A Time Machine restore, a virtual machine snapshot or a Windows system image brings back old app data, while the key stays in the Secure Enclave or the TPM. On Android, uninstalling the app, clearing the app's data or moving to a new phone deletes the Keystore keys together with the data. The phone then comes back as a new device, with nothing to fork. Keeping the key while the data goes back takes a rooted phone or a snapshot.
- On iOS and macOS, the stored positions turn a rollback that the check of peers would miss into a short wait. Each position belongs to one device AID and one pod, so a position blocks only the chains that actually went back. Also, 2 identities on one Mac never share a position. A position has to be raised before the device sends the record. Otherwise a record could reach a peer while the stored position still lies below that record. A later restore could then bring back data that ends just below the record, the stored position would agree with that data, and the device would sign a second record at the same position. A pod with no other device needs no wait, because nobody else holds the device's records there.
- The keychain class matters. An item of class `WhenPasscodeSetThisDeviceOnly` is never in a backup. A restore therefore does not change the stored positions, and on a new device they are gone, together with the Secure Enclave key. An item of a plain `ThisDeviceOnly` class is in the backup, so the stored positions would go back together with the data. The Android Keystore holds keys only, and it has no place for stored positions.
- An honest device that forks is revoked like a stolen device, because nothing in its events or records tells it apart from a device in a thief's hands. The cost is one linking.
- The fork rule is our own. On duplicity, KERI itself either stops trusting the identifier as a whole, or lets each validator keep the event that the validator saw first.

**Examples.**

- **A rollback that the check catches.** Alice restores her Mac's app data from last week's Time Machine backup. The Secure Enclave key is untouched, so the Mac still signs as its device AID, `E-mac`. The restored data says that the Mac's newest record in the Tokyo pod is #300. During the week, however, the Mac wrote records up to #340, and Bob's phone holds all of them. When the Mac starts, and before it writes in the Tokyo pod, it asks the pod's peers for its own newest record. Bob's phone answers #340 and sends #301 to #340. The Mac's next record is #341, not a second #301. Suppose the Mac had also written a record #341 just before the restore, and that record never reached a peer. Then the new #341 takes the place of the old #341 without harm, since no other copy of the old #341 exists.
- **A rollback caught offline.** Alice restores her Mac's app data from last week's Time Machine backup and boards a plane. The keychain still holds #340 as the Mac's position in the Tokyo pod, while the restored data ends at #300. In the Hiking pod, the stored position and the data agree, since the Mac wrote nothing there during the week. Alice writes "hotel booked" in the Tokyo pod, and the app keeps it as a draft. A note that she writes in the Hiking pod is signed at once. After Alice lands, Bob's phone sends the Mac #301 to #340, and the app signs the draft as #341.
- **A rollback that the check misses.** Alice restores her Windows PC from last week's system image, and the PC's key stays in the TPM. The PC stores no positions. She is on a plane, and no peer is reachable. The PC believes that its chain in the Tokyo pod ends at #300, so it writes #301, "hotel booked", at once. But Bob's phone already holds the PC's earlier #301 to #340, and a stamp from earlier in the week covers #340. When the PC is online again, it requests a stamp, and Bob's phone receives the new #301. Bob's phone now holds 2 records at position 301, which is a fork. Bob's phone stops syncing with the PC, and Alice's phone tells her that the PC looks compromised. She revokes the PC and links it again, and the PC gets a new device AID. Stamps from before the revocation cover both branches, so the PC's earlier #301 to #340 and the new "hotel booked" are all accepted.
- **A thief's fork.** Malware in the app on Alice's phone signs a second record at position 301 of the phone's chain in the Tokyo pod, and shows that record only to Bob. Carol's phone holds the real #301. When Bob's phone syncs with Carol's phone, Bob's phone holds both records at position 301. Every member's device that sees the fork stops syncing with Alice's phone. Alice's laptop alerts her, and she revokes the phone. The real #301 is accepted, since stamps from before the revocation cover it. The malware's record is accepted only if a stamp from before the revocation covers it. If a stamp does cover it, that is the accepted risk of malware in the app (DR-41).
- **Android.** Alice clears the app's data on her Android phone. The Keystore keys are deleted together with the data, so the phone holds no key of its old device AID and cannot sign at an old position. The phone is linked again as a new device, and nothing forks.

**To verify.** That a Time Machine restore or a Migration Assistant transfer on macOS does not change a keychain item of class `WhenPasscodeSetThisDeviceOnly`, as is the case for an iOS backup.

## Signing and presence

### DR-23. 2 strengths of signature, 2 levels of presence

**Decision.**

- There are 2 strengths of signature. Day-to-day acts are records. One device signs each record with its device AID's key, which this document calls the record-signing key. Linking a device and revoking a device are rotations of the identity's KEL, signed by any 2 parties, by a sole device or by a recovery key.
- A rotation asks for the user's presence, by fingerprint or device passcode, at every signature.
- The record-signing key asks for the user's presence once per signing session, and then signs without asking until the signing session ends. A signing session ends when the app or the device locks, or after a period of inactivity that a product setting defines.
- On Android, the record-signing key stays usable for a set time after authentication (`setUserAuthenticationParameters`). On iOS and macOS, one authenticated `LAContext` authorizes signatures until the app invalidates that `LAContext`, so the app ends the signing session itself.
- The platform makes the record-signing key unusable while the device is locked. After an authentication, the key signs without a new authentication for at most 1 hour. That period is called the key's window. On Android, the Keystore enforces the window. On iOS and macOS, the app enforces the window by invalidating the `LAContext`, and the bound that the platform itself enforces is the device lock. When the window closes, the app asks for presence again.

**Why.** A fingerprint before every record would be too much, while one fingerprint at the start of a signing session is acceptable. The signing session itself is a rule of the app. On Android, an unlock of the lock screen also opens the record-signing key's window, and the window runs on its own timer. So the platform's limits keep a locked phone from signing anything. A thief who uses a stolen, unlocked phone through the app signs for at most an hour, unless the thief can authenticate again (DR-41). Malware inside the app is a different case, and DR-41 lists it as an accepted risk too. On Android, the Keystore enforces that hour. On iOS and macOS, the app enforces it. The price is at most one prompt an hour. Rotations change who controls the identity, so every rotation needs the user to be present on each device that signs it.

**Example.** Alice opens Tellipod at 9:00 and touches the fingerprint sensor once. She then writes in 3 pods without a prompt until 10:00, when the app asks for her fingerprint again, and so on through the day, at most once an hour. In the evening, linking her new tablet asks for her fingerprint again, and her laptop, which co-signs the rotation, asks for it too.

**To verify.** Windows: Windows Hello has no stable, documented mode in which a key stays usable for a set time. It has only a prerelease cache configuration, `KeyCredentialCacheConfiguration`. Until that configuration is tested, a Windows device may have to ask for presence at every record. iOS and macOS: whether the platform caps how long an authenticated `LAContext` authorizes signatures with a Secure Enclave key.

### DR-24. Nothing is signed without the user present

**Decision.** No device signs a record outside a signing session. Anything that the app would write on the user's behalf waits for the next signing session. Background sync continues: it moves records that others signed, and it authenticates with the iroh endpoint key, which signs no records. Stamp requests continue as well, since they sign nothing (DR-20).

**Why.** Every record that an identity signs is binding (DR-20). Signing only while the user is present keeps the number of acts that nobody chose small.

**Example.** Alice sets a reminder to post in the Tokyo pod at 7:00. The reminder is posted when she next opens the app, at 8:15.

## Recovery and the co-signer

### DR-25. Recovery: the Tellipod service by default, a paper sheet, or both

**Decision.** An identity commits to a recovery key held by the Tellipod recovery service, to a recovery key written on a paper sheet, or to both. Each recovery key has weight 1, so either one alone can recover the identity. The service is the default. A person who does not want to rely on Tellipod uses the paper.

**Why.** Recovery must outrank a stolen device when the thief does not know the user's PIN. A thief who has both the device and the PIN is an accepted risk (DR-41). Recovery must also restore an identity whose devices are all lost. With both recovery keys, the identity survives the loss of either backend. The price is that a theft of either backend's key exposes the identity, since the first recovery can drop the other backend's key. For an identity with an external co-signer, the paper outranks a stolen device only together with an honest external co-signer. An honest external co-signer refuses to drop the paper's key (DR-29). The paper also outranks the stolen device only while the thief holds no second device of the user.

**Example.** Alice's next keys are: phone 1/2, laptop 1/2, co-signer 1/2, recovery service 1, paper 1. A burglar who finds the paper owns the identity, even though Alice still knows her PIN.

### DR-26. The recovery service is non-custodial

**Decision.** The Tellipod recovery service stores the recovery key encrypted. It releases the key only after the user passes the email check and enters the PIN, and the PIN is checked inside an enclave (DR-31). The phone that carries out the recovery signs the recovery rotation itself. That rotation adds the phone's key and seals the inception of the phone's device AID, as a linking does (DR-6). The phone also stores a newly generated recovery key with the service. A user who has lost the PIN and every device has lost the identity. The service stores the encrypted key under a random identifier. The service does not learn the AID at enrolment or at recovery, although Tellipod's witness, which sees the enrolling and the recovering rotation seconds apart, can connect them. The service learns the AID only when it is asked to erase the recovery key. The erase request carries the identity's KEL, and the service checks the request's signatures against that KEL. The service erases a recovery key only on a request signed by the identity's current devices, and never because of wrong PINs (DR-32). The service notifies the enrolled email address of every failed attempt.

**Why.** A service that held a usable recovery key, of weight 1, could rotate any identity alone. Its operator, an intruder or a legal order served on the service could then rotate any identity through the service. The service does hold personal data: an email address tied to an encrypted key. Through that data, Tellipod can tell that 2 identities belong to one person when they recover through the same email address.

**Example.** Alice loses every device. On a new phone, she confirms her email address and types her PIN. The phone receives the recovery key, signs the recovery rotation, and enrols a fresh recovery key.

### DR-27. The paper sheet: 24 words, recovery only

**Decision.** The paper sheet holds one generated passphrase of 24 words, taken from the English word list of BIP-39, the Bitcoin standard for mnemonic phrases. That word list has 2,048 words. The 24 words seed one recovery key. The commitment to that key is carried forward from rotation to rotation until the key is used. Every use of the paper ends with a new sheet. There is one sheet, kept in one safe place, and not several sheets with a threshold. The paper serves recovery only, and it never stands in for a second party at linking. Each identity gets its own sheet.

**Why.** 24 words carry 256 bits of randomness, plus a checksum that catches most typing mistakes. Typing the words exposes the key, and that is why every use ends with a new sheet. Using the paper for routine linking would expose the key on devices that may be compromised, while linking can simply wait for a second party.

**Example.** Alice has no external co-signer, and she loses her phone. Her laptop alone carries 1/2. She types the 24 words on the laptop. The laptop signs a recovery rotation that drops the phone, gives the laptop weight 1, and commits to the key of a fresh passphrase. Alice writes down the new 24 words and destroys the old sheet.

### DR-28. Replacing a recovery key or resetting a forgotten PIN waits

**Decision.** Replacing a recovery key while the identity still has devices needs the agreement of a majority of the identity's devices, and the external co-signer checks that majority. Such replacements include a switch from the service to the paper, a new service key after a forgotten PIN, and a new sheet for a lost one. The external co-signer then holds the replacement for 30 days, and it notifies every device. A recovery rotation during those 30 days cancels the replacement. Without an external co-signer, 2 devices or a sole device replace the recovery key at once. A forgotten PIN is reset the same way, without the PIN. A majority of the identity's devices request a new PIN and a new recovery key. For a single-device user, that one device alone is the majority. The external co-signer holds the request for 30 days, and it notifies every device and the email address. Any act during the wait that uses the current PIN or a recovery key cancels the request. This reset also lifts any delay on the co-signer path.

**Why.** "I lost my paper" is also what a thief would claim. KERI's threshold cannot express a majority of the devices, since one device plus the external co-signer already meets the threshold. For a user with one phone, that phone is the majority, so the majority rule alone would not stop a thief. The wait forces a thief to keep a stolen phone unnoticed for the whole 30 days, while a user who really lost a phone recovers within that time. The wait does not stop a thief who holds a device and the user's PIN. Such a thief links a device of the thief's own and rotates with 2 devices, which needs no wait (DR-41). Without the reset, every way back goes through the PIN. Replacing the service key needs the external co-signer, and the external co-signer needs the PIN. A single-device user who forgot the PIN could then never link a device or change recovery again.

**Example.** Alice loses her paper. Her phone and laptop ask for a new sheet. The co-signer holds the request for 30 days, and it notifies both devices. On day 31, the key of the new sheet is committed. If a thief with only the phone had asked, the request would lack the laptop's signature, and the co-signer would refuse it. In a separate case, Alice has only her phone and forgets her PIN. She requests a reset, waits 30 days, sets a new PIN and gets a new recovery key.

### DR-29. The second party of a rotation is a role

**Decision.** The second party of a rotation is another device of the user, or an external co-signer. An external co-signer is either the Tellipod co-signer or a co-signer node that the user hosts on an always-on machine. An external co-signer is a PDN node acting as a Service of the identity, and it is reachable over iroh like any device. An identity has at most one external co-signer, and switching to another external co-signer is a rotation. Every second party reads the rotation before signing it, and asks for its user's presence. A device acting as second party checks in the app that the rotation commits to the recovery key again, and it refuses a rotation unless it holds the latest KEL. The external co-signer signs only a rotation that commits to the recovery key again, except a replacement that it holds under DR-28. The external co-signer never signs 2 different events at one position. While no second party is reachable, linking waits.

**Why.** Users choose whether to rely on Tellipod. Another device of theirs can be the second party instead of the external co-signer. Suppose that a thief holds one device and obtains a second signature. The rules keep that thief from dropping the recovery key in the rotation. A thief who holds a device and the user's PIN is the accepted risk of DR-41. The rules also keep the identity's KEL free of 2 rotations at one position.

**Example.** Alice links a tablet with her phone. Her laptop shows "approve the tablet?", checks that the rotation keeps the commitment to her paper's key, and asks for her fingerprint.

### DR-30. The Tellipod co-signer lives in an enclave

**Decision.** The Tellipod co-signer's signing key is generated inside an enclave and is never exported from the enclave. The enclave signs only after the PIN check, or, for a reset of a forgotten PIN, after the 30-day wait of that reset (DR-28). The enclave also enforces the rules of DR-29. Witness receipts and stamps may be produced outside the enclave. A self-hosted co-signer needs no enclave.

**Why.** Without the enclave, Tellipod's operator could co-sign without the PIN, and an operator colluding with a thief who holds the user's phone could drop the user's paper. A dishonest witness receipt is detectable without an enclave, since 2 receipts at one position are evidence in themselves. A stamp at an out-of-date position, by contrast, produces no such evidence, and DR-41 accepts that risk.

**Example.** A thief takes Alice's phone and bribes a Tellipod admin. The admin asks the co-signer to sign a rotation that drops Alice's paper. The enclave refuses, since the PIN is missing. Even with the PIN, the enclave still refuses, since the rotation does not commit to the recovery key again.

### DR-31. One PIN, checked in an attested enclave

**Decision.** The Tellipod co-signer and the recovery service share one PIN. One service, backed by an enclave and modelled on Signal's secure value recovery, checks that PIN. Before the app sends anything, it checks the enclave's attestation, a signed statement about the code that the enclave runs. The app checks 3 things about the attestation. The attestation must be signed by a key that is built into the processor and certified by the chip vendor. It must give the hash of a public, reproducible build. Finally, it must show firmware that the vendor has not withdrawn. The app stretches the PIN with Argon2 and sends it over a channel that ends inside the enclave. A desirable enhancement is to split the secret and the guess counter across enclaves of different chip vendors at different cloud providers, or across independent operators. A self-hosted co-signer checks its own, separate PIN with OPAQUE, a password protocol that never sends the PIN to the server.

**Why.** A short PIN is safe only if nobody can guess it offline, the operator included. On its own, a password protocol such as OPAQUE keeps the PIN off the network, but whoever holds what the server stores for the user can still try all 1,000,000 PINs of 6 digits in seconds. The enclave's hardware enforces the limit on guesses. Signal's code is under the AGPL-3.0 license, so it serves as a design reference only. The trust that remains lies with the chip vendor and with anyone who has physical access to the server, cloud staff included. In 2025, WireTap extracted an Intel SGX attestation key, and Battering RAM broke the attestation of Intel SGX and AMD SEV-SNP. Both attacks worked on DDR4 memory. TEE.fail extracted Intel SGX and TDX provisioning keys and AMD SEV-SNP keys on DDR5 memory. Rolling the enclave's stored state back would reset the guess counter, so the counter is replicated across several enclaves. AWS Nitro Enclaves attest with AWS's own certificate authority, not with a chip vendor's, so they do not qualify.

**Example.** A Tellipod admin copies the PIN database and gets only ciphertext. Code without the guess limit fails attestation, so the app sends that code nothing.

### DR-32. Wrong PINs bring delays, never erasure or a freeze

**Decision.** The enclave checks the PIN on 2 paths. On the recovery path, the recovery service releases a recovery key. On the co-signer path, the Tellipod co-signer signs a rotation. The enclave counts wrong PINs separately for each path. On the recovery path, it counts them for each enrolment. After 10 wrong PINs on that path, every further try waits longer: 1 hour, then 2 hours, then 4, 8 and so on. The recovery key is never erased because of wrong PINs. On the co-signer path, the enclave counts wrong PINs for each requesting device AID, with the same growing delays. It checks the requesting device's signature before it checks the PIN, so that every count belongs to a device AID that really signed the request. Failures from one device therefore delay only that device's requests, and the identity is never frozen.

**Why.** On the recovery path, only the email check stands before the PIN attempts. A thief can pass the email check by reading the code in the stolen phone's own mail app, and so can anyone who broke into the user's inbox. If wrong PINs erased the key, anyone who gets past the email check could destroy the user's recovery on purpose. And the erasure would add no protection that the delays do not already give. If wrong PINs froze co-signing for the whole identity, 10 bad requests from a stolen phone would keep the user's other devices and the co-signer from revoking the stolen phone. The delay doubles with each try. So after the first 10 tries, the delays allow about 13 more tries in the first year, about 23 tries in all, and fewer in every year after. An attacker therefore gets through only a tiny fraction of the 1,000,000 PINs of 6 digits. In practice, that bound is as tight as erasure. A thief cannot escape the count for each device by linking a second device, since linking needs the co-signer, and the co-signer needs the PIN.

**Example.** A thief has Alice's phone and its passcode, but not her PIN. He reads the email code on the phone and enters a wrong PIN 10 times on the recovery path. Alice's recovery key survives, each further try waits hours, and her mailbox shows the attempts. He then makes 10 co-signing requests from the phone with wrong PINs, and only the phone is delayed. On Tuesday, Alice enters her PIN on her laptop, and the laptop and the co-signer revoke the phone at once.

### DR-33. What Tellipod learns

**Decision.** For a default user, Tellipod runs the co-signer, the recovery service and the witness. Tellipod holds less than the threshold only because the recovery service is non-custodial: the co-signer alone carries 1/2, and the recovery key that the recovery service stores is encrypted (DR-26). The co-signer reads every rotation that it co-signs. Each such rotation shows the AID, the number of devices and the time. The co-signer also sees the requesting device's network address, unless a relay carries the request. For identities whose witness Tellipod runs (DR-15), the witness sees every event of the identity. The witness also learns when and how often stamps are requested for the identity, and so roughly how active the identity's devices are (DR-20). The witness learns nothing of pods, their members or their data, since a stamp request carries nothing about pods: besides the identity's AID, it carries only a padded Merkle root. A witness that answers batched queries through a relay learns which identities someone is interested in. Over time, those identities add up to a set of contacts, though the witness does not learn which pod connects them. Where Tellipod runs both the relay and the witness, Tellipod can combine what the relay sees with what the witness learns. The recovery service ties an email address to an encrypted key, and the email provider learns that the user has a Tellipod recovery enrolment. A person may need a persona that neither pod members nor Tellipod can connect to the person's other identities. Such a persona uses another external co-signer or none, and another email address or the paper.

**Why.** The co-signer must read rotations to enforce its rules, and the witness must see what it receipts. Pods stay out of the identity's KEL (DR-13), so nothing about pods reaches Tellipod.

**Example.** Tellipod sees that Alice linked a third device on Tuesday. Tellipod does not see that she is in the Tokyo pod.

## Personas and privacy

### DR-34. Separate identities are opt-in, as personas

**Decision.** A person may want to keep contexts that pod members cannot connect to each other through any identifier. Such a person creates another identity, called a persona, on the same devices. There is no separate identifier for each pod.

**Why.** A separate identifier for each pod would repeat every device link, revocation and recovery in every pod. Personas put the cost only on the people who want them.

**Example.** Alice keeps 2 identities on her phone and her laptop: "Alice" for her family pods, and the persona "Alice-work" for her colleagues.

### DR-35. Several identities on one device

**Decision.** One device can host several identities. Each identity has its own device AID and its own iroh endpoint key on that device.

**Why.** A person may keep separate identities (DR-34). If the identities shared an iroh endpoint key, that key would be a permanent identifier that connects them for anyone who is in pods with both identities.

**Example.** Alice's phone hosts both "Alice" and "Alice-work", so it holds 2 device AIDs and 2 iroh endpoint keys.

### DR-36. A persona hides identifiers, not the network or Tellipod

**Decision.** A persona has its own AID and KEL, its own device AIDs, its own iroh endpoint keys and its own recovery backend, which for a paper user is its own sheet. No identifier therefore connects the persona to another persona. A persona does not hide the shared IP address, device changes that appear in several KELs on the same day, habits of writing, or the connections that Tellipod can see through the co-signer and through a shared recovery email address. These limits are accepted.

**Why.** The design cannot fully keep pod members from connecting personas in any case, since iroh exposes the same IP address. The design can still keep its own identifiers from connecting personas outright.

**Example.** Bob is in pods with both "Alice" and "Alice-work". He sees 2 unrelated AIDs and 2 sets of device AIDs, but the same IP address. Linking Alice's new tablet asks her twice, once for each persona.

### DR-37. The number of devices is visible

**Decision.** Each KEL, and the device AIDs that sign records, show how many devices an identity has and how often those devices change. The design does not hide that information.

**Why.** Hiding the number of devices would take group signatures or ring signatures, which KERI's standard encoding does not offer. Pod members see which device signed each record in any case.

**Example.** Bob can tell that Alice writes from 3 devices and linked a new one last month.

## Membership basis

Pod membership will get a specification of its own. The decisions in this section are the basis of that specification.

### DR-38. Membership lists identities

**Decision.** Pod membership lists identities, by their AIDs, and never devices or device keys. A device that an identity links after the identity has joined a pod reaches the pod without any act of the other members.

**Why.** Operations on membership concern people, while data is synced between their devices.

**Example.** Alice links a tablet after joining the Tokyo pod. The tablet syncs the pod at once, and Bob does nothing.

### DR-39. Membership acts are records, without a TEL

**Decision.** A membership act, which adds or removes a member, is a record that one device AID signs and that is written into the pod's membership store. A membership act is never anchored by a rotation, and it uses no ACDC registry (TEL). If a membership act takes the ACDC format, its issuer is the device AID. The rule that such a record is the identity's act is our own rule: standard KERI tools verify the record's signature, not the identity behind it. The membership specification chooses between ACDC and a format of our own. ACDC has one known problem. The ACDC specification's form without a registry still anchors each credential in the issuer's KEL. For a device AID as issuer, that means one interaction event for each membership act, so the device AID's KEL would grow with activity. Membership acts, by contrast, are signed and not anchored. A removed member's later acts are rejected by their position (DR-40). The non-repudiation of a membership act rests on 3 things: the device AID's signature, the check that the device is linked, and, after a revocation, a stamp from before the revocation or an admission (DR-20). Concurrent acts of several owners are ordered by the pod's own merge rule.

**Why.** Membership acts are frequent, so a rotation for each act is unacceptable. A KEL, and a TEL anchored in that KEL, have one writer. An identity, however, has several devices that write concurrently and offline, and a pod has several owners. A registry for each device would make memberships issued by a device that is no longer linked impossible to withdraw. One registry shared by all devices would fork whenever 2 of the devices write at once. A TEL could not order the acts of different owners anyway.

**Example.** Alice's phone, offline on a plane, removes Carol from the Tokyo pod. At the same time, Alice's laptop at home adds Dave. Both acts are records in the membership store, and nothing forks.

### DR-40. A removed member is kept out by position

**Decision.** A removal is a record that lists records of the removed member. For each device of the removed member and each branch of that device's chain, the removal lists the newest record that the remover holds. Of the removed member's records, only those in the history of a listed record are accepted (DR-17). Honest devices stop syncing with the removed member's devices once they hold the removal. This has a cost. Suppose that the removed member honestly wrote a record that the remover had not yet received. That record is rejected everywhere. Whether such a removal can be corrected later is for the membership specification to decide. Membership runs in intervals. A re-add is a record that starts a new interval. In the new interval, each device of the member first writes a record that names the re-add record. From each device, only the record that names the re-add record, and the device's records after it, are accepted in the new interval. Records written while the member was out are never accepted.

**Why.** The goal is that a member removed by an owner can no longer write records in the pod. No anchor can prove that a record did not exist. Without a limit by position, a removed member could write a new record and claim that it came before the removal. Without intervals, a removal would keep a member out for good, even after the member is invited back. A record that names the re-add record shows that it was written after the member was re-added.

**Example.** Alice's laptop holds the records of Bob's phone up to #40, and the laptop removes Bob from the pod. The removal lists #40 for Bob's phone. Bob's phone then writes #41 and claims that #41 came before the removal, but #41 is rejected. No record of Bob's tablet is accepted, since the laptop held none of them. A month later, Alice re-adds Bob with her record A90. Bob's phone then writes #43, which names A90, so #43 and every later record of the phone are accepted. #41 and #42 were written while Bob was out, and they come before #43, so they are not accepted. The records of Bob's tablet are accepted from the tablet's first record that names A90 onwards. In a separate case, after the removal, Bob's phone shows a second, different record at position 39. That record lies outside the history of #40, so it is rejected. The 2 records at position 39 prove a fork. The fork marks Bob's phone as compromised (DR-22).

## Accepted risks

### DR-41. Accepted risks

**Decision.** 9 risks are accepted rather than designed out:

- A thief who holds a device and the user's PIN takes the identity for good. With the Tellipod co-signer, the stolen device and the co-signer link a device of the thief's own. The stolen device and the thief's device then drop the co-signer, and they replace or drop the recovery key without any wait. All of this takes minutes and needs only stock software. With the recovery service, the thief passes the email check in the stolen phone's own mail app, and releases the recovery key with the PIN.
- A thief who takes 2 devices at once, with their unlock secrets, holds 2 of the parties that a rotation needs.
- A thief who holds a sole device and its unlock secret owns the identity.
- A thief who takes a phone with a signing session open, or who knows its passcode and opens signing sessions, signs records until the signing session ends or the device is revoked. Those records become the identity's when a stamp from before the revocation covers them.
- A thief who holds the phone of a single-device user, and the phone's passcode, can request the reset for a forgotten PIN (DR-28). The thief takes the identity if the user does nothing for 30 days.
- Malware that runs inside the app's process signs records without a prompt while the record-signing key's window is open. On Android, the window stays open for at most 1 hour. On iOS and macOS, the app itself enforces the hour, so such malware signs until the device locks.
- A user may disown her most recent records: those that her device wrote since its last stamp. For a modified app that never requests stamps, or for a witness of the user's own that refuses them, these are at most the records of the last 7 days (DR-20).
- A witness that reports an out-of-date position issues stamps that cover a thief's records written after the revocation. Those records then become the identity's.
- A recovery rotation can move the identity to a new witness without the old witness's receipt (DR-16). The old witness can still issue stamps at its last position. Those stamps look as if they came before every later revocation, the recovery rotation itself included. Devices send new events to former witnesses as well. An honest former witness receipts the move. Its later stamps then give the position of the move, where the KEL lists the new witness, so those stamps no longer count. A former witness that does not learn of the move, or that is hostile, can issue stamps that cover a thief's later records.

**Why.** Stealing a device together with the user's PIN is unlikely. A compromise of the app is a compromise of the device on every platform. The device lock bounds such a compromise in time. On Android, the Keystore's 1-hour window bounds it as well. Both risks that involve a witness fall mainly on the user, because the thief's records become the user's. The effects of those records in a pod, such as the removal of a member, last until the user repairs them with ordinary pod acts. The 30-day reset is the price of a way out for a user who forgot the PIN. The email notice gives the user the whole 30 days to recover on a new phone with the PIN that she still knows. User presence for every rotation means that an unattended, unlocked device is not enough, and presence once per signing session keeps records easy to sign.

**Example.** A thief watches Alice type her PIN on the train, and then steals her phone. At 9:00, the stolen phone and the co-signer link the thief's laptop. At 9:02, the stolen phone and the thief's laptop drop the co-signer. At 9:03, the same 2 devices replace Alice's paper with a sheet of the thief's own. In another case, a burglar takes Alice's phone and laptop from her bag, and knows how to unlock both. The burglar needs no Tellipod PIN. The 2 devices together rotate Alice's paper out.

## Deferred

- **The linking ceremony** — how a new device and an existing device find each other, how each one confirms the other, and what happens when the ceremony is interrupted.
- **Pod invite and join via QR code** — how a newcomer first obtains a member's AID and KEL, and what an invite carries.
- **How a revocation reaches other members' devices** — how peers pass new KEL events on, and how fast. The 24-hour freshness bound, with its fallback to the witness, is already decided (DR-15).
- **Tools and Services** — including the restricted identity that a Service uses. Tools have no identity of their own.
- **Organizations** as identities.
- **A passive co-signer** — a co-signer key kept in an encrypted file, in storage that the user picks. A related option is recovery through delegation: a recovery AID delegates the identity's AID, signs approvals with the passive co-signer's key, and holds the offline recovery key as its next key.
- **Apache 2.0 KERI building blocks as dependencies** — whether the implementation may depend on cesride for the encoding, or whether everything is written from scratch. The licenses of cesride and parside still have to be checked.
- **The membership specification** — the format of membership acts, what owners may do, the merge rule for concurrent acts of several owners, and the lifecycle of a pod's membership store. It also has to decide whether a removal can be corrected when it lists fewer records of the removed member than a device of the remover's identity held. For example, Alice's laptop holds Bob's record #40, and her phone, which lags behind, removes Bob while it holds only #35. If the removal is corrected, Bob's records #36 to #40 are accepted.
