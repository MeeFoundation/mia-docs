# The directory carries the identity's key events

The directory gains one entry family and loses nothing. Its layout and the reading of it is [kel-store](../data-layer-kel-store/spec.md); what this delta fixes is that key events live here, that their keys cannot collide with the families already present, and that record-level device discovery remains available before payloads arrive without making an unverified record an access credential.

## MODIFIED Requirements

### Requirement: One entry per device, node id in the key
A device SHALL be recorded by an entry at path `devices/<node-id>` (64 lowercase hex chars of the device's `NodeId`). The payload SHALL be treated as opaque by record-level device listing: whether `list_devices` returns the record MUST NOT depend on payload bytes. The payload SHALL carry a complete tagged `DeviceBindingProof` in exactly 1 of 2 variants:

- `Linked` SHALL contain the canonical newcomer-signed request transcript, inviter-signed proof manifest returned for that request, and newcomer-signed confirmation transcript produced after the reply and both bootstrap tickets verify. Together they include the identity root, both device identifiers, both authenticated connection `NodeId` values, nonce, delegated-inception digest, anchor location, both store commitments, and the relevant key-state locations.
- `Created` SHALL contain the exact profile-1 `founder-binding` preimage and 2 signatures over the identical bytes: versions, identity root, founder identifier and exact `NodeId`, delegated-inception digest, both store commitments, root-anchor location, and founder/root key-state locations.

The 3 signatures in `Linked` and the 2 signatures in `Created` SHALL cover the same identity, subject device identifier, and exact subject endpoint through the canonical transcripts defined by profile 1. `Created` is valid only for the device directly delegated by the root during creation; `Linked` is valid only after the newcomer verifies the reply and signs confirmation.

The entry key is discovery data; `DeviceBindingProof` is the cryptographic association between that key's endpoint and the device identifier. Copying either proof variant to another `devices/<node-id>` path SHALL fail because the path's node id does not equal the subject node id inside every applicable signed object. A record at `pending-devices/<node-id>` written by the inviter SHALL carry the exact profile-1 `PendingRecord` (`PDR1`): its inviter creation time and a `PendingLinkedOffer` containing only the exact signed request and signed manifest. The signed identity root SHALL equal the hosted identity whose directory carries the record, and the signed inviter AID SHALL be an accepted device of that same identity; a valid offer copied from another identity's directory is invalid here. The inner offer is sufficient for uniqueness lookup only after those ownership checks and for the newcomer to check what the inviter committed, but the wrapper is not a `DeviceBindingProof` and cannot authorize or be copied into confirmed: only the newcomer can add the canonical confirmation signature that completes `Linked`. A `Created` proof SHALL be written directly as the founding device's confirmed payload only after the founding delegation and its root anchor are accepted; a marker-only founder record is invalid.

One device identifier SHALL have at most one endpoint in either pending or confirmed state in this change. A request presenting the same device identifier and the same authenticated node id is an idempotent retry. A request presenting that identifier from another node id SHALL be refused whether the existing record is pending or confirmed; a saved endpoint key makes a node-id change unnecessary for an honest restart, and endpoint supersession requires the later change's proof and conflict rules.

The directory SHALL expose a local lookup from device identifier to every pending and confirmed node id, built only from present payloads whose pending offer or confirmed binding proof verifies. A missing payload SHALL yield an indeterminate lookup rather than "identifier absent". A ceremony deciding uniqueness SHALL fail closed instead of treating a not-yet-readable payload as permission to add another endpoint, and the linking critical section SHALL not wait for payload delivery. If locally visible valid confirmed proofs bind one device identifier to more than one node id, all of those bindings SHALL be classified as conflicting and none SHALL grant full access; the conflict SHALL remain observable until an explicit endpoint-supersession operation resolves it.

#### Scenario: Registering a device writes the record
- **WHEN** `add_device` is called with a device's node id and a valid complete canonical `DeviceBindingProof` payload for that exact node id
- **THEN** an entry exists at `devices/<node-id>` whose payload bytes are exactly the supplied proof bytes

#### Scenario: Registration is idempotent
- **WHEN** the same device is registered twice with the same valid complete proof bytes
- **THEN** the device set contains that device once and the stored payload remains byte-for-byte that proof

#### Scenario: A pending identifier cannot move to another endpoint
- **WHEN** a pending device identifier is presented from another authenticated node id
- **THEN** the new request is refused, the original pending record remains, and no record is written for the new node id

#### Scenario: One confirmed identifier holds one endpoint place
- **WHEN** a device identifier already confirmed under one node id is presented under another
- **THEN** no pending or confirmed record is written for the new node id, and the existing confirmed record is unchanged

#### Scenario: A missing device payload is not absence
- **WHEN** a confirmed device record is present but its payload is not yet readable
- **THEN** lookup by device identifier is indeterminate, not absent, while record-level device membership remains unchanged

#### Scenario: A copied binding proof does not bind another endpoint
- **WHEN** a directory writer copies a legitimate device's complete payload to `devices/<attacker-node-id>`
- **THEN** the copied record is visible to `list_devices` but its binding proof fails because both signed objects name the legitimate node id

#### Scenario: Creation records a proved founder
- **WHEN** creation accepts the root, founding delegated inception, and matching root anchor
- **THEN** `devices/<founder-node-id>` is confirmed with a `Created` proof signed by the founding device identifier and the root, rather than with a marker

### Requirement: The device set reads at record level
Listing devices SHALL depend only on entry records, never on payload bytes, so the device set is visible as soon as records sync — before any payload is fetched. This SHALL hold unchanged now that a device record's payload names the device's identifier and its anchoring event: a device is visible to the identity's other devices as soon as its record syncs. This listing is discovery state, not an authorization verdict; full session access is decided by the joined record-and-KERI check below.

#### Scenario: A device is listed as soon as its record arrives
- **WHEN** a device record has replicated to another device of the identity
- **THEN** `list_devices` there includes it, without waiting on payload content

#### Scenario: A device is listed before its payload arrives
- **WHEN** a device record has replicated but its payload bytes have not
- **THEN** the device set includes it, as it does today

#### Scenario: Membership does not wait on verification
- **WHEN** a device record is present and its identifier's chain has not yet been verified locally
- **THEN** the device set includes it, while the unverified record grants no full session access

## ADDED Requirements

### Requirement: Key events are a family of the directory
The directory SHALL carry the identity's key events as an entry family of its own replica, disjoint from the device records, the typed tickets, the connections records, and the retraction markers. An identity SHALL NOT gain a second device-internal replica for them: one replica per identity is what makes "the directory synced but the other store silently did not" unrepresentable.

#### Scenario: One replica carries both
- **WHEN** an identity's key events and its device records are written
- **THEN** both are entries of the same directory replica, and no additional replica is created for the events

#### Scenario: Families do not collide
- **WHEN** a device record, a typed ticket, a connections record, a retraction marker, and a key event all exist for one identity
- **THEN** each is read by its own family and none is returned by another family's read

### Requirement: Confirmation adds proof only the newcomer can make
A record at `pending-devices/<node-id>` SHALL carry the exact `PDR1` `PendingRecord` whose inner `PendingLinkedOffer` has the exact canonical signed request and manifest. Before writing confirmed, the newcomer SHALL require the wrapper to decode canonically, require its path node id and the offer's newcomer node id to equal its own authenticated endpoint, require the signed root to equal the hosted identity owning this directory and the signed inviter to be an accepted device of that root, verify both offer signatures, the anchored chain, both sealed store commitments, and successful consuming import of the byte-bound `VerifiedBootstrapPair`, then sign the canonical `link-confirmation` transcript with the accepted newcomer device key. The resulting `Linked` proof SHALL retain the request and manifest byte-for-byte and add that confirmation transcript and signature; the pending timestamp is lifecycle metadata and SHALL NOT enter the proof or authorization. A marker, identifier-and-anchor tuple, locally trusted endpoint fields, cross-directory copy, or copied pending payload SHALL be invalid.

#### Scenario: A pending offer belongs to one identity directory

- **WHEN** a canonical and correctly signed pending offer for identity A is copied into identity B's directory under its original endpoint path
- **THEN** B does not treat it as a pending device because the signed root and inviter are not owned by B's hosted identity

Confirmation requires no further network round trip. It is 2 directory writes whose order SHALL be: write the confirmed record first, then tombstone pending. Each write SHALL be idempotent. The confirmed-record write is the linking commit point: after it succeeds the link is retained and only pending cleanup resumes, in-process and at startup. The signed confirmation and completed proof SHALL be durable before this write so a restart reproduces the same bytes. Once cleanup responsibility is durable, the operation reports success rather than rolling the identity back; pending may transiently remain and still confers nothing.

#### Scenario: The confirmed record completes what the pending one carried
- **WHEN** a device registered as pending is confirmed
- **THEN** its confirmed record carries the same request and manifest bytes plus a valid newcomer confirmation over their digests, the store commitments, anchor, endpoint, and newcomer key state

#### Scenario: A directory writer cannot promote pending
- **WHEN** a directory writer copies a valid pending offer under the same node-id path into the confirmed family
- **THEN** the record is not a valid `Linked` proof and grants no full access because the newcomer confirmation signature is absent

#### Scenario: An interrupted confirmation completes on repeat
- **WHEN** a runtime fails between the two writes of a confirmation, and confirmation is repeated
- **THEN** the link remains committed, the device ends in the confirmed set exactly once with its identifier and anchor intact, the pending record is eventually tombstoned, and at no point is the device absent from both sets

### Requirement: Full device access joins the confirmed record to accepted KERI authority
`SessionAccess::Full` for an authenticated peer SHALL require all of the following local facts: a confirmed record whose path names that peer's authenticated `NodeId`; a complete tagged `DeviceBindingProof` whose applicable signatures all verify and name that same node id through their canonical transcripts; and an accepted, signature-valid chain in which the proof's subject device identifier reaches this identity's root and the accepted delegator branch carries the proof's named seal. `Linked` requires request, manifest, and newcomer confirmation signatures and the confirmation's exact signed-object and store-commitment digests. `Created` requires founder and root signatures. For `Linked`, the inviter in the manifest SHALL be the subject's fixed delegator. For `Created`, the root SHALL be the subject's fixed delegator and root countersigner. The authorization projection SHALL be derived from the accepted KERI view and verified confirmed proof, not from either input alone.

Holding a directory write ticket, writing `devices/<node-id>`, copying another record's payload or a pending offer, or supplying locally trusted endpoint fields SHALL therefore be insufficient to gain full access. A pending record, missing newcomer confirmation, incomplete or malformed proof, any invalid signature, endpoint mismatch, unanchored identifier, chain rooted in another identity, or record whose key does not match the authenticated peer's `NodeId` SHALL NOT produce `SessionAccess::Full`; independently valid grant-derived access MAY still apply. The joined verdict SHALL update as record payloads and accepted key events arrive, without re-walking the whole chain for every session. If more than one locally valid confirmed proof binds the same device identifier to different node ids, every conflicting endpoint SHALL fail closed rather than choosing by arrival order, author id, or last-writer-wins.

`data-layer` SHALL expose a runtime-only replacement API for one complete `IdentityAccessProjection`: identity, monotonically increasing projection generation, the exact directory-device-input generation evaluated, every `NodeId` currently eligible for identity-device `Full`, every conflicting or explicitly denied binding, and the proof digests plus `{aid, sequence, SAID}` head snapshot from which the runtime derived those decisions. The directory-device-input generation SHALL advance on every relevant pending/confirmed record change and on every transition of its payload between readable and unreadable. `data-layer` SHALL synchronously close the prior identity-device projection and notify `pdn-node` when that generation advances; a projection whose input generation no longer equals the current directory input SHALL be unusable even before runtime verification finishes. `pdn-node` SHALL be the sole producer and normative verifier of the replacement projection; `AccessBook` SHALL treat it as opaque authorization input and SHALL NOT infer KERI authority from directory records itself. Hosting an identity SHALL install a closed generation first, and any absent, stale, partial, malformed, or generation-skipping projection SHALL grant no identity-device `Full` while leaving independently valid grant-derived access unchanged.

Replacing a projection SHALL atomically replace the whole identity-device decision set under that identity's access lock. A granting generation SHALL become visible only after its referenced KERI security state is durably committed. A transition that may remove `Full` SHALL first durably arm a cross-backend intent and install a closed generation that synchronously invalidates every deposited identity-device write admission and terminates every active sync session authorized by an older projection; it SHALL then commit the KERI verdict, install the complete new projection, and clear the intent. No read, write, ingest admission, or new session may continue on the older `Full` generation after closure returns. Reopen or failure at any boundary SHALL keep identity-device access closed until the intent, KERI state, projection, admissions, and sessions agree. Projection changes SHALL notify `AccessBook` directly and SHALL NOT wait for periodic reconciliation.

#### Scenario: A forged confirmed record is not a full-access credential
- **WHEN** a holder of the directory write capability copies a legitimate device's valid anchored chain and confirmed-record payload to `devices/<attacker-node-id>`
- **THEN** `list_devices` may show the record, but a session authenticated as that node id does not receive `SessionAccess::Full`

#### Scenario: All 3 linked signatures authorize an identity device
- **WHEN** a session's authenticated node id has a confirmed `Linked` proof carrying valid request, manifest, and newcomer-confirmation signatures that bind that node id to a device identifier with a locally accepted anchored chain to this identity
- **THEN** the authorization projection classifies that session as `SessionAccess::Full`

#### Scenario: The founder remains a full-access device
- **WHEN** another device of the identity classifies the founding endpoint from its confirmed `Created` proof and accepted root-anchored chain
- **THEN** the 2 creation signatures authorize `SessionAccess::Full` for that founder without a linking transcript exception

#### Scenario: A copied founder proof binds no other endpoint
- **WHEN** a directory writer copies the founder's valid `Created` proof under another node id
- **THEN** the copied endpoint receives no full access because both creation signatures name the founder's original node id

#### Scenario: KERI authority without confirmation grants no full access
- **WHEN** a valid anchored device identifier has no confirmed record for the session's authenticated node id
- **THEN** the session does not receive `SessionAccess::Full`

#### Scenario: Conflicting confirmed endpoints fail closed
- **WHEN** locally verified confirmed records bind one device identifier to 2 different authenticated node ids
- **THEN** neither node id receives `SessionAccess::Full`, and the binding conflict is reported

#### Scenario: A newly detected conflict revokes existing Full immediately

- **WHEN** an endpoint has `SessionAccess::Full` and the runtime then verifies a conflicting confirmed proof for the same device identifier
- **THEN** the projection transition closes before returning from conflict processing, invalidates that endpoint's deposited write admission, terminates its active Full-authorized sync sessions, and denies subsequent reads, writes, and sessions without waiting for reconciliation

#### Scenario: A new device-record input cannot use a stale projection

- **WHEN** a confirmed-device record or its payload state changes after a Full projection was installed
- **THEN** `data-layer` advances the directory-device-input generation, closes identity-device Full and notifies the runtime synchronously, and does not reuse the old projection while the new input is unevaluated

#### Scenario: A projection crash remains fail closed

- **WHEN** the process stops after arming a projection transition or closing the old generation but before installing the complete new projection
- **THEN** reopen grants no identity-device `Full` until replay makes the durable KERI state and one complete projection generation agree
