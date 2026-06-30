---
status: accepted
date: 2026-06-30
---

# One namespace per issuer: drop the `(about, issued_by)` namespace id

## Context and Problem Statement

The earlier convention made a domain namespace the pair `(about, issued_by)`: one replica per _(subject, issuer)_. In parallel, UWill ([ADR-0007](0007-uwill.md)) authorizes access **per claim** (`res = ClaimId`). So the `about` dimension of the namespace and UWill's per-claim grants are **two parallel mechanisms for the same thing** — sharing/visibility granularity. Carrying both is redundant, and it forces a side mapping in `data-layer` between each random `pdn-store` namespace key and its `(about, issued_by)` meaning.

Can we collapse to a single addressing axis — and, once collapsed, does a "namespace" remain a concept anything above `data-layer` needs to see at all?

## Decision

- **Drop the domain `NamespaceId = (about, issued_by)`.** `about` becomes a field _inside_ the claim (it already is: `Claim.about`), not a namespace coordinate.
- **One `pdn-store` namespace per issuer.** All of an issuer's claims (about anyone) live in that one namespace. The data binding is keyed by the issuer `PdnId`: `Binding::Data { issuer }`.
- **Granularity lives entirely in UWill** (per-claim), not in the namespace boundary.
- **pdn-node is namespace-free.** Nothing above `data-layer` names a namespace: claims are addressed by `ClaimId` and authorized by UWill. `Binding` and `BindingIndex` are `data-layer` internals.
- **The namespace is demoted to a `data-layer`-internal replication bucket** — the iroh-docs set-reconciliation unit and gossip topic, nothing more. Addressing moves to `ClaimId`, write-authority to UWill.

A namespace survives because **UWill authorizes, it does not replicate**: a per-issuer set that replicates by reconciliation is irreducible on iroh-docs, so we coarsen it to one-per-issuer rather than try to remove it.

This is orthogonal to the device-internal stores (`ConnectionsStore`, `PrivateMetadataStore`), which are bound by `identity` and admitted by Invariant 1 (see `../../components/pdn-node/invariants.md`): unaffected by how data namespaces are addressed.

## Consequences

- Good — removes a redundant granularity axis; UWill becomes the single authorization mechanism; aligns the namespace with the issuer identity.
- Good — simpler addressing: one replica per issuer, not one per subject.
- Good — pdn-node is namespace-free: a smaller, capability-only surface (`ClaimId` + UWill), with `Binding`/`BindingIndex` demoted to `data-layer` internals.
- Bad — the capability gate (ADR-0008) becomes the sole writer authority: namespace-key possession no longer authorizes writes, so correctness leans entirely on the fork's ingest checks.

## More Information

The realization is specified in `../../components/pdn-node/namespace-addressing.md` (the namespace-free addressing surface). The interim namespace-key/mapping path, confidentiality, device bootstrap, and pre-UWill relaxations live in the design of the archived `per-issuer-namespace` change, not in this ADR.

Related: [ADR-0007](0007-uwill.md), [ADR-0008](0008-iroh-without-willow.md); `../../components/pdn-node/invariants.md` (Invariant 1).
