# pdn-node: runtime core — delta for cells

## MODIFIED Requirements

### Requirement: Identity service creates and links identities
The identity service SHALL create an identity on its first device — minting its announcement key pair ([private metadata store](../../data-layer/private-metadata-store/spec.md)) and deriving its `PdnId` from the pair's public key by the `PdnId` steps of the [cell stores](../../data-layer/cell-store/spec.md) spec (cells D44), a placeholder for the autonomic identifier of ADR-0003, and provisioning its store set: the private-metadata directory and the data namespace, with the data-namespace ticket published in the directory ([device-linking](../device-linking/spec.md)). It SHALL mint a linking invite for a hosted identity — the one-time secret and the bearer-free linking payload — and SHALL link this runtime into an existing identity from a scanned linking payload, one explicit linking act per identity; the payload names the identity, and a runtime already hosting it refuses before dialing.

**Example:** Alice-work and Alice-leisure are both hosted on Alice's phone a1, which mints a linking invite for each; her tablet a3 runs a runtime that hosts no identity yet.

| call on a3 | result |
|---|---|
| `link(Alice-work's payload, timeout)` | a3 hosts Alice-work; `connections().list(Alice-leisure)` answers `UnknownIdentity` |
| `link(Alice-leisure's payload, timeout)` | a3 hosts Alice-leisure too: one linking act per identity |
| `link(a second payload for Alice-work, timeout)` | `IdentityAlreadyHosted { identity: Alice-work }`, before any dial; that secret stays unburned |

#### Scenario: Create on one runtime, link on another
- **WHEN** an identity is created on runtime A and runtime B links from a linking invite minted on A
- **THEN** B hosts the identity: it appears among B's hosted identities, and the identity's directory and data namespace converge on B

#### Scenario: Linking one identity imports nothing of another
- **WHEN** runtime B is linked into identity X while identity Y exists elsewhere
- **THEN** B hosts X only, and operations addressed to Y on B are refused as unknown

#### Scenario: An identity's `PdnId` derives from its announcement key
- **WHEN** an identity is created on runtime A and runtime B links into it
- **THEN** the identity's `PdnId` equals the `PdnId` derived from the announcement public key in its directory, on A and on B alike
