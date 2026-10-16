# Design: sync-observation

## Context

Two tests read this surface. The load tests (`pdn-app/sync-test/load.md`) run a matrix of pods — 2 to 16 member nodes, 0 to 100,000 records, two payload sizes — once with every node on the laptop and once with the phone as the measured node `r`, and compare the two to decide whether a laptop-only run is honest for each number. They need every node's events with timestamps taken where they happen, a joiner's events from its first session on, the pod interval set and recorded, the build profile of every node, and a CPU sample of the phone that tells the node's threads from the rest of the application. The reliability test (`pdn-app/sync-test/design.md`) classifies every expected entry on every reader by the record-store sessions that should have carried it: an entry absent from the reader when the reader's side of a qualifying session finished is violated, and elapsed time alone never turns "not yet" into "lost". It needs the entries each node received and the sessions it finished, in an order that says which session an entry arrived in; a record of each session that it can match against the other side's record of the same session; a final listing that reports each entry's verdict; and the removaled member's record-store stream ending when that member forgets the store. `pdn-app/sync-test/plan.md` fixes the record both tests read ("Shared interfaces", the event record and the run directory) and leaves to this change how the store, the data layer, the runtime and the 2 hosts provide it. Every measurement runs on release builds.

What the code does today, checked for this design:

- `Engine::subscribe` in `crates/pdn-store/src/engine.rs` subscribes to the replica (inserts) and to the live actor (sessions, downloads) on 2 channels of 256 and merges them with `or`, which interleaves them in whatever order the consumer polls. `Doc::subscribe` in `api.rs` reaches it through the API actor over a stream of 64.
- Both channels are `Delivery::Lossy` (`subscribers.rs`): a full channel drops the event and a `Lagged` follows the last one delivered. Only the live actor subscribes to a replica `Blocking`.
- The replica reports an insert from a session inside `sync_process_message` in `crates/pdn-store/src/sync.rs`, before it answers the round; the live actor's own subscription is blocking, so the insert is in the live actor's channel before the session task sees the round's answer.
- The live actor's loop in `run_inner` (`engine/live.rs`) is a `biased` select that takes replica events before the results of finished sessions.
- `SyncEvent` carries `peer`, `origin`, `started`, `finished` and a result whose error is a string; `SyncDetails` carries `entries_sent` and `entries_received` from `SyncOutcome`. A failed teardown (`ConnectError::Close`, `AcceptError::Close`) drops the outcome and its counts.
- A dial the peer refuses as already syncing (`AbortReason::AlreadySyncing`) produces no event on either side. A session the accepting side refuses before the pair registers — the access provider's uniform `NotFound`, which is how `serve_pod` in `crates/data-layer/src/access.rs` refuses a caller its fold holds as no member — produces no event on the accepting side; the dialing side reports it as `ConnectError::RemoteAbort`.
- The 300-second bound around a dial (`SYNC_SESSION_TIMEOUT`, `connect_and_sync` in `net.rs`) wraps an elapsed session as `ConnectError::Connect`, whether or not the connection was already carrying the exchange. `connect_and_sync` opens one connection per session.
- A session between 2 identities of one node runs over an in-process pipe (`sync_in_process` in `engine/live.rs`), finishes through the same path as a dialed session, and reports a `SyncFinished` whose peer is the node itself.
- Every hosted identity has an engine of its own, and a pod's two stores are two replicas of it (`PodBinding` in `crates/data-layer/src/registry.rs`: `membership`, and `records`, absent on a tombstone). Dropping a replica (`drop_doc`) makes the live actor leave it with `kill_subscribers`, which ends every live subscription to it. A removal folded by the removaled member, and a leave, drop the record store and keep the membership store (`forget_pod` in `crates/data-layer/src/node.rs`, called from `depart` and `arm_pods` in `crates/pdn-node/src/pods.rs`).
- No pod read nudges a session: `list_records`, `read` and `pod_record_view` start none. The record view (`RecordView` in `crates/data-layer/src/pod/record_view.rs`) holds every entry of the record store beside its `Verdict` (`pod/fold.rs`: `Counted`, `CountedForNothing`, `NotYet`, `OutsideLayout`); its `RecordEntry` holds the key, the author, the timestamp, and the content hash only once the payload has arrived. `Runtime::pod_record_view_for_test` passes it through behind `test-util`.
- The pod interval is `SpawnOptions::pod_reconcile_interval`, 300 seconds by default; the ordinary reconcile pass skips pod stores. `pdn-node-http` reads `PDN_DATA_DIR`, `PDN_HOST`, `PDN_PORT`, `PDN_CONNECTIVITY` and `PDN_DEBUG` and sets no interval; `pdn-mobile`'s `bring_up` takes the reconcile interval and no pod interval.
- `join` in `crates/pdn-node/src/pods.rs` runs the join dialogue, then `import_pod` in `crates/data-layer/src/node.rs` imports both stores and starts their sync before it returns (`start_pod`: the membership store, then the record store); the join then waits up to 30 seconds (`JOIN_CATCH_UP_TIMEOUT`) for each store's first session, and a catch-up that outlasts the wait leaves the pod recorded and answers `CatchUpTimedOut`. The live actor opens a replica for sync, and subscribes to it, inside its `start_sync`, before the first dial.
- The facade builds its asynchronous runtime with `tokio::runtime::Builder::new_multi_thread` in `PdnNode::new` (`crates/pdn-mobile/src/node.rs`) and names none of its threads; the store's actor runs on a thread of its own named `sync-actor`, one per hosted identity's engine.
- `pdn-node-http` admits at most 16 debug requests (`admit_request` in `lib.rs`); the permit is released when the handler returns its response, before a streamed body ends. `GET /debug/status` answers the node id and the hosted identities.

## Goals / Non-Goals

**Goals:**

- A record per event in the shape `plan.md` fixes, from the laptop host and the phone alike, covering both stores of a pod, with every `insert_remote` of a session before that session's `sync_finished`.
- No event of a 1,000-entry session lost, whatever the consumer's pace within a bound, every loss that does happen visible, and every `t` taken when the runtime receives the event, not when the consumer reads it.
- A joiner's catch-up observed from its first insert.
- The 2 sides of one session recognizable as one session.
- A final listing with each entry's verdict, which starts no session.
- The pod interval set by the test on every node, and the build profile reported by every node.
- The phone's CPU reported for the node's threads apart from the whole process, and every sample window in which the application was not active told apart.
- All of it in a release build of the test, none of it in a build that ships.

**Non-Goals:**

- Changing what a session does or reports as its outcome (`session-outcome`).
- A product-facing event surface, metrics, or a stable wire format for the records.
- CPU or memory reporting by `pdn-node-http`: the load runner reads laptop processes with `ps`.

## Decisions

### D1. The ordered subscription takes every event from the live actor

`pdn-store` gains a second subscription to one replica, the ordered subscription. Its events all come from the live actor: the live actor forwards the `LocalInsert` and `RemoteInsert` it already receives on its blocking replica subscription to ordered subscribers of that namespace, beside the session, download and neighbour events it emits itself. One producer and one channel, so the subscriber sees events in the order the live actor handled them. That order puts a session's inserts before the session's end, exactly: the replica puts each insert into the live actor's channel before it answers the round that carried it, the session ends only after its last round is answered, and the live actor's loop takes replica events before finished sessions. It also keeps a later session's inserts after an earlier session's end, for the pair that matters: the live actor starts the pair's next dialed session only after handling the previous one's end, and refuses an incoming one as already syncing while the previous one runs. A download's `ContentReady` comes after the insert that queued it for the same reason. In-process sessions take the same path and keep the same order. The ordered subscription is refused for a replica the live sync does not hold open, since the live actor receives no inserts for one, and it ends when the replica is dropped, as every live subscription does. It can also be taken together with the start of a replica's sync: the start message carries it, and the live actor registers it in the step that opens the replica for sync, before the first dial, so it sees that sync from its first event; the observed join (D12) starts both stores this way. The product's `Engine::subscribe` keeps its 2 channels.

**Example:** the phone's record store; its pass dials w5, the session inserts 2 entries, and the next session with w5 inserts a third.

| live actor handles | ordered subscriber receives |
|---|---|
| replica event: insert `by/<w3>/immutable-document/<a>/1` | `insert_remote` of it |
| replica event: insert `by/<w3>/immutable-document/<b>/1` | `insert_remote` of it |
| session result: dialed w5, ok | `sync_finished` |
| download of the first payload completes | `content_ready`, its hash |
| next session with w5 starts | — |
| replica event: insert `by/<w4>/immutable-document/<c>/1` | `insert_remote` of it |

**Rejected alternatives:**

- Keep the 2 channels and, on each event from the live actor, first drain what the replica channel holds
  - **Pros:** no change to the live actor.
  - **Cons:** exact only for a consumer that is never late: one reading a session's end after the pair's next session has delivered drains that session's inserts ahead of it, and the test then counts an entry as delivered by a session that did not carry it — a violation hidden.
- A sequence stamp from one counter on both channels, merged by stamp
  - **Cons:** changes the channel type of every replica subscriber, the live actor's own included, to deliver what one producer already delivers in order.
- Make `Engine::subscribe` itself ordered for every subscriber
  - **Cons:** a replica not open for live sync would stop reporting its inserts to the product's subscribers.

### D2. The ordered subscription names its capacity, and observation asks for 4,096 per store

The ordered subscription takes its channel's capacity from the caller and stays `Lossy`: past the capacity, events are dropped behind one `Lagged`, and the live actor never waits on it. Observation asks for 4,096 on each store. Its reader is the runtime's own draining task (D5), which empties the channel as the live actor fills it, so the capacity covers that task's scheduling delay; it still holds a whole session of 1,000 entries, at most 2,002 events on its store — 1,000 inserts, at most 1,000 downloads completing, the session's end and the end of its downloads. A slow consumer is absorbed behind the runtime, by its buffer of numbered records (D5). Any loss, at the channel or at the buffer, arrives as `lagged`, which the reliability test counts against the pairs it touches (`undetermined`). The load test reports a cell whose stream carried any `lagged` record or `seq` gap with its lag count and leaves it out of the time metrics; a cell whose `r`, or joiner, never held every record is incomplete and left out of every fit. The product's subscriptions keep 256: a bounded channel allocates its slots when it is created, so a larger default costs every product subscription the memory of the largest one.

**Example:** the load test's catch-up cells, on the joiner's record store.

| cell | events of the catch-up | what holds them |
|---|---|---|
| V = 1,000 | at most 2,002 | the store's capacity alone, even if the runtime's task did not run until the catch-up ended |
| V = 10,000 | at most 20,002 | the runtime's task draining the store's channel; the runtime's buffer, even if the consumer reads nothing until the catch-up ends |
| V = 100,000 | at most 200,002 | the same; the buffer holds them while the observed join waits and the consumer cannot yet read (D12) |

**Rejected alternatives:**

- `Delivery::Blocking` for observation
  - **Cons:** the live actor, and every replica it serves, then waits on an HTTP client; a stalled coordinator stops the node's sync, and the observer changes what it observes.
- An unbounded channel
  - **Cons:** a consumer that stops reading grows the node's memory until the phone is killed; the loss is then the whole process, not a counted lag.
- A capacity sized for a 100,000-record catch-up
  - **Cons:** the slots are allocated up front, so each subscription holds tens of megabytes from its first event, and the load test's resident-size measurement of `r` would carry them.
- Raising `SUBSCRIBE_CHANNEL_CAP` for every subscription
  - **Cons:** the memory above, paid by every product subscription (the connection and private metadata stores subscribe per replica).

### D3. Both sides derive a session id from the connection

A session over a network connection carries a session id: 16 bytes both ends export from the connection's TLS keying material (`Connection::export_keying_material` in iroh, with a fixed label and no context), taken as soon as the connection is established and carried with the session's result on every path after that, failures included. Nothing new crosses the wire, and the value is the same on the 2 ends and different for every connection. Each session is its own connection (`connect_and_sync` dials one per session, and an accepted connection carries one session), so the id names the session. A session that failed before a connection existed, and a session between 2 identities of one node (in-process, no connection), carries none.

The id makes pairing the 2 sides of a session a lookup.

**Example:** 3 dials of the phone to w5's record store, as each side logs them.

| phone (`origin` `connect`) | w5 (`origin` `accept`) |
|---|---|
| `error_kind` `connect`, no `session` (w5 unreachable during the cut) | — |
| `remote_abort`, `session` `51c0…` (w5's fold does not yet list the phone's member) | — |
| ok, `received` 12, `session` `9f3a…` | ok, `sent` 12, `session` `9f3a…` |

**Rejected alternatives:**

- Pairing in order after dropping failures
  - **Cons:** in 2 cases the reader logs a session the writer does not — a dial the writer refuses before the pair registers (the reader logs `remote_abort`, the writer nothing), and the 300-second bound elapsing mid-exchange (the reader logs `connect`, the writer logs its own side) — and either shifts every later pair by one.
- A random nonce in the session's first message
  - **Cons:** changes the wire format, and a node of an older build cannot read the message.
- iroh's `stable_id`
  - **Cons:** local to one end; the other end's value differs.

### D4. A session event states its stage and, when the exchange completed, its counts

A failed session's event carries `error_kind`, the stage named by the error's variant, and the counts of entries sent and received whenever the exchange's rounds completed: on success, and on a failure of the teardown alone. `ConnectError::Close` and `AcceptError::Close` carry the outcome the rounds produced, which the teardown failure discards today. The kinds are the 4 `plan.md` names; which sessions reach an event at all is the code's today and is stated here, not changed.

**Example:** every way a session ends, and what its event says.

| side | how it ends | event | `error_kind` | counts |
|---|---|---|---|---|
| dialing | connection or stream not established, or the 300-second bound elapsed (`ConnectError::Connect`) | yes | `connect` | — |
| dialing | refused as already syncing | none | — | — |
| dialing | refused otherwise (`ConnectError::RemoteAbort`) | yes | `remote_abort` | — |
| dialing | a round failed (`ConnectError::Sync`) | yes | `sync` | — |
| dialing | rounds completed, teardown failed (`ConnectError::Close`) | yes | `close` | yes |
| accepting | failed before the first message named a namespace, or refused | none | — | — |
| accepting | a round failed, or no first message within the bound (`AcceptError::Sync`) | yes, when the pair was registered | `sync` | — |
| accepting | rounds completed, teardown failed (`AcceptError::Close`) | yes | `close` | yes |
| either | ok | yes | — | yes |

So a teardown split — one side ok, the other `close` — shows its counts on both sides, and the test can tell it from a split in the middle of the exchange.

**Rejected alternatives:**

- A fifth kind, `timeout`, for the elapsed bound
  - **Cons:** the session id already tells the test whether the writer saw the session; `plan.md` fixes 4 kinds, and a fifth buys nothing the test reads.
- Counts on every failure, as far as the rounds got
  - **Cons:** a partial count on one side and none on the other pairs nothing; the test uses counts only to check a completed exchange.

### D5. One subscription per member and pod, numbered once by the runtime for every hop

`pdn-node` opens, for one hosted identity and one pod it holds, an ordered subscription on each of the pod's stores and yields their events as one stream of records in the shape `plan.md` fixes. Each record names its store (`membership` or `records`). Within a store the stream keeps the store's order (D1); between the two stores it keeps the order the runtime takes them in, and the tests compare events of different stores by their times on the node's clock. The runtime numbers the records: `sub` is a random 64-bit value, in lowercase hexadecimal, new for every subscription; `seq` counts from 0 by 1; `t` is the runtime's clock when it takes the event off the store's subscription, in microseconds since the Unix epoch, as are `entry_ts`, `started` and `finished`. A task of the runtime's own, spawned with the subscription, takes the events off both stores' subscriptions as they arrive, stamps and numbers them and turns them into records, and never waits on the consumer, so `t` is when the event reached the runtime whatever the consumer's pace. The records wait for the consumer in a buffer of at most 262,144, a queue that takes memory only for the records in it, and a consumer's read takes the oldest. Past that bound the records that do not fit are dropped unnumbered, and once the buffer has room a `lagged` record names each store that lost some. 262,144 holds the at most 200,002 events of a 100,000-record catch-up's first session, and the membership store's beside them, which wait while the observed join runs and its consumer cannot read yet (D12). The task ends when the consumer drops the subscription. Neighbour events are dropped before numbering, so they leave no gap. A store's `Lagged` becomes a `lagged` record naming that store. When a store's subscription ends while the runtime runs — the record store dropped by `forget_pod` on a removal the member folds or on a leave — the stream yields `closed` for that store and goes on with the other; a subscription opened on a tombstone yields `closed` for the record store as its first record. When the runtime stops, the stream ends with no further record. The record is one serde type in `pdn-node`, and both hosts write its JSON form, so the laptop host and the phone emit the same bytes for the same event. Every hop after the runtime — the HTTP response of either host — reads the runtime's buffer and passes records through unnumbered, and a loss on any of them shows as a gap in `seq`. A co-located identity that holds no store of the pod is refused, whoever else on the node holds it.

**Example:** the removaled control member `k`'s stream around the removal.

```
k:                  {"sub":"5e0d…","seq":310,"store":"membership","kind":"insert_remote","key":"member/<k>/3/removed/<w1>/2",…}
                    {"sub":"5e0d…","seq":311,"store":"records","kind":"closed",…}
                    {"sub":"5e0d…","seq":312,"store":"membership","kind":"sync_finished",…}
```

**Rejected alternatives:**

- One channel registered under both stores
  - **Pros:** one order across the two stores.
  - **Cons:** a burst on the record store drops membership events with it, and dropping the record store removes it from a channel that stays open, so `closed` needs an event of its own the store does not have.
- A subscription per store, opened by the consumer
  - **Cons:** two streams, two numberings and two HTTP responses per node for what every consumer reads together.
- A numbering per hop
  - **Cons:** a record renumbered by a host hides a loss between the runtime and that host; one numbering at the source exposes a loss on every hop after it.
- `t` taken in the live actor when the event is produced
  - **Cons:** a timestamp field on every event of the store's; `plan.md` fixes `t` as when the host observed the event. The runtime's task takes each event within a scheduling delay of the live actor, which is what the latency computed from `content_ready`'s `t` adds.
- Stamping and numbering when the consumer reads
  - **Cons:** a consumer that reads late — a response behind a slow coordinator — moves `t` to the read, and the load test's latencies then measure the consumer.
- The buffer as a bounded channel
  - **Cons:** its slots are allocated when it is created, so every subscription holds the memory of a 100,000-record catch-up from its first record.

### D6. The record listing is the record view, entry by entry, with what arrived

`RecordEntry` gains the entry's content hash and its length, both set whether or not the payload has arrived; its presence stays what the record view judges by. `pdn-node` gains, behind `test-util`, the record listing of one hosted identity's record store of one pod: for every entry the record view holds, its key, its author, the content hash, the length, whether the payload is present, the payload when it is, and the verdict — `counted`, `not_yet`, `for_nothing` or `outside_layout` — with the reason a verdict other than `counted` names (`payload`, `actor_chain`, `author_not_actor_device` and the rest of `Awaiting` and `ForNothing`, in snake case). It refuses where the record view does: an identity that holds no record store of the pod, a tombstone included. Like every pod read it starts no session. In JSON the payload is base64 (standard alphabet).

**Example:** the phone's listing at the end of a run, one entry per row.

| `key` | `author` | `hash` | `len` | `present` | `verdict` |
|---|---|---|---|---|---|
| `by/<w3>/immutable-document/<a>/1` | w3's device | `8c1d…` | 256 | true, with its payload | `counted` |
| `by/<w3>/immutable-document/<b>/1` | w3's device | `2b77…` | 256 | false | `not_yet`, `payload` |
| `by/<w3>/immutable-document/<a>/1` | an author no statement of w3 lists | `e04f…` | 256 | true, with its payload | `for_nothing`, `author_not_actor_device` |

The second is "content lost" to the reliability test. The third shares the first's key: the record store holds one entry per key and author, so the listing is a list of entries and a key can appear more than once.

**Rejected alternatives:**

- The listing as a map from key to entry
  - **Cons:** two entries under one key — a forged one beside the real one, or one record from two devices of its member — leave one of them out, and the reliability test cannot see the one it is missing.
- The verdict alone, with no reason
  - **Cons:** an `uncounted` finding then names a verdict without saying what the entry waits for, and every such finding needs a rerun to diagnose.

### D7. The laptop host serves the 3 calls behind a feature, and streams have their own bound

`pdn-node-http` gains a cargo feature `observation = ["pdn-node/test-util"]`, off by default. With it, and with `PDN_DEBUG` on, 3 routes exist: an event route that opens the subscription of one hosted identity to one pod and answers `200` with `content-type: application/x-ndjson`, writing one record per line and flushing each; an observed join route that takes the invite the product's join route takes, calls the runtime's observed join (D12) and, once it has answered, answers as the event route does for the subscription it returned, with the pod id in a response header; and a listing route answering the record listing as one JSON array. A join refused or failed before its import answers the status and text the product's join route answers. The observed join's body is the event route's line for line, so the coordinator reads both with one reader and writes both to the same file of the run directory. Route names stay unpinned as the host spec says; the ones below are illustrative. Each route delegates to one runtime call. The request that opens a stream is admitted like any other and releases its permit when the headers are sent, so an open stream holds none of the 16; open streams have a bound of their own, 32, and a subscription beyond it is answered `503` without opening one. An observed join takes its place among the 32 when its request arrives, so one beyond the bound is answered `503` without joining, and it holds its request permit while the join runs, as the product's join route does. The runtime lock is held to open the subscription and not while it runs. A stream ends when the runtime stops and when the host's stop signal arrives, so the host's 5-second graceful drain is not spent waiting on streams that never end by themselves.

**Example:** the reliability test's laptop reader `r`, and a load cell's busiest node.

```
GET /debug/identities/{r}/pods/{pod}/events   → 200, a line per record, open for the run (1 of 32)
POST /debug/identities/{j}/pods/join-observed  → after the join: 200, the pod id in a header, then a line per record from seq 0 (1 of 32)
POST /debug/identities/{w1}/pods/{pod}/records → admitted by the 16-request bound, on w1's host
GET /debug/identities/{r}/pods/{pod}/listing  → 200, a JSON array, once at the end
```

Each node of either test is observed by one stream per pod it holds; a coordinator that re-subscribes after a dropped connection opens another before the host notices the first closed, and 32 leaves room for that on every stream of a node that holds up to 16 pods.

**Rejected alternatives:**

- Counting open streams against the 16 request permits
  - **Cons:** a host observed on several pods, with re-subscriptions, leaves few permits for the run's writes and joins on that host, and the test sheds its own writes as `503`.
- Server-sent events or a WebSocket
  - **Cons:** the coordinator is Python standard library; JSON Lines over one response is read line by line with `urllib` and nothing else.
- The observed join's pod id as a first line before the records
  - **Cons:** the body then differs from the event route's, and the coordinator's reader and the run directory's files each skip a line that is no record.
- The observed join answering `200` at once and streaming while the join runs
  - **Pros:** the consumer reads the catch-up while the join waits, and the runtime's buffer holds less.
  - **Cons:** a refused join then arrives inside a response already answered `200`, and the runtime's observed join answers the subscription only once the join has waited.
- A join route answering the pod, followed by the event route
  - **Cons:** the subscription opens after the joiner's first session, which is what the observed join exists to avoid.

### D8. `PDN_POD_RECONCILE_INTERVAL_SECS` sets the pod interval, in every build

The host reads `PDN_POD_RECONCILE_INTERVAL_SECS` at start, as it reads its other settings, and passes it to the spawn's `pod_reconcile_interval`. Unset keeps the runtime's default of 300 seconds; a positive whole number of seconds sets it; anything else stops the start with an error naming the variable, before any directory is touched. It is a host setting like `PDN_CONNECTIVITY`, so it is not behind the feature. The ordinary reconcile interval keeps the runtime's default of 10 seconds with no setting: it does not reach pod stores, and the phone's reset brings its node up at the same 10 seconds, so the passes over the other stores cost the same on both sides of the load comparison. The container stand's rule that nothing shortens the cadence names this setting.

**Example:**

| `PDN_POD_RECONCILE_INTERVAL_SECS` | the node's pass over each pod store |
|---|---|
| unset | 300 seconds: what the load tests measure |
| `30` | 30 seconds: the reliability test's default run, whose stall deadline is 5 times that after the last write |
| `120` | the reliability test's planted "slow safety net" |
| `0`, `-5`, `30s`, empty | the start stops: `PDN_POD_RECONCILE_INTERVAL_SECS must be a positive whole number of seconds` |

**Rejected alternatives:**

- Behind the `observation` feature
  - **Cons:** the interval is what a host chooses for its own reasons; a laptop node standing in for a phone needs it with or without observation.
- `PDN_RECONCILE_INTERVAL_SECS` beside it
  - **Cons:** the ordinary pass skips pod stores, so nothing either test measures depends on it, and the phone's reset matches the laptop's default instead.

### D9. The observation build is a release build, and every host says which build it is

The observation feature compiles in a release build and is checked there: `just check` checks `pdn-node-http` with `observation` under `--release` beside its product pass, and the stand's observation image is a release build as the stand's image is. `GET /debug/status` adds 2 lines after the node line: `profile release` or `profile debug`, from whether debug assertions are compiled in, and `observation on` or `observation off`. The stand's image builds without the feature; `ops/Dockerfile` takes a build argument `FEATURES`, empty by default, passed to both the dependency layer and the build, and `scripts/build-image.sh` takes the features to pass. The container suite builds both images and runs the observation scenarios against the second. `scripts/test-features.sh` adds `pdn-node-http/observation` and `pdn-mobile/observation` to the dev pass for an unselected run, and gives `-p pdn-node-http` and `-p pdn-mobile` their own feature, so `just test` compiles and runs the observation code.

**Example:** what each command builds, and what its status answers.

| command | `pdn-node-http` built with | `/debug/status` |
|---|---|---|
| `just check`, product pass | no feature | — |
| `just check`, release pass | `observation`, `--release` | — |
| `just test` | `observation` (and `pdn-node/test-util`), debug | `profile debug`, `observation on` |
| `just build-image` | no feature, release: the stand's image | `profile release`, `observation off` |
| the container suite | both images, release | as above, and `observation on` on the second |
| `cargo build --release -p pdn-node-http --features observation` | what the tests run on the laptop | `profile release`, `observation on` |

The coordinator refuses to measure a node whose status says `profile debug` or `observation off`.

**Rejected alternatives:**

- One image with the feature, gated by `PDN_DEBUG` alone
  - **Cons:** the image the live demos run on (container stand, "The live demos run on the stand's image") would carry the test-only runtime surface.
- The build profile in a route of its own
  - **Cons:** a second probe for what the one human-readable probe already exists to answer.

### D10. The facade's test build serves the laptop host's surface on the phone's loopback, and every build names the node's threads

`pdn-mobile` gains a feature `observation = ["pdn-node/test-util", "pdn-node-http/observation"]`. With it the facade exports 2 calls. `serve_test_surface(storage_dir, port)` starts, on the facade's runtime, an HTTP server bound to `127.0.0.1` at that port and answers it with the laptop host's debug router (`router` in `crates/pdn-node-http`: the debug routes a coordinator drives a laptop node with, and the 3 observation routes of D7) against the node that is up, beside 3 routes of the phone's own: a reset, which stops the node, deletes `storage_dir`, brings a node up on it at a reconcile interval of 10 seconds and the pod interval and the connectivity the request names (`direct`, `relays` or `product`, as `PDN_CONNECTIVITY` names them), creates one identity, and answers the identity, the node id and the build profile; the device samples (D11), answered from a sequence number on, a read from a sequence number releasing the samples up to it; and the clock, answering the device's wall clock in microseconds. The server outlives a reset, and while no node is up a route that needs one answers `503`. `report_device_sample(json)` hands the server one sample of the native module's (D11), which the samples route answers unread. A record reaches the coordinator as the laptop host writes it — the same router, the same serde type, the same bytes — so the observation path on the phone is the laptop's, and no record crosses into JavaScript. Refusals answer the laptop host's error table. `pdn-sdk` builds a test artifact with the feature on request, in the release configuration a release is built in; it is named as a test build and never published as a release. Only that artifact links `pdn-node-http`; what ships keeps its host dependency pointing toward the runtime alone.

In every build, the test build and what ships alike, `PdnNode::new` names the threads of its asynchronous runtime with the prefix `pdn-node` (`thread_name` on the runtime's builder, which names the worker threads and the blocking threads both), so the native module's sampler tells the node's threads from the application's (D11). A name changes nothing the runtime does, and one runtime in every build keeps the load test measuring the threads a device runs.

**Example:** the phone's surface brought up and driven over the cable; route names are illustrative, as the host spec leaves them unpinned.

```
phone, native module at launch:  serveTestSurface(dir, 3011)          127.0.0.1:3011 on the phone
laptop:                          iproxy -u <udid> 3311:3011           the laptop's 127.0.0.1:3311 → the phone's 127.0.0.1:3011 over usbmux
coordinator → 127.0.0.1:3311:    POST /debug/agent/reset {"pod_interval_secs":300,"connectivity":"direct"}
                                   ← {"identity":"…","node":"…","profile":"release"}
                                 POST /debug/identities/{me}/pods/join-observed   (w1's invite)
                                   ← 200, the pod id in a header, a line per record from seq 0
                                 GET  /debug/agent/samples?after=41   ← the samples from 42 on
                                 GET  /debug/agent/clock              ← {"t":1790000044051200}
```

**Rejected alternatives:**

- The 3 observation calls exported through uniffi, read by an agent in JavaScript
  - **Cons:** every record crosses into JavaScript on the cores the node runs on, and the phone's observation path is then not the laptop's, so the load comparison measures the path beside the device.
- A surface of the phone's own, written beside the laptop host's
  - **Cons:** a second implementation of the routes the coordinator reads, and the 2 drift apart.
- The pod interval and the connectivity as parameters of the shipped `bring_up`
  - **Cons:** changes the product's surface, which `mobile-host-surface` has not archived, for values the product keeps at the runtime's default and at its own connectivity.
- Naming the threads in the test build only
  - **Cons:** a runtime built one way for the tests and another for devices, for a name that changes nothing else.

### D11. The application's test build serves the test surface over the cable, in the release configuration, and the release build nothing of it

`pdn-app` gains a build variant of its own for the tests, built in the release configuration. It links the facade's test artifact and holds the agent; the release variant links a release of `pdn-sdk` and contains no agent code. The agent is a screen showing the run id, the surface's port and the agent's state, and nothing else, and it stays still so the screens add no CPU of their own. A native module reads the launch environment — the run id and the port, set by `xcrun devicectl device process launch` — and, with both present, starts the facade's test surface (D10) on the application's node directory and that port; a launch without them starts nothing. The coordinator reaches the surface over the device's cable: `iproxy` forwards a port of the laptop through usbmux to the phone's loopback, so nothing on the phone listens on the local network, the records and the samples never cross the Wi-Fi the measured sync uses, and the coordinator keeps control of the phone while its Wi-Fi path is cut. While the launch lasts the native module sets `isIdleTimerDisabled`, so the device neither locks nor dims during a run. Once a second the native module samples the process and hands the sample to the facade (D10): the user and system CPU time of the whole process from `getrusage(RUSAGE_SELF)`; the user and system CPU time of the node's threads, listed with `task_threads` and read with `thread_info` per thread, a thread counting as the node's when its name starts with the facade's prefix `pdn-node` or is the store's `sync-actor`, each thread's change since the previous sample added to a running total so a thread that exits between samples takes at most its last second with it; the process's resident memory (`phys_footprint` from `task_info`); `ProcessInfo.thermalState`; whether Low Power Mode is on (`isLowPowerModeEnabled`); the battery's state and level (`UIDevice.batteryState`, `batteryLevel`); and the application's state. Every change of the application's state (`active`, `inactive`, `background`) is handed over as it happens, as a sample of its own. The test surface's server runs on the facade's runtime, so its work counts in the node's share, as the laptop host's server counts in a laptop node's process; the process total less the node's share is the application's own work — the screen and the sampler — and any thread no one named, and the observation's cost is measured on the phone as on the laptop, with an open stream and without one (`load.md`). A sample window in which the application was not `active` throughout is invalid for measurement, and the coordinator marks the cell it falls in. The coordinator drives the phone's node through the surface's routes as it drives a laptop node's, and reads the clock route over the cable for the phone's clock offset.

**Example:** the coordinator's requests through the tunnel in one catch-up cell, and a sample.

| request | what the phone does |
|---|---|
| the act route, `leave` | leaves the pod, so no identity whose node is reset stays a member |
| reset, pod interval 300, `direct` | stops the node, deletes its directory, brings a node up, creates one identity; answers the identity, the node id and `release` |
| the observed join route, on w1's invite | joins through the observed join (D12) and streams the records from `seq` 0 |
| the listing route | answers the record listing |
| the samples route, after the last sample read | answers the samples taken since |
| the clock route | answers the device's clock at once |

`{"seq":42,"sample":{"kind":"cpu","t":1790000044051000,"cpu_user_us":81234000,"cpu_sys_us":10422000,"node_cpu_user_us":70110000,"node_cpu_sys_us":9802000,"resident_bytes":182452224,"thermal":"nominal","low_power":false,"battery":"charging","battery_level":0.81,"app_state":"active"}}`

**Rejected alternatives:**

- The agent as the coordinator's HTTP client over the local network, forwarding the records it reads
  - **Cons:** the records cross the Wi-Fi the measured sync uses — a 100,000-record catch-up forwards an `insert_remote` of about 500 bytes and a `content_ready` of about 240 for each record, some 70 MB beside its 26 MB of payloads — and each record crosses into JavaScript on the cores the node runs on.
- The surface listening on the local network
  - **Cons:** any device on the network reaches a server that resets the node, and its traffic shares the measured Wi-Fi.
- The server on a runtime of its own, apart from the node's threads
  - **Pros:** the node's share would hold the node's work alone.
  - **Cons:** the laptop node's process holds its server's work, so the two sides of the load comparison would count different things.
- A runtime switch in the release build
  - **Cons:** the agent's code and the test-only facade would ship to every device, off only by a value.
- The test build in the debug configuration
  - **Cons:** the store's debug build is several times slower, so every number the load test compares would describe a build no device runs.
- The whole process's CPU alone, less the idle workload's per cell
  - **Cons:** the application's own work and the threads no one named then count as the node's, and on the laptop no such work shares the node's process.
- The node's threads alone
  - **Cons:** the application's own work is then unreported, and a phone whose application outgrows the node cannot be told from one whose node is slow.
- The store's actor thread renamed to the facade's prefix
  - **Cons:** a divergence in `pdn-store` for a name the sampler can list beside the prefix.

### D12. An observed join opens the subscription between the import and the start of sync

`pdn-node` gains, behind `test-util`, `Runtime::join_pod_observed_for_test(identity, invite)`. It runs the join dialogue as `join` does, imports both stores, opens the subscription of that identity to the pod (D5) before either store's sync starts, then starts both stores' sync and waits as `join` does, and answers the pod together with the open subscription. In `data-layer` an observed variant of `import_pod` registers and tracks both stores as `import_pod` does and starts each store with its ordered subscription attached to the start (D1), returning both subscriptions beside the catch-up; on a pod already held, or on a tombstone's record store, a store whose sync already runs gets the ordered subscription a caller takes alone. A catch-up that outlasts the join's wait leaves the pod recorded, as `join` does, and the call answers the pod and the subscription with it, the catch-up going on in the stream; a join refused or failed before the import answers as `join` answers and opens nothing. The join's acts and their order are `join`'s, so the observed join arranges nothing the product's join does not: only the moment the observation starts moves. The laptop host serves it as a route (D7), and the phone's test surface serves the same route (D10). The load test's catch-up workload reads the catch-up from the joiner's records, from its first insert to the last `content_ready`.

**Example:** a catch-up at V = 10,000 whose first record-store session carries 6,000 records before the join returns at 9 seconds, and the rest by 15 seconds.

| join | what the load test sees |
|---|---|
| the observed join | every insert and `content_ready` from 0 seconds; the end at the last `content_ready`, about 15 seconds |
| the product's join, then a subscription | no record of the first 6,000; the end only at a listing that holds 10,000 |

Whether a joiner's first session is reported is no access matter: no party gains or loses a store by it. The scenario that makes the observed join fail when broken is the product's join followed by a subscription, which misses the first session's inserts; the access denial beside it is a join refused on a consumed invite, which opens no subscription.

**Rejected alternatives:**

- The catch-up's end taken from the record listing polled after the join returns
  - **Cons:** each poll rebuilds the whole record view, which at 100,000 records is load on the measured node that `load.md` excludes, and the end is only as precise as the polling.
- The observed join answering the subscription before it waits
  - **Pros:** the consumer reads while the join waits, and the runtime's buffer holds less.
  - **Cons:** a caller then learns of a failed catch-up from somewhere other than the call, and the join then waits differently from `join`.
- A subscription the store opens on a replica before the live sync holds it open
  - **Cons:** the refusal of a subscription that would report nothing is lost for every caller, to serve one that knows its start follows.

## Operating conditions

- **Several identities on one node — changes the outcome, bounded.** A subscription addresses one hosted identity's stores of one pod, and each identity has its own engine, so records never mix identities; an identity that holds no store of the pod is refused (scenario). A session event names the counterpart node, not its member, which is a stated limit: 2 members on one writer node are one `peer`. A session between 2 members of one node runs in process, carries no session id and names the node itself as `peer` on both sides (scenario); it is no network session, and the reliability test does not pair it.
- **One device or several; a device linking before, during or after — does not change the outcome.** A sibling's session appears with the sibling's node as its `peer`, and an entry that arrived from a sibling names it in `from`; the records report both as they are.
- **The connection is unstable — changes the outcome.** A dropped event stream loses the records until the coordinator subscribes again with a new `sub`, and the tests count the gap. A dropped observed join loses the catch-up's records the same way, and a new subscription cannot recover the joiner's first session; the cell then lacks its catch-up from the stream and the record listing still says what the joiner holds. On the phone the stream runs through the cable's tunnel; a dropped tunnel ends the stream as a dropped connection ends a laptop node's, and the coordinator subscribes again.
- **The disk fills — does not change the observation's outcome.** The observation writes nothing on either host; the node's own failure to store is what the tests measure.
- **The process ends without warning; the device restarts — changes the outcome.** A subscription does not survive the process: the coordinator relaunches the application over the cable, opens its tunnel again and subscribes anew with a new `sub`, and records produced between the kill and the new subscription are not reported (scenario).
- **A member is removed or leaves — changes the outcome.** The record store is dropped, its stream yields `closed`, and the membership store's stream goes on (scenario). A pod joined again is observed by a new subscription.
- **The application leaves the active state — changes the outcome on the phone.** The native module keeps the idle timer off while the launch lasts, so the device does not lock on its own; any window in which the application was not `active` is invalid for measurement, told by the state on every sample and every reported change (scenarios).
- **A write to several places is not atomic — does not apply.** The observation writes nothing.
- **Clocks disagree — does not change the outcome.** Every time in a record is on the clock of the node that produced it; the reliability test's classification compares no 2 devices' clocks, and both tests use cross-device offsets for latency only.
- **Capabilities move — does not apply.** A pod's stores are held whole by every member, with no grant to narrow or widen; the change of membership that matters is the removal above.

## Risks / Trade-offs

- [The ordered subscription diverges from upstream iroh-docs] → recorded in the store crate's `CLAUDE.md` and `UPSTREAM.md`; an upstream patch touching `live::Event` or the live actor's replica-event handling is adapted.
- [The live actor clones each insert for ordered subscribers] → only for a namespace that has one, which no product build opens.
- [The runtime's buffer holds a slow consumer's records in the node's memory] → a record is a few hundred bytes, so a buffer near its bound of 262,144 holds tens of megabytes of the phone's memory, and only while the consumer is behind; the coordinator reads each stream as it arrives, over loopback from a laptop node and over the cable from the phone, and a consumer that keeps pace on average empties the buffer before the end of a workload, when the load test reads the resident size.
- [A 100,000-record catch-up outruns the buffer behind a consumer that never catches up] → the loss is a counted `lagged`, and the record listing at the end still states what the joiner holds.
- [The session id relies on iroh exporting keying material] → iroh 1.x exposes it on `Connection`; if an upgrade drops it, the event carries no id and the test falls back to pairing in order, with the 2 cases D3 lists against it undetermined.
- [`t` includes the wait between the live actor and the runtime's task] → a scheduling delay, since the task drains the store's channel as it fills; the consumer's pace does not reach `t`.
- [The phone's node CPU leaves out a thread no one named] → a thread a library starts without the facade's prefix counts in the remainder, so the observation's reported cost is an upper bound; the node's own runtime, its blocking threads and the store's actor are all named.
- [The runtime's numbering task counts as the node's CPU] → it runs on the facade's runtime, so its work per record is in the node's share on the phone, as it is in the laptop node's process; it is the same work on both sides of the comparison.
- [A test build of the application that leaks] → its surface listens on the phone's loopback alone, reached over a cable from the machine the phone is attached to, and resets its node on request; it is built on request, installed on named devices, and published nowhere.
- [usbmux reaching a socket bound to the phone's loopback is unproven here] → the network spike (task 3.1) opens the tunnel to a test server on the phone before the rest of group 3 is built on it.
- [The test artifact links the laptop host's router] → only the test artifact does; what ships keeps its host dependency toward the runtime alone, as the laptop host's spec states.

## Open Questions

- How the contradiction with `mobile-host-surface` is written down: a qualifier added in that change before it archives, or MODIFIED deltas here after it has. Either keeps what ships unchanged; the person approving this change chooses.
