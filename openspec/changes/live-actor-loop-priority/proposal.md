# Proposal: live-actor-loop-priority

## Why

An engine of pdn-store handles everything it does in one loop, `LiveActor::run_inner` in `src/engine/live.rs`: a `select!` under `biased`, which polls its branches from the top and takes the first one ready. The branches are, in this order: finished payload downloads, the inbox, replica events, finished dials, finished accepts, ended gossip receive loops. A branch is reached only on a turn where nothing above it is ready, and the handler a turn runs holds the loop for as long as it waits: a report from the swarm waits on the sync actor (`has_news_for_us` in `on_sync_report`), a remote insert waits on the blob store up to twice (`on_replica_event`).

The inbox carries every gossip op of every swarm the engine joined — a `SyncReport`, a `ContentReady`, a neighbor's arrival and departure — beside the host's calls, such as `Doc::sync_with_peers`, and the engine's own timers. It holds 64 messages, and a full inbox makes every gossip receive loop of the engine wait. Nothing bounds how often a swarm member sends.

The end of a session sits below the inbox and the replica events, in `on_sync_via_connect_finished` and `on_sync_via_accept_finished`, and it carries what a finished session does: its `SyncFinished`, the post-sync report that takes the news one hop further, the retry of parked content from that peer, the release of the dials held behind it by `Engine::order_after`, a pair's redial. A load test with all nodes on one laptop, 16 members writing 20 records a second together, measured what this order costs the branch below a busy inbox: in a build with downloads below the inbox and the replica events, a download that took 34 ms on the median had its result wait 946 ms on the median and 17.7 s at the 90th percentile before the loop handled it; with downloads first, the same test measured a wait of 30 ms. The wait of a session's end has not been measured. The same build gives one hint: a `ContentReady` followed the last `SyncFinished` by 2.7 ms on the median while sessions ended every 48.5 ms, which is what two branches reached only on the same rare free turns look like.

The second case needs no load at all. The threat model places in a pod's swarm a holder of its tickets that is no member, a removed member above all, and its gossip ops enter the inbox as any member's do. While the inbox holds a message on every turn, no session's end is handled.

**Example:** Bob's phone b1 is removed from "Family", stays in the record store's swarm, and keeps sending Alice's laptop a1 `Op::SyncReport` messages with author heads a1 already holds, while a1's session with Alice's phone a2 ends.

| a1's loop | what it costs a1 | what waits |
|---|---|---|
| takes one of b1's reports from the inbox | one wait on the sync actor, which answers that there is no news | — |
| finds a2's session ended while a report of b1's is ready | — | the whole end: a1's `SyncFinished`, its post-sync report, the dials held behind it, for as long as b1 sends faster than a1's sync actor answers |

The rate b1 needs is not measured. Under defect-reachability the second case is by construction a modified node stalling an honest one through what it sends, which obliges a fix; the first obliges one as well if the measurement finds a wait of seconds, since a host reaches it through the public surface of pdn-node whenever many members of a pod write at once.

## What Changes

Nothing is decided. The change first measures the wait of a session's end under the same load test: a log line where the session's task finishes and one where its end is handled, paired by namespace, peer and counterpart. It then settles how the loop bounds that wait, and specifies and builds the answer. The options are listed under Open Questions, and none of them is chosen.

## Open Questions

### How the loop bounds the wait of a session's end

Every option keeps one order the loop depends on: a session's replica events are handled before its end. When a session's task finishes, every entry it inserted already sits in the live actor's event channel, and `biased` takes those events first, so the end finds that session's content queued for download, and it emits `PendingContentReady` only once those downloads are done. Handled the other way round, the end finds nothing queued and emits `PendingContentReady` before that session's content is even asked for.

- Session ends above the inbox, and the replica events above them: downloads, replica events, dials, accepts, inbox. Nothing a swarm member sends delays a session's end, since replica events come only from sessions the access provider admitted and from the host's own writes. A catch-up of 10,000 entries then holds the inbox — the host's calls, `Shutdown`, every swarm's gossip — for all of its 10,000 events, each with up to two waits on the blob store.
- No `biased`, with the one dependent order made explicit: a session's end first handles the replica events already queued, through `DrainingSync` in `src/engine/live/draining.rs`. A turn starts its poll at a random branch, so a stream on one branch takes its share of the turns and no more. Interleavings the fixed order makes rare become as likely as any other, and the scenarios of the data layer and pdn-node answer for each of them.
- A budget of inbox messages: after a fixed number of them in a row, the next turn polls the branches below the inbox first. The wait of a session's end is bounded by that many inbox handlers and the replica events queued; the number is a constant to size.
- The waits off the loop: `has_news_for_us` runs in a task that reports back, as the content scan does through `ToLiveActor::ContentScanned`, so a report costs the loop no wait. The inbox then empties whenever messages arrive slower than the loop takes them, which covers the honest load; a faster stream still holds the branches below, and the tasks need a bound of their own.

**Example:** two cases on a1 — b1's stream of reports while the session with a2 ends, and a catch-up of 10,000 entries from Alice's tablet a3 while the host calls `Doc::sync_with_peers` on another pod.

| option | the end of a2's session | the host's call during a3's catch-up |
|---|---|---|
| the order as it stands | handled on the first turn that finds the inbox empty: never, while b1 keeps sending fast enough | handled on the next turn, ahead of the catch-up's events |
| session ends and replica events above the inbox | handled once the events queued before it are, whatever b1 sends | handled after all 10,000 events |
| no `biased` | handled within a few turns on average | handled within a few turns on average |
| a budget of 32 inbox messages | handled after at most 32 of b1's reports | handled on the next turn, as today |
| the waits off the loop | handled whenever the inbox empties: at once while b1 sends slower than the loop takes a report, never while b1 sends faster | handled on the next turn, as today |

## Operating conditions

Several identities on one node change the reach of a stream: each identity's engine runs its own live actor and sync actor, so b1's stream in one identity's swarm holds that identity's loop alone, while the blob store is one per node and its waits in one loop lengthen those in every other. A membership that moves is the second case itself: a removed member's device that does not leave the swarm keeps its place there. An unstable connection changes the first case: the load test's reader on a phone over Wi-Fi, where a session took five times as long, saw a payload readable 15 ms after its entry arrived, so the measurement runs with every node on one machine, where the wait shows. A clock running ahead changes what one of b1's reports costs and not the outcome: a report naming author heads from the future claims news, and a1 dials b1's node, one dial per pair at a time. A restart empties the inbox and every queue, and nothing durable depends on the order; linking and a disk that fills leave the outcome as it is.

## Out of Scope

- Finished downloads, which come first in the loop and which the load test measured there.
- What a single gossip message costs before it reaches the inbox, and the transport's stream counts, which the unclassified-connection-bounds change weighs.

## Capabilities

None is settled. Every option touches `crates/pdn-store` alone. The data layer's [change subscription](../../specs/components/mee-pdn/data-layer/change-subscription/spec.md) spec, whose requirement that the live engine takes its events while it waits on the store already describes this loop, gains a requirement bounding the wait of a session's end, if the change puts one there.

## Impact

- **`crates/pdn-store`**: `LiveActor::run_inner`, `on_sync_via_connect_finished` and `on_sync_via_accept_finished` in `src/engine/live.rs`; `DrainingSync` in `src/engine/live/draining.rs` if a session's end handles the queued events itself; `on_sync_report` if its wait moves off the loop.
- **Tests**: a deterministic test of the bound needs a way to hold the loop on a turn while messages queue, which the store does not have, so the proof is designed with the change.
