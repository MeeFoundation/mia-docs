# Proposal: sync-throughput

## Why

A pod of 100 member nodes on one laptop falls behind its writers. In the load test's ramp (`mee-pdn/sync-test/load.md`), 99 writers place 20 records a second between them, 256 bytes each, and the reader `r` takes them in at 5 to 10 records a second: a step of 500 records written in 25 seconds takes 50 to 100 seconds to arrive, and the median delay from a write to the record readable on `r` passes 30 seconds at about 7,000 records, where the ramp stops. At 50 nodes the same ramp holds a median of 3 to 7 seconds up to 20,000 records.

A profile of the nodes during a 500-record step names two costs, each paid once per session, and every record costs many sessions across the pod.

- Every session's snapshot commits the store's pending write batch, as the `reconciliation-sessions` spec requires, and redb commits with a file sync. The store's actor thread spends about 90% of its busy time in that sync (`fcntl` with `F_FULLFSYNC` on macOS), and with 100 nodes on one disk every sync waits behind the others'.
- Every session on a pod's store classifies the party across it, dialing or accepting, and every classification builds the pod's membership view anew: it reads every entry of the membership store and its payload, and checks the signatures of the created event, every joined event and every device statement, 200 of them in a pod of 100 members. Once the sync is gone, that check is the largest CPU cost on every node.

Neither cost buys anything when nothing changed: a snapshot needs the batch readable, not on disk, and a membership store that took no write since the last view yields the same view.

**Example:** a short ramp (N = 100, to 1,000 records, 20 records a second), its step from 500 to 1,000 records, on the same laptop.

| build | median delay | 95th percentile | the step takes | `r` takes in | laptop busy |
|---|---|---|---|---|---|
| main at `1ccab04` | 13.7 s | 19.7 s | 80 s | about 6 records a second | 74% |
| a snapshot's commit unsynced | 9.6 s | 13.5 s | 41 s | about 12 records a second | 93% |
| and the membership view kept | 1.5 s | 2.2 s | 29 s | 20 records a second, the writers' rate | 61% |

Writing the host's log from a thread of its own leaves this step as it was, a median of 1.6 to 2.0 s over three runs, and lowers the median of the 100-record steps before it from about 1.6 s to 1.0 s; the laptop then works at about 80%.

The load test's default ramp, to 20,000 records, reaches its end at N = 100 with all four changes below: a median delay of 1.7 s at 1,000 records, 9.4 s at 10,000 and 19.4 s at 20,000, every record on `r`, and a fresh `r` catching up on the 20,000 in 2.1 s without losing an event. Before them the same ramp stopped at 7,000 records, its median 32 s behind.

## What Changes

- **A snapshot's commit skips the file sync.** The store commits the pending batch when a session opens its snapshot, so every entry inserted before session setup is in the snapshot, and that commit leaves the file unsynced. A synced commit follows within the 500-millisecond settle window the `durable-storage` spec states, counted from the oldest unsynced write, whether or not the store's actor goes idle, and a flush syncs at once. The window within which a write reaches the disk is unchanged.
- **The access book keeps each pod's membership view while its membership store takes no write.** The view is built again once the membership store's write count moves; a view that read a payload still awaited is not kept, since a payload's arrival moves no count. A replica's removal moves its count too.
- **The HTTP host writes its log from a thread of its own.** A runtime worker that logs, the store's live actor among them, queues the line and goes on, and one thread writes the queue to standard output; past 128,000 queued lines a line is dropped rather than waited for.
- **An ordered subscription converts up to 64 events ahead of its reader.** With the store's `observation` feature, the events of an ordered subscription are converted ahead of their reader and still yielded in order, so the load test's observation keeps up with a catch-up that no longer pauses on a file sync between snapshots.

None of them changes the wire, a verdict, or what a session serves.

## Impact

- `crates/pdn-store`: `Store::snapshot`, `Store::snapshot_owned`, `Store::flush` and the actor's timer commit; `Store::remove_replica` counts as a write; `SyncHandle::flush_store` is public for a test hook; with the `observation` feature, `Engine::observe` and `Engine::sync_with_peers_observed` convert through `observed_events`.
- `crates/data-layer`: `AccessBook::membership_view_and_entries` keeps views; two test-only calls, `sync_replica_store_for_test` and `membership_view_builds_for_test`.
- `crates/pdn-node`: the test-only `sync_replica_store_for_test`.
- `crates/pdn-node-http`: the log's subscriber, with `tracing-appender` as a new dependency.
- Specs: `components/mee-pdn/data-layer/durable-storage`.
