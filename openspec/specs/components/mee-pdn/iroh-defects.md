# Where iroh fails the platform

What the iroh crates the workspace builds on — iroh, iroh-gossip, iroh-blobs and iroh-docs, from which pdn-store descends — do wrong in ways a node of the platform meets, what the platform does instead, and which test holds the platform's answer. A defect is listed here once a node of ours has met it, whether or not upstream knows of it.

## The stance

The platform does not wait on upstream. A defect iroh carries is answered in the workspace, at the narrowest point that closes it: a selector of our own behind a hook iroh offers, a fixed upstream revision patched in, a fork of our own, a configuration iroh's own code should have set. Upstream releases rarely, and fixes sent to it sit unread: the two pull requests pdn-store sent to iroh-docs in July 2026, #111 and #112 — one a pair of nodes that stopped syncing for good, the other content that never arrived — are open three months later with no review. A fix is still offered upstream, as a pull request or an issue, so that the record shows upstream was told; nothing in the workspace waits for its answer.

The only guarantee anything in iroh carries is the workspace's own tests. A hook iroh marks unstable, a revision of its main branch and a release it calls stable are trusted alike: as far as a test of ours drives them, and no further. Every answer listed below names the test that fails without it, and a bump of any iroh crate runs those tests first.

**Example:** what each kind of answer below rests on.

| answer | where it lives | what holds it |
|---|---|---|
| a selector of our own | `crates/data-layer/src/path_selector.rs` | its unit tests and the stand's kill scenario |
| a patched revision | `[patch.crates-io]` in the workspace `Cargo.toml` | the stand's kill scenario |
| a fork of our own | `MeeFoundation/iroh-blobs`, patched in | `a_blob_store_that_cannot_open_fails_the_spawn` in the data layer's `tests/persistence.rs` |
| our own configuration | the stand's HTTP client | every stand test |

## iroh 1.3: a peer that restarted at a new address is dialed at its old one

iroh's default path selector, `BiasedRttPathSelector`, keeps a selected path until a path of the same tier is at least 5 ms faster by its last measured round-trip time. A peer killed and started again listens on a new port; the old path is dead, but it keeps the round-trip time it last measured, and the connection that carried it lives on until its idle timeout. On a local network no path is 5 ms faster than a dead one measured at under 2 ms, so every connection the node opens to the restarted peer sends its handshake to the dead port, and the node's sync dials and payload downloads time out while the connections the peer opens toward it work. iroh selects again only once the last connection to the peer closes, and the node's own failed dials keep one open on the dead path.

The platform installs a selector of its own through iroh's `path_selector` hook, which iroh keeps behind its `unstable-custom-transports` feature: a path some connection to the peer has received on comes before one none has, then iroh's tiers, then, within a tier, the path more of the node's connections to the peer have received on, whatever their round-trip times; between paths alike in these the choice is iroh's own. The [node assembly](data-layer/node-assembly/spec.md) spec states it as "A peer that restarts at a new address is reached at it"; the unit tests in `path_selector.rs` and `a_killed_node_is_the_same_node_and_a_fresh_one_holds_nothing` in the host's `tests/stand_restart.rs` hold it. Upstream has no fix.

**Example:** Bob's node b1, after Alice's node a1 was killed and started on port 33947 instead of 57771.

| path | connections that received on it | last round-trip time | iroh's selector | the platform's |
|---|---|---|---|---|
| `172.18.0.2:57771` | 1, from before the kill | 1.9 ms | kept | left |
| `172.18.0.2:33947` | 3, opened by a1 after its start | 0.4 ms | not 5 ms faster | selected |

## iroh-gossip 0.101.0: a peer that restarted with the same node id gets no neighbor

When two nodes first meet in a swarm, the node that answered the other's `Neighbor` with a `Neighbor` of its own keeps that answer pending, and the other never replies to it. A peer killed and started again with the same node id joins the swarm anew; the node still counts it as a neighbor and sends a `Neighbor` back only when none to that peer is pending, so it sends nothing. The restarted peer is left with no neighbor and announces its writes to nobody, and the node never learns the peer's old connection is gone, because a newer connection to the peer exists when the old one times out. A write placed on the restarted node reaches the other member only at the pod's next pass, up to 300 s later.

Upstream fixed it on its main branch, pull request #161 ("answer a join from a peer that is already a neighbor"), on 2026-10-09, with #178 and #191 on the connection and swarm lifecycle after it, and released none of them. The workspace takes iroh-gossip from that branch at a fixed revision through `[patch.crates-io]` until a release carries the fix. The [node assembly](data-layer/node-assembly/spec.md) spec states it as "A peer that restarts with the same node id is a neighbor again at once"; the same stand scenario holds it.

## iroh-blobs 0.103: a file store that fails to open hangs its process

`FsStore::load` spawns a tokio runtime of its own, and when opening the store fails, the runtime is dropped from one of its own threads, which blocks for good: the error never reaches the caller and the process hangs. A teardown of the store can deadlock the same way. Upstream holds three issues on it, #249, #252 and #260, all open. The workspace takes iroh-blobs from a fork of its own, `MeeFoundation/iroh-blobs`, upstream's release with the fix, through `[patch.crates-io]`; the fork's `UPSTREAM.md` records what it carries and when it goes. `a_blob_store_that_cannot_open_fails_the_spawn` in the data layer's `tests/persistence.rs` holds it: against upstream's 0.103.1 the spawn of a node whose blob database cannot open hangs, and against the fork it fails with an error.

## iroh-blobs 0.103: the file store builds only by luck

iroh-blobs' `fs-store` feature calls tokio's `block_in_place` without enabling `rt-multi-thread`, the tokio feature it sits behind, so a crate that enables `fs-store` alone does not compile. pdn-store enables `rt-multi-thread` on its own tokio dependency, beside a comment that says why.

## iroh-blobs 0.103: a request reaching a file store that is shutting down panics

A request that reaches iroh-blobs' file store while it shuts down meets a file whose state the shutdown poisoned, and the store's task panics ("poisoned storage should not be used" in its `bao_file.rs`). A running docs engine starts downloads, each of which reads the blob store first, so closing the blob store before the engines stop meets it whenever downloads are under way: pdn-store's own restart test, `content_a_restart_left_missing_is_fetched_from_the_first_sync_peer`, met it in every run until its node stopped the engine first, and now counts the panics of its process and fails on one. For the node itself, `a_node_stopped_with_a_fetch_under_way_stops_without_a_panic` in the data layer's `tests/node_shutdown.rs` reads the order of the node's stop and fails when the engines stop after the blob store closes, since a download lands between the two only some of the time. A peer's request meets it too: iroh's router shuts its protocols down before it cancels their connections, so the blob protocol's shutdown closes the store while a connection's handler can still hold a request it read; `a_node_stopped_while_a_peer_observes_its_payload_stops_without_a_panic` in the same file met it in nearly every stop. The handler iroh-blobs ships runs each stream in a task of its own, which the router neither cancels nor awaits, so a request a stream read before the stop still reaches the store after the router's shutdown returned: with the store closed after the router alone, the same test met the panic in 6 of 300 runs on a runner of 4 CPUs. The node stops every engine before the router, mounts the blob protocol with a handler of its own, which runs each stream in a task the node tracks, and with a shutdown that leaves the store open, and closes the store itself once the router's shutdown has returned, the streams' tasks have ended and the store has finished what they handed it, waiting up to 5 seconds for those; a node dropped without its shutdown stops the same way, in a task of its own. The [node assembly](data-layer/node-assembly/spec.md) spec states the order under "Shutdown stops every protocol side by side, and a late call fails". The two tests that pin it in the data layer's `tests/node_shutdown.rs`, `a_node_stopped_while_a_peer_observes_its_payload_stops_without_a_panic` and `a_node_dropped_while_a_peer_observes_its_payload_stops_without_a_panic`, hold one stream between the request it read and the store until the router's shutdown has returned, and meet the panic in every run without the wait. Upstream's store goes on taking requests after its database closed and poisons what they touch, issue #233 and pull request #214 on it both open; the fork records that as a defect of its own.

## iroh-blobs 0.103: a store's garbage collection outlives the store

The blob stores spawn their garbage collection as a task with a store handle of its own, and that task leaves its loop only when a run fails; a run the protect callback aborts is skipped. The file store's main actor ends only once every store handle is gone, so as long as the task lives it holds that actor and the store's private runtime, one worker thread per core. A node whose callback aborted every run after its stop left one such runtime behind per stop, for the rest of the process. No upstream issue names it; #291 asks the loop to survive a failed run, and #235 a public way to run a collection, which would let a caller run the loop itself.

The platform ends the task from the callback, through the public interface alone. iroh-blobs asks the callback every minute at most (`BLOB_COLLECTION_TICK` in the data layer's `src/node.rs`), and the callback lets a run go ahead only once the node's collection interval has passed. Once the node's stop has closed the blob store, and only then, the callback answers so that the next run goes ahead: iroh-blobs drops the store's metadata database before its shutdown answers, and a run's first call, like every call that could remove anything, goes to that database, so the run fails before it sweeps and the task ends. The callback asks the store to sync first and lets the run go ahead only if that call fails too, so a store that still answers after its shutdown is left to a skipped run rather than swept against an empty protected set. A node dropped outside a tokio runtime runs no stop; the callback then finds the node's identities gone and shuts the store down itself. A stopped node's store runtime therefore lives for at most a minute after the stop. `a_stopped_node_leaves_no_blob_collection_running`, `a_dropped_node_leaves_no_blob_collection_running` and `a_node_dropped_outside_a_runtime_leaves_no_blob_collection_running` in the data layer's `tests/node_shutdown.rs` hold it. They fail at an iroh-blobs bump where a run on a closed store no longer fails, or where a failed run no longer ends the task, which is what #291 asks for; either leaves the leak back, never a sweep, and the answer then is to end the task another way.

**Example:** Alice's laptop a1, whose host stops its runtime and starts a new one in the same process.

| moment | the old store's collection task |
|---|---|
| `shutdown` closes the old blob store | asleep until its next ask |
| the next ask, at most a minute later | the callback finds the store refusing a sync and lets the run go ahead; the run fails on its first call |
| after | the task has ended, the store's last handle goes with the node, and its runtime stops |

## iroh-blobs 0.103: the memory store's collection removes a payload imported while it runs

A collection run marks the payloads every tag and temp tag names, then sweeps every other payload the store holds. A payload imported between the two carries a temp tag the mark did not see; the file store remembers every payload written since the run began and sweeps none of them, while the memory store keeps no such record, so its sweep removes the payload, a local write's own included: the entry stays and its payload is gone. Upstream's main branch carries the same memory store. The platform collects only over the file store a node on a storage directory runs: a node in memory exists only in a test build, behind the data layer's `test-util` feature, and its blob store is never collected. On nodes in memory collecting every 200 milliseconds, `a_payload_fetched_while_a_run_is_under_way_stays` in the data layer's `tests/blob_collection.rs` lost the writer's payload that way in about one run in a hundred on a runner of 4 CPUs; the scenarios of that file run on storage directories.

**Example:** a memory store collected every 200 milliseconds while Alice places a claim.

| step | the store |
|---|---|
| the run marks every tag and temp tag | the claim's payload not imported yet |
| the claim's payload is imported, its temp tag taken, its entry written | entry and payload held |
| the run sweeps | the payload removed: no mark names it, and the memory store does not remember it was just written |

## iroh 1.3: an HTTP client in the same build panics on its first request

iroh enables reqwest's `rustls-no-provider` feature, and cargo unifies it into every reqwest client of the build: under it a client takes only a TLS provider installed process-wide, so the stand's own HTTP client panicked on its first request, plain HTTP included. iroh's maintainers keep the feature and decline to change it (iroh issue #4442). The stand's client passes a TLS configuration of its own, the one iroh's relay tests build, in `plain_http_tls` in the host's `tests/common/mod.rs`.

## iroh-docs: everything pdn-store diverges in

pdn-store is the platform's own variant of iroh-docs ([ADR-0016](../../architecture/adr/0016-pdn-store-is-the-platforms-own.md)); the rules it follows where iroh-docs does otherwise are listed with their reasons in `crates/pdn-store/CLAUDE.md`, and the verdict on each upstream commit and fix pull request read since the fork is in `crates/pdn-store/UPSTREAM.md`.
