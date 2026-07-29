# Design: frozen-session-snapshots

## Context

Subset reconciliation freezes a session's rights at setup: the egress filter is built once from the caller's resolved claims and cannot re-read them. The data the session serves was never frozen with them, so the two halves of a session's decisions read different states. The archived subset-rbsr change specified the fix as task 2.3 and recorded two redb properties to verify — long-lived read transactions pin pages, and taking a snapshot commits an open write transaction.

The work was implemented against the tree of 22-Jul-2026 and held back unmerged. `capability-scoped-writes` landed in between and touches the same files, so the change is finished here against the tree that includes it.

## Goals / Non-Goals

**Goals:**

- One session serves one view, taken at session setup, on both store backends.
- Ingest keeps reading live state, and the reasons are written down where the next reader will look.
- The rights half of the freeze becomes a stated requirement, since two other requirements already lean on it.
- The seam between the frozen view and capability-scoped-writes' rejection echo is pinned by a test, not left to hold by accident.

**Non-Goals:**

- Materialized per-audience views (subset-rbsr task 2.4) — its triggers never fired, and a snapshot costs no copying.
- Closing the multi-device rejection window recorded below. It is stated, guarded, and left open.
- Any change to what a session is allowed to serve. This changes *when* the served set is read, never *what* it contains.

## Decisions

**D1 — The snapshot is owned by the sync actor and named by a session id.** The actor holds a registry of frozen snapshots; `sync_session_start` opens one and returns a guard whose drop releases it. Session ids travel with `sync_initial_message` and `sync_process_message`, so the actor resolves the snapshot per call rather than storing per-replica state that a second concurrent session would race for. Several sessions over one replica therefore hold several snapshots, each at its own moment, which is what per-session freezing means.

**D2 — Resolution is fail-closed.** A session id naming no registered snapshot, or one registered for another namespace, is an error rather than a silent fall back to live reads. A session whose snapshot has gone — the replica was closed under it — fails instead of quietly serving a drifting view, which would be the bug this change exists to prevent, arriving unannounced.

**D3 — Release covers cancellation, not just completion.** The guard releases the snapshot when it is dropped, so an aborted future releases it as it unwinds; the actor also sweeps a replica's snapshots when the replica closes, covering a release message lost to a full queue. Read transactions pin pages, so a leaked snapshot is a leaked page set for as long as the node runs.

**D4 — Egress reads the snapshot; ingest reads live.** `get_first` and `get_range` read the snapshot when one is set, and the fingerprints computed from them follow, because the store derives fingerprints by iterating ranges. `prefixes_of`, `entry_put`, and `remove_prefix_filtered` always read live. Two things ride on the live half. The last-writer-wins comparison: judged against a stale snapshot, an older remote entry would overwrite a newer local write the snapshot predates, and the store would move backwards in time. And `would_insert`, which capability-scoped-writes made the gate on the rejection echoed to a sender — judged against the snapshot it would name an entry the replica took in after session setup, and the sender deletes its own copy on that word.

**D5 — What the freeze buys is stated with its limit.** A drifting store does not break reconciliation: it is anti-entropy, and what one session misses the next one carries — the unfiltered engine ran on live reads throughout. The freeze buys agreement among the things one session derives, and it puts the data half of a session's decisions on the footing the rights half already stands on. Claiming more than that in the spec would be false, and the requirement says so in as many words.

**D6 — The rights freeze is written down rather than assumed.** It is implemented (the filter closure owns a captured claim set), tested (`withdrawn_grant_refuses_the_next_session_but_keeps_delivered_data`), and referenced by the write-set requirement of capability-gated ingest and by this change's own snapshot requirement — but stated by neither. It becomes a requirement, with the bound it places on revocation as its point rather than an aside: a withdrawal takes effect from the next session.

## Risks / Trade-offs

- [A held snapshot pins store pages for a session's lifetime] → the guard releases on every exit path including cancellation, and closing a replica sweeps its snapshots; sessions are bounded by their exchange, so the pinned set is bounded by concurrent sessions rather than by uptime.
- [Egress and ingest deliberately disagree about the store] → the disagreement is the design, and it is recorded on the field itself, so the next reader assigning a new check to one side or the other has the rule in front of them rather than having to infer it.
- [A rejection judged against the frozen view would destroy the sender's data] → the gate reads live by construction, and a test pins it: an entry landing after session setup draws no rejection. Verified by mutation — removing the snapshot from the test collapses its premise.
- [A device of a multi-device issuer speaks for the issuer it cannot see] → recorded as a requirement of write retraction, with its guards; not closed, see below.

## Open Questions

- **The multi-device rejection window is open.** A rejection states that the refusing device lacks the entry; capability-scoped-writes reads that as the issuer lacking it. A device that admitted an entry can go offline before it replicates, and a sibling reached afterwards, judging by a grant narrowed meanwhile, signals honestly — so the writer retracts a write the issuer holds and keeps, and is told it was refused. Three ways out are stated in the requirement and none is chosen: leave the window and lean on the recorded content hash as a recovery address; signal only from a device that knows itself caught up, which returns sibling availability to the path; or make retraction reversible, which turns prevention into repair. Choosing wants a measurement this change does not carry — how often an admitting device goes offline before it replicates. Closing it belongs to its own change.
