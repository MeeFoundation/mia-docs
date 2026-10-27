## Context

The proposal says why the store is cut down. What shapes how:

- **The RPC layer.** `Docs` in `src/protocol.rs` owns the engine and an `RpcActor` task (`src/api/actor.rs`); `DocsApi` and `Doc` in `src/api.rs` hold an irpc client of that task. Every call becomes a request of `DocsProtocol` (`src/api/protocol.rs`), the task handles one request at a time, and each handler calls the engine and turns its error into a `serde_error::Error`. Without the `rpc` feature the client is in-process only. The task holds the engine, and a `Doc` sits inside what the engine holds — the data layer's access provider keeps a registry of every pod's `Doc` handles — so `Docs` aborts the task when its last clone drops, and a call after that fails.
- **What the data layer calls.** Of the 27 requests, the data layer sends 15: open, list, create, drop, import of a capability, set, get, delete, start sync (as `start_sync` and `sync_with_peers`), leave gossip, share (as `share` and `ticket`), subscribe, get sync peers, create an author, and get the default author. It mints write tickets alone; three of its tests mint read tickets as fixtures. It mounts `DocsDispatch` as the docs handler and protects payloads from blob collection through `Engine::collection_hashes`, never through the engine's own protect callback. No crate reads the store's metrics; two unit tests in `src/net/codec.rs` read `sync_sessions_open` and `sync_sessions_reclaimed`.
- **Configurations.** `default = ["metrics", "rpc", "fs-store"]`; `just check-store` lints all features, no features and rustdoc and builds `wasm32-unknown-unknown`; `just test-store` tests all features and no features and runs the README's doctest. Nothing else in the workspace builds for wasm: `rust-toolchain.toml` also pins `wasm32-wasip1`, which has had no user since `crates/mee-wasm` of v3-single-device went, and `mee-pdn.code-workspace` still points rust-analyzer at that generation's crates. `deny.toml` audits with `all-features = true`, its comment naming the store's wasm and migration features; besides the store's, the workspace's only features are the `test-util` of `pdn-node` and of the data layer, which gate no dependency.
- **Encodings.** A ticket encodes `Capability` with postcard, `Write` as variant 0; the namespaces table stores a capability as a kind byte, `Write = 1`, and 32 bytes. A PMS keeps the tickets of its identity's pods, so a stand node holds encoded tickets across updates.
- **Store opening.** `Store::new_impl` in `src/store/fs.rs` creates every table in a write transaction of its own, then runs migrations 001 to 004, each of which converts a store older iroh-docs releases wrote and skips one this crate wrote.
- **Upstream.** Upstream's `main` has no commit after `8cfeacb`, the newest entry of `UPSTREAM.md`, as of 2026-10-15. Its open pull requests titled as fixes include #93 (a bound on the in-memory public key cache, which `src/store/pubkeys.rs` here leaves unbounded), #94, #106, #111, #112, #114 and #88.

## Goals / Non-Goals

**Goals:**

- Every scenario of the data layer, `pdn-node` and the stand passes unchanged, and a node of this build syncs with a node of the build before it.
- A reader of the store meets only code that a crate of the workspace reaches, and the compiler keeps it that way for crate-private code.
- One configuration of the store, built, linted and tested by the workspace's own recipes.

**Non-Goals:**

- Reworking what stays: the engine, the live actor, the codec, the ranger and the store keep their behaviour, the order of the live actor's loop (D15) aside; the work removes what nothing reaches, and the one structural change is the call path of D1.
- The workspace's lints for the store, and moving the store's tests into the library.
- Renaming the crate's types (`Doc`, `DocsApi`, `Docs`) or the sync ALPN.

## Decisions

### D1. `Doc` and `DocsApi` call the engine; `Docs` alone keeps it alive

`DocsApi` and `Doc` hold a weak reference to the engine and call its methods and its sync handle directly, with what each `RpcActor` handler did now in the method body: `Doc::set_bytes` adds the payload to the blob store, inserts the entry, holds the payload's temp tag and answers the hash it wrote; a read of the entry back would be a second message to the sync actor, and a write, a delete or a drop from another task at the same key could fall between the two and change the answer. `Docs` holds the one strong reference, so the engine lives as long as some clone of `Docs` does. A call on a handle whose engine is gone fails with an error saying the store has stopped, as a call to the aborted task fails today. Calls from one task run in the order the task makes them; calls from different tasks meet first at the sync actor, which already orders every store operation by arrival. A call now runs in its caller's future, so a caller can drop it between two of its steps, and calls from other tasks can run between them; the two methods for which either changes the outcome keep their steps together. `Doc::set_bytes` hands the payload's temp tag to the engine's held payloads however the call ends, since the store inserts an entry it was sent whether or not its caller still waits. `DocsApi::drop_doc` leaves the replica and deletes it in one step of the live actor, since a start of sync taken between the two reopens the replica and fails the delete, and the delete closes every handle of the replica first, since an open another caller holds would keep it open and fail the delete too. `DocsApi::open` answers `None` for a namespace the store does not hold and an error for one it holds and cannot open, so the data layer opens a replica without walking the store's namespaces. Errors reach the caller as the engine raised them. `irpc` stays a dependency, since iroh-blobs' API answers in its types, but the store no longer defines a protocol of its own.

**Example:** the data layer's access provider holds pod "Family"'s membership `Doc` in its registry, and the engine holds the provider.

| moment | today | after this change |
|---|---|---|
| a session's accept asks the provider, which reads `member/<carol>/…` | the read waits in the identity's `RpcActor` queue behind every earlier request of every replica | the read goes to the sync actor |
| the node stops the identity and drops its `Docs` | the task is aborted, the engine drops | the last strong reference drops, the engine drops |
| a task still holding the `Doc` reads afterwards | fails: the task is gone | fails: the engine is gone |

**Rejected alternatives:**

- Keep the RPC actor, drop only the `rpc` feature
  - **Pros:** the smallest edit
  - **Cons:** about 1,900 lines whose purpose is a network RPC nobody runs; one queue per identity that every call waits in, a session's access decision included; errors flattened to their message
- `Doc` holding a strong reference to the engine
  - **Cons:** the engine holds the access provider, which holds every pod's `Doc`, so the engine never drops and its sync actor thread never joins
- The data layer holding the engine and passing a namespace to every call
  - **Cons:** rewrites every call site of the data layer to gain nothing over a handle that carries its namespace

### D2. Read capabilities go; a write capability's encodings stay byte-identical

`Capability::Read`, `CapabilityKind::Read`, `ShareMode`, the read-only refusal on insert and the merge of a read capability into a write one go. `Capability` keeps its shape as an enum with the one variant `Write`, so postcard writes the same variant index before the secret, and the namespaces table keeps the kind byte `1`; a kind byte `2` read from a file is refused as an unknown capability. No store file an earlier build wrote is carried over: stands and devices start from empty with this build, so no namespaces row of kind byte `2` exists where it runs. A store that held one would keep that replica unopenable, since a write import of a namespace the table already lists changes nothing. `Doc::share`, `Doc::ticket` and the data layer's `share_ticket` lose their mode argument.

**Example:** the bytes of a write ticket for one node with no addresses, as `test_ticket_base32` in `src/ticket.rs` pins them once it is rewritten from its read ticket onto a write one — the same before and after the change, so a ticket a PMS stored before the update decodes after it to the same namespace secret, node and identity.

```
00          # TicketWireFormat::Variant0
00          # Capability::Write, variant index 0 (a read ticket has 01 here)
20          # the secret's length, 32, as postcard writes a byte slice
<32 bytes>  # the namespace secret
01          # one node
<32 bytes>  # its node id
00          # no addresses
<32 bytes>  # the identity
```

**Rejected alternatives:**

- Keep read capabilities
  - **Cons:** a mode every caller passes as `Write`, a refusal path on every insert, and a merge rule on every import, for tickets only test fixtures mint
- `Capability` replaced by the bare namespace secret
  - **Cons:** the ticket loses its variant index, so every ticket a PMS holds stops decoding after the update and the node loses its pods, to save one enum

### D3. One configuration: no features, no wasm target

`[features]` goes. The file-backed store, `Docs::persistent` and `Store::persistent` are always built; the metrics group keeps only the two values a test reads, crate-private, and the counters nobody reads go; `noq`, `serde-error`, `cfg_aliases`, `build.rs` and the `wasm_browser` paths — the sync actor as a tokio task in the browser — go. `just check-store`, `just test-store` and the pipeline's `store` job go, `precommit-check` and `fix` stop calling them, and `rust-toolchain.toml` pins no wasm target. `just check` gains clippy on the store with warnings denied and rustdoc on it with warnings denied (D5). The tooling that described the matrix follows it: `deny.toml` keeps `all-features = true`, its comment saying that the audit covers every dependency any feature gates, whichever build enables it; the root `README.md` loses its line on the two recipes; rust-analyzer's `linkedProjects` in `mee-pdn.code-workspace` name the workspace's `Cargo.toml` alone. iroh-blobs' `fs-store` and tokio's `rt-multi-thread`, which the store's `fs-store` feature turned on, become features of the plain dependencies, the comment on why tokio's is needed kept beside them.

**Example:** the commands that compile the store before and after.

| command | before | after |
|---|---|---|
| `just check` | default features, warnings allowed | the one configuration, warnings denied, rustdoc |
| `just check-store` | 4 builds, one of them for `wasm32-unknown-unknown` | gone |
| `just test-store` | 2 nextest runs and a doctest run | gone |
| pipeline | jobs `lint-test-wasm` and `store` | jobs `lint` and `in-process-tests` |
| `rust-toolchain.toml` targets | `wasm32-wasip1`, `wasm32-unknown-unknown` | none beyond the host's |

**Rejected alternatives:**

- Keep the wasm build for a browser host
  - **Pros:** the host spec anticipates a wasm host embedding the core one day
  - **Cons:** nothing above the store builds for wasm today, so the build proves nothing a host could use; upstream's "build on wasm" commit (`bf1fc32`) shows the way when a host comes
- Drop `all-features` from `deny.toml` with the store's features
  - **Pros:** after the change no feature gates a dependency, so the audit reads the same graph without it
  - **Cons:** a dependency a later feature gates would leave the audit without anyone noticing
- Keep `fs-store` as a feature
  - **Pros:** a build without redb's file backend is smaller
  - **Cons:** no consumer builds without it, and a second configuration doubles what a change must compile

### D4. What goes, by the rule "nothing outside the store reaches it"

An item goes when no other crate of the workspace reaches it, directly or through what it calls, and only the store's own tests or its RPC layer use it. The inventory, each item checked against the data layer's calls:

| item | only users today | outcome |
|---|---|---|
| `DocsProtocol`, `RpcActor`, `DocsApi::connect`, `DocsApi::listen` | the RPC layer | gone (D1) |
| `Capability::Read`, `ShareMode` | three data-layer tests' fixtures | gone (D2) |
| `DownloadPolicy`, `FilterKind`, the `download_policy` table's reads and writes | store tests | gone; every entry's content is wanted, as the default policy says today |
| author list, import, export, delete, set default | store tests | gone; create and get default stay |
| `Doc::import_file`, `export_file`, their progress types | store tests | gone |
| `Doc::close`, `status`, `set_hash`, `get_exact`, `leave`; `DocsApi::import`, `import_and_subscribe`; `start_sync_scoped` | store tests | gone; the sync handle's `get_exact` stays for the store's own tests |
| `Query` sorting and offset | store tests | gone; the default order stays |
| migrations 001 to 004, `NAMESPACES_TABLE_V1` | stores older iroh-docs releases wrote | gone; `Store::new_impl` creates every table before them |
| `ProtectCallbackHandler`, `Builder::protect_handler`, the engine's protect task | store tests | gone; blob collection protects through `Engine::collection_hashes` |
| `impl ProtocolHandler for Docs` | store tests | gone; the store's tests mount `DocsDispatch` with a resolver of one identity |
| metrics nobody reads | none | gone (D3) |
| `README.md`, `examples/setup.rs` | the doctest, the example | gone; the crate doc is one paragraph |

What stays though only the store reaches it inside: the ranger's generic store traits and their proptest store, the default author and its file, `DocTicket`, the session hooks and dial controls ADR-0014 lists. The table is the starting point, not a ceiling: once D5 makes the rest crate-private, the compiler names whatever else nothing calls, and it goes by the same rule.

**Example:** `Doc::get_exact` — the data layer reads a single entry with `get_one(Query::key_exact(key).author(author))`, so `Doc::get_exact` goes, while the sync handle's `get_exact` stays behind `cfg(test)`: the codec's tests read what a session delivered through it.

**Rejected alternatives:**

- Keep what a future feature might want, such as download policies for large payloads
  - **Cons:** a future feature looks at upstream for its answer (D7), where this code is kept for it

### D5. The public surface is what is named outside the store's sources; the rest is crate-private and denied as dead

Every item no other crate of the workspace and no integration test of the store names becomes crate-private, unless the signature of a public item carries it: the compiler refuses a crate-private type in a public interface. `just check` lints the store with warnings denied, so a crate-private item nothing calls fails the check. A public item named only by the store's own integration tests stays public: its users are outside the library, where the compiler cannot see them, so such an item is the one place the rule holds by review.

**Example:** `filter::serve_whole`, named only by `tests/util/mod.rs`, stays public; `QueryBuilder`, named by nothing outside, stays public because `Query::all` returns it; `Engine::start_sync_keeping_default` is called only by `Doc::share` and stays crate-private; a `pub(crate) fn` whose last caller goes fails `just check` with `function ... is never used`.

**Rejected alternatives:**

- Move the integration tests into the library as unit tests
  - **Pros:** the compiler would see test-only items too
  - **Cons:** the stress default and the nightly hunt select the scenario tests by `-E 'kind(test)'`, so the store's scenarios would drop out of both, and a unit-test binary would no longer mean a deterministic test
- A `test-util` feature for test-only items
  - **Cons:** a second configuration, which D3 removes
- Keep every item public
  - **Cons:** nothing finds code nothing calls, and the crate grows back

### D6. Tests go with the code they test; tests of kept behaviour reach it the way the platform does

A test whose subject is a removed item goes with it. A test of kept behaviour stays, and where it reached that behaviour through a removed call it is rewritten onto a call the data layer makes. `tests/util.rs` moves to `tests/util/mod.rs`, so it is a module of the binaries that declare it and builds no binary of its own.

**Example:** five tests.

| test | subject | outcome |
|---|---|---|
| `test_doc_import_export` in `tests/client.rs` | file import and export | goes |
| `redb_doc_import_stress` in `tests/gc.rs` | file import into a persistent store | goes, and `tests/gc.rs` with it |
| `sync_drop_doc` in `tests/sync.rs` | a dropped replica stops syncing | stays; its `get_exact` read becomes `get_one(Query::key_exact(..).author(..))` |
| `test_replica_capability_memory` in `src/sync.rs` | a read capability refuses inserts | goes |
| `test_ticket_base32` in `src/ticket.rs` | a ticket's bytes | stays, rewritten from a read ticket onto a write one, its expected bytes taken from the build before the change |

**Rejected alternatives:**

- Keep the tests of removed code until the end of the change
  - **Cons:** they hold the removed code alive and fail the dead-code check, which is the signal the inventory relies on

### D7. The store is the platform's own; upstream gets a watch on fixes and a look per need (ADR-0016)

A new ADR-0016 records the relation. The crate no longer tracks upstream commit by commit, and no upstream patch is expected to apply. Two duties stay. At every bump of iroh, iroh-blobs or iroh-gossip in the workspace, upstream's commits since the last entry of `UPSTREAM.md` and its open pull requests titled as fixes are read; each that touches code the store still holds gets an entry with a verdict, and a defect it confirms here is fixed or recorded as a change of its own. And a change that needs the store to do something new looks at upstream first, and its design says what it found. `UPSTREAM.md` opens with these two duties and keeps its entries as the record of what the crate took. ADR-0014 changes where it says the crate carries upstream's version, records every upstream commit, and takes upstream releases that touch neither the ranger nor the session setup.

**Example:** the next bump of iroh — upstream's log from `8cfeacb` on and its open fix pull requests are read; #93, which bounds the in-memory public key cache that `src/store/pubkeys.rs` here also leaves unbounded, gets an entry, while a fix to download policies would get none, the code being gone.

**Rejected alternatives:**

- Keep tracking every upstream commit
  - **Cons:** entries for commits about code the store no longer holds — wasm, the RPC layer, download policies — are the reading this change exists to stop
- No watch at all
  - **Cons:** a fix upstream makes in the ranger, the codec or the store file, which both still share, never reaches this crate

### D8. The crate's guidance describes the crate, not its distance from upstream

`crates/pdn-store/CLAUDE.md` keeps every rule of behaviour and its reason, and loses the RPC layer, the feature flags, the wasm notes, the pre-push items for `check-store` and `test-store`, and each clause saying what upstream does instead or that an upstream patch touching the code is adapted. The root `CLAUDE.md` and `.claude/rules/pdn-store.md` lose the two recipes and the README doctest. Code comments that compare with upstream go unless the comparison is the reason for the code, as for `EntrySignature`.

**Example:** the subscriber rule in `crates/pdn-store/CLAUDE.md` keeps "every subscription opened through the public interface is `Lossy`, and only the live actor subscribes `Blocking`", and its reason, and loses "Upstream waits on every subscriber … an upstream patch touching `Subscribers`, `Event` or `LiveEvent` is adapted".

**Rejected alternatives:**

- Keep the comparisons as hints for the look at upstream
  - **Cons:** they are read on every visit to the crate, while a look at upstream is rare and reads upstream's code anyway

### D9. Version, documentation and attribution

The manifest carries `version = "0.1.0"`, `pdn-node`'s version, and keeps `publish = false`, upstream's license files and its `authors` entry, which the MIT and Apache licenses ask to keep with the code. `README.md` goes and `src/lib.rs` opens with one paragraph: what the crate is, that the embedder judges every session (ADR-0014), and where its guidance lives.

**Example:** `crates/pdn-store/Cargo.toml` reads `version = "0.1.0"` and `license = "MIT/Apache-2.0"`, with `LICENSE-APACHE` and `LICENSE-MIT` beside it.

### D10. The work runs in phases, the call path first

Each phase ends green under `just check` and `just test`. The last upstream pass and ADR-0016 come first, being documents. Then D1 alone, followed by a stress pass over the data layer's and `pdn-node`'s scenarios: it is the one step that changes how calls wait. Then the removals of D2 to D4 with their tests (D6), then the configuration and tooling of D3, whose `just check` denies the store's warnings, then the visibility pass of D5, which that check turns into more removals, then the guidance of D8 and D9, and a last stress pass over the same scenarios.

**Example:** a failure in the stress pass after D1 is a defect of the direct calls, diagnosed before any removal is stacked on it.

**Rejected alternatives:**

- One sweep and one stress pass at the end
  - **Cons:** a failure could come from the call path or from any removal, and has to be found among all of them

### D11. A peer that restarts with the same node id is a neighbor again at once: iroh-gossip from its main branch

The stand's kill scenario showed a node killed and started again reaching its pod's other member only at the pod's next pass, 300 s later, the scenario having absorbed it with a six-minute budget. One cause is in iroh-gossip 0.101.0: the member's node answers the restarted node's `Join` with nothing, held back by a neighbor request to that peer pending since they first met, so the restarted node announces its writes to no neighbor. Upstream fixed it on its main branch, #161, and has released nothing since. The workspace takes iroh-gossip from that branch at the fixed revision `6cbbafa865`, through `[patch.crates-io]`, until a release carries the fix; `deny.toml` admits the branch as a source. The revision also carries upstream's #178 and #191 on the connection and swarm lifecycle. The scenario's budget comes down to the convergence budget, two minutes, so the scenario fails whenever a restarted node's writes wait for a pass. The detail is in `components/mee-pdn/iroh-defects.md` and the node assembly spec.

**Example:** the kill scenario's last wait, a record Alice's node places right after its start, read on Bob's node.

| build | the wait |
|---|---|
| iroh-gossip 0.101.0, a 6 min budget | passes in 301 s, at Bob's pod pass |
| iroh-gossip 0.101.0, a 2 min budget | fails |
| the patched revision and D12, a 2 min budget | passes in 13 s |

**Rejected alternatives:**

- Wait for upstream's next release
  - **Cons:** upstream released nothing in the six weeks since 0.101.0, and the fix is a week old on its main branch; every restart of a member's device costs its writes a pass until then
- A fork of iroh-gossip carrying #161 alone
  - **Pros:** none of #178 and #191's behaviour changes
  - **Cons:** a fork to rebase onto every upstream change, for a fix upstream already holds next to the two that complete it

### D12. A peer that restarts at a new address is reached at it: a path selector of the platform's own

With D11 in place the restarted node's writes reach the other member, but their payloads do not: the member's node dials the restarted node at its old port. iroh 1.3.0's default selector keeps a selected path until one of the same tier is at least 5 ms faster by its last round-trip time, a dead path keeps the round-trip time it last measured, and on a local network nothing is 5 ms faster than that. The data layer installs `ReceivingPathSelector` (`crates/data-layer/src/path_selector.rs`) on every endpoint through iroh's `path_selector` hook: a path some connection to the peer has received on comes before one none has, then iroh's tiers, then, within a tier, the path more of the node's connections to the peer have received on, whatever their round-trip times; between paths alike in these the choice is iroh's own, its stickiness reproduced, since iroh exports its own selector to nobody. The order is one ranking, so selecting again with nothing changed keeps the path selected, and it is computed in one pass over the node's connections to the peer, as iroh's own selector is. The decision is a pure function over what the selector reads of each path, tested on its own; the stand's kill scenario tests it in place.

**Example:** Bob's node's paths to Alice's node after a kill, port 57771 before and 33947 after.

| path | connections that received on it | last round-trip time | selected |
|---|---|---|---|
| `172.18.0.2:57771` | 1 | 1.9 ms | before |
| `172.18.0.2:33947` | 3 | 0.4 ms | after |

**Rejected alternatives:**

- A fork of iroh with the fix in its selector
  - **Pros:** the fix sits where the defect is
  - **Cons:** a fork of the transport to rebase onto every iroh release, for what a hook iroh offers already carries
- Keeping the endpoint's port across restarts
  - **Pros:** no selector of our own
  - **Cons:** helps only a node that comes back at the same address; a device restarted on another network meets the same dead path

### D13. An entry whose hash and length disagree on emptiness is dropped at ingest

`validate_entry`, the one point every entry offered in a session passes, checks that the entry has the empty hash exactly when it has length 0, beside the key's length. The store judged emptiness by the hash and other readers by the length, so an entry with the empty hash and a length, which a modified node can sign, read as a deletion to one and as content to another. Such an entry is dropped like any other that fails validation, and a record read back from a store file is built without the check, since a store written before this change can hold one.

**Example:** two entries a modified member's device offers, beside a whole one.

| entry | ingest |
|---|---|
| key `whole`, the hash of "v", length 1 | stored |
| key `empty-hash-with-a-length`, the empty hash, length 5 | dropped |
| key `a-length-of-zero`, the hash of "v", length 0 | dropped |

### D14. A node stops its engines, then its router, then its blob protocol's streams, then its blob store

`SyncNode::shutdown` and a node's drop share one stop, `stop_node` in `src/node.rs`; a drop runs it in a task of its own. It shuts every hosted identity's engine down first: a running engine starts downloads, each of which reads the blob store before it fetches, and iroh-blobs answers a read reaching a file store that is shutting down by panicking on its own task. A stopped engine starts none; a download it started before stopping is not awaited, and stops at its next progress report, its writes into a store going away dropped. The router shuts its protocols down before it cancels their connections, so the node mounts the blob protocol with a shutdown that leaves the store open. The router's shutdown awaits every connection's handler, but iroh-blobs' handler runs each stream in a task of its own, which the router neither cancels nor awaits, so a request a stream read before the stop reaches the store after the router's shutdown returns. The node therefore serves the blob protocol with a handler of its own, `BlobsServing`, which runs each stream's task on a `TaskTracker`, from `tokio-util`, a dependency the data layer takes for it. Once the router's shutdown has returned, the stop closes the tracker and waits for the streams, then for the store to finish what they handed it, up to 5 seconds (`BLOB_STORE_IDLE_WAIT`): a stream ends at its next read or write on the closed endpoint, and a request at its first answer, which goes to no one, so the wait is short. Only then does it close the store and release the directory lock. The store's tests shut their node down engines first, and `content_a_restart_left_missing_is_fetched_from_the_first_sync_peer` in the store counts the panics of its process and fails on one. In the data layer's `tests/node_shutdown.rs` three tests pin the order, each failing in one run with its half removed: `a_node_stopped_with_a_fetch_under_way_stops_without_a_panic` reads the steps of the node's stop and fails when the engines stop after the blob store closes, and `a_node_stopped_while_a_peer_observes_its_payload_stops_without_a_panic` and `a_node_dropped_while_a_peer_observes_its_payload_stops_without_a_panic` hold one blob stream between the request it read and the store until the router's shutdown has returned, and meet the panic without the wait.

**Example:** the steps of `SyncNode::shutdown`.

| step | what the stop does |
|---|---|
| 1 | the reconcile pass stops |
| 2 | each identity's engine shuts down and starts no further download |
| 3 | the router shuts every protocol down, the blob protocol's shutdown leaving the store open, and awaits every connection's handler |
| 4 | the blob protocol's streams end and the blob store finishes what they handed it, up to 5 s |
| 5 | the blob store closes, and the storage lock is released |

**Rejected alternatives:**

- iroh-blobs' handler fixed in the fork to track its streams
  - **Pros:** offered upstream, it would fix every embedder of iroh-blobs
  - **Cons:** one more divergence of the fork from upstream, for what about 20 lines of the node's own handler do
- The blob store closed as soon as the router's shutdown returns
  - **Cons:** a request a stream read before the stop reaches the closed store: `a_node_stopped_while_a_peer_observes_its_payload_stops_without_a_panic`, then repeated ten stops a run, met the panic in 6 of 300 runs on a runner of 4 CPUs
- A drop that closes the blob store alone, leaving the ordered stop to `shutdown`
  - **Cons:** a runtime dropped without `shutdown` is a circumstance the public surface has to survive, and its drop then closes the store beneath a stream's read and under a running engine

### D15. The live actor takes a finished download before its inbox

`LiveActor::run_inner` in `src/engine/live.rs` polls its finished downloads first under its `biased` `select!`, above the inbox. A branch is reached only on a turn where nothing above it is ready, and under load the inbox, which carries every gossip op of every swarm the engine joined, holds a message on nearly every turn. A finished download is what makes a payload readable and announces it with `ContentReady`, so its wait is part of the content lag every member of a pod sees. The finished downloads are bounded by the downloads this actor started, so taking them first holds back nothing else for long. A load test with 16 members on one laptop, writing 20 records a second together and 10,000 in all, measured a content lag of 77 ms on the median and 141 ms at the 90th percentile on every node with this order.

**Example:** one payload download of that load test, which took 34 ms on the median: from its end to `on_download_ready`, it waited 30 ms on the median.

**Rejected alternatives:**

- Finished downloads the fifth of six branches, below the inbox and the replica events
  - **Cons:** under the same load a finished download waited 946 ms on the median and 17.7 s at the 90th percentile, and the content lag on every node was 1.0 s on the median and 17.8 s at the 90th percentile

## Operating conditions

- **A device that restarts** changes the outcome twice. A store file and the tickets a PMS holds outlive the process. And its peers still hold their connections to the process that ended, which iroh-gossip and iroh's path selector both mistake for the live peer (D11, D12); the stand's kill scenario holds both at the convergence budget. D2 keeps both encodings, and the removed migrations convert only stores this crate never wrote; `test_ticket_base32` pins the write ticket's bytes, a test of `Capability::raw` pins the kind byte `1`, and `sync_restart_node` and the data layer's persistence scenarios reopen a store file and the default author file.
- **Several identities on one node**: unchanged; `DocsDispatch` stays the one accept path, and the store's tests move onto it.
- **Callers on several tasks** — the access provider, the pass, the host's requests — no longer queue in one task per identity (D1); the risk is below.
- **One device or several, linking at any moment, an unstable connection, a disk that fills, clocks that disagree, a membership that moves**: unchanged; no removed item takes part in any of them.

## Risks / Trade-offs

- [Some caller relies on the RPC queue's order between calls from different tasks] → calls from one task keep their order; the PMS orders its own writes behind its `pending_mutations` lock; the stress pass right after D1 isolates any such defect.
- [A method whose steps the RPC actor ran as one meets a dropped caller or a call from another task between them] → `set_bytes` and `drop_doc` keep their steps together (D1), each with a test that fails when they are apart; a method added later is weighed the same way.
- [An upstream fix lands between two iroh bumps] → it waits for the next bump of iroh the workspace takes; a defect reported in public but not yet merged reaches the watch through the open pull requests it reads.
- [A browser host arrives] → the wasm build returns with it, upstream's `bf1fc32` as the reference.
- [The compiler-led removals of D5 reach further than the inventory] → each goes by the same rule, and a removal that breaks a scenario is the scenario naming a user the inventory missed.

- [iroh changes the `path_selector` hook, which it keeps outside its semantic versioning] → the selector's unit tests and the stand's kill scenario fail at the bump that changes it, which is when it is adapted.
- [The patched iroh-gossip revision behaves otherwise than 0.101.0 beyond #161: connections close once unused, a node alone rejoins] → the stress pass of the in-process scenarios and of the stand runs on it before the change lands.

## Migration Plan

No data migration: stands and devices are recreated from empty with this build, and no store file of an earlier build is carried over. Stores, tickets and the default author file keep their encodings (D2). Nodes of this build and the build before it sync with each other: no message of the store changes, and the iroh-gossip revision's stream header carries a flag byte a node on 0.101.0 reads and ignores, as upstream's `stream_header_works_across_versions` checks. Rolling back is reverting the change.
