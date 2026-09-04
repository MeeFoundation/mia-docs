---
status: accepted
date: 2026-09-04
---

# Restrict reads at reconciliation time (subset-RBSR)

## Context and Problem Statement

Invariant 2 requires that a node receive a claim only if it holds a read capability for it. But iroh-docs reconciliation converges two peers to the union of a whole document — there is no per-claim read control, so any peer that can sync a replica receives every claim in it. ADR-0008 gave the write side a gate at ingest; the read side has no counterpart.

## Decision

Enforce per-claim read access by filtering what a serving node reveals during reconciliation — subset-RBSR: reconcile only the subset a peer may read. A claim the peer holds no read capability for is never revealed during reconciliation, so neither its content nor its existence reaches the peer. This is the read-side counterpart of the ADR-0008 ingest gate and, like it, lives inside `pdn-store` — but reaches deeper, into the reconciliation path rather than the single `validate_entry` hook.

## Consequences

- Good — per-claim read control at sync time, symmetric with the ingest gate; the claim, not the replica, becomes the unit of read access.
- Bad — a second, deeper modification to `pdn-store`: the reconciliation path, not only the ingest hook.
- Neutral — same-identity reconciliation is unaffected: an identity's own devices are read-authorized for all of that identity's data (Invariant 1).

## More Information

Inside a cell the filter has no work: the cell store is served whole to member devices, and read access there is membership rather than a per-claim capability, with gossip among the members in place of the egress filter. What keeps this decision alive is everything served outside a cell — an issuer's namespace reconciled with an audience under a grant, and an identity's own namespaces. Cells narrow where the read filter applies; unlike the capability format it enforces ([ADR-0007](0007-uwill.md)), they do not leave it without a subject.

The realization is specified in [subset reconciliation](../../components/data-layer/subset-reconciliation.md) and the grant vocabulary it consumes in [read capabilities](../../components/data-layer/read-capabilities.md); the filter itself lives in `crates/pdn-store`. The trade-offs weighed while building it stay in the design of the archived `subset-rbsr` change. Related: [ADR-0008](0008-iroh-without-willow.md) (the ingest gate), [ADR-0007](0007-uwill.md) (UWill, the capability the read grant grows into); Invariant 2 (`../../components/pdn-node/invariants.md`).
