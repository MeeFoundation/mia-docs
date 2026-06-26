---
status: draft
date: 2026-06-19
---

# One namespace per issuer: drop the `(about, issued_by)` namespace id

## Context and Problem Statement

The 22-Apr convention made a domain namespace the pair `(about, issued_by)`: one replica per _(subject, issuer)_. In parallel, UWill ([ADR-0007](0007-uwill.md)) authorizes access **per claim** (`res = ClaimId`). So the `about` dimension of the namespace and UWill's per-claim grants are **two parallel mechanisms for the same thing** — sharing/visibility granularity. Carrying both is redundant, and it forces a side mapping in `data-layer` between each random `pdn-store` namespace key and its `(about, issued_by)` meaning.

Can we collapse to a single addressing axis — and, once collapsed, does a "namespace" remain a concept anything above `data-layer` needs to see at all?

## Decision

- **Drop the domain `NamespaceId = (about, issued_by)`.** `about` becomes a field _inside_ the claim (it already is: `Claim.about`), not a namespace coordinate.
- **One `pdn-store` namespace per issuer.** All of an issuer's claims (about anyone) live in that one namespace. The data binding is keyed by the issuer `PdnId`: `Binding::Data { issuer }`.
- **Granularity lives entirely in UWill** (per-claim), not in the namespace boundary.
- **pdn-node is namespace-free.** Nothing above `data-layer` names a namespace: claims are addressed by `ClaimId` and authorized by UWill. The `DataLayer` trait re-keys from `&NamespaceId` to the issuer `PdnId` (a claim resolves issuer → replica internally); `Binding` and `BindingIndex` become `data-layer` internals.
- **The namespace is demoted to a `data-layer`-internal convergence bucket.** It keeps only its two iroh-docs roles — the set-reconciliation unit and the gossip topic — and sheds the other two: addressing moves to `ClaimId`, write-capability moves to UWill.
- **Compute the namespace key from the issuer identity; drop the mapping.** Because write authority now lives entirely in UWill, the namespace secret is never shared — so the key can be derived from (and verified against) the issuer identity without the derived-secret-sharing hazard, and the `BindingIndex` mapping table is eliminated. A random key + interim mapping stays permissible until the computed key lands: an implementation choice, not an architectural one.

The reason a namespace survives at all: **UWill authorizes, it does not replicate.** A per-peer-group set that converges by reconciliation is irreducible on iroh-docs, so we coarsen it to one-per-issuer and stop surfacing it — we do not try to remove it. Pushing to zero replicas would mean a different substrate (content-addressed claims fetched per UWill) and rebuilding convergence by hand — latest-wins per claim, revocation propagation, a what's-new index — each itself a converging set, i.e. a namespace under another name.

This is orthogonal to the device-internal stores, which are **approved and unaffected**: `ConnectionsStore` and `PrivateMetadataStore` are bound by `identity` and admitted by Invariant 1 (see `../invariants.md`), independent of how data namespaces are addressed. They are the same convergence bucket for an identity's own devices, and stay replicas regardless.

```
per identity Alice:
  Data namespace        (1, keyed by alice)   peer-visible, all Alice's claims
  ConnectionsStore      (1, identity alice)      device-internal, Invariant 1
  PrivateMetadataStore  (1, identity alice)      device-internal, Invariant 1
Binding = Data { issuer } | Connections { identity } | PrivateMetadata { identity }
```

## Consequences

- Good — removes a redundant granularity axis; UWill becomes the single authorization mechanism; aligns the namespace with the issuer identity.
- Good — simpler addressing: fewer replicas (one per issuer, not one per subject), and a clear path to eliminating the mapping table.
- Good — pdn-node is namespace-free: a smaller, capability-only surface (`ClaimId` + UWill), with `Binding`/`BindingIndex` demoted to `data-layer` internals.
- Bad — coarser confidentiality (Open Question 1).
- Bad — the capability gate (ADR-0008) becomes the sole writer authority: namespace-key possession no longer authorizes writes, so correctness leans entirely on the fork's ingest checks.
- Neutral — the device-internal stores and Invariant 1 are unchanged.

## More Information

Related: [ADR-0007](0007-uwill.md), [ADR-0008](0008-iroh-without-willow.md); `../invariants.md` (Invariant 1).
