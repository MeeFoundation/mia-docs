---
status: proposed
date: 2026-10-27
---
# KERI identity layer — architectural decisions

Draft for review. Each record states one decision, why it was taken, and usually an example; a "To verify" line marks a point still to be checked against the KERI specification, a platform or the sync engine. Numbers run through the whole document; the headings only group related decisions. Deferred topics are listed at the end.

## Terms

- **PDN** — Private Data Network, the platform; data moves between devices over iroh.
- **Tellipod** — the product: the PDN plus the Android, iOS and desktop apps.
- **Pod** — a shared space with many members, usually about one topic, such as "planning a trip to Tokyo".
- **Identity** — a person, known to others by one KERI identifier.
- **AID** — KERI's autonomic identifier: a self-certifying identifier bound to a key event log.
- **KEL** — key event log: the signed, hash-chained sequence of an AID's key events.
- **Establishment event** — an inception or a rotation: an event that sets the current keys and commits to the digests of the next ones (pre-rotation).
- **Interaction event** — a KEL event that changes no keys and anchors data, such as a digest.
- **Weight and threshold** — each key carries a weight; an event is valid when the weights of its signers reach at least the threshold, here 1.
- **Partial rotation** — a rotation that uses some of the committed next keys and carries the commitments of the others forward unchanged.
- **Digest seal** — a digest of some data, anchored in a KEL event, which fixes that data without putting it in the KEL.
- **Escrow** — where a validator holds an event it cannot validate yet, such as one that arrived before its predecessor.
- **Delegation** — an AID whose inception and rotations are valid only when its delegator anchors them in its own KEL.
- **Witness** — a server named in an AID's KEL that receipts its events and refuses to receipt a second event at a position it has already receipted.
- **Keys of a device** — four kinds: its key in the identity's key set (P-256, in hardware, signs rotations); its device AID's keys (P-256, in hardware, sign claims and the iroh key binding); its iroh endpoint key (Ed25519, in memory while the node runs, stored wrapped; its network identity); and a wrapping key in hardware, whose type follows the platform, which only encrypts the iroh key at rest.
- **Device AID** — a device's own AID, delegated by the identity's AID, one for each identity on the device.
- **Claim** — a statement one device signs as issued by its identity; pod data, never a KEL event.
- **Entry** — a record in a pod, signed by the device that wrote it.
- **Co-signer** — the second party of a rotation: another device of the user, the Tellipod service, or a co-signer node the user hosts. An **external co-signer** is one that is not a device of the user: the Tellipod service or a self-hosted node.
- **Recovery key** — a key of weight 1 held by the Tellipod recovery service or written on a paper sheet.
- **Role statement** — a public statement, anchored in every establishment event, naming the role of each key: recovery, co-signer or device.
- **ACDC and TEL** — KERI's format for verifiable credentials (Authentic Chained Data Container), and the log that records whether each credential is issued or revoked (Transaction Event Log).
- **Seen heads** — the newest entry of each other device that an entry's author holds, named in the entry.
- **Acknowledgement** — an entry of one device naming an entry of another device in its seen heads, which shows that the first device held it.
- **Cut-off** — in a pod, the highest entry of a revoked device that another device of the same identity acknowledged, or for a removed member the head the removal names; only entries in its history count.
- **Enclave** — a hardware-protected area of a server's processor whose memory and code the server's operator cannot read or change; the trust that remains lies with the chip vendor and the machine's physical security.

## Identity and devices

### DR-1. KERI is the identity layer, in its standard encoding

**Decision.** Every identity is a KERI AID. Its KELs use KERI's standard encoding (CESR), so existing KERI implementations can verify them — for P-256 signatures, those that follow keripy (DR-8). Anything this design adds — role statements, for example — travels as data inside conformant events or as a rule applied on top of them, never as a change of the encoding.

**Why.** A self-certifying identifier makes an identity independent of any server, and the standard encoding keeps every KEL checkable by tools the project did not write.

**Example.** keripy, given Alice's KEL, computes the same current keys as Bob's phone does; it parses Alice's role statement as data and ignores its meaning.

### DR-2. One identity across all of a person's devices

**Decision.** A person is one identity with one AID on all their devices. Linking a device, revoking one and rotating keys never change the AID.

**Why.** Pod membership and claims name the person, not the hardware. A new phone must not turn Alice into a new member of every pod.

**Example.** Alice replaces her phone. Her pods still list the same AID, and Bob notices nothing.

### DR-3. Our own KERI implementation, limited to the subset in use

**Decision.** The project implements KERI itself, under Apache 2.0, covering only what this design uses: inception and rotation with partial rotation and weighted thresholds, the establishment-only configuration, delegated inception and rotation, interaction events and digest seals in device AIDs' KELs, witness receipts, and the escrows these need. The identity's KEL needs neither interaction events nor KERI's superseding recovery. ACDC registries (TEL) are out of scope. Conformance is checked in both directions against test vectors generated with keripy, the reference implementation (Apache 2.0), which serves as an outside test oracle: its code never enters the product.

**Why.** keriox, the existing Rust implementation, is under the EUPL, which an Apache 2.0 project cannot take in; the design needs only the subset listed.

**Example.** A test feeds a KEL that keripy produced into our validator, and a KEL ours produced into keripy; both must reach the same key state.

### DR-4. Every device does the full KERI work itself

**Decision.** Each device validates KELs completely — including escrows for events that arrive out of order, are partially signed or wait for a delegator's approval — is reachable over iroh, and checks the copies of KELs it receives. There is no cloud agent of the kind KERI's Signify client relies on, where the KERIA agent keeps the user's KELs and mailbox in the cloud. The escrow is capped per identity and per sender, since events that cannot be validated until a gap fills could otherwise fill the device's storage.

**Why.** The platform is local-first, and KELs are small enough for a phone (DR-15). The cost moves to a complete, correct KERI implementation on the device, not to storage or compute.

**Example.** Bob's phone receives Alice's rotation 7 before rotation 6; it holds 7 in an escrow until 6 arrives, then validates both. A pod member who sends events for Alice's positions 900 to 5,000 fills only Alice's share of the escrow and that member's own, and the rest are dropped.

### DR-5. Several identities on one device

**Decision.** One device can host several identities. Each identity has its own device AID and its own iroh endpoint key on that device.

**Why.** A person may keep separate identities (DR-36). A shared iroh endpoint key would be a permanent identifier linking them for anyone in pods of both.

**Example.** Alice's phone hosts "Alice" and "Alice-work": two device AIDs and two iroh endpoint keys on one phone.

### DR-6. Each device has its own delegated AID

**Decision.** Each pair of an identity and a device has a device AID, delegated by the identity's AID. The rotation that links the device anchors the device AID's inception; the identity's inception anchors the first device's. The device AID signs the device's claims and anchors its iroh key binding; its KEL allows interaction events. Rotating a device AID's own keys needs the identity's approval in a two-party rotation (DR-10), which is rare, since a compromised device is revoked instead. KERI also lets a compromised rotation of a device AID be superseded: the device AID's pre-committed next keys sign a replacement at the same position, and the identity approves it in a later rotation; this works only for the latest compromised rotation.

**Why.** A device signs claims all day, while its key in the identity's key set is single-use and changes at every rotation. The device needs a key it can use repeatedly and a name that stays the same across the identity's rotations — for its entries, its iroh key binding and its revocation.

**Example.** Alice's rotation 3 adds the laptop's key to her key set and anchors the inception of `E-laptop`. At rotation 4 the laptop's key in the key set changes; `E-laptop` stays, and its claims in the Hiking pod keep their author.

### DR-7. The iroh endpoint key is separate and bound by the device AID

**Decision.** A device's iroh endpoint key (Ed25519) is separate from its KERI keys. It is bound by an interaction event in the device AID's KEL, and through the device AID to the identity. The secret is stored encrypted under a separate, non-exportable wrapping key in the hardware — the Secure Enclave, the Android Keystore, a TPM; its type follows the platform, and it signs nothing — unwrapped into memory when the node starts, and kept out of backups where the platform allows; the wrapping key asks for no user presence, since background sync runs without the user. On a device with no such hardware, the secret is a file kept out of backups.

**Why.** If the endpoint key were a KERI key, every rotation would change the device's network identity and break the connections and tickets that name it. Binding it in the device AID's KEL needs no second party. Pod sync admits a device by this key, so as a plain file in app data it would travel with every backup, and whoever stole one would read every pod as that device, with nothing signalling a second endpoint.

**Example.** The laptop's first interaction event binds its iroh key. Alice's later rotations leave that binding untouched. Mallory obtains Alice's Time Machine backup; it holds only the wrapped secret, useless without the Mac's Secure Enclave, while a restore onto the same Mac unwraps it as before.

### DR-8. Hardware-bound keys on P-256

**Decision.** A device's key in the identity's key set and its device AID's keys are P-256 keys, bound to the device's hardware where it has any, and never leave the device. Recovery keys are software keys. Conformance for P-256 signatures is keripy-level, and the gap in the CESR specification is tracked or pushed upstream.

**Why.** P-256 is the curve that the iOS and macOS Secure Enclave, Android StrongBox and TPMs have in common; the Secure Enclave offers no Ed25519, and hardware binding outweighs conformance with the specification's table. A recovery key is typed into whichever device recovers, so it cannot be bound to one. The CESR specification defines P-256 keys and plain signatures, but its table of indexed signatures — the kind KERI controller signatures use — has no P-256 entry; keripy, the reference implementation, defines them.

**Example.** The laptop's keys live in its TPM; the paper sheet's key is derived from the 24 words on the device that recovers.

### DR-9. Device AIDs have no witnesses; a forked device is treated as compromised

**Decision.** Device AIDs name no witnesses. If two records at one position appear in a device's own records — its device AID's KEL or its hash chain of entries in a pod (DR-35) — the branch of an entry chain that another device of the identity acknowledged counts and the other is rejected — if neither is acknowledged, neither counts — and the entries before the fork are untouched. The device is treated as compromised: honest devices stop syncing with it and accept no new entry from it, and its identity's other devices alert the user, until the identity revokes it. To avoid an honest fork, a device asks pod peers for its own newest entries after starting, before it signs in that pod, and for its device AID's KEL before an interaction event; on iOS and macOS a durable counter is kept as a keychain item of class `WhenPasscodeSetThisDeviceOnly`, which is never backed up and so disappears together with the Secure Enclave key, while a plain `ThisDeviceOnly` item would roll back with a same-device restore. A device that writes while no peer is reachable writes at once, as local-first requires, and catches up when one is; a fork the guard misses costs the device its linking: it is revoked and linked again.

**Why.** Only interaction events of a device AID can fork, since its key changes need the identity's approval. An honest device forks only when its state rolls back while its hardware key survives — a desktop restored from a backup or a snapshot; on Android, uninstalling or clearing the app deletes its keys together with its data. Whatever ever left the device sits with a peer, so asking peers reveals the true position. The fork rule is our own: KERI itself, on duplicity, distrusts an identifier as a whole or lets each validator keep its own first-seen copy.

**Example.** Alice restores her Mac's app data from last week's Time Machine backup; the Secure Enclave key survived. The app thinks its last entry in the Tokyo pod is #300, but Bob holds #340. On start it asks the Tokyo peers, learns #340, and writes #341, not a second #301.

## The identity's key event log

### DR-10. The identity's KEL holds rotations only

**Decision.** The identity's KEL uses KERI's establishment-only configuration, set in the identity's inception (`"c":["EO"]`), the only place KERI allows it: an inception and rotations, no interaction events. Linking a device is a rotation that adds its key; revoking one is a rotation that drops it. Each rotation is signed by any two parties, by a sole device (DR-12) or by a recovery key, and is final once accepted. While no second party is reachable, linking waits. Whatever must be anchored in this KEL costs a two-party rotation, so frequent records — claims, membership — are never anchored there.

**Why.** No single device writes to the identity's KEL, so a thief holding one device changes nothing in it and no single device can fork it. KERI defines the configuration: "Only establishment events MUST appear in this KEL".

**Example.** Alice links a tablet from her phone; her laptop shows "approve the tablet?", she approves, and the rotation adding the tablet's key is final.

### DR-11. Any two parties can rotate

**Decision.** Every device carries weight 1/2, the external co-signer — Tellipod's or a self-hosted one — 1/2, and each recovery key 1; the threshold is 1. An identity without an external co-signer has no such slot, and a sole device without one carries weight 1 (DR-12). Otherwise the weights do not depend on the number of devices. KERI expresses them as one clause of fractional weights, such as `["1/2","1/2","1/2","1","1"]`, satisfied when the weights of the signers sum to at least 1; no weight may exceed 1.

**Why.** No device is special: any two parties agree on a change, losing any one device leaves the rest working, and the co-signer's operator alone (1/2) can never rotate an identity.

**Example.** Alice has a phone, a laptop and the Tellipod co-signer. Phone and laptop make 1, phone and co-signer make 1, the co-signer alone is 1/2, the paper alone is 1.

### DR-12. A sole device carries weight 1

**Decision.** While an identity has one device and no external co-signer, that device carries weight 1. The rotation that links a second device weights both at 1/2; a revocation that leaves one device weights it back to 1. Identities with a co-signer need no special case.

**Why.** Every user without a co-signer links a second device at some point; without this, that routine act would need the recovery key, costing a paper user a new sheet and exposing the recovery key on a device. The risk — whoever holds the sole device and its unlock secret owns the identity — is accepted (DR-31), and user presence for every rotation (DR-17) keeps an unlocked phone lying on a table from being enough.

**Example.** Alice creates her identity on her phone (phone 1, paper 1). She links her laptop by scanning its QR code and confirming on the phone (phone 1/2, laptop 1/2, paper 1).

### DR-13. The current-key threshold mirrors the next-key threshold

**Decision.** In every establishment event, each current key carries the weight its role has in DR-11 and DR-12, with threshold 1.

**Why.** KERI requires it: "the set of signatures on a Rotation event MUST satisfy two thresholds. These are the newly current threshold and the old prior next threshold from the most recent prior Establishment event." A rotation's current-key list holds the keys it exposes and may add keys that were never pre-rotated. The identity's current keys sign nothing but rotations, so mirroring the next threshold makes whatever satisfies one satisfy the other.

**Example.** The laptop and the Tellipod co-signer link Alice's tablet: the rotation lists the laptop and co-signer keys as current, 1/2 each. A recovery rotation by the paper lists only the paper's key, at 1.

### DR-14. An offline device stays in the key set

**Decision.** A rotation carries forward, unchanged, the next-key commitment of every device that stays in the key set but does not sign it.

**Why.** A rotation must not need every device present; a switched-off desktop has to stay usable. Since a device's key in the key set signs rotations only, carrying its commitment forward is all it needs. KERI allows it: "A Partial rotation operation on a set of pre-rotated keys MAY hold back some as unexposed while exposing others as needed".

**Example.** Alice's desktop is off while her phone and laptop link a tablet. The rotation repeats the desktop's commitment, and the desktop signs a later rotation with the key it committed.

### DR-15. KELs stay small and are stored once per identity

**Decision.** The identity's KEL records identity acts only — device links and revocations — never pod membership, pod data or claims. A device stores one copy of each KEL it knows, shared by every pod it is in.

**Why.** The KEL then grows with device changes, not with activity, and storage grows with the number of people a device knows, not with the number of pods. Estimate, to be replaced by measurement: about 16 KB after three years of ordinary use, 64 KB for a heavy user, so 100 pod members' KELs come to about 2 MB to 6 MB and are checked for the first time in under a second on a phone.

**Example.** Bob is in three pods with Alice; his phone keeps one copy of Alice's KEL.

### DR-16. Every establishment event names the role of each key

**Decision.** Every establishment event anchors, by a digest seal, a public role statement that names the role of each key: recovery (paper or service), co-signer, or device. The statement is KERI self-addressing data — CESR-encoded and carrying its own digest — and travels with the KEL. A rotation whose role statement no longer names a device AID is that device's revocation (DR-33). Rules read the roles of a rotation's signers from the previous establishment event.

**Why.** KERI validation sees only positions and weights, and defines no roles. Our rules need them: a rotation signed with a recovery key may change the witness with the new witness's receipt alone (DR-30), while a sole device carries weight 1 as well, and the co-signer must know which commitment is the recovery key's. Reading roles from the previous event keeps a thief from relabelling their way into recovery within the rotation that uses it. The statement reveals nothing new: the number of devices is visible anyway (DR-38).

**Example.** Alice's event 8 anchors "key 0: recovery (paper), key 1: recovery (service), key 2: co-signer, keys 3 and 4: devices `E-phone` and `E-laptop`". Event 9 may move Alice to another witness without the old one's receipt only if it is signed with key 0 or key 1.

## Signing and presence

### DR-17. Two strengths of signature, two levels of presence

**Decision.** Day-to-day acts are claims, signed by one device with its device AID's key. Linking and revoking a device are rotations of the identity's KEL, signed by any two parties, by a sole device or by a recovery key. A rotation asks for the user's presence (fingerprint or device passcode) at every signature; the claim key asks for it once per session and then signs freely until the session ends — when the app or the device locks, or after a period of inactivity, a product setting. On Android the key stays usable for a set time after authentication (`setUserAuthenticationParameters`); on iOS and macOS one authenticated `LAContext` authorizes the signatures until the app invalidates it, so the app ends the session itself. The hardware bounds what the app enforces: the claim key is unusable while the device is locked, and its window lasts at most 1 hour after the last authentication, after which the app asks again.

**Why.** A fingerprint before every claim would be too much; one at the start of a session is acceptable. The session itself is the app's rule — on Android a lock-screen unlock also opens the key's window, and the window runs on its own timer — so the hardware limits keep a locked phone from signing anything and a stolen, unlocked one from signing for more than an hour; one prompt an hour at most is the price. Rotations change who controls the identity, so every one of them needs the user present, on both devices.

**Example.** Alice opens Tellipod in the morning and touches the sensor once; she writes in three pods all day without a prompt. Linking her new tablet in the evening asks for her fingerprint again, and so does her laptop, which co-signs.

**To verify.** Windows: Windows Hello has no stable, documented timed mode, only a prerelease cache configuration (`KeyCredentialCacheConfiguration`); until it is tested, a Windows device may have to ask for presence at every claim.

### DR-18. Nothing is signed without the user present

**Decision.** No device signs an entry outside a session. Whatever the app would write on the user's behalf waits for the next session. Background sync continues: it moves entries others signed and authenticates with the iroh endpoint key, which signs no entries.

**Why.** Every entry an identity signs is binding (DR-33); signing only with the user present keeps the number of acts nobody chose small.

**Example.** A reminder Alice set to post in the Tokyo pod at 7:00 is posted when she next opens the app at 8:15.

### DR-19. A claim is pod data, verified against two KELs

**Decision.** A claim is signed by one device AID and stored as pod data, never as a KEL event. A verifier checks the signature against the device AID's KEL at the key state the claim names, and checks in the identity's KEL that the device AID was linked and, if the device has since been revoked, that another device of the identity acknowledged the claim (DR-33).

**Why.** Claims are frequent; keeping them out of the KEL keeps the KEL small and leaves the identity's keys single-use.

**Example.** Bob's phone verifies Alice's laptop's message in the Hiking pod against `E-laptop`'s KEL and against Alice's KEL, which anchors `E-laptop`'s inception and no unlinking.

## Recovery

### DR-20. Recovery: the Tellipod service by default, a paper sheet, or both

**Decision.** An identity commits a recovery key held by the Tellipod recovery service, one written on a paper sheet, or both. Each has weight 1, so either alone recovers. The service is the default; a person who does not want to rely on Tellipod uses the paper.

**Why.** Recovery must outrank a stolen device whose PIN the thief does not know — a thief who has both is an accepted risk (DR-31) — and restore an identity whose devices are all lost. With both, the identity survives the loss of either backend; the price is exposure to the theft of either, since the first recovery can drop the other backend's key.

**Example.** Alice's next keys: phone 1/2, laptop 1/2, co-signer 1/2, service 1, paper 1. A burglar who finds the paper owns the identity even though Alice still knows her PIN.

### DR-21. The recovery service is non-custodial

**Decision.** The Tellipod recovery service stores the recovery key encrypted and releases it only after the user's email check and recovery PIN, checked inside an enclave (DR-26). The phone that recovers signs the recovery rotation itself and stores a newly generated recovery key with the service. A user who has lost the PIN and every device has lost the identity. The service stores the encrypted key under a random identifier and need not learn the AID. It erases a recovery key only on a request signed by the identity's current devices, never because of wrong PINs (DR-27), and it notifies the enrolled email of every failed attempt.

**Why.** A service holding a usable recovery key (weight 1) could rotate any identity alone: its operator, an intruder, or a legal order served on it. The service does hold personal data — an email address linked to an encrypted key — which links two identities recovering through the same email for Tellipod.

**Example.** Alice loses every device. On a new phone she confirms her email and types her PIN; the phone receives the key, signs the recovery rotation and enrols a fresh recovery key.

### DR-22. The paper sheet: 24 words, recovery only

**Decision.** The paper sheet is one generated passphrase of 24 words from the BIP-39 English word list of 2,048 words. The words seed one recovery key, whose commitment is carried forward from rotation to rotation until it is used. Every use ends with a new sheet. There is one sheet, not a threshold of several, kept in one safe place. The paper serves recovery only, never as a stand-in for a second party at linking. Each identity gets its own sheet.

**Why.** 24 words carry 256 bits of randomness plus a checksum that catches most typing mistakes. Typing them exposes the key, hence a new sheet after every use. Using the paper for routine linking would expose it on devices that may be compromised, while linking can simply wait for a second party.

**Example.** Alice, without an external co-signer, loses her phone; her laptop alone carries 1/2. She types the 24 words on the laptop, which signs a recovery rotation that drops the phone, weights the laptop at 1 and commits a fresh passphrase; Alice writes down the new 24 words and destroys the old sheet.

### DR-23. Replacing a recovery key, or a forgotten PIN, waits

**Decision.** Replacing a recovery key while devices remain — switching from the service to the paper, a new service key after a forgotten PIN, a new sheet for a lost one — needs the agreement of a majority of the identity's devices, which the external co-signer checks, and is then held by the external co-signer for 30 days while it notifies every device; a recovery rotation during the period cancels it. Without an external co-signer, two devices or a sole device replace it at once. A forgotten PIN is reset the same way, without the PIN: a majority of the identity's devices — for a single-device user, that device alone — request a new PIN and a new recovery key, and the co-signer holds the request for 30 days while it notifies every device and the email address; any act during the wait that uses the current PIN or a recovery key cancels it. The same path lifts any delay on the co-signer path.

**Why.** "I lost my paper" is also what a thief would claim, and KERI's threshold cannot express a majority of the devices, since one device plus the co-signer already meets it. For a user with one phone, that phone is the majority, so the rule alone would not stop a thief. The wait makes a thief keep a stolen phone unnoticed for the whole period, while an owner who really lost a phone recovers within it. It does not stop a thief who holds a device and its PIN: such a thief links a device of their own and rotates with two devices, which needs no wait (DR-31). Without the reset, every route back goes through the PIN: replacing the service key needs the co-signer, and the co-signer needs the PIN, so a single-device user who forgot it could never link a device or change recovery again.

**Example.** Alice loses her paper. Her phone and laptop ask for a new sheet; the co-signer holds the request for 30 days and notifies both devices and her email, and on day 31 the new sheet's key is committed. Had a thief with the phone alone asked, the request would lack the laptop's signature, and the co-signer would refuse it. Separately, Alice, who has only her phone, forgets her PIN: she requests a reset, waits 30 days, sets a new PIN and gets a new recovery key.

## Co-signer and enclave

### DR-24. The co-signer is a role

**Decision.** The second party of a rotation is another device of the user, or an external co-signer: the Tellipod co-signer, or a co-signer node the user hosts on an always-on machine. An external co-signer is a PDN node acting as a Service of the identity, reachable over iroh like any device. An identity names at most one external co-signer; switching is a rotation. Every second party reads the rotation before signing it and asks for its user's presence. A device acting as second party checks in the app that the rotation commits the recovery key again, and refuses a rotation unless it holds the latest KEL. The external co-signer signs only a rotation that commits the recovery key again — except a replacement it holds under DR-23 — and never two different events at one position. While no second party is reachable, linking waits.

**Why.** Users choose whether to rely on Tellipod; another device of theirs can do the job. The rules keep a thief who holds one device and gets a second signature from dropping the recovery key, and keep the identity's KEL free of two rotations at one position.

**Example.** Alice links a tablet with her phone; her laptop shows "approve the tablet?", checks that the rotation keeps her paper's commitment, and asks for her fingerprint.

### DR-25. The Tellipod co-signer lives in an enclave

**Decision.** The Tellipod co-signer's signing key is generated inside an enclave and never leaves it; the enclave signs only after the PIN check — or, for a reset of a forgotten PIN, after its 30-day wait (DR-23) — and enforces the rules of DR-24. Witness receipts may be produced outside the enclave. A self-hosted co-signer needs no enclave.

**Why.** Otherwise Tellipod's operator could co-sign without the PIN, and an operator colluding with a thief who holds Alice's phone could drop her paper. A dishonest receipt is detectable without the enclave, since two receipts at one position are evidence in themselves.

**Example.** A Tellipod admin, bribed by the thief who took Alice's phone, asks the co-signer to sign a rotation dropping her paper. The enclave refuses for want of the PIN, and with the PIN it still refuses, since the rotation does not commit the recovery key again.

### DR-26. One PIN, checked in an attested enclave

**Decision.** The Tellipod co-signer and the recovery service share one PIN, checked in one enclave-backed service modelled on Signal's secure value recovery. Before sending anything, the app checks the enclave's attestation: signed by a key built into the processor and certified by the chip vendor, naming the hash of a public, reproducible build, and showing firmware the vendor has not revoked. The app sends the PIN stretched with Argon2 over a channel that ends inside the enclave. Splitting the secret and the guess counter across enclaves of different chip vendors at different cloud providers, or across independent operators, is a desirable enhancement. A self-hosted co-signer checks its own, separate PIN with OPAQUE.

**Why.** A short PIN is safe only if nobody can guess it offline — including the operator. A password protocol such as OPAQUE alone keeps the PIN off the wire, but whoever holds the server's stored record tries all 1,000,000 six-digit PINs in seconds. The enclave's hardware enforces the guess limit. Signal's code is AGPL-3.0, so it serves as a design reference only. What remains: the chip vendor, and anyone with physical access to the server, cloud staff included — in 2025 WireTap extracted an SGX attestation key and Battering RAM broke SGX and SEV-SNP attestation, both on DDR4 memory, and TEE.fail extracted SGX and TDX provisioning keys and SEV-SNP keys on DDR5. Rolling the enclave's stored state back would reset the guess counter, so the counter is replicated across several enclaves. AWS Nitro Enclaves attest with AWS's own certificate authority, not a chip vendor's, so they do not qualify.

**Example.** A Tellipod admin copies the PIN database and gets only ciphertext; code without the guess limit fails attestation, so the app sends it nothing.

### DR-27. Wrong PINs delay; they never erase or freeze

**Decision.** The enclave counts wrong PINs separately for each path. On the recovery path, after 10 wrong PINs every further try waits longer — 1 hour, then 2, 4, 8 and so on — and the recovery key is never erased because of wrong PINs. On the co-signer path, wrong PINs are counted per requesting device, with the same growing delays, so failures from one device delay that device's requests only; the identity is never frozen.

**Why.** The email check alone gates the recovery path, and a thief can pass it by reading the code in the stolen phone's own mail app, as can anyone who broke into the owner's inbox. If wrong PINs erased the key, they would destroy recovery without gaining anything; if they froze co-signing for the whole identity, ten bad requests from a stolen phone would keep the owner's other devices and the co-signer from revoking it. Growing delays allow about 23 tries a year, so guessing a six-digit PIN would take about 40,000 years — practically as tight a bound as erasure. A thief cannot link a second device to escape the per-device count, since linking needs the co-signer and the co-signer needs the PIN.

**Example.** A thief with Alice's phone and passcode, but not her PIN, reads the email code on the phone and fails 10 times on the recovery path; her key survives, each further try waits hours, and her mailbox shows the attempts. He then makes 10 bad co-signing requests from the phone; only the phone is delayed, and on Tuesday Alice's laptop with her PIN and the co-signer revoke the phone at once.

### DR-28. What Tellipod learns

**Decision.** For a default user, Tellipod runs the co-signer, the recovery service and the witness. The co-signer reads every rotation it co-signs — the AID, the number of devices, the time — and, for identities whose witness Tellipod runs (DR-29), the witness sees every event of the identity, plus the requesting device's network address unless a relay carries the request. It learns nothing of pods, their members or their data. A witness answering batched queries through a relay learns which identities someone is interested in — over time a contact set, though not which pod connects them — and where Tellipod runs both the relay and the witness it can join the two (DR-29). The recovery service links an email address to an encrypted key, and the email provider learns that the user has a Tellipod recovery enrolment. A persona that must be unlinkable to Tellipod as well uses another external co-signer or none, and another email or the paper.

**Why.** It must read rotations to enforce its rules, and the witness must see what it receipts. Pods stay out of the identity's KEL (DR-15), so nothing about them reaches Tellipod.

**Example.** Tellipod sees that Alice linked a third device on Tuesday; it does not see that she is in the Tokyo pod.

## Witnesses and forks

### DR-29. Every identity has a witness

**Decision.** Every identity names a witness in its own KEL: Tellipod's by default, any other KERI witness provider, or one the user hosts. The witness is separate from the co-signer: it holds no key of the identity and can rotate nothing. A rotation counts only once the witness has receipted it, and the witness receipts only the first event at each position. Identities with different witnesses share a pod, and changing the witness is a rotation (DR-30). A device takes other identities' KELs, receipts included, from pod peers and verifies the receipts offline. It asks a witness directly only for its own identity before writing (DR-34), and for another identity when its copy has not been confirmed within the last 24 hours by a source other than the device it is about to sync with — then through a relay, batched with its other overdue queries. A device never vouches for its own identity's freshness. Every member's device also stores the KELs of the members of its pods, serves them to other devices and compares the copies it receives.

**Why.** Without a party that orders events, no fork rule both converges and protects accepted history: either every device falls back to the same state when it sees two rotations at one position — and then a late rival, signed a year later by keys carried forward since, can undo history that was already accepted — or each device keeps the event it saw first, and members disagree for good about which branch holds. The witness gives the single order: a rival is never accepted, a thief cannot show different histories to different members, and the revocation reaches every member's device within the freshness bound. It sees the identity's KEL — its device changes — never pods. The costs: a witness is required even for users who run no other infrastructure, softened by the free choice of witness; linking and revoking need the witness reachable, so two devices on a local network without internet cannot link a third, while claims are unaffected.

Asking the witness before every session would tell it who checks whom; taking KELs from peers avoids that, and the 24-hour bound keeps a revoked device — itself a peer serving an old, valid KEL — from delaying a revocation for longer.

**Example.** Phone and co-signer link a tablet while laptop and desktop revoke the old phone, both at event 9; the witness receipts only the first, and the second is never accepted. On Tuesday Alice's laptop and the co-signer revoke her stolen phone, and then the laptop and Carol go offline; Bob's phone keeps syncing Tokyo with the phone, whose copy of Alice's KEL cannot vouch for itself; the last copy from anyone else is 20 hours old, so 4 hours later Bob's phone asks Alice's witness through the relay, learns of the revocation, and stops syncing with the phone. Alice, who uses no Tellipod co-signer, runs a small witness on her home server instead.

### DR-30. Changing the witness, retries and a misbehaving witness

**Decision.** A rotation that changes the witness needs receipts from the old witness and the new one, except a rotation signed with a recovery key — as the previous establishment event's role statement names it (DR-16) — which needs the new witness only. Every signer stores the new keys and the signed event durably before it releases the event, and resends the same event on a retry. Two receipts by one witness at one position prove that witness's misbehaviour, and the identity moves to another witness by a recovery rotation. Co-signing devices refuse a rotation unless they hold the latest KEL.

**Why.** The recovery exception is the escape from a witness that is down or censors the identity; requiring the old witness otherwise keeps a thief with two devices from moving the identity to a witness of their own unseen by the old one. Saving before sending keeps a device that crashes after the witness receipted its rotation from losing the keys that rotation committed, and from building a second, conflicting rotation. Refusing without the latest KEL keeps a device from signing a rotation the witness will refuse.

**Example.** Alice's new phone signs recovery rotation 13, sends it to the witness, and crashes; on restart it finds 13 and its new keys saved and resends the same 13 instead of building a 13′. When Tellipod's witness is unreachable for a week, Alice's paper signs a rotation that moves her to her home witness.

**To verify.** Which witness set KERI receipts a witness-changing rotation against — the old, the new, or both.

### DR-31. Accepted risks

**Decision.** Six risks are accepted rather than designed out: a thief who holds a device and its PIN takes the identity for good — with the Tellipod co-signer, phone and co-signer link a device of the thief's own, and the two devices then drop the co-signer and replace or drop the recovery key at once, in minutes and with stock software; with the recovery service, the thief passes the email check in the stolen phone's own mail app and releases the recovery key with the PIN; a thief who takes two devices at once holds a quorum; a thief who holds a sole device and its unlock secret owns the identity; a thief who takes a phone with a session open signs claims until the session ends or the device is revoked, and those claims become the identity's once another of its devices acknowledges them; a thief who holds a single-device user's phone and its passcode can request a reset of the forgotten-PIN kind (DR-23) and takes the identity if the owner does nothing for 30 days; code running inside the app — malware in its process, or a thief who knows the passcode and bypasses the app's own session check — signs claims without a prompt while the claim key's window of at most 1 hour is open.

**Why.** Stealing a device together with its PIN is unlikely. App compromise is device compromise on every platform; the hardware window bounds it in time. The 30-day reset is the price of a way out for a user who forgot the PIN; the email notice gives the owner the whole period to recover on a new phone with the PIN she still knows. User presence for every rotation keeps an unattended unlocked device from being enough, and presence once per session keeps claims easy to sign.

**Example.** A thief who watched Alice type her PIN on the train steals her phone. At 9:00 phone and co-signer link the thief's laptop; at 9:02 the thief's two devices drop the co-signer; at 9:03 they replace Alice's paper with a sheet of their own. A burglar who takes Alice's phone and laptop from her bag needs no PIN at all: the two devices together rotate her paper out.

## Revocation and the cut-off

### DR-32. A device syncs a pod only while it is linked and its identity is a member

**Decision.** A device may sync a pod only while its identity is a member of the pod and the device is linked to that identity. Every peer checks both, for its own devices and for other members' devices alike. A revocation must therefore reach every device of every member of the identity's pods. A device that holds its own removal from a pod, or its identity's, stops syncing the pod but keeps its replica, and re-checks the removal whenever the remover's KEL changes; if the removal no longer counts, it resumes syncing.

**Why.** Membership names identities, not devices (DR-39); without the second check, a revoked laptop would keep syncing with Bob's devices. A removal written by a revoked device counts only once another device of the remover's identity acknowledges it (DR-33), and the revocation reaches the removed member through the remover's witness, not through the pod; without the re-check, a thief's removal written after the revocation would cut honest members off for good. The cost: a removed member's device keeps the pod's data until the removal settles.

**Example.** Alice revokes her laptop; once Bob's phone holds the revocation, it stops syncing with the laptop. Another time, Alice's phone is revoked at 10:06, and at 10:07 the thief writes Tokyo #441 from it, removing Bob. At 10:08 Bob's phone holds #441 and pauses Tokyo; at 10:10 it receives Alice's KEL from Carol's phone in Tokyo, sees the revocation, finds #441 acknowledged by none of Alice's devices, and resumes Tokyo.

### DR-33. A revoked device's entries count once another device of the identity acknowledges them

**Decision.** Revoking a device is the rotation that drops its key; that rotation's role statement no longer names the device AID (DR-16). From then on, an entry of the revoked device counts only if another device of the same identity acknowledged it: named it, or a later entry of the revoked device, in the seen heads of an entry that counts itself (DR-35). In each pod the highest acknowledged entry is the effective cut-off, and the revoked device's entries in its history count. Acknowledgements only accumulate, so the cut-off only rises, and replicas holding the same entries agree. After a revocation, each remaining device writes an ordinary entry in each of the identity's pods once it has synced it, which admits the honest entries it holds; this may happen later, as when a new phone finishes syncing after a recovery. In a pod the identity has left or been removed from, the end of its membership is the cut-off, and revocation changes nothing there. A replica drops an entry that no acknowledgement covers and takes it back if one arrives later. After its revocation, a device AID's own KEL carries no weight. Nothing about pods is anchored in the identity's KEL.

**Why.** Non-repudiation: everything a device signed while linked is the identity's, a thief's entries included, and an owner cannot disown it by declaring the device stolen — otherwise a promise made on Tuesday could be disowned on Friday. With no trusted clock, "signed while linked" is shown by another device of the identity having seen the entry, and an ordinary entry already carries that evidence in its seen heads; revocation therefore needs no statement of its own and reveals nothing about the identity's pods. The owner repairs what a thief did with ordinary pod acts, and the record stays. The cost: an honest entry that no other device of the identity ever held is lost.

**Example.** Alice has a phone and a laptop. In the Tokyo pod, with Bob, the phone wrote #1 to #440 — #437 says "I'll pay the hotel deposit, 500 EUR" — and the laptop's entry L80 names phone #440 in its seen heads. In the Ginger pod, with Carol, the phone wrote #1 to #55 and the laptop's G12 names phone #50. In the Hiking pod, with Dave, the phone wrote #1 to #120, the laptop never wrote, and Alice left Hiking in March. The phone is stolen on Monday and the thief writes Tokyo #441; on Tuesday the laptop and the co-signer revoke the phone, and the laptop writes Tokyo L81 and Ginger G13. In Tokyo, #1 to #440 count, the promise included; #441 is rejected everywhere, and Bob's replica, which accepted #441 on Tuesday morning, drops it. In Ginger, G12 alone admits #1 to #50, and G13 admits #51 to #55. Hiking is untouched: its cut-off is Alice's departure, and Dave keeps #1 to #120.

**To verify.** That the sync engine can undo the effects of a dropped entry and redo them when an acknowledgement arrives later.

### DR-34. Acknowledgements win over any cut-off claimed at revocation

**Decision.** Whatever another device of the identity acknowledged counts, even if the revoking parties claim not to have seen it; no cut-off set at revocation overrides an acknowledgement. Before a device writes in a session, it fetches its identity's KEL from the witness, and it syncs with no device of its own identity before that.

**Why.** A verifier cannot tell whether an acknowledgement was written before or after the revocation, so when an acknowledgement goes above a cut-off claimed at revocation, one of the two must win. If the claimed cut-off won, a dishonest owner could disown entries by letting a device with no history in the pod revoke at a low cut-off. With acknowledgements winning, the other members are protected, and the risk falls on the owner: a device of hers that has not yet learned of the revocation may acknowledge a thief's entries written after it, which then become hers. She repairs that with ordinary pod acts — the exposure already accepted for a thief's acts before a revocation, extended until each of her devices learns of it. Fetching the KEL from the witness before writing narrows that window to a device that writes while the witness is unreachable, which local-first operation allows. One gap remains: in a pod where the identity is still a member and none of its other devices ever wrote, a dishonest owner can leave out the admitting entry and disown the revoked device's entries there; other members' copies show it but do not prevent it.

**Example.** Dishonest: to disown #437, Alice links a tablet, which revokes the phone claiming to have seen only #430. The laptop's L80 acknowledged #440, so the cut-off stays #440, and Bob's phone, which holds L80, computes the same. Stale: Alice's desktop is off from Saturday; after the revocation the thief writes #441 to #600, #450 removing Bob from the pod. On Friday the desktop wakes, fetches Alice's KEL from the witness before writing, learns of the revocation and never names #600. Had it written with the witness unreachable, after syncing #600 from the stolen phone, #441 to #600 would have become Alice's, and she would add Bob back.

### DR-35. Entries form hash chains and name what their author has seen

**Decision.** Each device's entries in a pod form a hash chain: every entry carries its sequence number and the digest of the previous one. Every entry names its seen heads — the newest entry of each other device its author holds. Acknowledgements (DR-33) and a member's removal (DR-41) are read from seen heads; only entries in the history of an acknowledged or named head count.

**Why.** A signature or an anchor proves that an entry existed, never that another did not. Position is what lets a verifier reject an entry written later and claimed to be older, or a fork of the chain at an earlier position, without rejecting the honest history around it.

**Example.** The laptop's Tokyo entry L80 names the phone's #440 and Bob's #312, so everything in the history of phone #440 — #1 to #440 — is acknowledged by it. Malware on the phone gives Bob a rival #1′; it lies outside the history of #440, so only #1′ is rejected.

**To verify.** Whether the sync engine's entries can carry hash chains and seen heads, and how to keep seen heads small: every entry names a head for each other device in the pod — about 300 heads, some 12 KB, in a pod of 100 members with 3 devices each — and the heads of revoked or removed devices never drop out. Candidates: naming only the heads that changed since the author's previous entry, and dropping the heads of devices revoked or removed for good.

## Privacy and personas

### DR-36. Separate identities are opt-in, as personas

**Decision.** A person who wants contexts that pod members cannot link creates another identity, a persona, on the same devices. There is no separate identifier per pod.

**Why.** A separate identifier per pod would repeat every device link, revocation and recovery in every pod. Personas put the cost only on those who want them.

**Example.** Alice keeps "Alice" for her family pods and "Alice-work" for her colleagues, both on her phone and laptop.

### DR-37. A persona hides identifiers, not the network or Tellipod

**Decision.** A persona has its own AID and KEL, its own device AIDs, its own iroh endpoint keys and its own recovery backend — for paper users its own sheet — so no identifier links it to another persona. It does not hide the shared IP address, device changes that land in several KELs on the same day, habits of writing, or links visible to Tellipod through the co-signer and a shared recovery email; these are accepted.

**Why.** Full unlinkability from pod members is out of reach anyway, since iroh exposes the same IP address; what the design can do is keep its own identifiers from linking personas outright.

**Example.** Bob, in pods with both "Alice" and "Alice-work", sees two unrelated AIDs and two sets of device AIDs, but the same IP address; linking Alice's new tablet asks twice, once per persona.

### DR-38. The number of devices is visible

**Decision.** Each KEL and the device AIDs that sign claims show how many devices an identity has and how often they change. This is not hidden.

**Why.** Hiding it would take group or ring signatures, which KERI's standard encoding does not offer; pod members see which device signed each entry in any case.

**Example.** Bob can tell that Alice writes from three devices and linked a new one last month.

## Membership basis

Pod membership will get a specification of its own. These records are its basis.

### DR-39. Membership names identities

**Decision.** Pod membership names identities (AIDs), never devices or device keys. A device an identity links after joining a pod reaches the pod without any act of the other members.

**Why.** Operations on membership concern people; data synchronization happens between their devices.

**Example.** Alice links a tablet after joining the Tokyo pod; the tablet syncs the pod at once, and Bob does nothing.

### DR-40. Membership records are claims, without a TEL

**Decision.** A membership record — adding or removing a member — is a claim signed by one device AID and written into the pod's membership store. It is never anchored by a rotation and uses no ACDC registry (TEL). If it takes the ACDC format, its issuer is the device AID, and that the record counts as the identity's act is our rule: standard KERI tools verify the signature, not the identity behind it. ACDC or a format of our own is the membership specification's choice, with one known issue: the ACDC specification's form without a registry still anchors each credential in the issuer's KEL — for a device AID one interaction event per record, so its KEL would grow with activity — while these records are signed and kept out by position (DR-41), not anchored. Its non-repudiation rests on the device AID's signature, the linked-device check, and acknowledgement by the identity's other devices after a revocation (DR-33). Concurrent acts of several owners are ordered by the pod's own merge rule.

**Why.** Membership records are frequent, so a rotation for each is unacceptable. A KEL and a TEL anchored in it have one writer, while an identity has several devices writing concurrently and offline, and a pod has several owners: a registry per device leaves memberships issued by an unlinked device impossible to revoke, and one registry shared by all devices forks whenever two of them write at once. A TEL could not order the acts of different owners anyway.

**Example.** Alice's phone, offline on a plane, removes Carol from the Tokyo pod while her laptop at home adds Dave; both are claims in the membership store, with no fork anywhere.

### DR-41. A removed member is kept out by position

**Decision.** A removal is an entry whose seen heads fix the removed member's cut-off, one head per device of theirs; only the removed member's entries in the history of those heads count (DR-35). Honest replicas stop syncing with the removed member's devices once they hold the removal. The cost: an entry the removed member honestly wrote that the remover had not yet received is rejected everywhere. Membership runs in intervals: a re-add is an entry that starts a new interval, in which the member's entries count only if their seen heads include the re-add entry; entries written while the member was out never count.

**Why.** The goal is that a member removed by an owner can no longer issue claims into the pod. No anchor can prove that an entry did not exist, so a removed member could otherwise write a new entry and claim it came before the removal. Without intervals, the cut-off would keep a member who is invited back out for good.

**Example.** Alice's laptop holds Bob's phone entries up to #40 and removes him. Entry #41, written later and claimed earlier, is rejected; a fork #39' is outside the history of #40 and rejected, and the two entries at position 39 prove it; Bob's tablet, of which Alice held nothing, loses all its entries. A month later Alice re-adds Bob with entry A90; his phone writes #43 naming A90 in its seen heads, which counts, while #41 and #42, written while he was out, name no re-add and do not.

## Deferred

- **The linking ceremony** — how a new device and an existing one find each other, how each confirms the other, and what happens when the ceremony is interrupted.
- **Pod invite and join via QR code** — how a newcomer first obtains a member's AID and KEL, and what an invite carries.
- **How a revocation reaches other members' devices** — how peers pass new KEL events on and how fast; the 24-hour freshness bound with its fallback to the witness is decided (DR-29).
- **Tools and Services** — including the restricted identity a service uses.
- **Organizations** as identities.
- **A passive co-signer** — a co-signer key in an encrypted file in storage the user picks, and recovery by delegation over it.
- **Apache-2.0 KERI building blocks as dependencies** — whether the implementation may depend on cesride for the encoding, or everything is written from scratch; the licenses of cesride and parside are to be checked.
- **The membership specification** — the record format, what owners may do, the merge rule for concurrent acts of several owners, the lifecycle of a pod's membership store, and whether, as for device revocation (DR-34), a removal's cut-off rises to every head of the removed member that any device of the remover's identity acknowledged: Alice's laptop has seen Bob's entry #40 and her phone, lagging behind, removes Bob having seen #35 — raised, Bob's #36 to #40 count.
