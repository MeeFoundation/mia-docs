# Proposal: bounded-payload-downloads

## Why

An engine of pdn-store starts a download for every payload it lacks the moment the entry naming it arrives (`queue_download` in `src/engine/live.rs`, through iroh-blobs' `Downloader`), so a catch-up of a pod's records starts one download per record at once. Each download that waits costs about 10 KiB: measured against iroh-blobs' downloader with downloads waiting on one provider, 10,000 of them grew the process's resident memory by 101 MiB and 100,000 by 976 MiB. The waiting buys nothing: a provider grants each connection 100 bidirectional streams, the transport's default, and iroh-blobs opens one stream per request, so at most 100 downloads toward one provider proceed at once and the rest wait inside the transport. Downloads wait whenever they end slower than the entries arrive, which every link but loopback brings about: a replica joining a namespace of 100,000 entries from a provider answering 50 ms late grew its process by 1,279 MiB, 765 MiB of it the waiting downloads, which a phone does not survive; under defect-reachability a host reaches it through the public surface of pdn-node, by joining, which obliges a fix.

A download also has no bound in time. iroh-blobs' downloader asks the providers of a payload one after another and moves on only when one fails, and a provider that accepts the request and sends nothing never fails: iroh's keep-alive, every 5 seconds, keeps the connection open, so the download waits for as long as the provider stays connected. A provider registered later by a finished session does not help, since a running download is not started again. A modified node does this by answering nothing; an honest node does it when its blob store hangs. Under defect-reachability a modified node stalling an honest one through what it sends is fixed without exception.

The end of every session pays for the waiting too: it registers its peer for each payload still waiting by asking the blob store about that payload, once per payload, inside the live actor's loop (`on_sync_finished`).

**Example:** Alice's tablet a3 joins "Family", a pod of 100,000 records whose payloads Alice's laptop a1 and Bob's phone b1 hold; b1 accepts every blob request and answers none.

| | as it stands | with this change |
|---|---|---|
| downloads a3 holds while the entries arrive | one per payload still missing, up to 100,000, about 10 KiB each | at most 100 toward a1 and 100 toward b1; every other payload waits as a queue entry |
| a payload whose download went to b1 first | never arrives | handed to a1 10 s after its download stopped making progress |
| blob store calls at the end of each session | one per payload still waiting | none for a payload already waiting |

## What Changes

- The live actor fetches each payload itself, from one provider it chooses, through a connection pool and iroh-blobs' `fetch`, in a task it owns, so dropping the task cancels the request and frees its stream. iroh-blobs' `Downloader` and the store's `ProviderNodes` discovery go.
- At most 100 fetches toward one provider are in flight per engine: the number of bidirectional streams the node's endpoint grants a connection. The data layer sets that count on its transport explicitly, from one constant, and hands the same constant to the store's builder. It is no host parameter and is not adjusted at runtime.
- Every other wanted payload waits in a queue per provider that holds it; a provider with room takes the next payload from its own queue, and each pair of payload and provider is queued once while the payload is wanted.
- A fetch with no progress for 10 seconds is dropped. The payload stays queued at its other providers and goes to the back of the stalled provider's queue; the stalled provider pauses for 1 second, each further pause twice the one before up to 16 seconds, for at most 2 minutes, and after each pause one fetch probes it, a success restoring its limit. A provider that is the payload's only one is therefore tried again rather than left.
- The end of a session queues its peer for the namespace's waiting payloads without a blob store call per payload.
- A test reproduces the silent provider against the code as it stands before the fix, and `components/mee-pdn/iroh-defects.md` records it as iroh-blobs-006.

## Operating conditions

Several identities on one node: each identity's engine keeps its own pool, queues and limit, and a provider that serves two identities of one node holds a connection for each, with streams of its own. An unstable connection: a phone that changes networks stalls its fetches; each is dropped after 10 seconds and fetched again from the bytes already stored, since a fetch asks only for what the store lacks. A restart: the queues live in memory; the content scan at a namespace's first start parks what is missing, as it does now, and the first session queues it. A disk that fills: a fetch that fails on the local store's write parks its payload and pauses no provider. A membership that moves: a removed member's device can still be registered as a provider, and what it sends is checked against the payload's hash; who is registered stays as it is. Clocks and linking leave the outcome as it is.

## Out of Scope

- What the map of a payload's providers holds, and when a payload leaves it.
- The transport's stream counts and windows: the bidirectional count stays 100, and this change only names it once.
- Where finished downloads sit in the live actor's loop: first, as they are.
- Several payloads in one request, iroh-blobs' `GetMany`, which shares one round trip among many payloads: the lever for links where 100 fetches toward one provider prove too slow.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `components/mee-pdn/data-layer/reconciliation-sessions`: two requirements are added — payload downloads toward one provider are bounded and the rest wait in a queue, and a download that makes no progress is handed on while its provider pauses and is probed.

## Impact

- **`crates/pdn-store`**: `src/engine/live.rs` — `queue_download`, `start_download`, `on_download_ready`, `on_sync_finished`, `on_content_scanned`, the `RetryDownload` message, `retry_unreached_download`, `end_retries_toward`, `QueuedHashes`; `ProviderNodes` goes. `Engine::spawn` in `src/engine.rs` and the builder in `src/protocol.rs` take the limit in place of a `Downloader`; the pool runs on iroh-util's default options.
- **`crates/data-layer`**: `bind_endpoint` in `src/node.rs` sets the bidirectional stream count from the constant it hands the store's builder.
- **Tests**: the store's test node gains a blob handler that counts its streams and one that answers nothing; `connections_past_a_hundred_toward_a_silent_peer_all_end` in `tests/sync.rs` drives the pool the engine now uses.
- **Docs**: `crates/pdn-store/CLAUDE.md`, `components/mee-pdn/iroh-defects.md`.
