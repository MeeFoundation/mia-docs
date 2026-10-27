# Runtime core

## Purpose

The embeddable runtime core: identity, [pods](../pods/spec.md) and sync services as thin glue over `data-layer`. Each embedded runtime is one running node — a host embeds one, and in-process tests embed several to stand up several nodes; one runtime hosts any number of identities (per data-layer [multi-identity](../../data-layer/multi-identity/spec.md)), each added by an explicit act. The core adds no sync or authorization mechanics of its own: every operation delegates to a `data-layer` primitive; read access is carried by session classification ([reconciliation sessions](../../data-layer/reconciliation-sessions/spec.md)) — every current member being served a pod's stores whole ([pod stores](../../data-layer/pod-store/spec.md)) — and the runtime registers everything it hosts, so its nodes are always armed.

## Requirements

### Requirement: The core embeds as a library
The runtime core SHALL be usable as a library with no host attached: a process embeds it, drives every service in-process, and shuts it down. The core SHALL NOT depend on any host machinery (HTTP or otherwise); hosts depend on the core, never the reverse.

#### Scenario: In-process embedding
- **WHEN** a test embeds the runtime core directly and drives the identity, pods, and sync services
- **THEN** every operation completes without any host process or HTTP surface involved

### Requirement: Identity service creates and links identities
The identity service SHALL create an identity on its first device — minting its [identity key](../../../../architecture/language/identity-key.md) pair ([private metadata store](../../data-layer/private-metadata-store/spec.md)) and deriving its `PdnId` from the pair's public key by the `PdnId` steps of the [pod stores](../../data-layer/pod-store/spec.md) spec, a placeholder for the autonomic identifier of ADR-0003, and provisioning its store set: the private metadata store (PMS) ([device-linking](../device-linking/spec.md)). It SHALL mint a linking invite for a hosted identity — the one-time secret and the bearer-free linking payload — and SHALL link this runtime into an existing identity from a scanned linking payload, one explicit linking act per identity; the payload names the identity, and a runtime already hosting it refuses before dialing.

**Example:** Alice-work and Alice-leisure are both hosted on Alice's phone a1, which mints a linking invite for each; her tablet a3 runs a runtime that hosts no identity yet.

| call on a3 | result |
|---|---|
| `link(Alice-work's payload, timeout)` | a3 hosts Alice-work; `pods().list(Alice-leisure)` answers `UnknownIdentity` |
| `link(Alice-leisure's payload, timeout)` | a3 hosts Alice-leisure too: one linking act per identity |
| `link(a second payload for Alice-work, timeout)` | `IdentityAlreadyHosted { identity: Alice-work }`, before any dial; that secret stays unburned |

#### Scenario: Create on one runtime, link on another
- **WHEN** an identity is created on runtime A and runtime B links from a linking invite minted on A
- **THEN** B hosts the identity: it appears among B's hosted identities, and the identity's PMS converges on B

#### Scenario: Linking one identity imports nothing of another
- **WHEN** runtime B is linked into identity X while identity Y exists elsewhere
- **THEN** B hosts X only, and operations addressed to Y on B are refused as unknown

#### Scenario: An identity's `PdnId` derives from its identity key
- **WHEN** an identity is created on runtime A and runtime B links into it
- **THEN** the identity's `PdnId` equals the `PdnId` derived from the public identity key in its PMS, on A and on B alike

### Requirement: Sync service reports the node id and the hosted identities
The sync service SHALL report the runtime's node id (its endpoint id) and the identities the runtime hosts — exactly those created or linked on it. It SHALL also answer a storage check from the replica store and the blob store themselves — the reads a host's readiness probe rests on, the blob store's included since a pod's placement on a full disk stops it while the replica store keeps answering ([host](../../pdn-node-http/host/spec.md)) — because every other report here is in-memory bookkeeping, which a store that stopped answering leaves untouched.

#### Scenario: Hosted identities follow create and link
- **WHEN** a fresh runtime reports its status, then creates one identity and links another
- **THEN** the report lists no identities first and afterwards exactly those two, with the node id unchanged throughout

### Requirement: A stop lets the serving half of every ceremony in flight finish

The runtime's shutdown SHALL let the serving half of every ceremony dialogue in flight — the linking dialogue and a pod's join, one answering another node and one answering another identity of the same node over the in-process pipe — finish within a fixed budget, before it stops anything that serving half writes through: the replica stores, the blob store, gossip. A stop that landed between the burn of the secret and the ceremony's commit would leave the invite spent and the ceremony half done, with nothing to retry it. The wait SHALL come before the node's own protocols shut down, because those shut down side by side and a wait inside one of them runs against stores already going away. A dialogue that would begin after the wait SHALL be refused before its secret is verified, so nothing burns. The dialing half is the host's own call and is not waited for: a host awaits its `link` or its `join` before it stops the runtime.

**Example:** Bob on b1 joins "Family" from Alice's invite while a1's runtime shuts down; the budget is `SHUTDOWN_SERVING_BUDGET`, 10 s.

| step | a1's serving half | a1's `Runtime::shutdown` |
|---|---|---|
| 1 | reads the join request, holding one permit | |
| 2 | | begins: waits for every permit, 10 s at most |
| 3 | verifies and burns the secret, writes Bob's joined event, sends both stores' tickets, returns its permit | |
| 4 | | the wait ends; the node stops its replica stores, blob store, gossip |
| 5 | a dialogue arriving now is closed before its secret is verified: the secret is not burned | |

#### Scenario: A stop waits for the serving half of a dialogue from another node

- **WHEN** the inviting runtime is shut down while its serving half of a join from another node has read the request and not yet verified it, and the runtime is started again on the same directory
- **THEN** the shutdown returned only after the serving half finished, and the pod lists the newcomer as a member on the inviting runtime after the restart

#### Scenario: A stop waits for the serving half of a co-located dialogue

- **WHEN** the runtime is shut down while two of its identities are mid-join, the serving half having read the request, and the runtime is started again on the same directory
- **THEN** the shutdown returned only after the serving half finished, and the pod lists the newcomer as a member after the restart

#### Scenario: A dialogue arriving after the wait writes nothing

- **WHEN** a join dialogue reaches a runtime whose shutdown has already waited for its serving halves
- **THEN** the dialogue is closed before its secret is verified, and the inviting runtime writes nothing for it
