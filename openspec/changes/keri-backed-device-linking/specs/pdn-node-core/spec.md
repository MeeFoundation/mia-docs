# Runtime core: the identity service creates an identity by inception

The identity service stops minting an identifier with nothing behind it. Creating an identity incepts a root identifier and the creating device's delegated identifier under it, and linking reports one more outcome — the material the inviter presented did not line up — with a reason the caller can act on.

## MODIFIED Requirements

### Requirement: Identity service creates and links identities
The identity service SHALL create an identity on its first device — preparing its private-metadata directory and data replica before a `PdnId` exists, sealing opaque role-tagged commitments to those 2 stores in the root inception, incepting the creating device as a delegate of the root, anchoring it, and writing a root-and-device-signed `Created` proof for the founder's exact node id ([device-linking](../pdn-node-device-linking/spec.md)). The data-namespace ticket SHALL be published in the directory after the prepared data replica is bound to the derived identity. It SHALL mint a linking invite for a hosted identity — the one-time secret and the linking payload, which carries no long-lived capability — and SHALL link this runtime into an existing identity from a scanned linking payload, one explicit linking act per identity; the payload names the identity, and a runtime already hosting it refuses before dialing.

`create() -> PdnId` SHALL remain non-idempotent because it accepts no caller key that could correlate a retry. Startup SHALL finish every durable creation record before accepting calls and SHALL expose the recovered identities through `hosted_identities`; each `create` admitted afterwards SHALL create and return another identity rather than consume an older record.

Linking SHALL report a failure of the presented verification material as its own outcome, with the closed typed reasons from `pdn-node-device-linking`, including the ordered bootstrap-ticket failure collection that preserves distinct store-commitment, insufficient-capability, and malformed-ticket results for every failed role. It SHALL remain distinguishable by a caller from a refusal, from an unreachable inviter, from a dialogue that outlived the budget, and from a catch-up timeout, without matching on error text.

#### Scenario: Create on one runtime, link on another
- **WHEN** an identity is created on runtime A and runtime B links from a linking invite minted on A
- **THEN** B hosts the identity: it appears among B's hosted identities, and the identity's directory and data namespace converge on B

#### Scenario: Linking one identity imports nothing of another
- **WHEN** runtime B is linked into identity X while identity Y exists elsewhere
- **THEN** B hosts X only, and operations addressed to Y on B are refused as unknown

#### Scenario: A created identity has a history behind it
- **WHEN** an identity is created
- **THEN** its identifier is the one its inception derives, and the creating device's identifier is a delegate anchored in that inception's log

#### Scenario: A new create does not consume recovered work
- **WHEN** startup completes an interrupted identity creation and a caller then invokes `create`
- **THEN** `hosted_identities` contains the recovered identity and the newly returned distinct identity

#### Scenario: Verification failure is its own outcome
- **WHEN** linking fails because the inviter's chain does not reach the payload's identity
- **THEN** the caller distinguishes that outcome from a refusal and from a catch-up timeout without matching on error text

#### Scenario: Tickets outside the identity's store set fail verification
- **WHEN** linking is answered with a verifying chain and a ticket whose role-tagged commitment the identity's history does not seal
- **THEN** the caller sees a verification failure whose reason it can tell from a chain that misses the identity, and the runtime hosts nothing new

#### Scenario: The founder remains authorized after another device links
- **WHEN** a created identity links a second device and both devices receive the founder's confirmed record and accepted chain
- **THEN** the second device classifies the founder as a full-access identity device from its `Created` proof, and data continues to replicate in both directions

## ADDED Requirements

### Requirement: Reserved device operations do not impersonate the KERI identity service

The existing `PdnOp::AddDevice`, `PdnOp::RevokeDevice`, `PdnOp::RotateKey`, and `PdnOp::ActiveDevices` variants SHALL remain reserved and SHALL NOT be emitted, accepted, or translated as aliases for this change's identity creation, device linking, identity forgetting, KERI rotation, revocation, or recovery. `Connection.peer_devices` SHALL retain its existing counterparty-metadata meaning and SHALL NOT be projected from the hosted identity's KERI device chain in this change. A later domain-API change MUST version or replace these meanings before enabling them.

#### Scenario: A reserved revoke operation grants no revocation semantics

- **WHEN** a caller presents the existing `RevokeDevice` operation to a runtime implementing this change
- **THEN** the runtime does not mutate KERI history, device proofs, access projection, or stored capabilities on its strength

### Requirement: The identity service forgets an identity explicitly
The identity service SHALL offer one operation that forgets a hosted or previously attempted identity: it removes the identity's pinned heads, its ceremony context, its key material, its creation and attempt records, and whatever replicas and bindings it still holds, leaving the runtime as it was before that identity was known to it. It SHALL be a distinct call, not a mode of `link` and not a consequence of any failure — the rollback of a failed linking deliberately keeps the first three, and only this operation removes them.

Forgetting SHALL be as careful with displaced state as the linking rollback is: a namespace this runtime also reaches through a peer's grant SHALL survive, because the grant bound the same issuer without making the identity hosted. The data namespace is unbound only when hosting this identity was what bound it, and a replica is dropped only when it is not the replica a surviving binding names — the same rule the rollback follows, for the same reason: an operation that undoes must not destroy state that predates it.

#### Scenario: Forgetting leaves the identity unknown
- **WHEN** an identity is forgotten on a runtime that hosted it
- **THEN** it is absent from the hosted identities, operations addressed to it are refused as unknown, and a later linking into it pins its history afresh

#### Scenario: Forgetting an identity leaves a granted namespace of the same issuer intact
- **WHEN** a runtime reached an issuer's namespace through a peer's grant and then forgets that issuer's identity, which it also hosted
- **THEN** the grant still reads that namespace's entries afterwards

#### Scenario: Forgetting one identity leaves another intact
- **WHEN** a runtime hosting two identities forgets one
- **THEN** the other remains hosted with its key material and pinned heads unchanged
