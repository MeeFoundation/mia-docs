# Where iroh fails the platform

What the iroh crates the workspace builds on — iroh, iroh-gossip, iroh-blobs, iroh-util and iroh-docs, from which pdn-store descends — do wrong in ways a node of the platform meets, what the platform does instead, and which test holds the platform's answer. A defect is listed here once a node of ours has met it or a test of ours has reproduced it, whether or not upstream knows of it.

## Names

Every defect listed here carries a name: the crate it lies in and a number of three digits, counted per crate in the order the defects were listed. The name stays with its defect after upstream fixes it or the platform's answer goes, and no other defect ever takes it. Code comments, `Cargo.toml`, pdn-store's `UPSTREAM.md` and the other documents point to a defect by its name, the way they point to an ADR by its number, and leave the description to the defect's section here.

**Example:** every defect listed, by name.

| name | the defect | upstream | the platform's answer |
|---|---|---|---|
| iroh-001 | a peer that restarted at a new address is dialed at its old one | no fix; a pull request of ours is prepared and not yet sent | a path selector of our own |
| iroh-002 | an HTTP client in the same build panics on its first request | declined, issue #4442 | the stand's client configures TLS itself |
| iroh-blobs-001 | a file store that fails to open hangs its process | fixed on main by #293, unreleased; issue #249 open | upstream's main at a fixed revision |
| iroh-blobs-002 | the file store builds only by luck | fixed on main by #272, unreleased | upstream's main at a fixed revision |
| iroh-blobs-003 | a request reaching a file store that is shutting down panics | issue #233 and pull request #214, open | the node's stop order and a blob protocol handler of its own |
| iroh-blobs-004 | a store's garbage collection outlives the store | no issue names it | the protect callback ends the collection's task |
| iroh-blobs-005 | the memory store's collection removes a payload imported while it runs | unfixed on main | no collection runs over a memory store |
| iroh-blobs-006 | a download from a provider that accepts the request and sends nothing never ends | no issue names it | pdn-store fetches in a task of its own, dropped after 10 s with no progress |
| iroh-blobs-007 | a request whose stream fails to open reports a failure of the local store | no issue names it | pdn-store opens the stream itself |
| iroh-blobs-008 | a payload the store failed to write is reported fetched | no issue names it | pdn-store asks the store once the request reports done |
| iroh-blobs-009 | a provider that lacks a payload answers as one that fails | on main since #298, unreleased; no issue names it | upstream's main at the commit before it |
| iroh-docs-001 | a dial the remote aborts as already syncing leaves the pair stuck | pull request #111 of ours, open | pdn-store's own fix |
| iroh-docs-002 | a payload the session's sender lacked waits on one gossip message | pull request #112 of ours, open | pdn-store's own fix |
| iroh-docs-003 | the sync report of a session that brought 100 authors or more is never sent | same code on main; no issue names it | none yet |
| iroh-gossip-001 | a peer that restarted with the same node id gets no neighbor | fixed on main, unreleased | upstream's main at a fixed revision |
| iroh-util-001 | the connection pool hangs past 100 waiting requests for one peer | fixed in 0.7.0 | the release 0.7.0, which iroh-blobs' main takes |

## The stance

The platform does not wait on upstream. A defect iroh carries is answered in the workspace, at the narrowest point that closes it: a selector of our own behind a hook iroh offers, a fixed upstream revision patched in, a fork of our own, a configuration iroh's own code should have set. Upstream releases rarely, and fixes sent to it sit unread: the two pull requests pdn-store sent to iroh-docs in July 2026, #111 and #112 — the fixes of iroh-docs-001, a pair of nodes that stopped syncing for good, and iroh-docs-002, content that never arrived — are open three months later with no review. A fix is still offered upstream, as a pull request or an issue, so that the record shows upstream was told; nothing in the workspace waits for its answer.

The only guarantee anything in iroh carries is the workspace's own tests. A hook iroh marks unstable, a revision of its main branch and a release it calls stable are trusted alike: as far as a test of ours drives them, and no further. Every answer listed below names the test that fails without it, and a bump of any iroh crate runs those tests first.

**Example:** what each kind of answer below rests on.

| answer | where it lives | what holds it |
|---|---|---|
| a selector of our own, iroh-001 | `crates/data-layer/src/path_selector.rs` | its unit tests and the stand's kill scenario |
| a patched revision, iroh-gossip-001, iroh-blobs-001 and iroh-blobs-009 | `[patch.crates-io]` in the workspace `Cargo.toml` | the stand's kill scenario, `a_blob_store_that_cannot_open_fails_the_spawn` in the data layer's `tests/persistence.rs`, and `a_provider_that_asked_what_it_lacks_answers_that_it_lacks_it` in pdn-store's `src/engine/live.rs` |
| a release, iroh-util-001 | iroh-util 0.7.0, which iroh-blobs' main takes | `connections_past_a_hundred_toward_a_silent_peer_all_end` in pdn-store's `tests/sync.rs` |
| our own configuration, iroh-002 | the stand's HTTP client | every stand test |

### Forks and patched revisions

A fix the workspace needs that upstream's main branch does not carry is held in a fork of our own, and every fork lives under `github.com/MeeFoundation`. Once upstream's main carries every fix a fork holds, released or not, the workspace patches in upstream's main at a fixed revision, leaves the fork as it is, and names above the patch in `Cargo.toml` every defect that revision answers.

A fork's own work lives on branches named `pdn/001`, `pdn/002` and on, counted per fork; the slash keeps them apart from upstream's branches and from defect names such as `iroh-blobs-001`. A branch the workspace has named is never deleted, rewritten or force-pushed, so every revision a `Cargo.lock` has recorded stays reachable. `Cargo.toml` takes the branch's head by `rev`, never by `branch`, and its comment names the branch.

Each commit on such a branch fixes one defect, is titled by the defect's name — `iroh-blobs-001: …` — rather than in upstream's commit convention, and names in its message the test of ours that fails without it, a test that fails every time. The commits lie in the order of their numbers and each applies on its own; one that rests on another names it. A pull request offered upstream is prepared apart, in upstream's own convention.

A move onto a newer upstream base starts the next branch at that base and takes the defects one at a time, in order. Each defect's test runs first without its commit: if it passes, upstream fixed the defect, the commit stays behind and the defect's entry records upstream's fix; otherwise the commit is applied, adapted where it no longer applies, and the defect's test and the workspace's suite pass before the next defect is taken. Meanwhile the workspace builds against a local checkout of the fork, patched in by path and never committed; only the finished branch is pushed. A branch that would carry no commit is not made.

**Example:** iroh-blobs, whose fork held one fix when upstream's main came to carry it.

| step | what the workspace takes | `a_blob_store_that_cannot_open_fails_the_spawn` |
|---|---|---|
| before | `MeeFoundation/iroh-blobs` at `2b0f54d`: upstream's 0.103.1 with our fix of iroh-blobs-001, made before this convention, on branch `fix-runtime-drop-on-own-thread` | passes |
| upstream's 0.103.1, without the fix | — | fails: the spawn still hangs after 30 seconds |
| upstream's main at `3369597`, carrying its own fix, #293, and no commit of ours | upstream's main at that revision, its comment naming iroh-blobs-001 and iroh-blobs-002; no `pdn/` branch is made, and the fork stays as it was | passes |

## iroh-001 · iroh 1.3: a peer that restarted at a new address is dialed at its old one

iroh's default path selector, `BiasedRttPathSelector`, keeps a selected path until a path of the same tier is at least 5 ms faster by its last measured round-trip time. A peer killed and started again listens on a new port; the old path is dead, but it keeps the round-trip time it last measured, and the connection that carried it lives on until its idle timeout. On a local network no path is 5 ms faster than a dead one measured at under 2 ms, so every connection the node opens to the restarted peer sends its handshake to the dead port, and the node's sync dials and payload downloads time out while the connections the peer opens toward it work. iroh drops its selection only once the last connection to the peer closes, and the node's own failed dials keep one open on the dead path.

The platform installs a selector of its own through iroh's `path_selector` hook, which iroh keeps behind its `unstable-custom-transports` feature: a path some connection to the peer has received on comes before one none has, then iroh's tiers, then, within a tier, the path more of the node's connections to the peer have received on, whatever their round-trip times; between paths alike in these the choice is iroh's own. The [node assembly](data-layer/node-assembly/spec.md) spec states it as "A peer that restarts at a new address is reached at it"; the unit tests in `path_selector.rs` and `a_killed_node_is_the_same_node_and_a_fresh_one_holds_nothing` in the host's `tests/stand_restart.rs` hold it. Upstream has no fix; a pull request of ours, which adds the same rule to iroh's own selector, is prepared and not yet sent.

A selector cannot cover every case from its side. iroh asks it when a connection to the peer opens or one of its paths is established or abandoned, never when a connection closes, and hands it no clock and no connection id. A peer that held more connections to the old address than the restarted node opens at its start keeps the dead path, and after those connections time out, 30 seconds after the kill, nothing asks again until the restarted node opens one more connection. The platform answers it without a patched iroh: a node runs the pass over its pods' stores once within 45 seconds of its spawn (`POD_PASS_AFTER_SPAWN` in the data layer's `src/node.rs`), and the connection that pass opens moves the peer to the new address. `a_killed_member_restarted_at_a_new_address_is_reached_there` in pdn-node's `tests/peer_restart.rs` holds it, with the member run as a process of its own and killed: with eight connections held to the old port, the record the restarted member placed did not reach the other member within 120 seconds without that pass, and does in about 50 with it.

**Example:** Bob's node b1, after Alice's node a1 was killed and started on port 33947 instead of 57771.

| path | connections that received on it | last round-trip time | iroh's selector | the platform's |
|---|---|---|---|---|
| `172.18.0.2:57771` | 1, from before the kill | 1.9 ms | kept | left |
| `172.18.0.2:33947` | 3, opened by a1 after its start | 0.4 ms | not 5 ms faster | selected |

## iroh-gossip-001 · iroh-gossip 0.101.0: a peer that restarted with the same node id gets no neighbor

When two nodes first meet in a swarm, the node that answered the other's `Neighbor` with a `Neighbor` of its own keeps that answer pending, and the other never replies to it. A peer killed and started again with the same node id joins the swarm anew; the node still counts it as a neighbor and sends a `Neighbor` back only when none to that peer is pending, so it sends nothing. The restarted peer is left with no neighbor and announces its writes to nobody, and the node never learns the peer's old connection is gone, because a newer connection to the peer exists when the old one times out. A write placed on the restarted node reaches the other member only at the pod's next pass, up to 300 s later.

Upstream fixed it on its main branch, pull request #161 ("answer a join from a peer that is already a neighbor"), on 2026-10-09, with #178, #191 and #192 on the connection and swarm lifecycle after it, and released none of them. The workspace takes iroh-gossip from that branch at a fixed revision through `[patch.crates-io]` until a release carries the fix. The [node assembly](data-layer/node-assembly/spec.md) spec states it as "A peer that restarts with the same node id is a neighbor again at once"; the same stand scenario holds it.

## iroh-blobs-001 · iroh-blobs 0.103: a file store that fails to open hangs its process

`FsStore::load` spawns a tokio runtime of its own, and when opening the store fails, the runtime is dropped from one of its own threads, which blocks for good: the error never reaches the caller and the process hangs. A teardown of the store can deadlock the same way. Upstream fixed it on its main branch, pull request #293 ("shut down the store runtime without blocking"), on 2026-10-21, closing its issues #252 and #260, and has released nothing since; #249, which asks that the store spawn no runtime of its own at all, stays open. The workspace takes iroh-blobs from that branch at a fixed revision through `[patch.crates-io]` until a release carries the fix; the fork it took before, `MeeFoundation/iroh-blobs`, stays as it was. `a_blob_store_that_cannot_open_fails_the_spawn` in the data layer's `tests/persistence.rs` holds it: against upstream's 0.103.1 the spawn of a node whose blob database cannot open hangs, and against the revision it fails with an error at once.

## iroh-blobs-002 · iroh-blobs 0.103: the file store builds only by luck

iroh-blobs' `fs-store` feature calls tokio's `block_in_place` without enabling `rt-multi-thread`, the tokio feature it sits behind, so a crate that enables `fs-store` alone does not compile. Upstream's main enables it with `fs-store` since pull request #272, on 2026-10-06, and has released nothing since; the revision the workspace takes carries it, so pdn-store enables nothing for it, and the product build of pdn-store, with no feature of its own (`just test-product`), compiles only with it.

## iroh-blobs-003 · iroh-blobs 0.103: a request reaching a file store that is shutting down panics

A request that reaches iroh-blobs' file store while it shuts down meets a file whose state the shutdown poisoned, and the store's task panics ("poisoned storage should not be used" in its `bao_file.rs`). A running docs engine starts downloads, each of which reads the blob store first, so closing the blob store before the engines stop meets it whenever downloads are under way: pdn-store's own restart test, `content_a_restart_left_missing_is_fetched_from_the_first_sync_peer`, met it in every run until its node stopped the engine first, and now counts the panics of its process and fails on one. For the node itself, `a_node_stopped_with_a_fetch_under_way_stops_without_a_panic` in the data layer's `tests/node_shutdown.rs` reads the order of the node's stop and fails when the engines stop after the blob store closes, since a download lands between the two only some of the time. A peer's request meets it too: iroh's router shuts its protocols down before it cancels their connections, so the blob protocol's shutdown closes the store while a connection's handler can still hold a request it read; `a_node_stopped_while_a_peer_observes_its_payload_stops_without_a_panic` in the same file met it in nearly every stop. The handler iroh-blobs ships runs each stream in a task of its own, which the router neither cancels nor awaits, so a request a stream read before the stop still reaches the store after the router's shutdown returned: with the store closed after the router alone, the same test met the panic in 6 of 300 runs on a runner of 4 CPUs. The node stops every engine before the router, mounts the blob protocol with a handler of its own, which runs each stream in a task the node tracks, and with a shutdown that leaves the store open, and closes the store itself once the router's shutdown has returned, the streams' tasks have ended and the store has finished what they handed it, waiting up to 5 seconds for those; a node dropped without its shutdown stops the same way, in a task of its own. The [node assembly](data-layer/node-assembly/spec.md) spec states the order under "Shutdown stops every protocol side by side, and a late call fails". The two tests that pin it in the data layer's `tests/node_shutdown.rs`, `a_node_stopped_while_a_peer_observes_its_payload_stops_without_a_panic` and `a_node_dropped_while_a_peer_observes_its_payload_stops_without_a_panic`, hold one stream between the request it read and the store until the router's shutdown has returned, and meet the panic in every run without the wait. Upstream's store goes on taking requests after its database closed and poisons what they touch, issue #233 and pull request #214 on it both open; the fork records that as a defect of its own.

## iroh-blobs-004 · iroh-blobs 0.103: a store's garbage collection outlives the store

The blob stores spawn their garbage collection as a task with a store handle of its own, and that task leaves its loop only when a run fails; a run the protect callback aborts is skipped. The file store's main actor ends only once every store handle is gone, so as long as the task lives it holds that actor and the store's private runtime, one worker thread per core. A node whose callback aborted every run after its stop left one such runtime behind per stop, for the rest of the process. No upstream issue names it; #291 asks the loop to survive a failed run, and #235 a public way to run a collection, which would let a caller run the loop itself.

The platform ends the task from the callback, through the public interface alone. iroh-blobs asks the callback every minute at most (`BLOB_COLLECTION_TICK` in the data layer's `src/node.rs`), and the callback lets a run go ahead only once the node's collection interval has passed. Once the node's stop has closed the blob store, and only then, the callback answers so that the next run goes ahead: iroh-blobs drops the store's metadata database before its shutdown answers, and a run's first call, like every call that could remove anything, goes to that database, so the run fails before it sweeps and the task ends. The callback asks the store to sync first and lets the run go ahead only if that call fails too, so a store that still answers after its shutdown is left to a skipped run rather than swept against an empty protected set. A node dropped outside a tokio runtime runs no stop; the callback then finds the node's identities gone and shuts the store down itself. A stopped node's store runtime therefore lives for at most a minute after the stop. `a_stopped_node_leaves_no_blob_collection_running`, `a_dropped_node_leaves_no_blob_collection_running` and `a_node_dropped_outside_a_runtime_leaves_no_blob_collection_running` in the data layer's `tests/node_shutdown.rs` hold it. They fail at an iroh-blobs bump where a run on a closed store no longer fails, or where a failed run no longer ends the task, which is what #291 asks for; either leaves the leak back, never a sweep, and the answer then is to end the task another way.

**Example:** Alice's laptop a1, whose host stops its runtime and starts a new one in the same process.

| moment | the old store's collection task |
|---|---|
| `shutdown` closes the old blob store | asleep until its next ask |
| the next ask, at most a minute later | the callback finds the store refusing a sync and lets the run go ahead; the run fails on its first call |
| after | the task has ended, the store's last handle goes with the node, and its runtime stops |

## iroh-blobs-005 · iroh-blobs 0.103: the memory store's collection removes a payload imported while it runs

A collection run marks the payloads every tag and temp tag names, then sweeps every other payload the store holds. A payload imported between the two carries a temp tag the mark did not see; the file store remembers every payload written since the run began and sweeps none of them, while the memory store keeps no such record, so its sweep removes the payload, a local write's own included: the entry stays and its payload is gone. Upstream's main branch carries the same memory store. The platform collects only over the file store a node on a storage directory runs: a node in memory exists only in a test build, behind the data layer's `test-util` feature, and its blob store is never collected. On nodes in memory collecting every 200 milliseconds, `a_payload_fetched_while_a_run_is_under_way_stays` in the data layer's `tests/blob_collection.rs` lost the writer's payload that way in about one run in a hundred on a runner of 4 CPUs; the scenarios of that file run on storage directories.

**Example:** a memory store collected every 200 milliseconds while Alice places a claim.

| step | the store |
|---|---|
| the run marks every tag and temp tag | the claim's payload not imported yet |
| the claim's payload is imported, its temp tag taken, its entry written | entry and payload held |
| the run sweeps | the payload removed: no mark names it, and the memory store does not remember it was just written |

## iroh-blobs-006 · iroh-blobs 0.103: a download from a provider that accepts the request and sends nothing never ends

iroh-blobs' `Downloader` asks the providers of a payload one after another, in a task of its own, and moves to the next only when one fails. A provider that accepts the request and sends nothing never fails: iroh's keep-alive, every 5 seconds, keeps the connection open, and nothing bounds the request in time. The download waits for as long as the provider stays connected, and a provider registered later reaches it only through a new download, which the engine starts after a failure that never comes. Dropping the download's handle does not help: the downloader's task notices a receiver gone only at its next progress message, which a silent provider never causes, so the request's stream stays taken. A modified node does this by answering nothing, and an honest node does it when its blob store hangs. `a_silent_providers_payloads_come_from_another_provider` in pdn-store's `tests/sync.rs` reproduces it: against an engine that downloads through the `Downloader`, none of 5 payloads first asked of a provider that answers nothing arrives within 60 seconds, though a second provider holding them finished a session with the replica. The platform does not use the `Downloader`: pdn-store's live actor fetches each payload from one provider with `execute_get`, whose future runs in a task the actor owns, and drops it after 10 seconds with no progress, freeing its stream and handing the payload to the other providers registered for it, the reconciliation sessions spec's "A download that makes no progress is handed on". The same test holds it: against the fetch, every payload arrives from the second provider about 10 seconds after its request to the silent one.

## iroh-blobs-007 · iroh-blobs 0.103: a request whose stream fails to open reports a failure of the local store

`Remote::fetch` and the other requests over a connection open their stream first, and when the connection is gone, a provider having closed it, they answer `GetError::LocalFailure` ("failed to open stream pair"), the variant every failure of the node's own blob store takes. A caller that tells the two apart, so as not to blame a provider for its own disk, takes the provider's closed connection for a local failure. pdn-store's fetch did, and parked the payload with no pause and no probe of the provider, so the payload waited for a session that might never come: a payload download from a gossip neighbor that closes every connection at once was not tried again in about one run in 13 of `a_download_from_a_neighbor_is_tried_again_until_the_replica_is_left` in pdn-store's `tests/dispatch.rs`. pdn-store opens the request's stream itself and hands `execute_get` the pair, so a stream that fails to open is the provider's failure; `a_request_over_a_connection_the_provider_closed_is_the_providers_failure` in `src/engine/live.rs` holds it, a request over a connection the provider closed coming out as the provider's failure, and as a local one when iroh-blobs opens the stream.

## iroh-blobs-008 · iroh-blobs 0.103: a payload the store failed to write is reported fetched

A request over a connection hands each piece it receives to the blob store's import and, once the transfer ends, waits for the import and its own reading together (`get_blob_ranges_impl` in its `api/remote.rs`), keeping the outer result of the import's answer and dropping the inner one, the import's own. The file store writes a payload past the 16 KiB it keeps inline in batches, one at each step from a leaf to a parent and the last once the transfer has ended, so a payload of 2 or 3 chunk groups, from 16,385 to 49,152 bytes, is written only after the end, and a write that fails there — on a disk that fills — is lost: the request reports itself done, and the store does not hold the payload. A write that fails earlier ends the import, and the next piece handed to it fails the request with `GetError::IrpcSend`, a variant that names neither side, though only the node's own store causes it. pdn-store's fetch took the first for a payload landed, announcing `ContentReady` for a payload the node did not hold, and the second for the provider's failure, pausing an honest provider for the node's own disk. pdn-store asks the store again once a request reports done and counts the fetch as landed only when the store holds the payload whole (`landed` in `src/engine/live.rs`), and counts `IrpcSend` as a failure of the local store; `a_payload_the_blob_store_fails_to_write_is_a_local_failure` in `src/engine/live.rs` holds both, over a file store whose data directory is replaced by a file once the store is open. No upstream issue names it.

**Example:** Alice's tablet a3, whose data directory accepts no file, fetches two payloads from Alice's laptop a1.

| payload | the store's write that fails | what the request reports | what pdn-store counts it as |
|---|---|---|---|
| 40,960 bytes, 3 chunk groups | the only one, after the transfer's end | done | a failure of the local store |
| 1 MiB | the first, during the transfer | `IrpcSend` | a failure of the local store |

## iroh-blobs-009 · iroh-blobs main since #298: a provider that lacks a payload answers as one that fails

A node whose replica holds an entry and not its payload is registered as a provider of that payload once a session with it ends, and a fetch from it ends with the provider's answer that it lacks the payload, which pdn-store takes as such: it drops that pair alone and pauses nothing (`outcome_of_failure` in `src/engine/live.rs`). Such a node has usually asked its own blob store what it lacks of the payload, through `Remote::local`, which every fetch asks first, iroh-blobs' own `Remote::fetch` included, and the question leaves the payload in the store as an entry without data: its status turns from `NotFound` to `Partial` with no size. Asked for that payload, a provider at the commit before pull request #298 ("detect truncated export_bao streams without relying on Done", 2026-10-26) resets the stream with an error code, the answer that it lacks the payload; with #298 the requester's fetch fails with `leaf hash mismatch` at offset 0, the error of a provider that sends data other than the payload, and pdn-store pauses the provider for at least 1 second, so a payload that only that node holds waits out the pause. #298 itself says that its provider now fails on an entry without data and leaves the store's early return for such an entry to a later change. `a_provider_that_asked_what_it_lacks_answers_that_it_lacks_it` in pdn-store's `src/engine/live.rs` holds it, failing with #298 and passing at the commit before it, `3369597`, as does the scenario `a_neighbor_lacking_a_payload_has_its_own_fetched_at_once` in `tests/sync.rs`. The workspace takes upstream's main at that commit. No upstream issue names it.

**Example:** a replica fetches two payloads from its neighbor, which holds the entry of "lacked" and not its payload, and then writes "own".

| fetch from the neighbor | upstream's main at `3369597` | with #298 |
|---|---|---|
| "lacked" | the neighbor lacks it: that pair is dropped | `leaf hash mismatch`: the neighbor is paused for at least 1 second |
| "own", written next | arrives at once | arrives once the pause ends, 2.7 seconds after its entry |

### Issue Title

A provider answers a request for a blob it holds no data of with data that fails verification

### Issue Body

A store that was only asked what it lacks of a blob — `Remote::local`, which `Remote::fetch` also asks first — keeps the blob as an entry without data: its status turns from `NotFound` to `Partial { size: None }`. A request for that blob from another node used to end the way a request for a hash the store never saw ends, with the stream reset with an error code. Since #298 it fails with `leaf hash mismatch` at offset 0, the error a requester gets from a provider that sends data other than the blob.

A requester can then no longer tell a provider that lacks a blob from one that sends corrupt data, so a downloader that backs off from failing providers backs off from an honest node that merely started a download of the blob. #298 says that `send_blob` now fails for an entry without data and leaves the early return in `export_bao_impl` for a later change; this is that gap as a requester sees it.

Reproduction, against iroh 1.4.1, with `anyhow`, `iroh = "1.4.1"`, iroh-blobs at the revision named and `tokio` with `macros` and `rt-multi-thread`:

```rust
use iroh::{endpoint::presets, protocol::Router, Endpoint};
use iroh_blobs::{
    protocol::GetRequest, store::mem::MemStore, BlobsProtocol, Hash, HashAndFormat, ALPN,
};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let provider_store = MemStore::new();
    let hash = Hash::new(b"payload");
    println!("status before local(): {:?}", provider_store.blobs().status(hash).await?);
    // Only ask what is missing; nothing is downloaded.
    provider_store.remote().local(HashAndFormat::raw(hash)).await?;
    println!("status after local():  {:?}", provider_store.blobs().status(hash).await?);

    let provider = Router::builder(Endpoint::bind(presets::Minimal).await?)
        .accept(ALPN, BlobsProtocol::new(&provider_store, None))
        .spawn();
    let requester = Endpoint::bind(presets::Minimal).await?;
    let conn = requester.connect(provider.endpoint().addr(), ALPN).await?;
    let res = MemStore::new()
        .remote()
        .execute_get(conn, GetRequest::from(HashAndFormat::raw(hash)))
        .await;
    println!("get from the provider: {res:?}");

    // The same request for a hash the provider's store was never asked about.
    let other = Hash::new(b"other");
    let conn = requester.connect(provider.endpoint().addr(), ALPN).await?;
    let res = MemStore::new()
        .remote()
        .execute_get(conn, GetRequest::from(HashAndFormat::raw(other)))
        .await;
    println!("get of a hash never asked about: {res:?}");

    requester.close().await;
    provider.shutdown().await?;
    Ok(())
}
```

At `3369597`, the commit before #298:

```
status before local(): NotFound
status after local():  Partial { size: None }
get from the provider: Err(io: stream reset by peer: error 3)
get of a hash never asked about: Err(io: stream reset by peer: error 3)
```

At `2cd6ed8`, with #298:

```
status before local(): NotFound
status after local():  Partial { size: None }
get from the provider: Err(leaf hash mismatch: 0)
get of a hash never asked about: Err(io: stream reset by peer: error 3)
```

Expected: a provider answers a request for a blob it holds no data of as it answers one for a hash its store never saw.

## iroh-002 · iroh 1.3: an HTTP client in the same build panics on its first request

iroh enables reqwest's `rustls-no-provider` feature, and cargo unifies it into every reqwest client of the build: under it a client takes only a TLS provider installed process-wide, so the stand's own HTTP client panicked on its first request, plain HTTP included. iroh's maintainers keep the feature and decline to change it (iroh issue #4442). The stand's client passes a TLS configuration of its own, the one iroh's relay tests build, in `plain_http_tls` in the host's `tests/common/mod.rs`.

## iroh-util-001 · iroh-util 0.6.0: the connection pool hangs past 100 waiting requests for one peer

pdn-store's engine takes the connections its payload fetches run over from iroh-util's `ConnectionPool`, one pool per engine and one `get_or_connect` per fetch, with at most `fetches_per_provider` fetches in flight toward one provider. In iroh-util 0.6.0 each peer's connection actor runs inside the pool's own task and reads a queue of 100 requests, and the pool's task waits whenever that queue is full. A queue that fills while the pool's task is busy is never read again: more than 100 requests for one peer at once, toward a peer whose connect hangs or one already connected, hang every fetch of that engine, in every pod of its identity, until the process restarts. Upstream described it in iroh-util pull request #1 and fixed it on its main branch by rewriting the pool as one actor, pull request #5, on 2026-10-07, followed by #17 and #18, and released it in 0.7.0 on 2026-10-22. iroh-blobs' main takes 0.7.0, and the workspace takes it with it. `connections_past_a_hundred_toward_a_silent_peer_all_end` in pdn-store's `tests/sync.rs` holds it: against 0.7.0, 500 connection requests toward a peer whose handshake gets no answer all end within 10 seconds, and against 0.6.0 none of them ends. 0.7.0 adds a bound 0.6.0 lacks, `max_pending_connections`, 64 attempts to connect running at once, and turns away every attempt past it: the engine would take an attempt turned away for a provider that failed to connect, and drop a provider that is no gossip neighbor for it. The engine sets that bound to the pool's bound on connections, 1,024, so attempts are bounded as in 0.6.0 (`fetch_pool_options` in `src/engine/live.rs`); `the_fetch_pool_turns_away_no_attempt_to_connect` there holds it, 65 attempts toward silent peers none of which is turned away. Whether a node of ours has met it is open. A node that joined a pod of 20,000 records on a laptop in a load test received every entry and then no payload for 200 seconds, with the cause not established, while a catch-up of 20,000 entries between two engines in one process completes against 0.6.0.

**Example:** requests from one pool toward a peer whose handshake gets no answer.

| requests | iroh-util 0.6.0 | iroh-util 0.7.0 |
|---|---|---|
| 50 | all fail after the 1-second connect timeout | all fail after the 1-second connect timeout |
| 150 | none answered after 10 seconds | all fail after the 1-second connect timeout |
| 20,000 | none answered after 10 seconds | all fail after the 1-second connect timeout |

## iroh-docs-001 · iroh-docs: a dial the remote aborts as already syncing leaves the pair stuck

When the remote aborts a dial because it sees an exchange with the dialer already running, iroh-docs leaves the dial recorded as running, and nothing finishes it: every later trigger to sync the pair is dropped as a duplicate, and the two nodes stop syncing the namespace for good. pdn-store returns the pair to idle on such an abort, sparing an exchange the remote's own dial took the slot over with (`NamespaceStates::abort_connect` in `src/engine/state.rs`), and dials the pair again half a second later, at most 3 times in a row. `abort_connect_returns_rejected_dial_to_idle` and `abort_connect_spares_accept_takeover` in the same file and `a_remote_always_syncing_is_redialed_a_bounded_number_of_times` in pdn-store's `tests/dispatch.rs` hold it. The fix went upstream as pull request #111 in July 2026 and is open with no review.

## iroh-docs-002 · iroh-docs: a payload the session's sender lacked waits on one gossip message

An entry can arrive before its payload, when the peer that sent it lacks the payload itself. iroh-docs parks such a payload and asks for it again only when a gossip `ContentReady` names it, a message gossip may lose, and once that message is lost nothing asks for the payload until some unrelated insert does. pdn-store asks the peer of every later successful session for the payloads the namespace has parked (`on_sync_finished` in `src/engine/live.rs`), and `sync_fetches_parked_content_from_later_sync_peer` in pdn-store's `tests/sync.rs` holds it. The fix went upstream as pull request #112 in July 2026 and is open with no review.

## iroh-docs-003 · iroh-docs: the sync report of a session that brought 100 authors or more is never sent

After a session that brought entries, the engine announces to its gossip neighbors the heads it received, the latest timestamp of each author, as a `SyncReport`; a neighbor that lacks the latest entry of any author the report names runs a sync with the sender at once, and that sync brings everything the neighbor lacks. The engine sizes the heads by gossip's `max_message_size`, the limit of a whole message, 4,096 bytes by default, while the message also carries the report's other fields, and gossip's own encoding takes its share of the limit: gossip takes at most 4,055 bytes of content, and in pdn-store the report of a session that brought 99 authors is 4,028 bytes and one of 100 authors 4,068 bytes. No report of 100 authors or more is ever sent: iroh-gossip 0.101.0 drops it in its write loop, its main since pull request #178 also resets the topic's stream and loses the messages queued behind it, and since #187 it refuses the broadcast with `TooLarge`, which pdn-store discards in silence (`broadcast_neighbors` in `src/engine/gossip.rs`). A neighbor that is behind then learns of the news only at its own next pass, every 300 seconds in a pod. Upstream iroh-docs sizes the report the same way, by `AuthorHeads::encode(Some(max_message_size))` in its `engine/live.rs`. pdn-store does not answer it yet; its reach is a pod with 100 or more devices that write, such as the load test's 100 nodes.

**Example:** the report a session sends to the neighbors, against gossip's 4,055 bytes of content.

| authors whose entries the session brought | the report | sent |
|---|---|---|
| 99 | 4,028 bytes | yes |
| 100 | 4,068 bytes | no |
| 102 or more | 4,148 bytes, the heads cut at 4,096 bytes | no |

### Issue Title

The sync report of a session with about 100 authors or more exceeds the gossip message limit and is never delivered

### Issue Body

After a sync that received entries, the live actor broadcasts a `SyncReport` to the topic's neighbors, so that a neighbor that is behind syncs at once. It encodes the report's heads with `AuthorHeads::encode(Some(self.gossip.max_message_size()))`, which caps the heads alone at the limit of a whole gossip message; the `Op` around them, the namespace and the heads' length prefix, and gossip's own encoding of the message, about 40 bytes, come on top. With the default `max_message_size` of 4,096 bytes and a head taking about 40 bytes, a report of about 100 authors or more no longer fits.

Such a report is never delivered. With iroh-gossip 0.101.0, `broadcast_neighbors` returns `Ok` and the message fails in the write loop; on iroh-gossip's main, after n0-computer/iroh-gossip#178, the failed write also resets the topic's stream, losing the messages queued behind it; after n0-computer/iroh-gossip#187, the broadcast returns `ApiError::TooLarge`, which the live actor discards. Neighbors that are behind then catch up only on their own next sync, and a document with that many authors stops spreading news through reports at all.

Sizing the heads by the content limit gossip now exposes, `GossipSender::max_content_size`, less the encoded size of the report around the heads, keeps every report within the limit; `AuthorHeads::encode` already keeps the newest heads when it has to cut.

## iroh-docs: everything pdn-store diverges in

pdn-store is the platform's own variant of iroh-docs ([ADR-0016](../../architecture/adr/0016-pdn-store-is-the-platforms-own.md)); the rules it follows where iroh-docs does otherwise are listed with their reasons in `crates/pdn-store/CLAUDE.md`, and the verdict on each upstream commit and fix pull request read since the fork is in `crates/pdn-store/UPSTREAM.md`.
