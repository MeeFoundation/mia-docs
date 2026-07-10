---
status: proposed
date: 2026-07-01
---

# Restrict reads at reconciliation time (subset-RBSR)

## Context and Problem Statement

Invariant 2 requires that a node receive a record only if it holds a read capability for it. But iroh-docs reconciliation converges two peers to the union of a whole document — there is no per-record read control, so any peer that can sync a replica receives every record in it. ADR-0008 gave the write side a gate at ingest; the read side has no counterpart.

## Decision

Enforce per-record read access by filtering what a serving node reveals during reconciliation — subset-RBSR: reconcile only the subset a peer may read. A record the peer holds no read capability for is never revealed during reconciliation, so neither its content nor its existence reaches the peer. This is the read-side counterpart of the ADR-0008 ingest gate and, like it, lives inside `pdn-store` — but reaches deeper, into the reconciliation path rather than the single `validate_entry` hook.

## Consequences

- Good — per-record read control at sync time, symmetric with the ingest gate; the record, not the replica, becomes the unit of read access.
- Bad — a second, deeper modification to `pdn-store`: the reconciliation path, not only the ingest hook.
- Neutral — same-identity reconciliation is unaffected: an identity's own devices are read-authorized for all of that identity's data (Invariant 1).

## More Information

The realization — the egress filter, the minimal read capability it consumes, and the trade-offs — is specified in the `subset-rbsr` change. Related: [ADR-0008](0008-iroh-without-willow.md) (the ingest gate), [ADR-0007](0007-uwill.md) (UWill, the capability the read grant grows into); Invariant 2 (`../../components/pdn-node/invariants.md`).
