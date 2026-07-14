---
status: proposed
date: 2026-06-03
---
# Use iroh-docs without Willow: our own iroh-docs variant with a capability-gated ingest

## Context and Problem Statement

The planned path (ADR-0005, ADR-0006) puts a *forked* Willow layer between the PDN node and iroh, so that fine-grained, revocable, PdnId-bound capabilities ([ADR-0004](0004-capabilities-should-refer-to-mee-identity.md), [ADR-0007](0007-uwill.md)) are enforced natively at the sync layer. Forking Willow and integrating UWill into its authorization is a large, open-ended effort.

Can we ship document replication **sooner** by syncing over `iroh-docs` — deferring or avoiding the Willow fork — *without* giving up native, write-time capability enforcement? Two constraints frame the answer: we will **not fork iroh** (the endpoint / transport / set-reconciliation engine) and we will **not write our own sync protocol**. iroh-docs must remain the thing that syncs.

The obvious answer is to treat iroh-docs as an immutable black box: sync everything unchanged into an *untrusted* store, and authorize after the fact at a PDN-side promotion gate. That works, but it buys shipping speed with a permanent tax: no prevention (the untrusted store can be spammed and must be GC'd), data duplicated across an untrusted and a trusted copy, and an observe-then-evict window between "synced" and "trusted". The sharper question the black-box assumption skips: **iroh-docs is small — a multi-writer KV store plus automerge-style reconciliation — so do we actually have to treat it as immutable?**

Facts verified against iroh-docs 0.100 (our fork: `github.com/MeeFoundation/pdn-store`):

1. Ingest funnels through **one** validation chokepoint: `validate_entry()` (`src/sync.rs:622`), called by both the direct `insert_remote_entry → insert_entry` path (`src/sync.rs:452`) and the live-sync path. It accepts on **namespace+author Ed25519 signature, namespace-id match, and timestamp ≤ now+10min** (`MAX_TIMESTAMP_FUTURE_SHIFT`, `src/sync.rs:48`) — nothing else.
2. That chokepoint sits on top of an **already-existing, per-entry, pre-persist accept/reject callback**. The set-reconciliation engine's `process_message()` takes a `validate_cb(&store, &entry, content_status) -> bool` (`src/ranger.rs:324`, doc at `:314`); when it returns `false` the entry is **dropped and never stored** (the `put` at `src/ranger.rs:394` is guarded by it). iroh-docs simply hardwires that callback to `validate_entry(...).is_ok()` (`src/sync.rs:548–555`) and does **not** expose it through its public API.
3. iroh share tickets are **bearer tokens with no expiry and no revocation**: once a `Write` ticket is handed out, the holder can produce namespace-signed entries indefinitely.

So while iroh-docs exposes no injectable pre-persist hook through its public API, internally the veto already exists, it is clean (one boolean per entry, evaluated before `put`), and it sits exactly where iroh-docs already does signature/timestamp validation. The forcing question becomes: **do we author our own variant of iroh-docs that runs our capability check at that seam — accepting or rejecting each entry at write time — or do we keep iroh-docs verbatim and pay the untrusted-store tax forever?**

## Decision Drivers

* Ship replication sooner than the Willow fork — but keep **prevention** (reject bad entries before they persist), not just post-hoc cleanup.
* No fork of **iroh** (transport / endpoint / set-reconciliation); no bespoke sync protocol.
* Keep the modification to iroh-docs **minimal and upstream-trackable** — a thin seam we re-apply across releases, not a divergent rewrite. iroh-docs is a KV-store + automerge, small enough that this is cheap (unlike Willow).
* Preserve UWill's guarantees (per-claim, expiring, revocable, PdnId-bound), enforced at the sync layer rather than bolted on afterwards.
* Capabilities are **data we control** — a verifiable key/delegation chain ([ADR-0007](0007-uwill.md)) — not iroh ACLs; iroh tickets cannot carry expiry or revocation.
* The gate needs the issued capabilities on hand when data arrives → a way to deliver them ahead of / alongside the data.

## Considered Options

* **Fork Willow now and enforce UWill at the sync layer** — the ADR-0006 path.
* **iroh-docs verbatim as an untrusted store + a PDN-side promotion gate** (observe-then-reconcile).
* **Our own minimal iroh-docs variant with a capability-gated ingest** — inject the UWill/Peering check at the existing `validate_entry` / `validate_cb` seam, so each entry is accepted (auto-merged) or rejected at write time. ← chosen

## Decision Outcome

Chosen option: **our own minimal variant of iroh-docs with a capability-gated ingest**, because it restores native, write-time capability enforcement at the cost of a *thin, well-located* modification — far cheaper than the Willow fork, and without the untrusted-store tax of the verbatim option.

It is a **fork in the git sense, but deliberately not a divergent one**: we do not re-architect iroh-docs, we vendor it and own a single seam ("свой вариант", not a rewrite). We still do **not** fork iroh itself, and the change is small enough to re-base onto upstream iroh-docs releases. The fork lives at `github.com/MeeFoundation/pdn-store`; the `data-layer` crate, building against it, is the staging ground.

**The seam.** `validate_entry()` (`src/sync.rs:622`) — the single chokepoint both ingest paths already call — gains a capability check. Equivalently/additionally, the ranger's `validate_cb` (`src/ranger.rs:324`) is plumbed out to a PDN-supplied validator instead of being hardwired to `validate_entry(...).is_ok()`. The callback already returns `bool` and already runs before `put`, so the semantics are exactly: **valid capability chain → auto-merge into the persistent store; invalid → turned away, never stored.** No separate untrusted store, no GC of junk, no observe-then-evict window.

**Capabilities are a verifiable key-chain, carried as payload/metadata — not transport ACLs.**

* **UWill** ([ADR-0007](0007-uwill.md)) — the heavyweight, per-claim, expiring, revocable, PdnId-bound capability: a delegation chain of keys plus a `PdnIdentityProof`, verifiable offline. Checked at the gate; governs admission of **data** entries.
* **Peering** — the lightweight connection capability ("does a connection with this PdnId exist"): a cheap pre-filter, carrying its own expiry/revocation since iroh tickets cannot. Governs admission of **metadata** entries.

**Capability delivery (metadata channel).** For the gate to validate a data entry, the relevant capability must already be local. Issued capabilities are therefore delivered to the peer **as metadata** ahead of the data they authorize: a dedicated metadata store/namespace, reachable by its own ticket, into which capabilities are written (and themselves Peering-gated on ingest). When data entries then arrive, the data-side validator looks the chain up locally. This matters because `validate_cb` sees the entry's record (key, author, content hash, timestamp, `ContentStatus`) but **not necessarily the blob content** — so authorization cannot depend on downloading the payload first.

**iroh tickets are demoted to transport bootstrap only** — "can this peer reach / write to this store", never "is this peer authorized". Their lack of expiry/revocation is acceptable because authority lives entirely in the capability chains we check at the gate.

### Consequences

* Good — **prevention, not cleanup**: forged / unauthorized / expired entries are rejected before they persist. No untrusted holding store, no spam-GC, no observe-then-evict window, no untrusted⇄trusted duplication.
* Good — native UWill enforcement at sync time, but at a fraction of the Willow-fork cost: the change is one boolean seam over a KV-store-plus-automerge.
* Good — still no iroh (transport) fork and no custom sync protocol; iroh-docs still does the syncing.
* Good — capabilities stay transport-independent: forever-tickets and unauthenticated relays cannot forge admitted state, because admission is our check, not iroh's signature floor.
* Bad — **we now own a variant of iroh-docs** and must track upstream (0.100 → later). Mitigated by keeping the change minimal and localized to `validate_entry` / `validate_cb`; the standing risk is that upstream reworks that seam.
* Bad — **revocation after admission is not covered by an ingest gate alone.** A capability valid at write time can be revoked later; a pre-persist veto stops bad *new* entries but does not retract an already-merged one. We still need revocations-as-entries to trigger eviction / re-validation of previously admitted state (the one thing the observe-then-reconcile model got for free).
* Bad — **bootstrapping order**: the metadata/capability channel must be populated before the data it authorizes, or valid data is rejected as un-authorizable and must be re-offered.
* Bad — confidentiality unchanged: entries are readable by every peer that can sync the store; sensitive payloads still need encryption, and the gate must decrypt to validate where the capability lives in content.
* Neutral — the Willow fork is deferred, not abandoned; this variant's gate is a smaller, concrete spec of what native enforcement must do.

## Validation

A draft `impl` of the PDN data layer (the `DataLayer` trait) over the iroh-docs variant that: rejects forged / expired / revoked / un-peered entries **at the `validate_entry` / `validate_cb` seam** under adversarial test inputs (rejected entries must be *absent* from the store, not merely unpromoted); admits valid entries by auto-merge; delivers capabilities over the metadata channel ahead of data; and evicts previously-admitted entries when a later revocation arrives. The `data-layer` crate, depending on the variant via git (`MeeFoundation/pdn-store`), is the staging ground. Compliance criterion: **no entry is stored that fails Peering (metadata) or UWill (data) validation at ingest.**

## Pros and Cons of the Options

### Fork Willow now and enforce UWill at the sync layer
* Good, native per-claim / revocable enforcement; designed for exactly this.
* Bad, large, open-ended implementation; blocks replication on the fork and on UWill integration risk.

### iroh-docs verbatim as an untrusted store + PDN-side promotion gate
* Good, zero modification to iroh-docs; fastest possible start.
* Good, trusted state is a rebuildable projection → revocation falls out as recompute / evict.
* Bad, no prevention — the untrusted store is spammable and needs quotas / TTL / GC.
* Bad, data duplicated (untrusted + trusted) and an eventual-consistency lag between "synced" and "trusted".

### Our own minimal iroh-docs variant with a capability-gated ingest (chosen)
* Good, write-time prevention at the seam iroh-docs already validates on; no untrusted-store tax.
* Good, minimal, upstream-trackable change over a small codebase; cheaper than Willow by far.
* Neutral, capabilities live as data (key-chains) we check, not as transport ACLs.
* Bad, we maintain a variant and must re-apply the seam across releases.
* Bad, revocation-after-admission and capability-delivery ordering still need their own machinery.

## More Information

The crux: iroh-docs is small enough (KV store + automerge over iroh's set-reconciliation) that we don't have to treat it as immutable — and the pre-persist accept/reject callback we need **already exists** internally (`ranger::process_message`'s `validate_cb`, currently hardwired to `validate_entry(...).is_ok()`), it just isn't exposed. Owning a thin variant that runs our capability chain there is far cheaper than the Willow fork and avoids the verbatim option's permanent untrusted-store cost. Names ("Peering", "metadata / data store") are working titles.

Open questions to resolve before `accepted`:

1. **Seam shape** — extend `validate_entry()` directly vs. plumb `validate_cb` out as a public, PDN-supplied validator; how to give it access to the capability/metadata index without the blob content.
2. **Revocation after admission** — revocations-as-entries + eviction / re-validation pass; how it interacts with automerge's last-writer-wins.
3. **Capability delivery** — the metadata-channel bootstrap: ticketed metadata store, write / Peering rules, and ordering vs. the data it authorizes.
4. **Upstream tracking** — vendoring / rebase strategy for the variant; pinning vs. following iroh-docs releases.
5. **Peering spec** — exact format, expiry / revocation, relationship to UWill (a degenerate UWill, or a separate token?).
6. **Confidentiality** — payload encryption for sensitive entries and how the gate validates over it.

Related ADRs: [ADR-0004](0004-capabilities-should-refer-to-mee-identity.md), [ADR-0007](0007-uwill.md). ADR-0005 (why Willow) and ADR-0006 (why a fork of Willow) were removed when the Willow-assuming material was cleaned up (commit e8a352a) and survive only in git history; the numbers 0005 and 0006 are not reused.

External references: iroh-docs 0.100 — single ingest chokepoint `validate_entry` (`src/sync.rs:622`), called from `insert_entry` (`:452`) and the live-sync `validate_cb` closure (`:548–555`); per-entry pre-persist accept/reject `validate_cb` in `ranger::process_message` (`src/ranger.rs:314,324,394`), not exposed publicly; share tickets are non-expiring bearer tokens.
