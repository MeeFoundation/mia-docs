# Proposal: frozen-session-snapshots

## Why

A reconciliation session reads the live store, so the set it serves moves under it while it runs: a fingerprint computed in one round and the items behind it in a later one can describe different states. Subset reconciliation already freezes the other half of a session — the caller's rights are resolved at session setup and hold for its lifetime — so a session's read and write decisions rest on one rights state but a drifting data state. The archived subset-rbsr change carried this as task 2.3 and left it open.

Two further things make the gap worth closing now rather than tolerating it. The rights half of the freeze is enforced, tested, and relied on by two other requirements, yet stated nowhere as a requirement of its own. And capability-scoped-writes has since made one ingest-side read destructive: the check deciding whether to echo a rejection makes its recipient physically delete its own entry, so which state that check reads is no longer a matter of local tidiness.

## What Changes

- A sync session serves its egress from a store snapshot frozen at session setup: every fingerprint, split boundary, offer, and item derives from that one view, and a write landing mid-session travels on the next session. Opening the snapshot commits the store's pending write batch, and the snapshot is released on every exit path — completion, refusal, failure, and cancellation alike.
- Ingest keeps reading the live store, and the reason is stated: the last-writer-wins comparison, so an older remote entry never overwrites a newer local write the snapshot predates, and the rejection gate, so a refusal never names an entry the replica took in after session setup.
- The read side's per-session rights freeze becomes a requirement in its own right, with the bound it places on revocation stated explicitly: a withdrawal takes effect from the next session, and what a peer obtained while granted stays with it.
- Capability-gated ingest gains the second cause that brings an already-held entry back to its gate. Narrowing a grant hides such an entry behind the egress filter; a session snapshot hides it when the entry lands after session setup. Both make the sender re-offer what the receiver keeps, and the gate reads live state in both.
- Write retraction records a window the archived capability-scoped-writes change left implicit: a rejection states that the *refusing device* lacks the entry, which on a multi-device issuer is narrower than the issuer lacking it.

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
- One window is recorded, not closed: a device of a multi-device issuer can reject an entry a sibling holds, and the writer retracts a write the issuer kept.
