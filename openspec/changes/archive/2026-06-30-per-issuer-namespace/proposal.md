# Proposal: per-issuer-namespace

## Why

A domain namespace was the pair `(about, issued_by)` — one replica per _(subject, issuer)_. UWill (ADR-0007) already authorizes **per claim** (`res = ClaimId`), so the namespace's `about` dimension and UWill's per-claim grants are two parallel mechanisms for the same thing: sharing/visibility granularity. Carrying both is redundant and forces a side mapping in `data-layer` between each random `pdn-store` namespace key and its `(about, issued_by)` meaning.

ADR-0009 decides the collapse: drop the pair, one namespace per issuer, granularity entirely in UWill, pdn-node namespace-free. This change realizes that decision and records the implementation-level choices the ADR deliberately keeps out — the ADR holds only what is expensive to reverse; the rest lives here.

## What Changes

- **Drop `NamespaceId = (about, issued_by)` (`pdn-types`).** `about` stays a field inside the claim (`Claim.about`); it is not a namespace coordinate.
- **One namespace per issuer (`data-layer`).** The data binding becomes `Binding::Data { issuer }`, keyed by the issuer `PdnId`; an issuer's claims (about anyone) share one replica. `BindingIndex` is keyed by issuer.
- **Re-key the `DataLayer` trait.** Its surface moves from `&NamespaceId` to the issuer `PdnId`; a claim resolves issuer → replica internally. `Binding`/`BindingIndex` become `data-layer` internals.
- **pdn-node namespace-free.** Above `data-layer`, claims are addressed by `ClaimId` and authorized by UWill; nothing names a namespace.
- **Interim namespace key (`data-layer`).** The namespace key stays a random `pdn-store` key plus the `BindingIndex` mapping. Computing it from the issuer identity (and dropping the mapping) is deferred until UWill is the sole write authority — see design D2.

## Out of Scope (deferred)

- **Computed namespace key / dropping the mapping** — safe only once write-authority is UWill, not namespace-secret possession (design D2). Until then: random key + interim mapping.
- **UWill itself** (ADR-0007) — this change consumes the per-claim model, it does not implement the token.
- **Lazy data-namespace import at device linking** — the directory rail and staging are recorded in design D4; the import is a follow-up. Device-internal stores are unaffected (`components/mee-pdn/pdn-node/device-linking.md`).
- **Confidentiality** — deferred to UWill; the replica boundary is not a confidentiality tool, so one-per-issuer regresses nothing (design D3).

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree, following the `components/mee-pdn/pdn-layer/uwill.md` convention.

| Capability (delta)              | Archive destination                                         |
| ------------------------------- | ----------------------------------------------------------- |
| `pdn-node-namespace-addressing` | `openspec/specs/components/mee-pdn/pdn-node/namespace-addressing.md` |

### New Capabilities

- `pdn-node-namespace-addressing`: how PDN addresses and authorizes claims with no namespace as a domain concept — `ClaimId` addressing, UWill authorization, one `data-layer` namespace per issuer, and the namespace demoted to a replication bucket.

### Modified Capabilities

<!-- none in this change: the data-layer specs that still name (about, issued_by)
  — components/mee-pdn/data-layer/ingest-policies.md, components/mee-pdn/data-layer/connection-metadata-store.md —
  are updated to Binding::Data { issuer } when the code lands, since pdn-types still
  carries the pair today. Tracked in tasks.md, not as deltas here. -->

## Impact

- **`crates/pdn-types`**: remove `NamespaceId = (about, issued_by)`; `about` lives in `Claim`.
- **`crates/data-layer`**: `Binding::Data { issuer }`; `BindingIndex` keyed by issuer; `DataLayer` trait re-keyed `&NamespaceId` → issuer `PdnId`; `SelfOwned` data arm matches on issuer. Namespace key stays random + mapping (interim).
- **`crates/pdn-layer` / future pdn-node**: claims addressed by `ClaimId` + UWill; no namespace naming.
- **Fork (`pdn-store`)**: not touched — addressing and binding resolution stay above the seam.
- **Unaffected**: device-internal stores and Invariant 1 (`components/mee-pdn/invariants.md`).
