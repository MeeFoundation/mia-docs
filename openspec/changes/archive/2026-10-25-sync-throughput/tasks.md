# Tasks: sync-throughput

Scope: the two costs the N = 100 profile names, each removed without a change to what a session serves, admits or keeps on disk. Every test states in its doc which mechanism, removed, makes it fail, and was run once with it removed.

## 1. A snapshot's commit skips the file sync (design, D1)

- [x] 1.1 `TransactionAndTables::commit` takes whether to sync; `Store::snapshot` and `Store::snapshot_owned` commit unsynced, `Store::flush`, the timer and a transaction past `MAX_COMMIT_DELAY` synced; `Store::unsynced_since` and `Store::sync_due_in`; a flush with nothing to write syncs the unsynced commits with an empty synced one
- [x] 1.2 The actor sleeps at most until the deadline and runs its timer commit there, idle or not (`Actor::commit_on_timer`)
- [x] 1.3 Tests: `a_snapshot_commits_without_a_sync_and_a_flush_syncs`, `a_snapshot_past_the_settle_window_syncs` in `src/store/fs.rs`; `a_busy_actor_takes_a_snapshots_commit_to_disk` in `src/actor.rs`, which fails with the deadline taken out of the actor's loop
- [x] 1.4 `SyncNode::sync_replica_store_for_test` and `Runtime::sync_replica_store_for_test` sync the replica store alone; `a_membership_write_is_on_disk_whole_when_it_returns` in `crates/data-layer/tests/persistence.rs` and `a_pod_whose_record_is_on_disk_opens_from_it` in `crates/pdn-node/tests/restart_recovery.rs` stage their order with it, since a read's commit is unsynced; each fails with the flush it guards removed
- [x] 1.5 `crates/pdn-store/CLAUDE.md` names the unsynced commit

## 2. A book keeps each pod's membership view (design, D2)

- [x] 2.1 `AccessBook` keeps the last view per pod with the count read before its entries, serves it while the count holds, keeps none that awaited a payload, at most 256 pods
- [x] 2.2 `Store::remove_replica` counts as a write; `a_removal_counts_as_a_write` in `src/store/fs.rs`
- [x] 2.3 `a_membership_view_is_built_again_only_after_a_write` in `crates/data-layer/tests/pod_stores.rs`, which fails with the count left out of the key

## 3. The HTTP host's log from a thread of its own (design, D3)

- [x] 3.1 `install_log` in `crates/pdn-node-http/src/main.rs`: `tracing-appender`'s non-blocking writer over standard output, the guard held to the end of `main`, `RUST_LOG` read as targets
- [x] 3.2 `just audit` with the new dependency
- [x] 3.3 `a_host_whose_log_nobody_reads_keeps_answering` in `crates/pdn-node-http/tests/log_writer.rs`: the binary with a full pipe, never read, as its standard output; fails with the subscriber writing from the thread that logs; named in `crates/pdn-node-http/CLAUDE.md`

## 4. Verification

- [x] 4.1 `just check` and `just test`
- [x] 4.2 `just test-docker`
- [x] 4.3 The stress pass over the scenario tests after D1 and D2: 20 iterations of `just stress`, no failure
- [x] 4.4 The stress pass at the size `flaky-tests.md` asks for: 100 iterations of `just stress` over the scenario suite with D1 to D3, no failure, and 100 of the `pod_tombstone` binary. Before them `a_join_after_a_leave_catches_up_on_the_records_placed_meanwhile` in `crates/data-layer/tests/pod_tombstone.rs` failed about once in 90 iterations, and not by D2: as the join answered, the claim's entry was held and its payload was still on its way, which a catch-up allows — it answers once a session went through, not once payloads landed. The test now asserts the entry at the answer and the record once its payload lands, and still fails with the record store started before the membership view shows the join
- [x] 4.5 A short ramp at N = 100, to 1,000 records, before and after each decision (the proposal's table), D3 as an A/B of three runs each

## 5. An ordered subscription converts up to 64 events ahead of its reader (design, D4)

- [x] 5.1 `observed_events` in `crates/pdn-store/src/engine.rs`: with the `observation` feature, up to `OBSERVED_CONVERSIONS` conversions in flight, yielded in order, behind `Engine::observe` and `Engine::sync_with_peers_observed`; `Engine::subscribe` keeps its one-at-a-time conversion
- [x] 5.2 `a_ten_thousand_entry_session_drained_at_conversion_pace_loses_nothing` in `crates/pdn-store/tests/observe.rs` guards it: with the conversions one at a time it lagged in 2 of 145 iterations of a 4-CPU runner over the workspace, and the peak fill of its channel under the store's own tests at 16 threads fell from 1,508 to 44
- [x] 5.3 The load test's catch-up at N = 24 on the laptop: the fresh `r`'s stream of 40,086 events carries no `lagged`, where D1 to D3 alone carried 3; the ramp's delays stay as they were. At N = 100, the default ramp to 20,000 records: the fresh `r`'s 40,239 events carry no `lagged`, where D1 to D3 alone carried 4, and it catches up in 2.1 s
