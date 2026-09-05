---
status: accepted
date: 2026-09-04
---
# Use iroh-docs without Willow: our own iroh-docs variant with a capability-gated ingest

## Context and Problem Statement

The planned path (ADR-0005, ADR-0006) puts a *forked* Willow layer between the PDN node and iroh, so that fine-grained, revocable, PdnId-bound capabilities ([ADR-0004](0004-capabilities-should-refer-to-mee-identity.md), [ADR-0007](0007-uwill.md)) are enforced natively at the sync layer. Forking Willow and integrating UWill into its authorization is a large, open-ended effort.

Can we ship document replication **sooner** by syncing over `iroh-docs` — deferring or avoiding the Willow fork — *without* giving up native, write-time capability enforcement? Two constraints frame the answer: we will **not fork iroh** (the endpoint / transport / set-reconciliation engine) and we will **not write our own sync protocol**. iroh-docs must remain the thing that syncs.

The obvious answer is to treat iroh-docs as an immutable black box: sync everything unchanged into an *untrusted* store, and authorize after the fact at a PDN-side promotion gate. That works, but it buys shipping speed with a permanent tax: no prevention (the untrusted store can be spammed and must be GC'd), data duplicated across an untrusted and a trusted copy, and an observe-then-evict window between "synced" and "trusted". The sharper question the black-box assumption skips: **iroh-docs is small — a multi-writer KV store plus automerge-style reconciliation — so do we actually have to treat it as immutable?**

Facts verified against iroh-docs 0.100, the release the variant starts from:

1. Ingest funnels through **one** validation chokepoint: `validate_entry()` in `src/sync.rs`, called by both the direct `insert_remote_entry → insert_entry` path and the live-sync path. It accepts on **namespace+author Ed25519 signature, namespace-id match, and timestamp ≤ now+10min** (`MAX_TIMESTAMP_FUTURE_SHIFT`) — nothing else.
2. That chokepoint sits on top of an **already-existing, per-entry, pre-persist accept/reject callback**. The set-reconciliation engine's `process_message()` takes a `validate_cb(&store, &entry, content_status) -> bool` in `src/ranger.rs`; when it returns `false` the entry is **dropped and never stored**, because the `put` is guarded by it. iroh-docs simply hardwires that callback to `validate_entry(...).is_ok()` and does **not** expose it through its public API.
3. iroh share tickets are **bearer tokens with no expiry and no revocation**: once a `Write` ticket is handed out, the holder can produce namespace-signed entries indefinitely.

So while iroh-docs exposes no injectable pre-persist hook through its public API, internally the veto already exists, it is clean (one boolean per entry, evaluated before `put`), and it sits exactly where iroh-docs already does signature/timestamp validation. The forcing question becomes: **do we author our own variant of iroh-docs that runs our capability check at that chokepoint — accepting or rejecting each entry at write time — or do we keep iroh-docs verbatim and pay the untrusted-store tax forever?**

## Decision Drivers

* Ship replication sooner than the Willow fork — but keep **prevention** (reject bad entries before they persist), not just post-hoc cleanup.
* No fork of **iroh** (transport / endpoint / set-reconciliation); no bespoke sync protocol.
* Keep the modification to iroh-docs **minimal and upstream-trackable** — a thin, localized change we re-apply across releases, not a divergent rewrite. iroh-docs is a KV-store + automerge, small enough that this is cheap (unlike Willow).
* Preserve UWill's guarantees (per-claim, expiring, revocable, PdnId-bound), enforced at the sync layer rather than bolted on afterwards.
* Capabilities are **data we control** — a verifiable key/delegation chain ([ADR-0007](0007-uwill.md)) — not iroh ACLs; iroh tickets cannot carry expiry or revocation.
* The gate needs the issued capabilities on hand when data arrives → a way to deliver them ahead of / alongside the data.

## Considered Options

* **Fork Willow now and enforce UWill at the sync layer** — the ADR-0006 path.
* **iroh-docs verbatim as an untrusted store + a PDN-side promotion gate** (observe-then-reconcile).
* **Our own minimal iroh-docs variant with a capability-gated ingest** — inject the UWill/Peering check at the existing `validate_entry` / `validate_cb` hook, so each entry is accepted (auto-merged) or rejected at write time. ← chosen

## Decision Outcome

Chosen option: **our own minimal variant of iroh-docs with a capability-gated ingest**, because it restores native, write-time capability enforcement at the cost of a *thin, well-located* modification — far cheaper than the Willow fork, and without the untrusted-store tax of the verbatim option.

It is a **fork in the git sense, but deliberately not a divergent one**: we do not re-architect iroh-docs, we vendor it and change a single point (a variant of our own, not a rewrite). We still do **not** fork iroh itself, and the change is small enough to re-base onto upstream iroh-docs releases. The variant lives in this workspace as the crate `pdn-store`, carrying upstream's version number; the `data-layer` crate, building against it, is the staging ground.

**The modification.** The ranger's `validate_cb` is plumbed out to a validator the data layer supplies, instead of being hardwired to `validate_entry(...).is_ok()`; `validate_entry` keeps its signature, namespace and timestamp checks untouched. The verdict is three-valued rather than boolean: **accept** — auto-merged into the persistent store; **reject** — turned away and echoed back on the reconciliation reply, so the sender retracts its own copy; **drop** — turned away in silence, for everything that is not a verdict on the sender's authority, such as a retraction this node already holds or a state it cannot read. No separate untrusted store, no GC of junk, no observe-then-evict window.

**What the gate judges.** Only a replica data-bound to an identity this node hosts: an entry from a device of the issuer is admitted whole, an entry from a granted writer is admitted when the claim it derives from lies inside that grant's write set, and a session the node cannot classify admits nothing — fail-closed. Directories and connection metadata stores are not capability-gated: they stay bounded by ticket possession and by the serving side's egress filter. The vocabulary the gate consumes is the issuer's recorded [read capabilities](../../components/mee-pdn/data-layer/read-capabilities.md), resolved against the session peer at session setup ([capability-gated ingest](../../components/mee-pdn/data-layer/capability-gated-ingest.md)).

**Capabilities are data we control, not transport ACLs.** A grant is a record the issuer writes and can narrow or withdraw, so authority never rests on ticket possession.

**Capability delivery (metadata channel).** For the gate to validate a data entry, the relevant capability must already be local. Issued capabilities are therefore delivered to the peer **as metadata** ahead of the data they authorize: a dedicated metadata store/namespace, reachable by its own ticket, into which capabilities are written. When data entries then arrive, the data-side validator looks the chain up locally. This matters because `validate_cb` sees the entry's record (key, author, content hash, timestamp, `ContentStatus`) but **not necessarily the blob content** — so authorization cannot depend on downloading the payload first.

**iroh tickets are demoted to transport bootstrap only** — "can this peer reach / write to this store", never "is this peer authorized". Their lack of expiry/revocation is acceptable because authority lives entirely in the capability chains we check at the gate.

### Consequences

* Good — **prevention, not cleanup**: forged / unauthorized / expired entries are rejected before they persist. No untrusted holding store, no spam-GC, no observe-then-evict window, no untrusted⇄trusted duplication.
* Good — native UWill enforcement at sync time, but at a fraction of the Willow-fork cost: the change is one boolean check over a KV-store-plus-automerge.
* Good — still no iroh (transport) fork and no custom sync protocol; iroh-docs still does the syncing.
* Good — capabilities stay transport-independent: forever-tickets and unauthenticated relays cannot forge admitted state, because admission is our check, not iroh's signature floor.
* Bad — **we now own a variant of iroh-docs** and must track upstream (0.100 → later). Mitigated by keeping the change minimal and localized to `validate_entry` / `validate_cb`; the standing risk is that upstream reworks that chokepoint.
* Bad — **revocation after admission is not covered by an ingest gate alone.** A capability valid at write time can be revoked later; a pre-persist veto stops bad *new* entries but does not retract an already-merged one. We still need revocations-as-entries to trigger eviction / re-validation of previously admitted state (the one thing the observe-then-reconcile model got for free).
* Bad — **bootstrapping order**: the metadata/capability channel must be populated before the data it authorizes, or valid data is rejected as un-authorizable and must be re-offered.
* Bad — confidentiality unchanged: entries are readable by every peer that can sync the store; sensitive payloads still need encryption, and the gate must decrypt to validate where the capability lives in content.
* Neutral — the Willow fork is deferred, not abandoned; this variant's gate is a smaller, concrete spec of what native enforcement must do.

## Validation

A draft `impl` of the PDN data layer (the `DataLayer` trait) over the iroh-docs variant that: rejects forged / expired / revoked / un-peered entries **at the `validate_entry` / `validate_cb` hook** under adversarial test inputs (rejected entries must be *absent* from the store, not merely unpromoted); admits valid entries by auto-merge; delivers capabilities over the metadata channel ahead of data; and evicts previously-admitted entries when a later revocation arrives. The `data-layer` crate, building against the in-tree variant, is the staging ground. Compliance criterion: **no entry is stored that the validator refuses** — an entry outside the sender's recorded write set is absent from a hosted issuer's replica, not merely unpromoted.

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
* Good, write-time prevention where iroh-docs already validates; no untrusted-store tax.
* Good, minimal, upstream-trackable change over a small codebase; cheaper than Willow by far.
* Neutral, capabilities live as data (key-chains) we check, not as transport ACLs.
* Bad, we maintain a variant and must re-apply the modification across releases.
* Bad, revocation-after-admission and capability-delivery ordering still need their own machinery.

## More Information

The crux: iroh-docs is small enough (KV store + automerge over iroh's set-reconciliation) that we don't have to treat it as immutable — and the pre-persist accept/reject callback we need **already exists** internally (`ranger::process_message`'s `validate_cb`, currently hardwired to `validate_entry(...).is_ok()`), it just isn't exposed. Owning a thin variant that runs our capability chain there is far cheaper than the Willow fork and avoids the verbatim option's permanent untrusted-store cost. The two capability kinds this decision expected at the gate are not what runs: UWill's token types live in `pdn-layer` and nothing enforces them, and Peering never became a token. Enforcing a delegation chain here waits on identity proofs ([ADR-0003](0003-mee-identity-represents-keri-autonomic-namespace.md), [ADR-0007](0007-uwill.md)).

What those open questions became:

1. **Check placement** — the ranger's callback is plumbed out and the data layer supplies the validator, so the gate reads the node's own recorded state and never the blob content.
2. **Revocation after admission** — retraction markers refuse the exact entries a withdrawal covers, and a rejected sender retracts its own copy on the echoed verdict ([write retraction](../../components/mee-pdn/data-layer/write-retraction.md)).
3. **Capability delivery** — grants travel in the [connection metadata store](../../components/mee-pdn/data-layer/connection-metadata-store.md) ahead of the data they authorize, and a session's write set is resolved from them at setup.
4. **Upstream tracking** — the variant is vendored into this workspace as `crates/pdn-store` and rebased onto upstream releases there.
5. **Peering** — dissolved. No such token exists: metadata replicas are not capability-gated, and admission there rests on ticket possession and the recorded connection.
6. **Confidentiality** — open. Entries are readable by every peer that can sync the store, and payload encryption is not built.

Related ADRs: [ADR-0004](0004-capabilities-should-refer-to-mee-identity.md), [ADR-0007](0007-uwill.md). [ADR-0005](0005-why-willow.md) (why Willow) and [ADR-0006](0006-why-fork-of-willow.md) (why a fork of Willow) are obsolete stubs: both were taken by decisions that stayed unwritten, and their files went when the Willow-assuming material was cleaned up (commit e8a352a). Neither number is reused.

External references: iroh-docs 0.100 — a single ingest chokepoint, `validate_entry` in `src/sync.rs`, called from `insert_entry` and from the live-sync closure; a per-entry pre-persist accept/reject `validate_cb` in `ranger::process_message`, not exposed publicly; share tickets are non-expiring bearer tokens.
