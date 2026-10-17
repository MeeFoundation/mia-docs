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

A request that reaches iroh-blobs' file store while it shuts down meets a file whose state the shutdown poisoned, and the store's task panics ("poisoned storage should not be used" in its `bao_file.rs`). A running docs engine starts downloads, each of which reads the blob store first, so stopping the router, which closes the blob store, before the engines meets it whenever downloads are under way: pdn-store's own restart test, `content_a_restart_left_missing_is_fetched_from_the_first_sync_peer`, met it in every run until its node stopped the engine first, and now counts the panics of its process and fails on one; so does `a_node_stopped_with_a_fetch_under_way_stops_without_a_panic` in the data layer's `tests/node_shutdown.rs`, for the node itself. A peer's request meets it too: iroh's router shuts its protocols down before it cancels their connections, so the blob protocol's shutdown closes the store while a connection's handler can still hold a request it read; `a_node_stopped_while_a_peer_observes_its_payload_stops_without_a_panic` in the same file met it in nearly every stop. The handler iroh-blobs ships runs each stream in a task of its own, which the router neither cancels nor awaits, so a request a stream read before the stop still reaches the store after the router's shutdown returned: with the store closed after the router alone, the same test met the panic in 6 of 300 runs on a runner of 4 CPUs. The node stops every engine before the router, mounts the blob protocol with a handler of its own, which runs each stream in a task the node tracks, and with a shutdown that leaves the store open, and closes the store itself once the router's shutdown has returned, the streams' tasks have ended and the store has finished what they handed it, waiting up to 5 seconds for those; the [node assembly](data-layer/node-assembly/spec.md) spec states the order under "Shutdown stops every protocol side by side, and a late call fails". Upstream's store goes on taking requests after its database closed and poisons what they touch, issue #233 and pull request #214 on it both open; the fork records that as a defect of its own.

## iroh 1.3: an HTTP client in the same build panics on its first request

iroh enables reqwest's `rustls-no-provider` feature, and cargo unifies it into every reqwest client of the build: under it a client takes only a TLS provider installed process-wide, so the stand's own HTTP client panicked on its first request, plain HTTP included. iroh's maintainers keep the feature and decline to change it (iroh issue #4442). The stand's client passes a TLS configuration of its own, the one iroh's relay tests build, in `plain_http_tls` in the host's `tests/common/mod.rs`.

## iroh-docs: everything pdn-store diverges in

pdn-store is the platform's own variant of iroh-docs ([ADR-0016](../../architecture/adr/0016-pdn-store-is-the-platforms-own.md)); the rules it follows where iroh-docs does otherwise are listed with their reasons in `crates/pdn-store/CLAUDE.md`, and the verdict on each upstream commit and fix pull request read since the fork is in `crates/pdn-store/UPSTREAM.md`.
