# UWill capability format

The UWill capability token: the format the `uwill` module of `pdn-layer` defines, and the chain-validation, revocation, and identity-resolution rules the format is shaped for. The architectural rationale — why UWill rather than Meadowcap or some other alternative — lives in [ADR-0007](../../../architecture/adr/0007-uwill.md).

What the workspace implements of this is the types alone: `Command`, `UwillCapability`, `CapabilityCid`, and `ValidityWindow` in `crates/pdn-layer/src/uwill.rs`. Nothing issues, transports, validates, or revokes a UWill token. Access is enforced on the [read capabilities](../data-layer/read-capabilities.md) grant — the single-link precursor whose per-claim command list mirrors this format — by the egress filter ([subset reconciliation](../data-layer/subset-reconciliation.md)) and the ingest gate ([capability-gated ingest](../data-layer/capability-gated-ingest.md)). Every section below past the token format describes rules no code runs.

## Token format

A UWill delegation is a standard UCAN v1.0.0-rc.1 Delegation (DAG-CBOR envelope):

| Field   | Meaning                                                                                                              |
| ------- | -------------------------------------------------------------------------------------------------------------------- |
| `iss`   | Delegator's identity.                                                                                                |
| `aud`   | Delegate's identity.                                                                                                 |
| `sub`   | Namespace owner's identity.                                                                                          |
| `cmd`   | List of granted commands. UWill-specific deviation from UCAN's single-command convention. See [Commands](#commands). |
| `res`   | Granted resource: the `ClaimId` of the specific claim this capability covers. See [Resource](#resource).             |
| `nbf`   | Wall-clock validity start (unix ms).                                                                                 |
| `exp`   | Wall-clock validity end (unix ms).                                                                                   |
| `nonce` | 12-byte random.                                                                                                      |

`iss`, `aud`, and `sub` are identities, not per-device keys: the type carries each as a `PdnId`, and the DID encoding (`did:key`, then `did:keri`) is the wire form the format is designed for. Resolving an identity to the devices that act for it happens below the token (see [Identity resolution](#identity-resolution)).

## Commands

UWill uses a flat command set, not a hierarchy:

- **`read`** — *always present* in every capability. Validators MUST reject any capability whose `cmd` list does not include `read`.
- **`write`** — optional; used for inbox/dropbox patterns and entry authorization.
- **`delete`** — optional.
- **`delegate`** — optional.

A read-only capability is `cmd: ["read"]`; a read-write capability is `cmd: ["read", "write"]`.

Read being mandatory is a deliberate placeholder, not a permanent invariant. It reserves the shape for a later capability variant *without* `read` — for example proof-of-existence ("you may verify this object exists in unchanged form, but not see its contents"). No such variant exists.

## Resource

A UWill capability grants access to **exactly one claim**. The resource field is a single `ClaimId`:

| Field      | Meaning                                                       |
| ---------- | ------------------------------------------------------------- |
| `claim_id` | The `ClaimId` of the claim this capability grants access to. |

`ClaimId` is the 32-byte stable identifier of a [Claim](../../../architecture/language/claim.md) at the PDN domain layer. Storage-level addressing (the pdn-store namespace and the entry path) is *not* exposed in UWill tokens: how a `ClaimId` maps onto an entry is the data layer's concern, and the derivation in [read capabilities](../data-layer/read-capabilities.md) computes the id from the issuer and the entry path.

Prefix-based scoping and other geometric regions are intentionally not supported at the UWill level. If a use case requires granting access to a set of claims, the issuer SHALL produce one UWill delegation per `ClaimId`.

> **Why claim-id only.** Top-level UWill capabilities trade expressiveness for auditability and domain alignment: a capability names exactly the claim it grants, with no implicit reach. Bulk-sharing patterns (a directory, a thread, a calendar's entries) are constructed at the layer above UWill by issuing capabilities per claim; storage-level scoping primitives (path prefixes, key ranges) are not exposed here.

## Chain validation

UCAN does not structurally verify narrowing — it only evaluates policies at invocation time. UWill adds two custom checks on top of UCAN's signature and principal-alignment validation:

1. **Resource identity.** A delegation step's `res.claim_id` MUST equal its parent's. Because resources are single claims, there is nothing narrower than the parent's resource to delegate.
2. **Command-subset.** A delegation step's `cmd` list MUST be a subset of its parent's. Reject the chain if a step adds commands not present in the parent.

Wall-clock validity: the effective window of a chain is `[max(all nbf), min(all exp)]`. A clock-drift tolerance of ±60 seconds is applied.

A chain is also rejected if any delegation's CID appears in the local revocation store.

## Revocation

Eventually-consistent, CID-based:

- Each peer maintains a local revocation store.
- A revocation is a UCAN Invocation with `cmd: ucan/revoke`, `arg.revoke` carrying the CID of the delegation being revoked.
- The revoker's authority is verified against the proof chain embedded in the invocation.
- Revocation records propagate as ordinary entries over pdn-store sync — no separate revocation protocol.

## Identity resolution

UWill capabilities reference identities; the sync layer authenticates a session by the peer's node id. The design bridges the two:

- A `PdnId` is resolved to the identity's device set — the device records of its directory, and the device set it publishes into each connection metadata store.
- Capability chains do not break on key rotation because they reference the identity, not raw keys.
- Adding or removing a device under an existing `PdnId` does not require re-issuing delegations — the device set widens or narrows on its own.

The DID form starts as `did:key` (direct ed25519 public-key extraction) and migrates to `did:keri` once KERI is wired in. The DID stays stable across key rotations.

## Open questions

- Claim identity and entry location. The reconciliation egress filter never needs a mapping table: it evaluates membership in the reverse direction, computing the claim identity from the entry key it already holds and testing it against the granted set. A mapping table, if one ever exists, serves only runtime-side resolution from `res` to storage locations (read and list surfaces, or compiling a scope into paths); it never rides into a reconciliation session.
- Proof-of-authorship placement. Whether claim authorship proof lives alongside the UCAN signature or stays separate as `PdnIdentityProof` in the PDN domain layer.
- Semantics of `write` on a claim. What does "write" mean when the resource is a claim — overwriting the attribute, appending a counter-claim, modifying the embedded capability? UWill only carries the command, not its semantics. The read-capabilities grant carries write per claim, and the data layer enforces it at the ingest hook (ADR-0008) by the transport-authenticated session identity — a synced entry is admitted into a hosted issuer's replica only from the issuer's own devices or, per claim, per the sender's recorded write grant; an entry outside that set is refused and retracted at the writer. The finer question — what a write *does* to the claim value versus its embedded capability — still lives in the PDN layer.
- Future commands. When `delete` and `delegate` see real use, what additional chain-validation rules beyond command-subset are required.
- Confidential encoding. A capability travels in cleartext inside the connection metadata store, exposing `ClaimId`s to every device of both identities. An encoding that hides them is out of scope for the initial implementation.
