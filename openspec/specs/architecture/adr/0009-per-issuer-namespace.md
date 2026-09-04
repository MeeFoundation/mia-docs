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
- **One `pdn-store` namespace per issuer.** All of an issuer's claims (about anyone) live in that one namespace — a separate set-reconciliation unit and gossip topic per issuer, not the issuer as a key-prefix inside a single shared namespace. The data layer's registry keys each data replica by its issuer `PdnId`.
- **Granularity lives entirely in the capability** (per claim), not in the namespace boundary. What carries it is the issuer's recorded read capabilities; UWill ([ADR-0007](0007-uwill.md)) is the format that grant grows into.
- **pdn-node's surface is namespace-free.** Nothing in its API names a namespace: claims are addressed by `ClaimId` and authorized per claim. Inside the runtime the ids are held all the same — the ceremonies hand over tickets to the directory and the data namespace, and the replicas they open have to be registered — so the property is one of the surface, not of the crate.
- **The namespace is demoted to a replication bucket** — the iroh-docs set-reconciliation unit and gossip topic, nothing more. Addressing moves to `ClaimId`, write-authority to the capability.

A namespace survives because **a capability authorizes, it does not replicate**: a per-issuer set that replicates by reconciliation is irreducible on iroh-docs, so we coarsen it to one-per-issuer rather than try to remove it.

This is orthogonal to the device-internal store (`PrivateMetadataStore`, the directory), which is bound by `identity` and admitted by Invariant 1 (see `../../components/mee-pdn/invariants.md`): unaffected by how data namespaces are addressed.

## Consequences

- Good — removes a redundant granularity axis; UWill becomes the single authorization mechanism; aligns the namespace with the issuer identity.
- Good — simpler addressing: one replica per issuer, not one per subject.
- Good — pdn-node is namespace-free: a smaller, capability-only surface (`ClaimId` + UWill), with `Binding`/`BindingIndex` demoted to `data-layer` internals.
- Bad — the capability gate (ADR-0008) becomes the sole writer authority: namespace-key possession no longer authorizes writes, so correctness leans entirely on the fork's ingest checks.

## Rejected alternative: one namespace for all issuers

Both layouts put every issuer's claims in the node's single physical store — iroh-docs keeps all namespaces in shared redb tables keyed by namespace. They differ in namespace count: per-issuer carves one namespace per issuer; the alternative uses one namespace holding everyone, with the issuer as a key-prefix inside it, filtering each reconciliation session down to what the peer may read. Considered and rejected.

- The namespace, not the physical store, is iroh-docs' reconciliation unit, gossip topic, and capability boundary. Reconciliation cost is set by the size of the namespace being reconciled, before any read-filter — the filter runs after and does not reduce it. A per-issuer namespace holds one issuer's claims; one shared namespace holds everyone's, so every session pays for the whole set to deliver the few claims a peer actually reads.
- The property that an already-synced namespace re-confirms in one round survives only per-issuer. A single issuer's namespace is usually quiescent, so its re-sync is near-instant; a shared namespace aggregates every writer and is never quiescent, so each peer re-descends the whole set on every write anywhere in it — including writes it may not read, which the filter then discards.
- Today that re-descent is proportional to the namespace's entry count (the fork computes a range fingerprint by scanning the range — its `// TODO: optimize`). Even once that is optimized to a cached fingerprint tree, one shared namespace still couples all writers into a single tree and routes every peer through it; per-issuer keeps each writer's changes in a separate tree a peer touches only when it reads that issuer.
- No storage is saved by sharing one namespace: the node already has a single physical store (one redb database) holding every namespace in shared tables, so per-issuer namespaces are key-ranges in those shared tables, not separate databases. The axis is namespace count, not store count.
- Independently of reconciliation cost, the per-issuer namespace is the authorization unit (a device fully owns its issuer's namespace — Invariant 1), revocation drops a whole namespace rather than excising claims scattered through a shared one, and gossip membership is per-namespace (an issuer's own devices swarm its namespace while scoped readers reconcile point-to-point outside it) — none of which one shared namespace can express.

## More Information

A cell, as the cells change designs it, is one shared replica held whole by every member's devices — a namespace that is not per issuer. The rejected alternative above does not argue against it: that argument is about one namespace holding every issuer's claims and serving each peer a filtered view of it, whereas a cell has bounded membership, runs no egress filter, and its members' devices are its own swarm. An identity's own data keeps the per-issuer namespace either way.

The realization is specified in `../../components/mee-pdn/pdn-node/namespace-addressing.md` (the namespace-free addressing surface). The interim namespace-key/mapping path, confidentiality, device bootstrap, and pre-UWill relaxations live in the design of the archived `per-issuer-namespace` change, not in this ADR.

Related: [ADR-0007](0007-uwill.md), [ADR-0008](0008-iroh-without-willow.md); `../../components/mee-pdn/invariants.md` (Invariant 1).
