## ADDED Requirements

### Requirement: The inviting runtime answers what became of a linking invite it minted
The identity service SHALL answer, for a linking payload, what became of its secret on this runtime: pending while it is unpresented and its lifetime runs; expired once its lifetime ended unpresented; burned once a presentation verified and burned it, until the inviter has handed the newcomer its reply; used, naming the newcomer's node id — the authenticated peer of the dialing connection, the id the inviter registered as pending — from then on; and unknown for a secret this runtime does not hold for the identity the payload names — never minted here, swept after its lifetime, or minted before the runtime last started. The answer SHALL be read alone: asking writes nothing, and a presentation before or after the question is verified, burned and refused exactly as without it, so a refused presentation leaves a pending invite pending. A failure once the secret burned — the pending device's write, the ticket's mint, a reply that cannot be written — SHALL leave the invite burned. An invite's state SHALL be kept while its lifetime runs; once it has ended, an invite never presented reads expired, one presented keeps reading burned or used, and the next linking invite this runtime mints sweeps it, after which it reads unknown.

**Example:** a1 (Alice's first device) mints a linking invite for Alice with the default lifetime of 2 minutes, and a2 (her second) links with it.

| moment | `linking_invite_state(payload)` on a1 |
|---|---|
| before a2 dials | pending |
| a1 burned the secret and is writing `pending-devices/<a2-node-id>` | burned |
| a1 handed a2 the reply with the PMS write ticket | used by `<a2-node-id>` |
| the same payload after a1 restarted | unknown |
| had the pending device's write failed instead | burned |

#### Scenario: A served linking marks the invite used by the newcomer
- **WHEN** runtime B links with a linking invite minted on runtime A
- **THEN** on A the invite reads pending before the link and used by B's node id once the link returned, the same id A registered

#### Scenario: A linking cut short after the burn leaves the invite burned
- **WHEN** durable storage refuses the pending-device write after a valid secret is burned
- **THEN** the invite reads burned, never used

#### Scenario: A refused linking presentation leaves a pending invite pending
- **WHEN** a dialer presents a secret that was never minted while a linking invite is pending
- **THEN** the pending invite still reads pending

#### Scenario: A linking invite never presented reads expired after its lifetime
- **WHEN** a linking invite minted with a lifetime of 1 second is asked about 2 seconds later, and again after a further linking invite was minted
- **THEN** it reads expired the first time and unknown the second

#### Scenario: A restart forgets every linking invite's state
- **WHEN** a linking invite was used, and the inviting runtime stops and starts again on its directory
- **THEN** the invite reads unknown

## MODIFIED Requirements

### Requirement: The secret is verified and burned atomically, before any state
On a presented secret the inviter SHALL atomically check-and-burn against its pending linking invites: present and unexpired → burned and the dialogue proceeds; expired, already burned, or unknown → refused. The check SHALL precede every state change, so a refused attempt leaves no observable state on the inviter: no device record written, no ticket minted. An unpresented secret SHALL expire at the end of its lifetime and thereafter be refused. A refused presentation SHALL NOT burn a live pending invite, and refusals SHALL be uniform — the dialer cannot distinguish wrong from expired from already burned.

**Example:** a2 presents a secret to a1 (Alice's second and first devices); the invite lives 2 minutes.

| secret presented | a1's `pending_linking_invites` afterwards | a2's link gets |
|---|---|---|
| minted 30 s ago, unused | marked burned; the dialogue goes on, and the entry reads used by a2 once the reply is handed over | the reply |
| the same secret again | unchanged: it reads used by a2 | `LinkingRefused` |
| minted 3 minutes ago, unused | unchanged: it reads expired until the next linking invite sweeps it | `LinkingRefused` |
| a live pod invite's secret | unchanged; `pending_pod_invites` keeps it | `LinkingRefused` |
| never minted | unchanged; a live invite still reads pending and still links | `LinkingRefused` |
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
| 2 | `verify_and_burn` | the secret is marked burned in `pending_linking_invites` |
| 3 | `add_pending_device` | `pending-devices/<a2-node-id>` in Alice's PMS on a1: a local write, no sync awaited |
| 4 | the PMS write ticket minted | |
| 5 | the reply is sent | the invite reads used by a2; a reply that never reaches a2 leaves it pending: visible to Alice's devices, admitted by none |
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
