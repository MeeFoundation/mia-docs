# Design: per-issuer-namespace

## Context

ADR-0009 collapses the `(about, issued_by)` namespace pair to one namespace per issuer, moves granularity to UWill, and makes pdn-node namespace-free. The ADR records only what is expensive to reverse. This document records how it is realized and the interim choices — the parts that change cheaply as UWill lands.

## Goals / Non-Goals

**Goals:**

- `pdn-types` carries no `(about, issued_by)` namespace; `data-layer` binds data by issuer; pdn-node names no namespace.
- A single addressing axis (`ClaimId`) and a single authorization mechanism (UWill).

**Non-Goals (this change):**

- Implementing UWill (ADR-0007).
- Computing the namespace key from identity / removing the mapping (deferred — D2).
- Lazy data-namespace import at device linking (D4 records the rail; the import is a follow-up).

## Decisions

### D1. The namespace survives, coarsened — not removed

UWill authorizes; it does not replicate. A per-issuer set that replicates by reconciliation is irreducible on iroh-docs, so we coarsen it to one-per-issuer and stop surfacing it, rather than try to remove it. Pushing to zero replicas would mean a different substrate (content-addressed claims fetched per UWill) and rebuilding replication by hand — latest-wins per claim, revocation propagation, a what's-new index — each itself a replicating set, i.e. a namespace under another name.

The namespace keeps only its two iroh-docs roles — the set-reconciliation unit and the gossip topic — and sheds the other two: addressing moves to `ClaimId`, write-capability to UWill.

### D2. Interim: random namespace key + mapping; computed key deferred to UWill

The end state is to compute the namespace key from the issuer identity and drop the `BindingIndex` mapping. That is safe only once write-authority is UWill, not possession of the namespace secret.

In iroh-docs, write = possession of the namespace secret, and we still hand that secret out (Write `DocTicket`s at linking). A **random** secret is safe to share as a bearer write-cap: losing it leaks one replica and nothing about the identity. A secret **derived from the issuer identity** is not — it is bound to the identity's key material, unrevocable without rotating the identity, and sharing it is exactly the "a derived secret can't be safely shared" hazard.

So while write = secret-possession, the namespace key MUST be random, and `data-layer` keeps `{random nsId → Binding}` (the issuer is not recoverable from a random key). Once UWill replaces secret-possession with proof-of-capability, the secret is never shared, the key can be derived from (and verified against) the issuer identity, and the mapping is eliminated.

**Cost of the interim:** `data-layer` must persist its binding metadata to rebuild `{nsId → Binding}` across restarts; the computed key would remove that.

### D3. Confidentiality is deferred to UWill

Not solved here, and one-per-issuer doesn't make it worse: the replica boundary was never the confidentiality tool — the gate (ADR-0008) is admission-only, so anyone who can sync a replica already reads all of it. Real content confidentiality (encryption, access control) is UWill-era, not replica partitioning.

### D4. Device bootstrap: one directory rail, two planes

A linked device comes up from a single seed — the `PrivateMetadataStore` ticket — and discovers every other store through that directory (`tickets/<kind>`); there is no second bootstrap path. Two planes:

- **Control plane** (directory + connections store): small, imported eagerly, blocking `link_device` under a liveness timeout.
- **Data plane** (per-issuer data namespaces, potentially large): discovered the same way but imported lazily, after linking — staged, not unimplemented.

The directory is complete by construction: every store an identity owns publishes its ticket into it (enforced in pdn-node; until then upheld by the caller). A device self-registers into the device set only after the directory has caught up, so the write does not race initial sync. Mechanics live in `components/data-layer/device-linking.md`.

### D5. Pre-UWill access is relaxed by design

The seed is a bearer write-ticket — write because the device self-registers, bearer because identity-bound, revocable, least-privilege access (a read-only directory seed plus a scoped join capability, per-store/per-claim grants) is UWill's job. These relaxations — bearer tickets (D5), random keys + mapping (D2) — are accepted until UWill lands. No enforced trust-ramp is built on bearer tokens, since any holder that syncs the directory already reads every ticket in it.

## Risks / Trade-offs

- **[Gate is sole writer authority]** Once granularity and write-auth leave the namespace, correctness leans entirely on the fork's ingest checks (ADR-0008). Accepted; it is the point of the collapse.
- **[Interim mapping persistence]** Random keys force `data-layer` to persist binding metadata to survive restarts (D2). Removed when the computed key lands.

## Open Questions

- Namespace-key derivation scheme (KDF, domain separation per binding kind) — specified when UWill makes derivation safe (D2).
- Data-plane import staging detail (eager vs on-first-access for large namespaces) — D4 fixes the rail, not the schedule.
