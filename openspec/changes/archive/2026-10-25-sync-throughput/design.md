# Design: sync-throughput

## Context

The load test's ramp at N = 100 (`mee-pdn/sync-test/load.md`) is the measure. A `sample` of the reader and two writers, 8 seconds into the 500-record step, is the evidence for each decision, with the numbers in the proposal's table.

What the code does, checked for this design:

- `Store::snapshot_owned` in `crates/pdn-store/src/store/fs.rs` commits the open write transaction before it opens a read transaction, and every session start (`SyncSessionStart` in `actor.rs`) and every listing (`get_many`) goes through it. redb 4 commits with `Durability::Immediate` unless told otherwise, which syncs the file.
- The actor's timer commits the batch once no action arrives for `MAX_COMMIT_DELAY`, 500 ms; a transaction older than that is committed on the next write.
- `AccessBook::classify` in `crates/data-layer/src/access.rs` builds the membership view through `membership_view_and_entries` for every session on a pod's store, the dialing and the accepting side alike, and `pod_contacts` in `node.rs` builds it for every derivation of a pod's contacts. A build reads every membership entry with `get_many`, asks the blob store for each payload, and checks the signatures of the created event, every joined event and every device statement (`MembershipView::new`).
- `Store::writes_of` counts the writes applied to a replica in memory; `remove_replica` did not count.

## Goals / Non-Goals

**Goals:**

- `r` takes in records at the writers' rate at N = 100 on the laptop.
- A slow log sink stops no runtime worker of the HTTP host.
- Nothing a spec promises changes: what a session serves, what it admits, what reaches the disk and when.

**Non-Goals:**

- The duplicate entries concurrent sessions carry, and the membership store's session before every record store's session, which the `pod-store` spec requires; both are measured and left for a change of their own.

## Decisions

### D1. A snapshot's commit skips the file sync, and the settle window bounds it

A commit made to open a snapshot is unsynced (`Durability::None`). The store keeps `unsynced_since`, the start of the oldest transaction committed without a sync. A commit syncs when it is asked to (`flush`, the timer, a transaction past `MAX_COMMIT_DELAY`) or when `unsynced_since` is already `MAX_COMMIT_DELAY` old. The actor sleeps at most until that deadline and runs its timer commit there, idle or not, and a flush with nothing left to write syncs the unsynced commits with an empty synced one.

A session needs the batch readable, which an unsynced commit gives at once; the disk needs it within the settle window, which the deadline gives. Under a session load the store syncs about twice a second instead of once per session.

**Example:** r's store during the 500-record step.

| time | action | file synced |
|---|---|---|
| 0 ms | a remote insert opens a transaction | no |
| 40 ms | a session's snapshot commits it | no: unsynced since 0 ms |
| 90 ms | another insert, then another snapshot | no |
| 500 ms | the actor's deadline, whatever is queued | yes, both commits |

**Rejected alternatives:**

- A snapshot over the committed state alone, the batch left open
  - **Cons:** a session would not serve the entries inserted before its setup, which the `reconciliation-sessions` spec requires.
- Every commit unsynced, the timer alone syncing
  - **Cons:** an actor never idle for 500 ms would hold writes off the disk for as long as it stays busy.

### D2. The access book keeps each pod's membership view while the membership store takes no write

`AccessBook` keeps the last view it built per pod with the write count the store had before its entries were read, and serves that view while the count holds. A view that read a payload still awaited is not kept: a payload's arrival changes the view and moves no count. A replica's removal counts as a write, so a store dropped and imported again is never mistaken for the one read. The book keeps at most 256 pods' views and drops them together past that.

The count is read before the entries, so a write landing during a build leaves a view newer than its count, which the next look reads as a change and builds again.

**Example:** the reader `r` in the load test's pod of 100 members, whose membership store holds the created event, 99 joined events and 100 device statements.

| moment | the membership store | the view |
|---|---|---|
| the first session after the last join | its 200 entries, the count as it stands | built: 200 entries and their payloads read, 200 signatures checked |
| every later session of the ramp | no write, the count unchanged | the kept one: nothing read, nothing checked |
| a member's new device statement arrives | one write, the count one higher | built again |

**Rejected alternatives:**

- A cache invalidated by the membership store's events
  - **Cons:** a subscription can lose events, and a lost one would keep a stale view; the count moves on every mutation and on nothing else.
- Checking each statement's signature once and keeping the verdicts per entry
  - **Pros:** a write would cost one check instead of a whole build.
  - **Cons:** the view's passes reorder verdicts across entries, so a kept verdict is not a kept view; the build stays, only its first half would be saved.

### D3. The HTTP host writes its log from a thread of its own

`pdn-node-http` installs its subscriber with `tracing-appender`'s non-blocking writer over standard output: a runtime worker that logs queues the line and goes on, and a thread of the writer's own writes it. Past 128,000 queued lines a line is dropped rather than waited for. The filter is the one `tracing_subscriber::fmt::init` builds without its `env-filter` feature, `RUST_LOG` read as targets, `info` when unset.

The store's live actor is one task, and it logs a few lines at `info` for every session it runs. A write to standard output that waits on the disk stops that task, and every session's coordination with it, for as long as the write takes.

**Example:** writer w2's runtime during the 500-record step, after D1 and D2, sampled for 10 s.

| what the workers wait in | samples |
|---|---|
| `write` under `Stdout::write_all`, the log's lines | 4,443 |
| the standard output's lock, behind that write | 1,897 |
| the file sync of either store | 808 |

**Rejected alternatives:**

- The session lines at `debug`
  - **Cons:** the container suite and the flake hunts read them at `info`; a slow sink would still stop the actor on every line that remains.
- A writer of the host's own over a channel
  - **Cons:** the same mechanism as the tracing project's maintained crate, kept by us.

### D4. An ordered subscription converts up to 64 events ahead of its reader

With the store's `observation` feature, an ordered subscription hands its reader each event through a conversion that asks the blob store whether a remote insert's payload is held. `observed_events` in `src/engine.rs` runs up to 64 of these conversions at once, ahead of the reader, and yields the events in the channel's order. One at a time, each conversion waits on a blob store that a catch-up keeps busy importing the very payloads it downloads, and after D1 the live actor no longer pauses on a file sync between snapshots: the reader falls behind, the channel of 4,096 events drops what it has no room for, and the subscription carries `lagged`. A content status read ahead is read closer to the insert it describes, never further from it.

**Example:** the load test's fresh `r` catching up on 20,000 records, its stream of the record store.

| build | events | `lagged` |
|---|---|---|
| before D1, N = 50 | 40,134 | 0 |
| D1 to D3, N = 24 | 28,834 | 3 |
| D1 to D3, N = 100 | 25,505 | 4 |
| D1 to D4, N = 24 | 40,086 | 0 |
| D1 to D4, N = 100 | 40,239 | 0 |

**Rejected alternatives:**

- A larger channel
  - **Cons:** holds a longer burst, not a faster reader: a catch-up past the channel's size lags again, and the channel allocates every slot when it is created.
- A pause of the live actor when the channel fills
  - **Cons:** the observed node would sync slower than the one it measures, and an ordered subscription never holds up the live actor.

## Operating conditions

- **A device that restarts:** the count and the kept views are both in memory and start empty together. Unsynced commits lost to a kill are within the settle window the spec already allows for: a record store's entry cut by a kill is read as absent, and a membership store's write flushes before it returns.
- **A membership that moves:** every join, removal, promotion, demotion and departure is a write to the membership store and moves its count.
- **A disk that fills:** a synced commit that fails at the deadline is kept for the next write or flush, as the timer's was.
- The others do not change the outcome.

## Risks / Trade-offs

- **A view kept past a change.** Only a mutation that does not move the count could do it; the count moves where the write is applied (`Store::wrote`), and a removal now moves it too. `a_membership_view_is_built_again_only_after_a_write` in `crates/data-layer/tests/pod_stores.rs` fails with the count left out of the key.
- **Durability under a busy actor.** `a_busy_actor_takes_a_snapshots_commit_to_disk` in `crates/pdn-store/src/actor.rs` fails with the deadline taken out of the actor's loop.
