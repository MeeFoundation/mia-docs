---
status: proposed
date: 2026-06-02
---
# Use iroh-docs without Willow: untrusted sync + a PDN-side validation gate

## Context and Problem Statement

The planned path ([ADR-0005](0005-why-willow.md), [ADR-0006](0006-why-fork-of-willow.md)) puts a *forked* Willow layer between the PDN node and iroh, so that fine-grained, revocable, MeeId-bound capabilities ([ADR-0004](0004-capabilities-should-refer-to-mee-id.md), [ADR-0007](0007-uwill.md)) are enforced natively at the sync layer. Forking Willow and integrating UWill into its authorization is a large, open-ended effort.

Can we ship document replication **sooner** by using `iroh-docs` as-is — deferring or avoiding the Willow fork — without weakening UWill's guarantees? Two hard constraints frame the answer: we will **not fork iroh**, and we will **not write our own sync protocol**. iroh-docs must do the syncing, unchanged.

Facts verified against iroh-docs 0.100:

1. A remote entry is accepted on **namespace+author Ed25519 signature, namespace-id match, and timestamp ≤ now+10min** — nothing else. There is **no injectable pre-persist authorization/validation hook** for incoming entries: the ingest gate (`validate_entry`) is hardcoded, and we can only observe writes *after* they land via `subscribe`. A genuine veto would require forking that seam — ruled out by the constraints.
2. iroh share tickets are **bearer tokens with no expiry and no revocation**: once a `Write` ticket is handed out, the holder can produce namespace-signed entries indefinitely.
3. Therefore iroh-docs cannot, by itself, enforce per-claim, time-bound, revocable, MeeId-scoped capabilities. Whatever it stores must be treated as **untrusted**.

The forcing question: if iroh's store is untrusted, *where* does authorization happen, and *how* is trusted state derived from it?

## Decision Drivers

* Ship replication sooner — save the Willow-fork implementation cost.
* No fork of iroh; no bespoke sync protocol (iroh-docs unchanged).
* Preserve UWill's guarantees (per-claim, expiring, revocable, MeeId-bound) regardless of what the transport enforces.
* A *cheap* pre-filter for metadata sync — "could this even have reached me?", i.e. does a connection with this MeeId exist at all — without running full UWill validation on every gossiped record.
* Untrusted input is adversarial: forged / replayed / spam entries must never become trusted state; eviction and GC must be possible.
* Confidentiality: the untrusted store is readable by every peer that can sync it.

## Considered Options

* **Fork Willow now and enforce UWill at the sync layer** — the [ADR-0006](0006-why-fork-of-willow.md) path.
* **Fork iroh-docs** to inject a pre-persist authorization callback at the `validate_entry` seam.
* **Use iroh-docs unchanged as an untrusted store; validate at a PDN-side gate** (observe-then-reconcile into trusted storage). ← chosen

## Decision Outcome

Chosen option: **iroh-docs unchanged as an untrusted store, with a PDN-side validation gate**, because it is the only option that satisfies both hard constraints (no iroh fork, no custom sync) while preserving UWill — and it *defers* rather than deletes the Willow fork.

The model (working names — see open questions):

**Three locations across two trust tiers.**

1. **Untrusted store** — one or more `iroh-docs` replicas. iroh-docs owns *all* networking, gossip, and reconciliation. We assume every record here is adversarial; iroh's signature / namespace / timestamp checks are the only floor.
2. **Trusted metadata store** — local, non-replicated. Admission gated by **Peering** (the lightweight connection capability): we keep metadata only for MeeIds we actually have a connection with. Answers "could this legitimately have reached me?".
3. **Trusted data store** — local, non-replicated. Admission gated by **UWill**: per-claim, expiring, revocable, MeeId-bound payload admission.

**The gate (promotion).** A trusted PDN-side task drains the untrusted store (via `subscribe` / reads), validates each record, and only then writes into the trusted metadata / data stores. Because iroh-docs has no pre-write veto, the gate is **promotion-time, observe-then-reconcile** — not write-time. Records that fail validation are never promoted and are GC'd from the untrusted store; revocations (themselves records) cause already-promoted state to be **evicted** on recompute. Trusted state is thus a deterministic projection of the validated subset of the untrusted log — rebuildable and revocation-aware.

**Two capability tiers, carried as payload data (not transport ACLs).**

* **UWill** ([ADR-0007](0007-uwill.md)) — the heavyweight, per-claim, expiring, revocable, MeeId-bound capability. Verified at the gate; governs admission into the trusted **data** store.
* **Peering** — the lightweight connection capability. Proves only that a **connection with a given MeeId exists**, i.e. that a piece of *metadata* could legitimately have reached us. A cheap pre-filter on metadata sync before (or instead of) full UWill evaluation; governs admission into the trusted **metadata** store. It must carry **its own** expiry / revocation, since iroh tickets cannot.

**iroh tickets are demoted to transport bootstrap only** — "can this peer reach / append to the untrusted store", never "is this peer authorized". Their lack of expiry / revocation is acceptable *precisely because* untrusted-store access grants no trusted access; authority lives entirely in the two capability tiers above, which we control.

### Consequences

* Good, because we ship on iroh-docs unchanged — no Willow fork, no iroh fork, no custom sync on the critical path.
* Good, because UWill's guarantees are independent of the transport: forever-tickets and unauthenticated relays cannot forge trusted state.
* Good, because trusted state is a rebuildable projection → revocation and conflict resolution fall out as recompute / evict.
* Good, because Peering rejects metadata from non-connections cheaply, without full UWill on every record.
* Bad, because there is no *prevention*: the untrusted store can be spammed / polluted; we can only refuse to promote and then GC. Needs quotas / TTL / cleanup.
* Bad, because validated data is duplicated (untrusted copy + trusted copy) and the gate adds latency / eventual consistency between "synced" and "trusted".
* Bad, because confidentiality requires encrypting payloads in the untrusted store (world-readable to syncing peers); the gate also has to decrypt.
* Neutral, because the Willow fork is deferred, not abandoned — if native sync-layer enforcement later proves worth it, this gate becomes the spec for what the fork must enforce.
* Known gap: Peering is named but not yet specified; untrusted-store topology and promotion timing are open (see below).

## Validation

A draft `impl` of the PDN sync layer (the `WillowLayer` trait) over iroh-docs that: writes only to the untrusted store; promotes via the gate into the trusted metadata / data stores; rejects forged / expired / revoked records under adversarial test inputs; and rebuilds trusted state from the untrusted log alone. The existing `iroh-docs-experiment` crate is the staging ground. Compliance criterion: **no record reaches trusted storage without passing Peering (metadata) or UWill (data) validation at the gate.**

## Pros and Cons of the Options

### Fork Willow now and enforce UWill at the sync layer
* Good, native per-claim / revocable enforcement at sync time; the untrusted store ≈ the trusted store.
* Good, prevention rather than cleanup — no observe-then-evict window.
* Bad, large, open-ended implementation; blocks replication on the fork.
* Bad, couples shipping to Willow + UWill integration risk.

### Fork iroh-docs to inject a pre-persist authorization callback
* Good, a true pre-write veto; the `validate_entry` / `validate_cb` seam is small and clean.
* Bad, violates the "don't fork iroh" constraint; we then own a divergent iroh-docs.
* Bad, still does not fix forever-tickets, and does not give UWill semantics without further work.

### iroh-docs unchanged as untrusted store + PDN-side gate (chosen)
* Good, satisfies both hard constraints; fastest path to replication.
* Good, transport-independent UWill; rebuildable, revocation-aware trusted state.
* Neutral, capabilities live as payload data, not as transport ACLs.
* Bad, no prevention (spam / pollution → GC needed); data duplicated; confidentiality needs payload encryption.

## More Information

The shape of this ADR: an untrusted store synced unchanged by iroh-docs, and a trusted store gated by our own validation — any peer may append to the untrusted store, but records enter trusted storage only after passing our checks. Names here ("untrusted store", "trusted store") are working titles to be revisited; the lightweight capability is named **Peering**.

Open questions to resolve before `accepted`:

1. **Untrusted-store topology** — per-connection / per-recipient inbox / per-namespace replicas.
2. **Promotion timing** — synchronous on read vs background reconcile.
3. **Confidentiality** — payload-encryption scheme for the untrusted store.
4. **GC / quota** policy for un-promotable records.
5. **Peering spec** — exact format, expiry / revocation mechanism, and its relationship to UWill (a degenerate UWill, or a separate token?).

Related ADRs: [ADR-0004](0004-capabilities-should-refer-to-mee-id.md), [ADR-0005](0005-why-willow.md), [ADR-0006](0006-why-fork-of-willow.md), [ADR-0007](0007-uwill.md).

External references: iroh-docs 0.100 — remote entries validated by namespace / author signature + timestamp only (`Replica::insert_entry` → `validate_entry`, `iroh-docs/src/sync.rs`); no injectable pre-persist hook (only after-the-fact `Doc::subscribe`); `DownloadPolicy` gates blob *download*, not record ingestion; share tickets are non-expiring bearer tokens.
