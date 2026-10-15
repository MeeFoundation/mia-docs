# Proposal: frozen-session-snapshots

## Why

A reconciliation session reads the live store, so the set it serves moves under it while it runs: a fingerprint computed in one round and the items behind it in a later one can describe different states. Subset reconciliation already freezes the other half of a session — the caller's rights are resolved at session setup and hold for its lifetime — so a session's read and write decisions rest on one rights state but a drifting data state. The archived subset-rbsr change carried this as task 2.3 and left it open.

Two further things make the gap worth closing now rather than tolerating it. The rights half of the freeze is enforced, tested, and relied on by two other requirements, yet stated nowhere as a requirement of its own. And capability-scoped-writes has since made one ingest-side read destructive: the check deciding whether to echo a rejection makes its recipient physically delete its own entry, so which state that check reads is no longer a matter of local tidiness.

## What Changes

- A sync session serves its egress from a store snapshot frozen at session setup: every fingerprint, split boundary, offer, and item derives from that one view, and a write landing mid-session travels on the next session. Opening the snapshot commits the store's pending write batch, and the snapshot is released on every exit path — completion, refusal, failure, and cancellation alike.
- Ingest keeps reading the live store, and the reason is stated: the last-writer-wins comparison, so an older remote entry never overwrites a newer local write the snapshot predates.
- The per-session rights freeze becomes a requirement in its own right, with the bound it places on a change of access stated explicitly: a removal takes effect from the next session, and what a device obtained before it stays with it.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `data-layer-subset-reconciliation`: a session serves a view frozen at session setup, and the caller's rights are resolved once at that same moment.
- `data-layer-capability-gated-ingest`: the rule that a rejection names only an entry the replica would newly store gains its second cause and an explicit live-state reading.
- `data-layer-write-retraction`: a rejection carries one device's knowledge, not the issuer's — stated with its window, its guards, and the options for closing it.

## Impact

- `pdn-store`: a session registry in the sync actor keyed by session id, a guard that releases the snapshot on every session exit path, a `session_snapshot` field on `StoreInstance` consumed by `get_first` and `get_range`, and session ids threaded through `sync_initial_message` / `sync_process_message` from `net/codec.rs`.
- `crates/*`: no source change — the fork's public surface the workspace consumes is unchanged, and sessions are opened inside the fork.
- Held read transactions pin store pages for a session's lifetime, so the guard's release on cancellation is load-bearing rather than tidy.
