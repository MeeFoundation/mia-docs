# UWill capability format

Technical specification of the UWill capability token, chain validation rules, revocation mechanism, and identity resolution as implemented inside the PDN node (and the `MeeFoundation/iroh-willow` fork it embeds). The architectural rationale — why UWill rather than Meadowcap or some other alternative — lives in [ADR-0007](../../architecture/adr/0007-uwill.md).

## Token format

A UWill delegation is a standard UCAN v1.0.0-rc.1 Delegation (DAG-CBOR envelope) with Willow-specific conventions:

| Field   | Meaning                                                                                                              |
| ------- | -------------------------------------------------------------------------------------------------------------------- |
| `iss`   | Delegator's MeeId-backed DID (`did:key` now, `did:keri` later).                                                      |
| `aud`   | Delegate's MeeId-backed DID.                                                                                         |
| `sub`   | Namespace owner's MeeId-backed DID.                                                                                  |
| `cmd`   | List of granted commands. UWill-specific deviation from UCAN's single-command convention. See [Commands](#commands). |
| `res`   | Granted resource: the `ClaimId` of the specific claim this capability covers. See [Resource](#resource).             |
| `nbf`   | Wall-clock validity start (unix ms).                                                                                 |
| `exp`   | Wall-clock validity end (unix ms).                                                                                   |
| `nonce` | 12-byte random.                                                                                                      |

`iss` and `aud` are higher-level identities, not per-device keys: the iroh-willow fork fans the delegation across the audience's currently active devices internally (see [Identity resolution](#identity-resolution)).

## Commands

UWill uses a flat command set, not a hierarchy:

- **`read`** — *always present* in every capability. Validators MUST reject any capability whose `cmd` list does not include `read`.
- **`write`** — optional; used for inbox/dropbox patterns and entry authorization.
- **`delete`** — optional.
- **`delegate`** — optional.

A read-only capability is `cmd: ["read"]`; a read-write capability is `cmd: ["read", "write"]`.

Read being mandatory is a deliberate placeholder, not a permanent invariant. It reserves the shape for a later capability variant *without* `read` — for example proof-of-existence ("you may verify this object exists in unchanged form, but not see its contents"). UWill does not currently implement that variant.

## Resource

A UWill capability grants access to **exactly one claim**. The resource field is a single `ClaimId`:

| Field      | Meaning                                                       |
| ---------- | ------------------------------------------------------------- |
| `claim_id` | The `ClaimId` of the claim this capability grants access to. |

`ClaimId` is the 32-byte stable identifier of a [Claim](../../architecture/language/claim.md) at the PDN domain layer. Willow-level addressing (namespace, subspace, path) is *not* exposed in UWill tokens: each `ClaimId` resolves to a specific willow leaf inside the iroh-willow fork's storage, and that mapping is the implementation's concern.

Prefix-based scoping and other geometric regions are intentionally not supported at the UWill level. If a use case requires granting access to a set of claims, the issuer SHALL produce one UWill delegation per `ClaimId`.

> **Why claim-id only.** Top-level UWill capabilities trade expressiveness for auditability and domain alignment: a capability names exactly the claim it grants, with no implicit reach. Bulk-sharing patterns (a directory, a thread, a calendar's entries) are constructed at the layer above UWill by issuing capabilities per claim; willow-level scoping primitives (prefix, subspace, time range) are not exposed here.

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
- Revocation records propagate through Willow's own sync infrastructure — no separate revocation protocol.

## Identity resolution

UWill capabilities reference MeeIds; Willow's wire protocol works in per-device keys. The implementation bridges the two:

- A `MeeId` is resolved through the identity layer to the set of currently active willow keys for that identity.
- Capability chains do not break on key rotation because they reference the MeeId-DID, not raw keys.
- Adding or removing a device under an existing MeeId does not require re-issuing delegations — the resolution layer widens or narrows the active key set internally.

The DID form starts as `did:key` (direct ed25519 public-key extraction) and migrates to `did:keri` once KERI is wired in. The DID stays stable across key rotations.

## PIO compatibility

Willow's Private Interest Overlap (PIO) protocol requires three properties from capabilities. UWill provides them as:

- **receiver** → `aud` DID resolved to the currently active willow keys for that MeeId.
- **granted_namespace** → `sub` DID resolved to a `NamespacePublicKey`.
- **granted_resource** → the `res.claim_id`, resolved by the iroh-willow fork to the underlying willow leaf. Overlap between two UWill receivers is equality on `ClaimId` — no prefix matching, no geometric area intersection.

## Open questions

- ClaimId ↔ willow leaf mapping. Resolving a `ClaimId` to a concrete willow `(namespace, subspace, path)` is the iroh-willow fork's responsibility. The mapping table, its propagation between peers, and its consistency model are not specified here.
- Proof-of-authorship placement. Whether claim authorship proof lives alongside the UCAN signature or stays separate as `MeeIdentityProof` in the PDN domain layer.
- Semantics of `write` on a claim. What does "write" mean when the resource is a claim — overwriting the attribute, appending a counter-claim, modifying the embedded capability? The current spec leaves this to the PDN layer; UWill only carries the command, not its semantics.
- Future commands. When `delete` and `delegate` see real use, what additional chain-validation rules beyond command-subset are required.
- Confidential sync encoding. Capabilities are currently sent in cleartext, exposing `ClaimId` topology to intermediary nodes. Meadowcap encoded capabilities relative to PIO context. A relative encoding that strips PAI-known fields is needed to restore confidentiality but is out of scope for the initial implementation.
