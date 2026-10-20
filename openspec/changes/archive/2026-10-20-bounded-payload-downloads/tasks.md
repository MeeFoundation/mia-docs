## 1. Reproduce the silent provider

- [x] 1.1 Give the store's test node two blob handlers in `tests/util/mod.rs`: one that counts the requests it holds open at once and records the highest count, and one that accepts every request and answers none until the test releases it; verify with a test that each does what it says
- [x] 1.2 Write the scenario "A silent provider's payloads come from another provider" in `tests/sync.rs` and run it against the code before section 3: it fails, every payload first asked of the silent provider never arriving
- [x] 1.3 Record iroh-blobs-006 in `components/mee-pdn/iroh-defects.md`: iroh-blobs' downloader has no bound in time on a request a provider accepted, with 1.2 as the test that reproduces it

## 2. The limit

- [x] 2.1 In the data layer's `src/node.rs`, one constant for the bidirectional stream count, 100, set in `bind_endpoint` beside the unidirectional count; `just check` passes
- [x] 2.2 The store's builder in `src/protocol.rs` takes the limit of fetches in flight per provider, 100 by default, and the data layer hands it the constant of 2.1; `Engine::spawn` takes the pool's options and the limit in place of a `Downloader`; `just check` passes

## 3. Fetching (design D2 to D6)

- [x] 3.1 The engine fetches through a connection pool of `iroh_blobs::util::connection_pool` and `Store::remote().fetch`, in tasks spawned into `download_tasks`; `ProviderNodes` and the `Downloader` go; the existing tests of `tests/sync.rs` and `tests/dispatch.rs` pass
- [x] 3.2 A queue per provider, each pair of payload and provider queued once while the payload is wanted, a payload in flight toward one provider at a time and put back on every registered provider's queue when its fetch fails or is dropped; `queued_hashes` keeps every payload in flight or waiting; a leave removes its namespace from the payloads it wanted; `sync_full_basic`, `sync_fetches_parked_content_from_later_sync_peer` and `content_a_restart_left_missing_is_fetched_from_the_first_sync_peer` pass
- [x] 3.3 The fetch task reads the fetch's progress, and a fetch with no progress for 10 seconds is dropped; 1.2 passes
- [x] 3.4 The series of pauses per provider as a plain structure taking the time as an argument — 1 second, doubling up to 16 seconds, for at most 2 minutes, one probe per pause, a success ending it and giving back the whole limit, a series run out emptying the provider's queue; it replaces `unreached_downloads` and `retry_after_failure`; unit tests set the time and check each of these, and `a_download_from_a_neighbor_is_tried_again_until_the_replica_is_left` passes
- [x] 3.5 A fetch that fails on the node's own blob store parks its payload and starts no series; a unit test of the classification of the fetch's error
- [x] 3.6 The end of a session registers its peer for the namespace's queued and parked payloads with no blob store call in the live actor's loop; no `blobs().status` remains on the loop's path, and the parked-content tests of 3.2 pass

## 4. Scenario tests

- [x] 4.1 "A catch-up keeps the limit toward its provider": a replica joins a namespace of 20,000 entries from one provider with the builder's limit at 2, the provider's counting handler never records more than 2, and every payload arrives; with the queue bypassed the handler records more than 2
- [x] 4.2 "A provider registered during a catch-up takes waiting payloads": a second provider finishes a session during the catch-up, both handlers record requests, neither more than the limit, and every payload arrives; with registration during a wait removed, the second handler records none
- [x] 4.3 "The only provider, silent for a while, is asked again": the only provider answers nothing for 15 seconds and then serves, every payload arrives, and the replica records no `SyncFinished` between; with the provider left for the payload after its stall, the payloads do not arrive before a session
- [x] 4.4 "A provider silent for 2 minutes waits for a session": the unit tests of 3.4 run the series to its end and check that no fetch goes to the provider until a session's end registers it again
- [x] 4.5 "A failure on the node's own blob store pauses no provider": the unit test of 3.5, which fails with local failures counted against the provider
- [x] 4.6 `downloads_past_a_hundred_toward_a_silent_peer_all_end` drives the pool the engine uses, and still fails against iroh-util 0.6.0, checked by dropping the patch locally

## 5. Docs

- [x] 5.1 `openspec validate bounded-payload-downloads --strict` passes, and every `#### Scenario:` heading is checked by eye
- [x] 5.2 `crates/pdn-store/CLAUDE.md`: the entry on retries toward a gossip neighbor states the series per provider, and a new entry states the limit, the queue and the 10-second bound; `crates/data-layer/CLAUDE.md` states that the transport's bidirectional count is the store's limit
- [x] 5.3 iroh-blobs-006 in `iroh-defects.md` names its answer, the fetch the live actor owns, and the test of 1.2
- [x] 5.4 Sweep the other open changes for the names this change removes or moves — `ProviderNodes`, `retry_after_failure`, `unreached_downloads`, the blob store call in `queue_download` — and update their text

## 6. Measure and stress

- [x] 6.1 Measure the resident memory of a node joining a namespace of 100,000 entries before and after the change, and record both in `design.md`
- [ ] 6.2 Run the load test's ramp with catch-up on a laptop: every catch-up completes, and the write-to-read latency and the content lag are no worse than in the run of 19 and 20 October 2026; record the figures in `design.md`
- [x] 6.3 `just fix` passes: the dependency audit, `just check`, `just test` and the container suite
- [ ] 6.4 Stress the store's and the data layer's sync and download scenarios under nextest per [flaky-tests](../../specs/code-practices/flaky-tests.md), before anything is built on top
