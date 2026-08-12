# Device linking carries a KERI proof

The ceremony keeps its shape — one dial, one bidirectional stream, one exchange, a one-time secret verified and burned before any state, a commit that precedes the reply — and gains the step both ADR-0011 and ADR-0012 left marked. The newcomer proves possession of the secret and live control of the new device AID by signing a request bound to the authenticated endpoint; that AID has no identity authority until its inception is anchored and no full access until confirmation. The inviter proves to the newcomer that it acts for the identity the payload names. The delegation model behind it is [keri-identity](../pdn-node-keri-identity/spec.md); the storage of key events is [kel-store](../data-layer-kel-store/spec.md).

## RENAMED Requirements
- FROM: `### Requirement: A linking invite is one-time, short-lived, and bearer-free`
- TO: `### Requirement: A linking invite is one-time, short-lived, and carries no long-lived capability`
- FROM: `### Requirement: The reply hands over the bootstrap tickets`
- TO: `### Requirement: The reply hands over the proof and the bootstrap tickets`

## MODIFIED Requirements

### Requirement: An identity is provisioned with its full store set on its first device
Creating an identity SHALL first use a 2-phase data-layer API to prepare its private-metadata directory and data replica without an issuer binding. That API SHALL return durable opaque handles and role-tagged `StoreCommitment` values, not raw namespace identifiers. The creation record SHALL durably name those handles and commitments before inception; a prepared replica whose handle never reached the record is unreferenced and SHALL NOT be adopted by recovery.

The root inception SHALL seal exactly the `directory` and `data` commitments. Creation SHALL then write the 3-event sequence into the prepared directory under the correct controllers' authorship: root `icp`, founder `dip`, and root `ixn` sealing that `dip`. The founder `dip` SHALL remain awaiting delegation after its write and SHALL become accepted only after the root `ixn` is written and accepted. Only then SHALL creation bind the prepared data replica to the derived `PdnId`, record the founding device at `devices/<founder-node-id>` with a complete `Created` `DeviceBindingProof`, and publish the data ticket. The `Created` proof SHALL use the exact profile-1 `founder-binding` preimage, including both store commitments and founder/root key-state locations; the founding device signs it and the root countersigns the identical bytes. A marker-only founder record SHALL NOT be written.

The identity store set SHALL mean exactly those 2 device-replicated stores and SHALL remain fixed in this change. Pairing's per-connection metadata replicas and cross-identity replicas imported through grants are not members of it. The directory copy of the data ticket is the durable record; the linking dialogue below hands the 2 bootstrap tickets over directly.

An unfinished creation SHALL be resumable by startup recovery from its exact recorded boundary. Inception and all 3 events SHALL be deterministic in the record's key material and commitments. A restart after the founder `dip` is assembled or persisted in the creation record but before the root `ixn` seal is written SHALL resume by deriving that same seal; it SHALL NOT accept the founder, bind the data issuer, or write a confirmed founder record until the seal is accepted. The creation record SHALL be cleared last, after the identity is hosted.

On startup the runtime SHALL resume every unfinished creation record before the identity service accepts a new `create` call. It SHALL keep creation records per attempt, so several identities can be created and interrupted independently and each resumes as itself. The existing `create() -> PdnId` call has no idempotency key and SHALL retain its non-idempotent meaning: every call admitted after startup recovery starts another identity. A caller whose earlier result is uncertain SHALL discover identities completed by recovery through `hosted_identities`; a repeated `create` call SHALL NOT consume or return an older creation record. Caller-correlated retries require an idempotency key and are outside this change.

#### Scenario: Creation provisions directory and data namespace
- **WHEN** an identity is created on a runtime
- **THEN** the runtime hosts the identity's directory with the creating device's signed `Created` proof in its confirmed device set, hosts the identity's data namespace, and the directory carries the data namespace's ticket under the `data` kind

#### Scenario: Creation incepts a root and its first device
- **WHEN** an identity is created
- **THEN** its directory carries the root `icp`, the creating device's `dip`, and the root `ixn` seal anchoring that `dip`, and all 3 are in the accepted history

#### Scenario: The inception seals the identity's own stores
- **WHEN** an identity is created
- **THEN** its inception seals opaque role-tagged commitments to its directory and data namespace, and recomputing the identifier from that inception reproduces it

#### Scenario: Startup resumes an interrupted creation as the same identity
- **WHEN** a runtime fails after recording prepared replica handles and root key material but before the root inception is accepted and then starts again
- **THEN** startup completes the recorded identity with the same identifiers, and `hosted_identities` exposes it without a new `create` call

#### Scenario: Restart between the founder inception and its seal is safe
- **WHEN** a runtime stops after recording the founder's delegated inception and before accepting the root event that seals it
- **THEN** startup derives and accepts the same root seal before binding the data issuer or confirming the founder, and no unanchored founder ever grants access

#### Scenario: Creation works before a PdnId exists
- **WHEN** creation needs the 2 store commitments before deriving the root identifier
- **THEN** it prepares both replicas through opaque data-layer handles and binds the prepared data replica to the derived `PdnId` only after derivation

#### Scenario: Two interrupted creations resume independently
- **WHEN** two identities are created on one runtime and both are interrupted before completion
- **THEN** each resumes as itself from its own creation record, and neither takes the other's key material

#### Scenario: Startup recovery precedes a new creation
- **WHEN** a runtime starts with one or more unfinished creation records and a caller requests a new identity
- **THEN** every recorded creation is resumed before the new `create` is admitted, and the new call creates another identity rather than consuming or returning an older record

#### Scenario: Repeating create is not a caller-correlated retry
- **WHEN** startup recovered an identity whose earlier `create` result the caller did not receive and the caller invokes `create` again
- **THEN** the runtime hosts both the recovered identity and the newly created identity, each returned or discoverable by its own service operation

### Requirement: A linking invite is one-time, short-lived, and carries no long-lived capability
The identity service SHALL mint a linking invite for a hosted identity: a fresh random one-time secret (32 bytes from the operating-system generator) with a short lifetime (a default with an invite-time override), held pending on the inviting runtime, and a self-contained linking payload carrying a format version, the inviting device's node address, the secret, the identity's `PdnId`, and the inviting device's identifier. The payload SHALL carry no ticket and no durable capability — a photographed payload expires with its secret. The secret itself is a bearer credential, short-lived and single-use: whoever holds it within its lifetime can present it, and the payload's property is the absence of anything long-lived, not the absence of bearer material.

Minting SHALL be refused, with no pending state created, for an identity the runtime does not host, and for an identity whose current proof bundle lacks the reserved capacity required below for redemption — a device that cannot fit the next delegation cannot usefully invite.

#### Scenario: The payload carries nothing long-lived
- **WHEN** a linking invite is minted for a hosted identity
- **THEN** its payload consists of the format version, the inviting device's node address, the one-time secret, the identity's `PdnId`, and the inviting device's identifier — no tickets, no keys, and no location of a future event

#### Scenario: Every linking invite carries a distinct secret
- **WHEN** two linking invites are minted, whether for one hosted identity or two
- **THEN** their secrets differ, and each is pending independently

#### Scenario: An invite for an unhosted identity is refused
- **WHEN** a linking invite is requested for an identity the runtime neither created nor linked
- **THEN** the operation fails with an unknown-identity error and no pending invite exists

#### Scenario: An invite is refused when the proof would not fit
- **WHEN** a linking invite is requested on a device whose current chain leaves insufficient reserved depth, event count, or bytes for redemption
- **THEN** minting fails with a typed error and no pending invite exists

### Requirement: The dialogue is one raw exchange on the linking ALPN
Linking SHALL dial the payload's node address under the dedicated linking ALPN, version 1 — distinct from the pairing ALPN — and run one bidirectional exchange: the dialing device presents the format version, the secret, a fresh nonce of 32 bytes from the operating-system generator, its delegated inception naming the inviting device's identifier as delegator, and its signature over the request transcript; the inviter — after the verify-and-burn, the checks, the anchoring, and the registration below — answers with one stream of frames. The request SHALL carry no request-preimage blob and no claimed node id. The inviter SHALL reconstruct the canonical preimage from the verified request fields, invite context, its authenticated local endpoint identity, and the connection's authenticated peer identity, then verify the signature before anchoring or writing pending state. The newcomer SHALL require the manifest's inviter and newcomer node ids to equal the same authenticated connection endpoints. A payload whose format version the dialing runtime does not speak SHALL be refused before dialing. Linking into an identity the dialing runtime already hosts SHALL be refused before dialing.

The exchange SHALL remain one request and one streamed reply. No acknowledgement from the newcomer SHALL gate the reply: an acknowledgement could be signed by any holder of the secret without verifying anything, so it would buy no boundary while costing a round trip.

#### Scenario: Linking completes between two runtimes
- **WHEN** runtime B links with a live linking invite minted on runtime A
- **THEN** the exchange completes over the version 1 linking ALPN and B holds the directory and data-namespace tickets from the reply

#### Scenario: An unknown payload version is refused before dialing
- **WHEN** link is given a payload with an unsupported format version
- **THEN** it refuses without opening a connection

#### Scenario: Linking into an already-hosted identity is refused before dialing
- **WHEN** link is invoked on a runtime that already hosts the payload's identity
- **THEN** the operation is refused and no dialogue runs

#### Scenario: The previous protocol version is not answered
- **WHEN** a device dials the version 0 linking ALPN
- **THEN** the ceremony does not run

### Requirement: The reply hands over the proof and the bootstrap tickets
The linking reply SHALL be one stream of frames on the same bidirectional stream: the key events replaying the identity's root and the chain of delegations down to the inviting device, the event anchoring the newcomer's delegated inception, the inviter's signature over a proof manifest, and write tickets to the identity's directory and to its data namespace — both minted fresh from replicas the inviting device hosts locally, so the ceremony reads nothing through directory ticket entries and no payload wait sits in the critical path.

The proof manifest SHALL inventory exactly the signed-KERI-event frames preceding it: canonical order, count, fixed event-frame kind, and ordered BLAKE3-256 digests of the exact encoded frame bodies, as fixed by profile 1. The manifest SHALL NOT inventory itself or the later tickets frame. It SHALL also repeat the canonical ceremony bindings from the request transcript. QUIC already prevents a network intermediary from cleanly reordering or truncating the stream; the signed inventory binds the inviter to the exact frames it chose to list and exposes a missing, changed, extra, or reordered inventoried frame. It does not prove that no valid event was omitted from both stream and inventory. Newcomer confirmation signs the sealed commitments and asserts completion of the required local byte-bound pair verification/import; it does not carry the tickets-frame bytes or independently reproducible capability-verdict evidence.

The dialing runtime SHALL hand both exact canonical ticket blobs, both sealed commitments, and the authenticated inviter fallback address to the data layer together. It SHALL import the 2 replicas only by consuming the resulting opaque `VerifiedBootstrapPair`, which byte-binds both successful role verdicts and the fallback hint to that one import. `pdn-node` SHALL NOT decode, mutate, role-swap, clone, or resupply a ticket between verification and import. The data layer SHALL internally recompute each ticket's role-tagged commitment and match it to the `directory` or `data` commitment sealed by the identity; neither raw namespace identifier nor decoded ticket SHALL cross into `pdn-node`. Registering an issuer from a field the reply supplied, without that comparison, is what makes a verified chain compatible with someone else's stores. Every device of an identity can therefore mint a linking invite, and the newcomer's authority is anchored by whichever device invited it.

#### Scenario: The newcomer comes up with the full store set
- **WHEN** runtime B links into an identity and the directory's first sync completes
- **THEN** B hosts the identity's directory and its data namespace, and an entry written under the identity on either runtime becomes readable on the other

#### Scenario: Linking through a non-founder device
- **WHEN** device 2 was itself linked into an identity, and device 3 links from an invite minted on device 2
- **THEN** device 3 comes up with the directory and the data namespace, device 3's inception is anchored in device 2's log, and all three devices' device sets converge to three

#### Scenario: A truncated stream is detected
- **WHEN** the reply's last frames do not arrive, or arrive out of the manifest's order
- **THEN** the newcomer refuses on the manifest rather than accepting a shorter chain

### Requirement: A refused link is legible to the dialer's caller
Linking SHALL report a refusal by the inviting device to its own caller as a refusal, distinguishable from a failure to reach or complete the dialogue, from a failure of the verification material, and from a failure to catch up afterwards. A dialogue still in flight when the caller's budget runs out SHALL surface as its own outcome — distinct from the refusal, whose dialogue ended, and from the catch-up timeout, whose dialogue completed. A verification failure SHALL carry either 1 non-ticket reason — `IdentityChainMismatch`, `AnchorMismatch`, `SignatureInvalid`, or `LimitExceeded` — or one `BootstrapTicketFailures` value. `BootstrapTicketFailures` SHALL be a nonempty ordered collection of 1 or 2 `{ role, reason }` entries, contain each failing role exactly once in `directory`, then `data` order, expose no namespace identifier, and include every non-`MatchWritable` verdict from the data layer's complete pair result. Its mapping SHALL be total: `CommitmentMismatch` maps only to `StoreCommitmentMismatch`, `InsufficientCapability` only to `BootstrapTicketInsufficientCapability`, and `MalformedTicket` only to `BootstrapTicketMalformed`; `MatchWritable` contributes no failure entry. No ticket verdict is collapsed, discarded because the other role also failed, or selected by arrival order. The first 3 non-ticket reasons and all ticket failures describe verification material; `LimitExceeded` is an operational bound. The refusal the dialing device receives from the inviter SHALL carry no reason, leaving the inviter's uniformity unchanged: these reasons are the dialing runtime's own findings, never something the inviter tells it. A caller SHALL distinguish them without inspecting human-readable error text.

#### Scenario: A refusal is not a transport failure
- **WHEN** linking presents a secret that has already been burned, and separately when it dials an address where no inviting device answers
- **THEN** the first reports a refusal and the second reports the unreachable outcome — each recognizable as its own, distinguishable without matching on error text

#### Scenario: A refusal is not a catch-up timeout
- **WHEN** linking is refused by the inviting device, and separately when the dialogue succeeds but the imported directory does not catch up within the timeout
- **THEN** the two are distinguishable without matching on error text, and both leave the newcomer with no replica, binding, or hosted entry for the identity — while keeping what the residue rule below keeps on purpose

#### Scenario: A hung inviter costs the caller its budget and nothing more
- **WHEN** the dialed inviter accepts the dialogue, reads the request, and never answers
- **THEN** `link` fails within the caller's budget with the dialogue-timeout outcome — distinguishable from the refusal and from the catch-up timeout without matching on error text — and the dialing runtime holds no replica, binding, or hosted entry for the identity

#### Scenario: A substituted identity and an oversized bundle are different outcomes
- **WHEN** an inviter answers with a chain that does not reach the payload's identity, and separately with an honest chain that exceeds a bundle limit
- **THEN** both fail verification with reasons the caller can tell apart without matching on error text

### Requirement: Link returns caught up, and failure leaves no local residue
`link` SHALL NOT report success until the imported directory has completed one successful sync exchange that started after the import — one bounded wait against the peer that just answered the dialogue, not a retry loop; a directory that cannot catch up within the caller's timeout SHALL surface as an error, not a hang. The property waited on is a completed session, not arrived content: a runtime that never synced and one that synced and found nothing new must not be confused, so polling the directory's contents does not discharge this requirement. Any accepted KEL events whose replicated payloads have not arrived SHALL remain independently reconstructible from the durable exact-byte accepted-head evidence; a completed session is never evidence for missing event bytes.

The caller's timeout SHALL bound the whole act, the dialogue included: the dialogue spends from the budget first and the catch-up gets what remains, so a dialed inviter that never answers costs the caller its budget — surfaced as its own typed outcome — and never the transport's idle timeout. Without this bound the budget would govern only the last third of the act, and a hung inviter would hold the caller for as long as the transport tolerates a silent connection, however small a budget the caller named.

The dialing runtime SHALL arm the identity for session classification the moment its directory is imported, before the data namespace is imported — so at no instant does the data binding exist ahead of the book that judges its sessions. The other order would serve the data namespace ticket-bounded (full view to any caller) for the whole catch-up wait, on a long-lived namespace id already known to every past grantee and every holder of a leaked ticket. The cost of arming early is bounded and fail-closed: while the directory is still converging, callers it cannot yet resolve are refused, and a refused device is served once its record replicates in — the node's periodic reconcile pass is the retry cadence.

On any failure after import and before the confirmed-device record is written, the dialing runtime SHALL undo what this linking did, in reverse order — the data-namespace import, the arming, the directory — and the identity is unknown to the runtime again. Undoing SHALL restore what the import displaced rather than delete it: an issuer can already be bound when the link runs, because a namespace reached through a peer's grant binds the same issuer without making the identity hosted, and the pre-dial refusal cannot see it. A rollback that forgot the issuer outright would destroy a replica this linking never imported, permanently — so the data namespace is unbound only when the link's import was what bound it, and the replica it brought up is dropped only when it is not the replica the restored binding names. A device record already committed on the inviter side may remain, per the lost-reply posture above. The confirmed-device write is the linking commit point: after it succeeds rollback SHALL be disarmed, the identity and imports SHALL be retained, and only the idempotent pending tombstone may remain as resumable cleanup.

"No local residue" SHALL mean exactly this, and no more, for an attempt that fails before the confirmation commit: the dialing runtime holds no replica of the identity, no binding of its issuer that this attempt created, no confirmed device record, and no hosted entry for it, so operations addressed to it are refused as unknown. Four things SHALL survive on purpose: the durable attempt with its keys and assembled inception; the pinned heads with their exact `KEL1` reconstruction sets and seal indexes; the exact signed request and manifest with their anchor and `{aid, sequence, SAID}` accepted-head snapshot; and, on the inviting side, whatever it committed before answering. Snapshot generations guard the original conditional write but later head advancement is validated by the exact-prefix rule. A newcomer confirmation is added to the ceremony record only after reply verification and consuming import of the byte-bound ticket pair succeed. Once confirmed is written, the act is committed and SHALL NOT be treated as failed merely because pending cleanup remains.

#### Scenario: Success implies the directory is caught up
- **WHEN** `link` returns success
- **THEN** the newcomer's directory replica has completed a successful sync exchange started after the import, and the device set it reads locally includes the identity's existing devices

#### Scenario: No serving window opens while the link catches up
- **WHEN** the data namespace of a linking identity receives a session from a caller the still-converging directory cannot resolve, before `link` has returned
- **THEN** the session is refused — the identity was armed before the data namespace was imported, so the namespace is never served ticket-bounded during the wait

#### Scenario: A timed-out link leaves nothing behind on the dialing node
- **WHEN** the directory cannot complete a first sync within the timeout
- **THEN** `link` fails, the identity is absent from the runtime's hosted identities and disarmed for classification, and operations addressed to it are refused as unknown — as they were before the attempt, not as storage errors against a dropped replica

#### Scenario: A failed link leaves a granted namespace of the same issuer intact
- **WHEN** a runtime reached an issuer's namespace through a peer's grant, then links into that same issuer and the link fails
- **THEN** the grant still reads that namespace's entries afterwards, and the identity is still not hosted — the rollback restored the binding it displaced instead of forgetting the issuer

#### Scenario: What a failed link deliberately keeps
- **WHEN** a linking fails after verification and rolls back
- **THEN** the runtime holds no replica, binding, or hosted entry for the identity, and still holds the attempt, pinned heads with complete reconstruction evidence, complete signed request and manifest, anchor location, and exact accepted-head snapshot of that ceremony

### Requirement: The secret is verified and burned atomically, before any state
On a presented secret the inviter SHALL atomically check-and-burn against its pending linking invites: present and unexpired → burned and the dialogue proceeds; expired, already burned, or unknown → refused. The check SHALL precede every state change, so a refused attempt leaves no observable state on the inviter: no key event, no device record written, no ticket minted — and the anchoring event is now the first durable write of the ceremony, so "before any state" is measured against it and not against the device record. An unpresented secret SHALL expire at the end of its lifetime and thereafter be refused. A refused presentation SHALL NOT burn a live pending invite, and refusals SHALL be uniform — the dialer cannot distinguish wrong from expired from already burned.

#### Scenario: A second presentation of the same secret is refused
- **WHEN** linking completed against an invite and a second link presents the same secret
- **THEN** the second attempt is refused, and the identity's device set is exactly as the first linking left it

#### Scenario: An expired secret is refused
- **WHEN** a secret is presented after its lifetime has elapsed
- **THEN** the attempt is refused and no observable state exists on the inviter — no key event, no device record, no ticket issued

#### Scenario: A wrong secret is refused and burns nothing
- **WHEN** a dialer presents a secret that was never minted while a linking invite is pending
- **THEN** the attempt is refused with no observable state on the inviter, and a subsequent presentation of the pending invite's real secret succeeds

### Requirement: The inviter registers the newcomer as pending before replying
After the burn and anchoring, the inviter SHALL write the newcomer's record as pending using the authenticated peer node id and only then reply. The pending payload SHALL be the exact profile-1 `PendingRecord` (`PDR1`): the inviter's creation time followed by a `PendingLinkedOffer` containing the exact canonical request with newcomer signature and exact canonical manifest with inviter signature, whose transcript carries the anchor location. It is deliberately not a complete `DeviceBindingProof`, because the newcomer has not yet verified the reply or signed its local-completion confirmation. The inviter SHALL write exactly the manifest bytes it streams. A pending record SHALL confer nothing and SHALL NOT be promotable by copying its payload into confirmed; full classification requires the later newcomer confirmation signature and accepted chain. A lost reply therefore leaves a visible but unauthorized pending offer, and a fresh invite converges.

At most one endpoint SHALL stand per device identifier in pending or confirmed state. A record is keyed by node id while the thing it registers is a device identifier, and a retry may present the same identifier again. A retry from the same authenticated node id SHALL be idempotent and MAY replace the pending offer with the fresh ceremony's valid offer for the same binding. A request presenting that identifier from a different node id SHALL be refused before anchoring or writing a pending record, whether the existing record is pending or confirmed. The standalone durable-storage predecessor preserves the honest device's endpoint key across a restart, so accepting another node id here serves no recovery case and would implement endpoint supersession without its proof or conflict rules.

This uniqueness check SHALL use the directory's local device-identifier lookup. If any confirmed or pending device record needed to decide uniqueness has no readable payload, the inviter SHALL fail closed with the uniform remote refusal and a typed local diagnostic, without waiting for replication or payload delivery inside the critical section.

#### Scenario: A retry from another endpoint is refused
- **WHEN** an unconfirmed device identifier is presented again with a valid request signature from another authenticated node id
- **THEN** the inviter refuses before anchoring or writing a record, and the original pending binding remains unchanged

#### Scenario: A confirmed identifier cannot move to another endpoint here
- **WHEN** a request presents a device identifier that is already confirmed under another node id
- **THEN** the inviter refuses before writing a pending record, and the confirmed device set is unchanged

#### Scenario: Identifier uniqueness fails closed on a missing payload
- **WHEN** the directory contains a device record whose payload is not readable when the inviter checks a presented device identifier
- **THEN** the inviter refuses uniformly without waiting or writing a pending record, and records the indeterminate lookup locally

#### Scenario: The newcomer is registered on the inviting device
- **WHEN** runtime B completes the linking dialogue against runtime A
- **THEN** A's directory replica already contains B's node id, with no wait on any sync exchange

#### Scenario: The registered id is the connection's, not a claimed one
- **WHEN** the inviter registers a newcomer
- **THEN** the recorded node id equals the authenticated endpoint id of the dialing connection

#### Scenario: A pending registration is served nothing
- **WHEN** a device is registered as pending in an identity's directory and holds a grant on one claim of that identity's data namespace
- **THEN** it receives exactly what the grant names, and the identity's remaining entries never reach it

#### Scenario: A dialogue lost after commit converges on a fresh invite
- **WHEN** a linking dialogue fails after the burn and the registration, and the same device later links with a fresh invite
- **THEN** the public linking service completes the second link, the identity remains hosted, the device is confirmed exactly once, and no pending registration remains

### Requirement: The newcomer confirms itself once the tickets are in hand
A device that has imported the directory and data namespace SHALL confirm itself before `link` reports success. It SHALL verify that pending is canonical `PDR1` and its inner offer carries the exact request and manifest it accepted, that both bind its authenticated endpoint, that the anchor belongs to its accepted chain, and that the 2 stores were imported by consuming the `VerifiedBootstrapPair` returned only for this exact successful joint verification. It SHALL then sign the profile-1 `link-confirmation` transcript over the signed-object digests, commitments, anchor, endpoint, and newcomer key-state location. The request, manifest, and this third signature form the complete `Linked` `DeviceBindingProof`; possession of a directory write ticket alone cannot produce it. The completed proof SHALL be durable before it is written as confirmed.

No additional network round trip is introduced. The confirmed write is the linking commit point: once it succeeds, rollback SHALL be disarmed and cancellation or failure of the pending tombstone SHALL retain the identity, imports, and confirmed proof. Tombstoning is idempotent durable cleanup resumed in-process and at startup. In the same step the device SHALL write its own delegated inception before confirmation and SHALL NOT re-author the inviter's anchoring event. Until the 3-signature proof and accepted chain replicate, other identity devices refuse the newcomer's full-access sessions.

Every pending registration SHALL use the profile-1 `PendingRecord` wrapper and carry the inviter's durable Unix-seconds creation time. On each runtime, expiry SHALL use the earlier of that untrusted wire value and a durable first-observed local time keyed by the BLAKE3-256 digest of the complete `PendingLinkedOffer`. The first-observed value SHALL live in `runtime-security/keri-v1/pending-observation`, not in a mutable directory entry or process clock cache.

No lifecycle record SHALL be created from unverified input. Before recording first-observed state, the runtime SHALL require canonical `PDR1`/`PDO1` encoding, path and signed endpoint equality, both request/manifest signatures, the manifest anchor on the accepted chain, and the subject AID used by the uniqueness lookup. It SHALL also bind the offer to the directory that carries it: the hosted identity root for that directory SHALL equal the root in the signed request and manifest, and the manifest's inviter AID SHALL be an accepted device of that identity and the inviter named by the request context. A cryptographically valid offer copied from another identity's directory is invalid in the receiving directory. For a verified offer, its observation and active index SHALL commit before that offer participates in uniqueness or expiry decisions; a storage failure leaves the lookup indeterminate and fails closed. An unreadable payload SHALL create no new observation, but if its path already has a verified observation and active digest, temporary unreadability SHALL preserve both, make lookup and expiry indeterminate, and perform no cleanup or tombstone action. When the same digest becomes readable again it SHALL resume from the original first-observed time. Cleanup SHALL delete an earlier observation and active index only after a readable payload is proven invalid or cross-directory, or the record is authoritatively removed, confirmed, or tombstoned. Thus a directory writer cannot grow local durable state with arbitrary differing bytes, temporary blob unavailability cannot refresh a verified offer, and this runtime cannot act on another identity's ceremony.

For one pending subject — identity, device AID, and `pending-devices/<node-id>` path together — the catalog SHALL retain one active-offer digest. Rewriting or replicating the same verified offer SHALL NOT move its first-observed time. A same-endpoint retry may supersede it only with another fully verified ceremony. Supersession SHALL use a `keri-v1` intent naming the pending path, old/new offer digests, old/new catalog generations, and exact new `PDR1`. Recovery SHALL keep the old observation when only the valid old payload remains, atomically install the new observation/index and delete the old when only the valid new payload remains, delete both observations/index when neither remains, and fail the subject closed as a conflicting pending state when both remain visible. No reopen may retain both as active or lose the observation for the sole valid payload that remains. A future or rewritten timestamp therefore cannot extend an offer's life, and the timestamp never contributes to authorization. An unconfirmed verified registration SHALL expire 86,400 seconds after its effective creation time and cleanup SHALL tombstone it. Pre-profile directory state is discarded by this change's migration plan and SHALL NOT be assigned lifecycle records. A post-burn storage or ticket-mint failure SHALL retain the uniform remote refusal while producing a typed local diagnostic.

#### Scenario: A completed link leaves the newcomer confirmed
- **WHEN** runtime B links into an identity hosted on runtime A
- **THEN** the identity's confirmed device set contains B's node id; normally nothing remains pending, and if the tombstone was interrupted its durable cleanup is resumed without rolling the link back

#### Scenario: A link that fails after the import confirms nothing
- **WHEN** a linking fails after importing the replicas but before writing the confirmed-device record, and rolls back
- **THEN** the dialing device is not in the identity's confirmed device set

#### Scenario: Abandoned pending registrations expire
- **WHEN** pending registrations remain unconfirmed for 24 hours across re-import or restart
- **THEN** cleanup tombstones them and none enters the confirmed device set

#### Scenario: Confirmation wins before expiry
- **WHEN** a pending device confirms before 24 hours pass
- **THEN** it enters the confirmed set exactly once and its pending record is removed

#### Scenario: Invalid pending bytes create no durable lifecycle state

- **WHEN** a directory writer submits any number of distinct pending payloads whose canonical wrapper, path binding, signatures, anchor, or accepted chain does not verify
- **THEN** none creates a pending-observation or active-offer record, and cleanup removes any observation for a payload that later becomes invalid or tombstoned

#### Scenario: A pending offer copied between identity directories is inert

- **WHEN** a valid `PDR1` from identity A is copied unchanged to a matching endpoint path in identity B's directory
- **THEN** B rejects it because its signed root and inviter do not belong to B, creates no pending-observation or active-offer record, and performs no expiry or tombstone action on its strength

#### Scenario: Pending supersession is crash-consistent

- **WHEN** a verified same-endpoint retry replaces one active offer and the process stops after any intent, directory-write, or catalog-batch boundary
- **THEN** reopen associates exactly one first-observed record with the verified pending payload that remains, removes the superseded observation, and never refreshes an unchanged offer

#### Scenario: Temporary payload unavailability does not refresh pending lifetime

- **WHEN** a verified pending offer becomes unreadable and later the same offer digest becomes readable again
- **THEN** its original first-observed record and active index remain, lookup and expiry are indeterminate while unreadable, and the 86,400-second lifetime resumes from the original time rather than restarting

#### Scenario: A crash after confirmation commit preserves the link
- **WHEN** the confirmed-device record is written and the runtime stops before tombstoning the pending record
- **THEN** the identity and its imports remain committed, startup repeats the pending tombstone, and the device is never absent from the confirmed set

#### Scenario: The newcomer writes only its own events
- **WHEN** a device completes linking
- **THEN** its directory carries its own inception written by it, and the inviter's anchoring event arrives by replication rather than under the newcomer's authorship

#### Scenario: Confirmation copies verifiable ceremony evidence
- **WHEN** the newcomer confirms after accepting a linking reply
- **THEN** the confirmed payload retains the same signed request and manifest bytes and adds the newcomer's valid signature asserting that it completed the specified local pair verification and import for the signed commitments and bound node id; another device verifies that assertion but cannot reconstruct the original ticket bytes or capability verdicts from the proof

#### Scenario: A writer cannot turn an offer into confirmation
- **WHEN** another directory writer copies the valid pending payload into a confirmed record under the same node id
- **THEN** the record grants no full access because it lacks the newcomer confirmation signature

#### Scenario: A stale endpoint cannot confirm after another endpoint appeared
- **WHEN** a second endpoint presents the same device identifier while the first endpoint's pending offer exists, and the first endpoint later confirms
- **THEN** the second presentation was refused, the first confirmation remains the only binding, and no confirmed record exists for the second endpoint

### Requirement: Post-verification local failures are observable
The inviter SHALL preserve uniform remote refusal after a linking secret is verified, but SHALL record every failure after the secret burns as a typed local diagnostic — storage or ticket-minting as before, and now also a failure to write the anchoring event and a proof bundle that exceeds a bound at redemption. This requirement is the one home for that rule: the ceremony's other requirements order the steps, and none of them restates what a post-burn failure does.

#### Scenario: Pending registration fails after burn
- **WHEN** durable storage refuses the pending-device write after a valid secret is burned
- **THEN** the peer receives the uniform refusal and the inviter records the storage failure locally

#### Scenario: The anchor write fails after burn
- **WHEN** durable storage refuses the anchoring event after a valid secret is burned
- **THEN** the peer receives the uniform refusal, the inviter records the failure locally, and no partial anchor remains

#### Scenario: A bundle over its bound at redemption is diagnosed
- **WHEN** the proof snapshot exceeds a bound after the secret is burned
- **THEN** the peer receives the uniform refusal and the inviter records the bound it exceeded

### Requirement: Cancellation cleanup precedes retry
After importing replicas and before confirmation commits, a cancelled linking attempt SHALL retain its reservation until rollback completes. Runtime shutdown SHALL wait up to 10 seconds for tracked linking and establishment cleanup, and cleanup owned by an older attempt SHALL NOT remove state committed by a later retry. Cancellation after the confirmed-device write SHALL NOT start rollback: the link is committed, its imports remain, and the tracked cleanup only finishes the pending tombstone.

A pre-commit cancelled attempt SHALL leave what a failed attempt leaves — no replica, no binding, no hosted entry, and the attempt record, the pinned heads, and the ceremony record kept on purpose — and the retry SHALL reuse that attempt record rather than assembling a second inception. The in-flight reservation that refuses a concurrent link SHALL be released when the cancelled attempt's rollback completes, so a retry is refused only while the earlier attempt is still unwinding, never because its record survived. A post-commit cancellation is not a failed attempt and startup SHALL resume only its cleanup.

#### Scenario: Retry after cancellation remains hosted
- **WHEN** linking is cancelled after import and the same identity is retried immediately
- **THEN** the retry completes only after old rollback and remains hosted after cleanup settles

#### Scenario: Shutdown completes cancellation cleanup
- **WHEN** runtime shutdown begins while rollback work is pending
- **THEN** shutdown waits within its cleanup budget and leaves no reservation or imported replica from the cancelled attempt

#### Scenario: A cancelled attempt is resumed, not restarted
- **WHEN** linking is cancelled after its inception was assembled and the same identity is retried against the same inviting device
- **THEN** the retry presents the same inception, and the identity gains one device identifier and one seal

#### Scenario: The reservation outlives the cancellation, not the attempt record
- **WHEN** a cancelled attempt's rollback has completed
- **THEN** a further link for that identity is admitted, and it finds the attempt record still on disk

#### Scenario: Cancellation after confirmation does not undo membership
- **WHEN** cancellation arrives after the confirmed-device record is written and before the pending record is tombstoned
- **THEN** the identity remains hosted and confirmed, no rollback runs, and tracked cleanup or startup completes the tombstone

## ADDED Requirements

### Requirement: The newcomer verifies before it imports
The dialing device SHALL verify the whole reply before importing any replica: the replay's root is the identity the payload names; the chain ends at the inviting device identifier the payload names; every link of the chain has the delegator named in the delegate's inception and the seal over that inception in the delegator's log; each log in the replay is internally consistent — every event chains to its predecessor by prior digest and sequence number, and no two events in the reply claim one identifier's position with different digests; the anchoring event seals this device's own inception; the manifest signature verifies under the inviting device's current keys, covers the nonce this exchange carried, and matches the frames received; and no limit is exceeded.

Every event of the replay SHALL have its own signatures verified against the key state its log establishes at that point — the inception's signatures under the keys the inception declares, and each later event's signatures under the keys established by the most recent establishment event before it. This check is what makes the rest mean anything: a root inception is public material and self-addressing protects only its own configuration, so an event that delegates — an interaction event carrying a seal — is protected by nothing but its signature. Without the check, an attacker replays a genuine identity's inception, appends an interaction event sealing a device identifier of its own, and produces a chain that satisfies every structural rule above.

The 2 tickets SHALL be submitted together to the pair-verification operation defined by `data-layer-identity-store-bootstrap` before either is imported. `data-layer` SHALL recompute each domain-separated commitment under the expected `directory` or `data` role, require each ticket's write capability, and return either the one opaque byte-bound `VerifiedBootstrapPair` or the complete 2-role verdict mapping, without returning a namespace identifier or decoded ticket to `pdn-node`. The runtime SHALL import only by consuming that returned pair. Every failed verdict SHALL map into the ordered public `BootstrapTicketFailures` value specified by the caller-outcome requirement; no single-ticket verdict authorizes import. Without this joint check a chain that verifies perfectly still leaves the newcomer importing whatever stores the answering device chose — another identity's, or a pair it forked for the occasion — and hosting them under the payload's identity. This bootstrap rule SHALL NOT change independently authorized grant imports.

Tickets arrive with the proof, so a failed verification SHALL discard them without importing anything and SHALL leave the runtime hosting nothing new — they reached the party that had already presented the secret, and they are useless without the import.

After reply verification and before either import, the dialing runtime SHALL commit the accepted head of every verified identifier, each head's complete exact `KEL1` reconstruction set and seal index, the exact signed request, signed manifest, anchor location, and accepted-head snapshot containing `{aid, sequence, SAID}` plus commit-time conditional generations as one recoverable security-state transition. A completed sync session or a head digest without those exact bytes SHALL NOT satisfy this boundary. Later head generations MAY advance only by preserving each ceremony snapshot as the byte-identical verified prefix defined by `pdn-node-keri-identity`. After `data-layer` verifies both tickets and its byte-bound `VerifiedBootstrapPair` is consumed to import them, the runtime SHALL extend that same ceremony record atomically with the exact newcomer confirmation preimage and signature before writing confirmed. That signature asserts successful local completion for the signed commitments; because it carries no ticket-frame digest or verdict proof, other devices SHALL NOT treat it as independently reproducible evidence of ticket bytes or capability. Only this extended record contains the complete `Linked` `DeviceBindingProof`. A reduced record containing only identifiers, endpoints, digests, verdicts, or locally trusted fields SHALL NOT satisfy either boundary. A storage failure SHALL expose no partially new acceptance state: it fails loudly before import, preserves every previously pinned head and reconstruction set, and leaves the attempt available for retry.

Verification SHALL be internal to the reply and SHALL NOT be described as detecting duplicity: a consistent reply proves the branch it contains, not the absence of another branch elsewhere.

#### Scenario: A chain that misses the payload's identity is refused
- **WHEN** the inviter answers with valid tickets and a well-formed chain whose root is another identity
- **THEN** the link fails, no replica is imported, and the runtime hosts no new identity

#### Scenario: An anchor over another inception is refused
- **WHEN** the anchoring event seals an inception other than the dialing device's own
- **THEN** the link fails before any import

#### Scenario: A reply that forks inside itself is refused
- **WHEN** the reply carries two events claiming one identifier's sequence number with different digests, each well formed
- **THEN** verification fails before any import — and this catches a fork the inviter presents in its own answer, which is all it catches

#### Scenario: A chain ending elsewhere is refused
- **WHEN** the reply's chain is well formed and rooted at the payload's identity but ends at a device identifier other than the one the payload names
- **THEN** verification fails before any import

#### Scenario: An event with an invalid signature is refused
- **WHEN** the reply's chain is structurally perfect but one event's signatures do not verify under the key state its log establishes
- **THEN** verification fails before any import

#### Scenario: A genuine inception with a forged delegation is refused
- **WHEN** the reply carries an identity's real inception followed by an interaction event that seals the answering device's identifier and is signed by keys the inception does not establish
- **THEN** verification fails before any import, and the runtime hosts nothing

#### Scenario: Tickets to another store set are refused
- **WHEN** the reply's chain verifies and reaches the payload's identity, and the directory ticket recomputes to a commitment the identity's inception does not seal for the directory role
- **THEN** verification fails before any import, with a reason distinguishable from a chain that misses the identity, and the runtime hosts no new identity

#### Scenario: A read-only bootstrap ticket is refused
- **WHEN** the reply's tickets match the sealed role-tagged commitments but one of them carries no write capability
- **THEN** verification fails before any import with one `BootstrapTicketFailures` entry containing `BootstrapTicketInsufficientCapability` and the affected role

#### Scenario: A malformed bootstrap ticket has its own reason

- **WHEN** either bootstrap ticket cannot be decoded canonically
- **THEN** verification fails before any import with a `BootstrapTicketMalformed` entry for every malformed role, distinct from commitment and capability failures

#### Scenario: Two ticket failures remain visible

- **WHEN** the directory ticket is malformed and the data ticket has a commitment mismatch
- **THEN** verification fails before any import with 2 `BootstrapTicketFailures` entries ordered as `directory`/`BootstrapTicketMalformed`, then `data`/`StoreCommitmentMismatch`

#### Scenario: Pair verification exposes no namespace capability
- **WHEN** `pdn-node` submits both exact bootstrap ticket blobs, both sealed commitments, and the authenticated fallback to `data-layer`
- **THEN** it receives only a consuming `VerifiedBootstrapPair` or the complete typed 2-role failure mapping, never a namespace identifier, decoded ticket, single-ticket verdict, or Boolean

#### Scenario: Accepted security state is committed before the imports
- **WHEN** verification succeeds
- **THEN** the accepted heads and the complete ceremony record are committed durably before the directory is imported

#### Scenario: A full disk cannot weaken the accepted security state
- **WHEN** storage refuses the accepted-head or ceremony-record commit after reply verification
- **THEN** `link` fails loudly before importing either replica, prior pinned heads remain unchanged, and the attempt remains available for retry

### Requirement: Both sides sign, over distinct transcripts
The dialing device SHALL sign the exact profile-1 request preimage, the inviter SHALL sign the exact profile-1 manifest preimage, and after verification the dialing device SHALL sign the exact profile-1 confirmation preimage. No generic serializer output or reconstructed map is a signed transcript. Request and manifest both cover both endpoints; confirmation covers the subject endpoint plus digests of those 2 signed objects, the sealed store commitments, anchor, and newcomer key state. The domain labels prevent cross-ceremony reuse, the endpoint fields prevent replay on another connection, the nonce ties the inviter answer to this exchange, and the third signature prevents a directory writer from promoting an offer the newcomer never accepted.

The inviter's signature over the manifest is what establishes that the party answering controls the chain's last identifier now, and the nonce is what makes that statement about this exchange rather than about any exchange. The anchoring event SHALL NOT be relied on for it: a retry reuses the anchor by design, so an anchor may predate the connection by hours and proves only that the delegation was authorized at some point. A newcomer SHALL therefore refuse a reply whose manifest signature does not cover the nonce it sent, even when every event in the reply verifies.

The dialing device SHALL durably keep the complete 3-signature `Linked` proof and accepted-head snapshot; commit-time generations guard the acceptance batch, while later heads validate the snapshot as an exact prefix. The referenced current head records SHALL retain their complete exact-byte reconstruction evidence. Pending SHALL be canonical `PDR1` whose inner offer carries the exact request and manifest; confirmed SHALL retain both and add the exact confirmation. A digest, identifiers and endpoints without signatures, a manifest without the request, a confirmed record without confirmation, or reconstruction from locally trusted fields SHALL NOT satisfy this requirement.

#### Scenario: A recorded reply is refused on a later exchange
- **WHEN** a reply captured from an earlier successful ceremony, manifest signature and all, is presented in a new exchange whose nonce differs
- **THEN** verification fails, because the signature covers the earlier nonce, and nothing is imported

#### Scenario: A replayed request is refused on a second connection
- **WHEN** a captured request is presented on a different connection while its secret is still live
- **THEN** the inviter refuses, and the pending invite is unaffected if the secret was never valid there

#### Scenario: A signature over the same fields under another label does not verify
- **WHEN** a signature over the same bindings, made under a different domain label, is presented as this ceremony's transcript
- **THEN** verification fails

#### Scenario: The ceremony's record survives a restart
- **WHEN** a runtime restarts after linking
- **THEN** it still holds the complete canonical signed request and manifest, their anchor location and accepted-head snapshot, and validates each snapshot as a byte-identical prefix of the current exact reconstruction evidence even when the current head generation advanced

### Requirement: The proof bundle is bounded, and the bound is checked three times
Every request and reply frame SHALL obey the profile-defined complete-body limit, and every request inception and reply signed-event frame SHALL obey the profile-defined shared signed-event-material limit. The transport prefix, exact numeric limits, signed-event definition, and `KEL1`/`PDL1` overhead accounting have one normative home in `pdn-node-keri-wire-profile`; this capability defines when the ceremony applies them. The request as a whole SHALL independently fit the complete-body limit. Direct postcard/Serde encoding of protocol structs SHALL NOT define `/pdn/linking/1`; the exact `PDL1` body kinds, fields, lengths, order, ticket text, and end marker come from that profile.

Profile 1 SHALL additionally enforce these fixed policy bounds: at most 1,968 signed-event frames per reply bundle, at most 16,777,216 encoded reply-body bytes, at most 32 delegation edges from root to newcomer, and at most 1,024 accepted events per identifier. The 1,968 limit is also the maximum flat inventory whose manifest frame fits the profile's complete-body limit; its derivation and exact 1,968/1,969 body sizes are owned by `pdn-node-keri-wire-profile`. Root depth is zero. Bundle bytes SHALL be the sum of complete canonical `PDL1` reply bodies, including magic, kind, lengths, objects, signatures, tickets, and end body, excluding only the 4-byte transport prefixes; the request is not part of the reply bundle. Applicable limits SHALL be checked when an invite is minted, by the inviter on the exact encoded snapshot, and by the newcomer while reading.

The check at minting SHALL reserve room rather than measure nonexistent bytes: one further delegation level, one further inviter event, a largest-permitted anchoring signed-event payload together with its maximum frame-envelope contribution inside the bundle bound, and the anchor's additional 33-byte inventory element inside the resulting manifest. It SHALL compute the prospective post-anchor event count and manifest-body size and refuse minting unless both fit. A device exactly at a relevant limit SHALL be refused an invite. The newcomer's signed inception and complete request body are first checked at redemption because minting cannot know them.

On both reading sides the profile bounds SHALL limit the read itself: before allocating or reading a claimed body, the inviter SHALL reject a request prefix over the profile's complete-body limit and the newcomer SHALL reject any reply prefix over the same limit. The inviter SHALL reject request inception material over the profile's shared signed-event-material limit before anchoring; the newcomer SHALL reject reply event material over that same limit before accepting it and stop when the accumulated encoded frame-body bytes or event count crosses a bundle bound. Linking SHALL use 1 caller-supplied absolute deadline computed before dialing; dial, request write, streamed reply, ticket verification/import, catch-up, confirmation, and cleanup each receive only the remaining duration, with no phase-specific reset or reserved slice. Expiry of that deadline at any phase is a timeout failure subject to the phase's existing rollback/commit boundary.

A bundle exceeding a limit at redemption SHALL be refused uniformly toward the peer and recorded as a typed local diagnostic. That refusal precedes the anchoring, so it leaves no key event and no directory entry — though the invite is already burned by then, and the refusal does not return it.

#### Scenario: Each limit refuses on its own
- **WHEN** a reply exceeds any one of the bounds
- **THEN** verification fails with the limit reason and nothing is imported

#### Scenario: Minting reserves room for the redemption's own events
- **WHEN** a linking invite is requested on a device whose chain has no room for one further delegation level, one further event body, or the anchor's additional manifest-inventory element
- **THEN** minting is refused with a typed error and no pending invite exists

#### Scenario: Flat manifest inventory has an exact event ceiling

- **WHEN** the prospective post-anchor snapshot contains 1,968 signed-event frames, and separately when it contains 1,969
- **THEN** the first manifest body is 65,516 bytes and fits, while the second would be 65,549 bytes and is refused before the anchor or pending record is written

#### Scenario: An oversized inception is refused at redemption
- **WHEN** a request presents a delegated inception larger than the per-event bound
- **THEN** the request is refused before anything is anchored, and the bound is recorded locally

#### Scenario: An oversized request prefix allocates nothing

- **WHEN** a dialer announces a request body longer than the profile's complete-body limit
- **THEN** the inviter refuses before allocating or reading the claimed body and writes no anchor or pending state

#### Scenario: A chain that grew after minting is refused at redemption
- **WHEN** the inviting device's log grows past a limit between minting an invite and its presentation
- **THEN** the ceremony refuses before anchoring, no key event and no device record are written, and the failure is recorded locally

### Requirement: The critical section holds the log while it anchors
On a presented secret the inviter SHALL, in order: verify and burn the secret; check the delegated inception and canonical request; take its key event log under a write lock; under that lock check pending and confirmed uniqueness; build the prospective anchor and proof snapshot; compute the exact post-anchor event count, encoded event-body total, and canonical manifest-body size; check every bound; write exactly that anchor; sign the already-sized canonical manifest; construct canonical `PDR1` around the `PendingLinkedOffer`; durably establish its verified observation or supersession intent; write that exact `PendingRecord`; mint the tickets; and only then stream the same manifest and frames. Only the newcomer can later complete `DeviceBindingProof` by signing confirmation.

The lock SHALL cover the device-binding uniqueness check, snapshot, anchor, manifest signature, and pending write together. Without that span 2 concurrent endpoints holding the same device keys could both observe no record and each obtain a valid proof, or another event could land between snapshot and anchor and leave the manifest describing a stream the log no longer matches. Anchoring SHALL be idempotent for a repeated inception from the same endpoint: an inception already sealed in the log SHALL NOT be sealed a second time.

#### Scenario: A retry does not anchor twice
- **WHEN** a device presents the same delegated inception again, with a fresh invite from the same inviting device
- **THEN** the inviter's log still carries exactly one seal over that inception

#### Scenario: The manifest matches the log
- **WHEN** the inviter anchors while its own device is otherwise active
- **THEN** the events described by the manifest are the events its log holds

### Requirement: The ceremony establishes control of the chain and nothing wider
A completed ceremony SHALL establish exactly 3 things: the answering device controls, at the time of the exchange, a device identifier whose chain reaches the named identity; request and manifest bind both parties to the exact endpoints, and newcomer confirmation proves that the newcomer accepted those signed objects and store commitments; and the imported stores are those the identity history seals. Pending replicates the first 2 signed objects but confers nothing; confirmed replicates all 3. Nothing SHALL treat the immutable proof as a current endpoint after loss or a later supersession.

It does not establish any of the following, and no requirement SHALL be written as though it did. A payload substituted whole — screen or code replaced before the human ever saw the genuine one — yields a consistent chain for the wrong identity; the defence is the out-of-band channel the human used, not anything in this ceremony. The one-time secret proves possession of that secret and nothing about which screen displayed it. A consistent reply proves the branch it contains and not the absence of another branch elsewhere, so duplicity by the identity's own devices is out of reach until witnesses exist. An observer of a payload learns which identity is being joined, as it already does for a pairing invite — accepted here, and not narrowed by anything in this change. And access remains bearer-bounded: whoever holds the directory's write ticket reads and writes the whole directory, key events included, so a leaked ticket is not narrowed by anything here.

#### Scenario: A wholly substituted payload is not detected
- **WHEN** a device links from a payload an attacker substituted in full, naming an identity the attacker controls
- **THEN** the ceremony completes, since every check it makes passes — the boundary of the guarantee, not a defect of it

#### Scenario: The answering device must control the chain's last identifier
- **WHEN** a device answers with a chain reaching the payload's identity but cannot sign with the keys the chain's last identifier establishes
- **THEN** it cannot produce a manifest signature over this exchange's nonce and bindings, and the ceremony fails even if the reusable anchoring event already exists

#### Scenario: A leaked directory ticket reaches the key events too
- **WHEN** a holder of an identity's directory write ticket that is not one of its devices reads the replica
- **THEN** it reads the key events as it reads every other entry, and nothing in this change narrows that

### Requirement: The ceremony survives its operating conditions
Storage failures after the secret burns SHALL keep the refusal uniform toward the peer while producing a typed local diagnostic, and this SHALL hold for the anchoring event and the key event writes exactly as it already holds for the pending device record.

Concurrency on one key event log SHALL be serialized by the write lock of the critical section: a second linking, or the device's own activity, SHALL NOT interleave between a snapshot and the anchor it describes. Several identities on one runtime SHALL keep their key material and their in-flight ceremonies separate, so an interruption in one leaves the others untouched.

A reply that stops mid-stream SHALL surface as a typed outcome within the caller's budget, distinguishable from a refusal and from a catch-up timeout, and SHALL NOT hang: the frames already read are discarded and nothing is imported.

Conditions deliberately left out of this change, so their absence is a decision and not an oversight: a device rejoining after a long partition with a stale view of an identity's history — it converges by replication, and nothing here shortens that; a key store the operating system has locked or lost — the failure surfaces as a storage error and there is no repair path in this change; and every condition that presumes rotation, revocation, or witnesses.

#### Scenario: A full disk after the burn refuses uniformly
- **WHEN** durable storage refuses the anchoring event after a valid secret is burned
- **THEN** the peer receives the uniform refusal, the inviter records the failure locally, and no partial anchor is left behind

#### Scenario: Two linkings against one device do not interleave
- **WHEN** two devices link against the same inviting device at the same time
- **THEN** each is anchored as its own event, and each manifest describes the log as it stands with that anchor

#### Scenario: One runtime's identities do not share ceremony state
- **WHEN** a runtime has an interrupted linking for identity X and creates identity Y
- **THEN** Y is created with its own key material, and X's attempt is unaffected

#### Scenario: A reply cut off mid-stream is its own outcome
- **WHEN** the inviter stops sending after some frames and the connection stays open until the budget runs out
- **THEN** `link` fails within the budget with an outcome distinguishable from a refusal and from a catch-up timeout, and nothing is imported

### Requirement: The inviter checks the inception it is asked to anchor
Before anchoring, the inviter SHALL check the delegated inception the request carries: its delegator field names this device's own identifier; its identifier is the qualified digest of the event itself; its signatures verify under the keys the event declares, at the threshold it declares; and its pre-rotation commitment is non-empty, since an inception that commits to nothing is abandoned at birth and could never rotate. A request failing any of these SHALL be refused uniformly, before the secret's burn is followed by any durable write.

#### Scenario: An inception naming another delegator is refused
- **WHEN** the request's inception names a delegator other than the inviting device
- **THEN** the request is refused and nothing is anchored

#### Scenario: An inception whose identifier is not its digest is refused
- **WHEN** the request's inception carries an identifier that is not the digest of that event
- **THEN** the request is refused and nothing is anchored

#### Scenario: An unsigned or under-signed inception is refused
- **WHEN** the request's inception carries no valid signature, or fewer than its declared threshold
- **THEN** the request is refused and nothing is anchored

#### Scenario: An inception with an empty pre-rotation commitment is refused
- **WHEN** the request's inception commits to no next keys
- **THEN** the request is refused and nothing is anchored
