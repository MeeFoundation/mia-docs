## REMOVED Requirements

### Requirement: An identity is provisioned with its full store set on its first device

**Reason**: Its store set includes the identity's data namespace and the PMS's `data` ticket, both removed by this change; the requirement returns as "An identity is provisioned with its PMS on its first device".

**Migration**: None: what an identity keeps for itself is a record in a pod it creates.

### Requirement: Link returns caught up, and failure leaves no local residue

**Reason**: Two of its cases — the data namespace's first sessions and a namespace held under a grant beside the link — rest on what this change removes; the requirement returns as "Link returns caught up, and a failed link leaves nothing behind".

**Migration**: None.

## MODIFIED Requirements

### Requirement: The dialogue is one raw exchange on the linking ALPN
Linking SHALL dial the payload's node address under the dedicated linking ALPN and run one raw bidirectional exchange: the dialing device presents the format version and the secret; the inviter — after the verify-and-burn and the registration below — answers with the bootstrap ticket. The request SHALL carry no node id: the inviter takes the newcomer's node id from the connection's authenticated peer identity. A payload whose format version the dialing runtime does not speak SHALL be refused before dialing. Linking into an identity the dialing runtime already hosts SHALL be refused before dialing.

**Example:** the request a2 (Alice's second device) sends to a1 (her first) on ALPN `/pdn/linking/0`, the secret shown as 32 bytes of `0x77`.

```
message:      LinkingRequest { version: 0, secret: [0x77; 32] }
encoded as:   21 00 00 00  00  77 77 … 77 (32 bytes)
encodes:      frame length 33 (u32 little-endian), version 0 (one byte), the secret (32 bytes, no length prefix)
not in it:    a2's node id; a1 takes it from connection.remote_id(), the connection's authenticated peer
```

#### Scenario: Linking completes between two runtimes
- **WHEN** runtime B links with a live linking invite minted on runtime A
- **THEN** the dialogue completes over the linking ALPN and B holds the PMS write ticket from the reply

#### Scenario: An unknown payload version is refused before dialing
- **WHEN** link is given a payload with an unsupported format version
- **THEN** it refuses without opening a connection

#### Scenario: Linking into an already-hosted identity is refused before dialing
- **WHEN** link is invoked on a runtime that already hosts the payload's identity
- **THEN** the operation is refused and no dialogue runs

### Requirement: The secret is verified and burned atomically, before any state
On a presented secret the inviter SHALL atomically check-and-burn against its pending linking invites: present and unexpired → burned and the dialogue proceeds; expired, already burned, or unknown → refused. The check SHALL precede every state change, so a refused attempt leaves no observable state on the inviter: no device record written, no ticket minted. An unpresented secret SHALL expire at the end of its lifetime and thereafter be refused. A refused presentation SHALL NOT burn a live pending invite, and refusals SHALL be uniform — the dialer cannot distinguish wrong from expired from already burned.

**Example:** a2 presents a secret to a1 (Alice's second and first devices); the invite lives 2 minutes.

| secret presented | a1's `pending_linking_invites` afterwards | a2's link gets |
|---|---|---|
| minted 30 s ago, unused | entry removed; the dialogue goes on | the reply |
| the same secret again | nothing left to remove | `LinkingRefused` |
| minted 3 minutes ago, unused | entry removed | `LinkingRefused` |
| a live pod invite's secret | unchanged; `pending_pod_invites` keeps it | `LinkingRefused` |
| never minted | unchanged; a live invite still links | `LinkingRefused` |
| every refusal: one close with code 0 and an empty reason, no device record written, no ticket minted | | |

#### Scenario: A second presentation of the same secret is refused
- **WHEN** linking completed against an invite and a second link presents the same secret
- **THEN** the second attempt is refused, and the identity's device set is exactly as the first linking left it

#### Scenario: An expired secret is refused
- **WHEN** a secret is presented after its lifetime has elapsed
- **THEN** the attempt is refused and no observable state exists on the inviter — no device record, no ticket issued

#### Scenario: A wrong secret is refused and burns nothing
- **WHEN** a dialer presents a secret that was never minted while a linking invite is pending
- **THEN** the attempt is refused with no observable state on the inviter, and a subsequent presentation of the pending invite's real secret succeeds

### Requirement: The inviter registers the newcomer as pending before replying
After the burn, the inviter SHALL write the newcomer's device record into its own PMS replica as pending — using the node id of the connection's authenticated peer, never a claimed field — and only then reply. The registration is a local write on a device that already holds the PMS, so no cross-node delivery sits in the linking critical path, and the identity's existing devices learn of the newcomer through ordinary PMS replication. A pending record SHALL confer nothing: session classification consults the confirmed device set alone, so a reply lost after the registration leaves a device that is visible to the identity's other devices and admitted nowhere, and a fresh invite converges. A pending record whose device never confirms SHALL be tombstoned by the first cleanup that runs 24 hours or more after the creation time its payload carries, whatever restarts or re-imports happen meanwhile, so an abandoned attempt leaves nothing that outlives it; the registration writes that payload as `01` followed by the time in 8 bytes of big-endian seconds since the Unix epoch. Cleanup SHALL treat every other payload by its shape: `01` alone is rewritten with the cleanup's own time, so that record expires 24 hours after the cleanup that first observed it; a version-1 payload of any other shape — `01` not followed by exactly 8 bytes, or followed by a time the clock cannot represent — is tombstoned by the first cleanup that observes it, without waiting 24 hours; a payload whose first byte names another version is left alone, and never expires on this build. The [private metadata store](../../data-layer/private-metadata-store/spec.md) holds when cleanup runs. The runtime's shutdown SHALL let this serving half — the burn, the registration and the reply — finish within the fixed budget it gives the serving half of every ceremony ([core](../core/spec.md)), before it stops the stores the registration writes to; a linking dialogue that would begin after that wait SHALL be refused before its secret is verified, so nothing burns.

**Example:** a1 (Alice's first device) serves the link of a2 (her second); `<a2-node-id>` comes from `connection.remote_id()`, not the request.

| # | step | what it does |
|---|---|---|
| 1 | `serving_halves.enter()` | takes a permit; once a shutdown has drained them, the dialogue is refused here, nothing burned |
| 2 | `verify_and_burn` | the secret leaves `pending_linking_invites` |
| 3 | `add_pending_device` | `pending-devices/<a2-node-id>` in Alice's PMS on a1: a local write, no sync awaited |
| 4 | the PMS write ticket minted | |
| 5 | the reply is sent | a reply that never reaches a2 leaves it pending: visible to Alice's devices, admitted by none |
| `Runtime::shutdown` waits up to 10 s (`SHUTDOWN_SERVING_BUDGET`) for a permit held in steps 1 to 5 before it stops the stores | | |

#### Scenario: The newcomer is registered on the inviting device
- **WHEN** runtime B completes the linking dialogue against runtime A
- **THEN** A's PMS replica already contains B's node id, with no wait on any sync exchange

#### Scenario: The registered id is the connection's, not a claimed one
- **WHEN** the inviter registers a newcomer
- **THEN** the recorded node id equals the authenticated endpoint id of the dialing connection

#### Scenario: A pending registration is served nothing
- **WHEN** a device is registered as pending in an identity's PMS and requests a session on the record store of a pod that identity is a member of
- **THEN** the session is refused as for an unhosted store, while a confirmed device of the identity is served the store whole

#### Scenario: A dialogue lost after commit converges on a fresh invite
- **WHEN** a linking dialogue fails after the burn and the registration, and the same device later links with a fresh invite
- **THEN** the public linking service completes the second link, the identity remains hosted, the device is confirmed exactly once, and no pending registration remains

#### Scenario: Abandoned pending registrations expire
- **WHEN** pending registrations remain unconfirmed for 24 hours across re-import or restart
- **THEN** cleanup tombstones them and none enters the confirmed device set

#### Scenario: Confirmation wins before expiry
- **WHEN** a pending device confirms before 24 hours pass
- **THEN** it enters the confirmed set exactly once and its pending record is removed

### Requirement: Post-verification local failures are observable
The inviter SHALL preserve uniform remote refusal after a linking secret is verified, but SHALL record every storage or ticket-minting failure after the secret burns as a typed local diagnostic.

**Example:** a1 (Alice's first device) fails after burning the secret a2 (her second) presented; identity = Alice, newcomer = a2's `NodeId`.

| failing step | a2's link gets | a1's `subscribe_linking_failures()` receives |
|---|---|---|
| `add_pending_device` | `LinkingRefused` | `LinkingLocalFailure::PendingDeviceWrite { identity, newcomer }` |
| PMS write-ticket mint | `LinkingRefused` | `LinkingLocalFailure::PmsTicketMint { identity, newcomer }` |

#### Scenario: Pending registration fails after burn
- **WHEN** durable storage refuses the pending-device write after a valid secret is burned
- **THEN** the peer receives the uniform refusal and the inviter records the storage failure locally

### Requirement: The newcomer confirms itself once the tickets are in hand
A device that has imported its identity's PMS SHALL promote its own pending record to confirmed. Writing that record requires the PMS's write ticket, so the record is evidence the reply arrived — which the inviter, having sent it into a connection that may drop, cannot establish. Until the confirmation replicates, the identity's other devices refuse the newcomer's sessions on the identity's pods and serve it once the record arrives.

The confirmation SHALL be written only after the newcomer's own hosting record is written, and never before it. What a device writes into the PMS replicates to every other device of the identity, and no rollback reaches it there — so a link that published before it committed could fail locally and still leave the identity naming a device that hosts nothing, with no operation anywhere able to take that name back. A written record survives a process kill, but its rename is not synced to disk ([restart recovery](../restart-recovery/spec.md)): an operating-system crash or a power loss just after the link can take the record back after the confirmation has replicated, and the identity then names a device that hosts nothing. A confirmation that fails after the commit SHALL NOT fail the link and SHALL NOT be rolled back: the device is hosted and recorded, and it SHALL write the record itself whenever it finds its identity's PMS without it — which is also how a device that was interrupted between the two comes back whole.

The confirmed set is written by the devices themselves, each holding the PMS's write ticket, and the newest write at a key is the one that reads back. Removal therefore cannot be expressed as the absence of a device's record: any device may write its own record again — and a device recovering its own hosting has reason to — after which the removal is simply gone, with nothing left to say it ever happened. Device revocation, when it is designed, SHALL be a record of its own, which a device consults before writing its own record and obeys, rather than the deletion of the record it revokes.

**Example:** a2 (Alice's second device) links from an invite of a1 (her first) and is killed at one of three moments; a2's hosting record is `identities/<alice-hex>/pms` on a2's disk.

| killed after | a2's hosting record | Alice's PMS for a2 | a2's next start |
|---|---|---|---|
| the catch-up | absent | `pending-devices/<a2-node-id>` | hosts nothing; the key expires 24 h after a1 wrote it |
| the commit | written | `pending-devices/<a2-node-id>` | hosts Alice; the armer's first sweep confirms a2 |
| `confirm_device` | written | `devices/<a2-node-id>` = `01` | hosts Alice |

#### Scenario: A completed link leaves the newcomer confirmed
- **WHEN** runtime B links into an identity hosted on runtime A
- **THEN** the identity's device set contains B's node id and nothing remains pending for it

#### Scenario: A link that fails after the import confirms nothing
- **WHEN** a linking fails after importing the replicas and rolls back
- **THEN** the dialing device is not in the identity's confirmed device set

#### Scenario: A link publishes nothing before it commits
- **WHEN** a link is held at its commit point and the identity's PMS is read from another of its devices
- **THEN** the dialing device is not in the confirmed set, and it appears there only after the commit is released

#### Scenario: A link that cannot be recorded leaves nothing on the identity
- **WHEN** a link fails because the dialing device cannot write the identity's hosting record
- **THEN** it hosts nothing, the identity's PMS never names it, and a later link from the same device succeeds and is named

### Requirement: The reply hands over the bootstrap tickets
The linking reply SHALL carry a write ticket to the identity's PMS, minted fresh from the replica the inviting device hosts locally — the ceremony reads nothing through PMS ticket entries, so no payload wait sits in the critical path. The dialing runtime SHALL import it as the identity's PMS replica. Every device of an identity can therefore mint a linking invite — the PMS is hosted wherever creation or linking brought it up, first device or not — and everything else the identity holds reaches the new device through its PMS: the identity key, and the tickets of the pods it is a member of, which the armer opens.

**Example:** the `LinkingResponse` a1 sends a2 (Alice's first and second devices): postcard, one frame of at most 65,536 bytes.

| field | what a1 puts in it | what a2 does with it |
|---|---|---|
| `pms` | write ticket minted from a1's PMS replica | appends a1's address from the payload, imports it as Alice's PMS |
| a1 reads nothing under `tickets/` to build it; a3 linking from a2 gets a ticket minted from the replica a2's own reply brought up | | |

#### Scenario: The newcomer comes up with the full store set
- **WHEN** runtime B links into an identity and the PMS's first sync completes
- **THEN** B hosts the identity's PMS, and a record either runtime writes into it becomes readable on the other

#### Scenario: Linking through a linked device
- **WHEN** device 2 was itself linked into an identity, and device 3 links from an invite minted on device 2
- **THEN** device 3 comes up with the PMS, and all three devices' device sets converge to three

### Requirement: Cancellation cleanup precedes retry
After importing the PMS, a cancelled linking attempt SHALL retain its reservation until rollback completes. Runtime shutdown SHALL wait up to 10 seconds for tracked linking cleanup, and cleanup owned by an older attempt SHALL NOT remove state committed by a later retry.

**Example:** a2 (Alice's second device): the host drops link #1 after its import and retries at once on a fresh invite.

| t | link #1, dropped | link #2, the retry |
|---|---|---|
| t0 | import done; the future is dropped | |
| t1 | `LinkRollbackGuard`'s drop spawns `undo_link`; the reservation stays held | refused before dialing: `LinkingInProgress` for Alice, the fresh invite unburned |
| t2 | `undo_link` done, then the reservation released | |
| t3 | | dialogue, import, commit: Alice hosted, nothing of #1 left to undo it |
| a `Runtime::shutdown` at t1 waits up to 10 s for `undo_link` before it stops the node | | |

#### Scenario: Retry after cancellation remains hosted
- **WHEN** linking is cancelled after import and the same identity is retried immediately
- **THEN** the retry completes only after old rollback and remains hosted after cleanup settles

#### Scenario: Shutdown completes cancellation cleanup
- **WHEN** runtime shutdown begins while rollback work is pending
- **THEN** shutdown waits within its cleanup budget and leaves no reservation or imported replica from the cancelled attempt

## ADDED Requirements

### Requirement: An identity is provisioned with its PMS on its first device
Creating an identity SHALL provision its store set on the creating device: the PMS is created, the creating device's node id is recorded in the PMS's device set, and the identity key pair is stored in it. The linking dialogue below hands the PMS over directly, and everything else an identity holds is reached through it.

**Example:** Alice's PMS right after `create()` on a1 (Alice's first device); `<a1-node-id>` is a1's `NodeId` in 64 lowercase hex.

| key | value | what it records |
|---|---|---|
| `devices/<a1-node-id>` | `01` | a1, the only confirmed device |
| `identity-key` | the serialized identity key pair | the key Alice's `PdnId` derives from |

#### Scenario: Creation provisions the PMS
- **WHEN** an identity is created on a runtime
- **THEN** the runtime hosts the identity's PMS with the creating device in its device set and the identity key pair in it, and hosts no other store for the identity

### Requirement: Link returns caught up, and a failed link leaves nothing behind
`link` SHALL NOT report success until the imported PMS has completed one successful sync exchange that started after the import — one bounded wait, not a retry loop, which a successful session with any peer ends; in practice that peer is the inviter, the only address the PMS ticket carries; a PMS that cannot catch up within the caller's timeout SHALL surface as an error, not a hang. The property waited on is a completed session, not arrived content: a runtime that never synced and one that synced and found nothing new must not be confused, so polling the PMS's contents does not discharge this requirement. The first exchange counts however quickly it finishes: the wait SHALL be listening before the arming starts the PMS's sync, because an exchange that finished before the wait began would leave it waiting for the next one, which the node's periodic reconcile pass may bring only after the caller's budget is spent.

The caller's timeout SHALL bound the whole act, the dialogue included: the dialogue spends from the budget first and the catch-up gets what remains, so a dialed inviter that never answers costs the caller its budget — surfaced as its own typed outcome — and never the transport's idle timeout. Without this bound the budget would govern only the last third of the act, and a hung inviter would hold the caller for as long as the transport tolerates a silent connection, however small a budget the caller named.

The dialing runtime SHALL arm the identity for session classification the moment its PMS is imported. The cost of arming early is bounded and fail-closed: while the PMS is still converging, callers it cannot yet resolve are refused, and a refused device is served once its record replicates in — the node's periodic reconcile pass is the retry cadence.

On any failure after import, the dialing runtime SHALL undo what this linking did in this order — the PMS replica, then the identity's half of the node, whose removal disarms the identity for session classification — so a failed link leaves no local residue and the identity is unknown to the runtime again. The emptied store the undo leaves, and the subdirectory holding it, MAY remain; a start SHALL host nothing from a subdirectory the runtime's record of hosted identities does not name. A device record already committed on the inviter side may remain, per the lost-reply posture above.

**Example:** a2 (Alice's second device) runs `link(payload, 30 s)`; its steps in order, and what running out of budget at each leaves.

| # | step | what it does |
|---|---|---|
| 1 | dialogue with a1 | spends from the 30 s first; still in flight at the deadline: fails, nothing to undo |
| 2 | `provision_identity`, then import the PMS | |
| 3 | `watch_catch_up` | listening before anything can sync the PMS |
| 4 | `host_identity` | armed, and the PMS's sync starts; a caller it cannot resolve yet is refused |
| 5 | wait with what is left | for the first successful session started after step 3, with any peer; none by the deadline: fails; `undo_link` drops the PMS, then `unhost_identity` drops Alice's half of the node, which disarms her |

#### Scenario: Success implies the PMS is caught up
- **WHEN** `link` returns success
- **THEN** the newcomer's PMS replica has completed a successful sync exchange started after the import, and the device set it reads locally includes the identity's existing devices

#### Scenario: The first exchange counts however quickly it finishes
- **WHEN** the PMS's first sync exchanges finish before the link begins its wait, and the caller's budget ends before the next periodic reconcile pass
- **THEN** `link` succeeds on the first exchange rather than failing with the catch-up timeout

#### Scenario: A timed-out link leaves nothing behind on the dialing node
- **WHEN** the PMS cannot complete a first sync within the timeout
- **THEN** `link` fails, the identity is absent from the runtime's hosted identities and disarmed for classification, and operations addressed to it are refused as unknown — as they were before the attempt, not as storage errors against a dropped replica

#### Scenario: A start hosts nothing from what a failed link left
- **WHEN** a link fails after its import and the runtime is restarted on the same directory
- **THEN** the identity is not hosted, nothing of it is readable, and the subdirectory the failed link created carries no identity into the hosted set
