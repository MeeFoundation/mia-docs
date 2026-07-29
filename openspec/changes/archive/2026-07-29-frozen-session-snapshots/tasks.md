# Tasks: frozen-session-snapshots

> Finishes task 2.3 of the archived subset-rbsr change against a tree that now
> includes capability-scoped-writes. Task 2.4 of subset-rbsr (materialized
> per-audience views) stays open there: its triggers never fired.

## 1. Session snapshots in the fork (D1-D4)

- [x] 1.1 Session registry in the sync actor: `sync_session_start` opens a snapshot for an open, sync-enabled replica and returns a `SyncSession` guard; ids resolve per call, so concurrent sessions over one replica each hold their own view
- [x] 1.2 Resolution is fail-closed (D2): an unregistered id, or one registered for another namespace, is an error rather than a silent fall back to live reads; a stale id after the replica closed fails too
- [x] 1.3 Release on every exit path (D3): the guard's drop releases the snapshot on completion, refusal, failure, and cancellation; closing a replica sweeps its snapshots, covering a release message lost to a full actor queue
- [x] 1.4 `StoreInstance::session_snapshot` consumed by `get_first` and `get_range`, and by the fingerprints the store derives from them; `prefixes_of`, `entry_put`, and `remove_prefix_filtered` stay live (D4), with the two consumers of that rule recorded on the field
- [x] 1.5 Session ids threaded from `net/codec.rs` through both roles: the dialing side opens before its initial message, the accepting side opens after the request is allowed, so a rejected request never opens one

## 2. Verification in the fork

- [x] 2.1 A mid-session write is not served and travels on the next session — both backends
- [x] 2.2 Opening a session commits the pending write batch, so an entry inserted just before setup is in the snapshot; the store stays writable and the new batch is invisible to the held snapshot — both backends (the second redb item subset-rbsr left to verify)
- [x] 2.3 A held snapshot's fingerprint does not drift under live writes, while the live view and a younger snapshot see them — snapshots and the live store read side by side (the first redb item: lifetimes stay within session bounds)
- [x] 2.4 Ingest reads live under a snapshot: an older remote entry loses against a newer local write the snapshot predates
- [x] 2.5 Session lifecycle and sweep: a session needs an open, sync-enabled replica; an id is bound to its namespace; closing the replica reclaims its sessions; a stale id fails rather than reading live; the guard's late release of a swept session is a no-op
- [x] 2.6 Snapshots are released on success, on refusal, and on a cancelled run — asserted through the actor's registered-session count

## 3. The seam with capability-scoped-writes (D4)

- [x] 3.1 `SyncHandle::spawn` gained a rejection-observer parameter while this work was held back; the session test helpers follow it
- [x] 3.2 The rejection gate reads live state, pinned beside the existing filter-narrowing case: an entry landing after session setup draws no rejection, so the sender never retracts a write the replica holds. Verified by mutation — removing the snapshot collapses the test's own premise, which is what makes the assertion bite
- [x] 3.3 Fork pre-push checklist green: fmt, clippy across all three feature sets, `cargo +nightly docs-rs`, `cargo deny`, tests plus doctests, and the wasm build

## 4. Specs

- [x] 4.1 `data-layer-subset-reconciliation`: a session serves a view frozen at session setup — with what the freeze buys and what it does not (D5)
- [x] 4.2 `data-layer-subset-reconciliation`: the caller's rights are resolved once, at session setup, with the bound it places on revocation (D6) — backfilling a rule two other requirements already leaned on
- [x] 4.3 `data-layer-capability-gated-ingest`: the second cause that brings an already-held entry back to the gate, and the live-state reading behind a rejection
- [x] 4.4 `data-layer-write-retraction`: a rejection carries one device's knowledge, not the issuer's — the window, its guards, and the unchosen options (design Open Questions)
- [x] 4.5 Sweep of the active `reconcile-trigger` change: its coalescing requirement assumed a session serves live state, so a write landing in a running session would clear a trigger it never travelled on
- [x] 4.6 Archived subset-rbsr task 2.3 marked done

## 5. Stress (flaky-tests.md)

- [x] 5.1 Wide sweep first: the whole workspace suite once against the patched fork, 88 of 88 green
- [x] 5.2 Deep loop on the fork's own session and scoped-write tests, 300 iterations, all green
- [x] 5.3 Deep loop on the workspace scenario suite, 100 iterations of 56 tests, all green — this also settles the truncated 5-iteration pass subset-rbsr's 2.3 work left owed. The per-test bound is about 3 percent at 95 percent confidence, which does not sit below the 1.2-to-2.5 percent rates the flaky-tests precedents measured; a series sized to rule 2 wants roughly 1,000 iterations and stays owed

The multi-device rejection window is recorded, not closed — it belongs to its own change.
