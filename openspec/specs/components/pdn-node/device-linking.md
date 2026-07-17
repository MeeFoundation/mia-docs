# Device linking

## Purpose

How a further device joins an identity, realizing [ADR-0012](../../architecture/adr/0012-linking-over-raw-iroh.md) on the runtime: a linking dialogue — one raw bidirectional exchange on the dedicated linking ALPN, separate from the pairing ALPN because the stakes differ (a whole-directory write ticket versus per-connection read tickets) — whose handler the runtime registers at spawn through the data-layer [assembly slot](../data-layer/node-assembly.md) and whose dial side rides the node's dial handle. The first-device counterpart belongs here too: creating an identity provisions its store set, which is what every later device is brought up onto. The dialogue hands the newcomer that store set directly — write tickets to the identity's [directory](../data-layer/private-metadata-store.md) and its [data store](../data-layer/data-store.md), minted from the inviter's local replicas and carried in the reply — so nothing in the linking critical path waits on reconciliation, and the inviter writes the newcomer's device record itself before replying. The exchange is bearer-level for now: the KERI proof of control over the presented `PdnId` is a marked step of this dialogue, deferred (ADR-0008's interim posture), and both devices must be online — pending linking invites, device removal, and revocation are future work.

## Requirements

### Requirement: An identity is provisioned with its full store set on its first device
Creating an identity SHALL provision its store set on the creating device: the private-metadata directory and the identity's data namespace are created, the creating device's node id is recorded in the directory's device set, and the data namespace's ticket is published in the directory under the `data` kind. The directory copy of the data ticket is the durable record; the linking dialogue below hands the bootstrap tickets over directly.

#### Scenario: Creation provisions directory and data namespace
- **WHEN** an identity is created on a runtime
- **THEN** the runtime hosts the identity's directory with the creating device in its device set, hosts the identity's data namespace, and the directory carries the data namespace's ticket under the `data` kind

### Requirement: A linking invite is one-time, short-lived, and bearer-free
The identity service SHALL mint a linking invite for a hosted identity: a fresh random one-time secret (32 bytes from the operating-system generator) with a short lifetime (a default with an invite-time override), held pending on the inviting runtime, and a self-contained linking payload carrying a format version, the inviting device's node address, the secret, and the identity's `PdnId`. The payload SHALL carry no ticket and no identity proof — nothing in it grants durable access, so a photographed payload expires with its secret. Minting a linking invite for an identity the runtime does not host SHALL be refused with no pending state created.

#### Scenario: The payload carries no bearer material
- **WHEN** a linking invite is minted for a hosted identity
- **THEN** its payload consists of the format version, the inviting device's node address, the one-time secret, and the identity's `PdnId` — no tickets and no identity proof

#### Scenario: Every linking invite carries a distinct secret
- **WHEN** two linking invites are minted, whether for one hosted identity or two
- **THEN** their secrets differ, and each is pending independently

#### Scenario: An invite for an unhosted identity is refused
- **WHEN** a linking invite is requested for an identity the runtime neither created nor linked
- **THEN** the operation fails with an unknown-identity error and no pending invite exists

### Requirement: The dialogue is one raw exchange on the linking ALPN
Linking SHALL dial the payload's node address under the dedicated linking ALPN — distinct from the pairing ALPN — and run one raw bidirectional exchange: the dialing device presents the format version and the secret; the inviter — after the verify-and-burn and the registration below — answers with the bootstrap tickets. The request SHALL carry no node id: the inviter takes the newcomer's node id from the connection's authenticated peer identity. A payload whose format version the dialing runtime does not speak SHALL be refused before dialing. Linking into an identity the dialing runtime already hosts SHALL be refused before dialing.

#### Scenario: Linking completes between two runtimes
- **WHEN** runtime B links with a live linking invite minted on runtime A
- **THEN** the dialogue completes over the linking ALPN and B holds the directory and data-namespace tickets from the reply

#### Scenario: An unknown payload version is refused before dialing
- **WHEN** link is given a payload with an unsupported format version
- **THEN** it refuses without opening a connection

#### Scenario: Linking into an already-hosted identity is refused before dialing
- **WHEN** link is invoked on a runtime that already hosts the payload's identity
- **THEN** the operation is refused and no dialogue runs

### Requirement: The secret is verified and burned atomically, before any state
On a presented secret the inviter SHALL atomically check-and-burn against its pending linking invites: present and unexpired → burned and the dialogue proceeds; expired, already burned, or unknown → refused. The check SHALL precede every state change, so a refused attempt leaves no observable state on the inviter: no device record written, no ticket minted. An unpresented secret SHALL expire at the end of its lifetime and thereafter be refused. A refused presentation SHALL NOT burn a live pending invite, and refusals SHALL be uniform — the dialer cannot distinguish wrong from expired from already burned.

#### Scenario: A second presentation of the same secret is refused
- **WHEN** linking completed against an invite and a second link presents the same secret
- **THEN** the second attempt is refused, and the identity's device set is exactly as the first linking left it

#### Scenario: An expired secret is refused
- **WHEN** a secret is presented after its lifetime has elapsed
- **THEN** the attempt is refused and no observable state exists on the inviter — no device record, no ticket issued

#### Scenario: A wrong secret is refused and burns nothing
- **WHEN** a dialer presents a secret that was never minted while a linking invite is pending
- **THEN** the attempt is refused with no observable state on the inviter, and a subsequent presentation of the pending invite's real secret succeeds

### Requirement: The inviter registers the newcomer before replying
After the burn, the inviter SHALL write the newcomer's device record into its own directory replica — using the node id of the connection's authenticated peer, never a claimed field — and only then reply. The registration is a local write on a device that already holds the directory, so no cross-node delivery sits in the linking critical path, and the identity's existing devices learn of the newcomer through ordinary directory replication. Commit precedes the reply: a reply lost after the registration leaves a device record with no linked device behind it, which is harmless (device records carry no liveness semantics), and a fresh invite converges.

#### Scenario: The newcomer is registered on the inviting device
- **WHEN** runtime B completes the linking dialogue against runtime A
- **THEN** A's directory replica already contains B's node id in the identity's device set, with no wait on any sync exchange

#### Scenario: The registered id is the connection's, not a claimed one
- **WHEN** the inviter registers a newcomer
- **THEN** the recorded node id equals the authenticated endpoint id of the dialing connection

#### Scenario: A dialogue lost after commit converges on a fresh invite
- **WHEN** a linking dialogue fails after the burn and the registration, and the same device later links with a fresh invite
- **THEN** the second linking completes and the device set contains the newcomer's node id once

### Requirement: The reply hands over the bootstrap tickets
The linking reply SHALL carry write tickets to the identity's directory and to its data namespace, both minted fresh from replicas the inviting device hosts locally — the ceremony reads nothing through directory ticket entries, so no payload wait sits in the critical path. The dialing runtime SHALL import both: the directory as the identity's directory replica, the data namespace registered under the payload's identity. Every device of an identity can therefore mint a linking invite — the store set is hosted wherever creation or linking brought it up, founder or not.

#### Scenario: The newcomer comes up with the full store set
- **WHEN** runtime B links into an identity and the directory's first sync completes
- **THEN** B hosts the identity's directory and its data namespace, and an entry written under the identity on either runtime becomes readable on the other

#### Scenario: Linking through a non-founder device
- **WHEN** device 2 was itself linked into an identity, and device 3 links from an invite minted on device 2
- **THEN** device 3 comes up with the directory and the data namespace, and all three devices' device sets converge to three

### Requirement: Link returns caught up, and failure leaves no local residue
`link` SHALL NOT report success until the imported directory has completed one successful sync exchange that started after the import — one bounded wait against the peer that just answered the dialogue, not a retry loop; a directory that cannot catch up within the caller's timeout SHALL surface as an error, not a hang. The property waited on is a completed session, not arrived content: a runtime that never synced and one that synced and found nothing new must not be confused, so polling the directory's contents does not discharge this requirement. On any failure after import, the dialing runtime SHALL undo what this linking imported — the directory, and the data namespace's binding — so a failed link leaves no local residue and the identity is unknown to the runtime again. Undoing SHALL restore what the import displaced rather than delete it: an issuer can already be bound when the link runs, because a namespace reached through a peer's grant binds the same issuer without making the identity hosted, and the pre-dial refusal cannot see it. A rollback that forgot the issuer outright would destroy a replica this linking never imported, permanently — so the data namespace is unbound only when the link's import was what bound it, and the replica it brought up is dropped only when it is not the replica the restored binding names. A device record already committed on the inviter side may remain, per the lost-reply posture above.

#### Scenario: Success implies the directory is caught up
- **WHEN** `link` returns success
- **THEN** the newcomer's directory replica has completed a successful sync exchange started after the import, and the device set it reads locally includes the identity's existing devices

#### Scenario: A timed-out link leaves nothing behind on the dialing node
- **WHEN** the directory cannot complete a first sync within the timeout
- **THEN** `link` fails, the identity is absent from the runtime's hosted identities, and operations addressed to it are refused as unknown — as they were before the attempt, not as storage errors against a dropped replica

#### Scenario: A failed link leaves a granted namespace of the same issuer intact
- **WHEN** a runtime reached an issuer's namespace through a peer's grant, then links into that same issuer and the link fails
- **THEN** the grant still reads that namespace's entries afterwards, and the identity is still not hosted — the rollback restored the binding it displaced instead of forgetting the issuer
