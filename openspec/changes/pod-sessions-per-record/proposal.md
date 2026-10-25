# Proposal: pod-sessions-per-record

## Why

A pod of 100 member nodes on one laptop keeps up with 99 writers placing 20 records a second: the reader `r` sees a record a median 1.5 seconds after its write. Almost all of that is the entry reaching `r` (1.4 s); its payload follows within 50 ms. What the entry waits for is the chain of sessions the write announcement starts, hop by hop through the swarm, and two features of that chain are measured below.

- **Every record store's dial waits behind a membership store's session that carries nothing.** The `pod-store` spec requires a session between two member devices to reconcile the membership store first, so a newcomer the session brings is served and a departure it brings is refused. During a ramp no one joins or leaves, so the membership session finds the two stores equal, after a full setup on both sides: a stream, the caller's classification and a snapshot.
- **Every entry arrives about four times.** Each node pulls from every neighbor that announces news, and concurrent pulls from different neighbors carry the same entries; each copy is received, its signature checked and then dropped as held.

**Example:** the ramp to 1,000 records at N = 100 (`mee-pdn/sync-test/load.md`, the quick profile), every node's sessions counted from the first record on, each session reported by both of its sides.

| store | session reports | carrying an entry | entries received | duration p50 | duration p95 |
|---|---|---|---|---|---|
| membership | 90,539 | 0 | 0 | 108 ms | 749 ms |
| records | 59,076 | 48,136 | 387,504 for the 99,000 the pod needs | 245 ms | 925 ms |

## What Changes

Nothing is decided. The change settles whether and how each of the two costs goes, and then specifies and builds the answer.

## Open Questions

### When may a record store's session skip the membership store's

- **The records announcement carries the membership store's fingerprint.** The reconciliation's fingerprint of the whole membership store rides the record store's sync report; a receiver whose own fingerprint is equal dials the record store alone, and any difference runs the membership session first as now. A node that lies about its fingerprint gains nothing a node withholding the membership session does not have already. It changes the gossip message (the `reconciliation-sessions` spec's example encoding) and tells a topic subscriber when the membership changes, which the membership store's own topic tells already.
- **The record store's session opening carries the dialer's membership fingerprint.** The acceptor answers whether it matches its own before it classifies; on a mismatch the dialer runs the membership session and dials again. The gossip message stays as it is; the session's opening changes, and a mismatch costs one round more than today.
- **The order stays, and the empty membership session gets cheaper.** Where its 108 ms go is unmeasured: setup, classification and the snapshot each queue behind the store's actor.

### How many pulls of one write a node runs at once

- **One pull per namespace in flight**, later announcements waiting for it and merged into one resync after it. Fewer copies; a pull from a slow neighbor delays the rest.
- **A pull skips a neighbor whose announced heads a pull in flight already covers.** The announcement carries the author heads that make the comparison.
- **Leave it**: a duplicate costs one signature check and is dropped, and `r`'s whole CPU per record is 6 ms at N = 100.
