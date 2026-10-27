# Design: bounded-payload-downloads

## Context

An engine's live actor turns every payload it wants into a download at once. A remote insert whose sender holds the payload calls `start_download`, which registers the sender in `hash_providers` and calls `queue_download`; that asks the blob store whether the payload is whole (`blobs().status`), and if not, hands iroh-blobs' `Downloader` a request naming every registered provider (`ProviderNodes`) and spawns a task into `download_tasks` that awaits it. The downloader runs one task of its own per request, takes a connection from a pool of iroh-util's, and asks the providers one after another. A request is answered on a bidirectional stream, and a provider grants each connection 100 of those, the transport's default, which `bind_endpoint` in the data layer leaves as it is while it sets the unidirectional count to 4,096.

The payloads wanted and not yet fetched live in two places: `queued_hashes`, the payloads with a running download, and `missing_hashes`, the payloads parked because the entry's sender lacked them or a download failed. `PendingContentReady` is emitted for a namespace once `queued_hashes` holds nothing of it after a session's end. A download that fails toward a gossip neighbor is tried again by a series per namespace and payload (`unreached_downloads`, `retry_unreached_download`), 1 second after the failure and doubling to 16 seconds for 2 minutes, as the reconciliation sessions spec requires; a provider registered while a download runs is reached by retrying the download once after it fails (`retry_after_failure`). The end of a session asks its peer for every parked payload of the namespace and registers it for every queued one, each through `queue_download` and its blob store call. A leave clears the parked payloads and the retry series of the namespace and leaves running downloads to finish.

The proposal gives the measurements; the specs give the two requirements.

## Goals / Non-Goals

**Goals:**

- What a waiting payload costs does not depend on how many payloads wait toward the same provider beyond its limit: a queue entry, and no task.
- No download waits on its provider without a bound in time, and the only provider of a payload is asked again.
- A session's end costs the live actor's loop no blob store call per payload that already waits.
- Toward one provider, a catch-up proceeds as fast as it does now.

**Non-Goals:**

- Faster catch-ups than 100 requests in flight toward a provider allow.
- Which nodes are registered as a payload's providers, and when a payload leaves that map.
- The order of the live actor's loop.

## Decisions

### D1. The limit is the stream count the endpoint grants, one constant

An engine has at most as many fetches in flight toward one provider as the node's endpoint grants a connection bidirectional streams: 100. The data layer holds the count as one constant, sets it on its transport in `bind_endpoint` beside the unidirectional count, and hands it to pdn-store's builder; the store's own default, which its tests' endpoints run on, is the transport's default, 100, and a test sets a lower one through the builder. Neither the host nor the running node changes it. For small payloads a provider then answers at most the limit divided by one request's time: the load test measured a request at about 15 ms between a laptop and a phone over Wi-Fi and 34 ms at the median between processes on one loaded laptop.

**Example:** what 100 fetches in flight toward one provider deliver of small payloads.

| link | one request | payloads per second toward one provider |
|---|---|---|
| a phone over Wi-Fi | 15 ms | about 6,600 |
| processes on one loaded laptop | 34 ms | about 2,900 |
| a cellular link | 100 ms | about 1,000 |

**Rejected alternatives:**

- A parameter of the host, in `SpawnOptions`
  - **Cons:** a host knows neither the round trips nor the providers at spawn; a value above the stream count holds memory in the transport, and one below it loses throughput
- A limit adjusted at runtime from measured round trips
  - **Cons:** the ceiling is the provider's stream count, which the fixed limit already reaches; a measured input makes the tests depend on timing
- One limit for the whole engine
  - **Cons:** a provider that answers nothing fills it, and every pod of the identity waits
- A lower fixed number, 32, the number iroh-blobs' downloader runs in parallel for one request it splits
  - **Cons:** 32 requests of 15 ms deliver about 2,100 payloads a second, below the 2,500 to 3,200 the phone reached over Wi-Fi in the load test

### D2. The live actor fetches through a pool, in tasks it owns

The engine keeps a connection pool, iroh-blobs' re-export of iroh-util's (`iroh_blobs::util::connection_pool`, with iroh-util-001 fixed), and fetches a payload from one chosen provider with `Store::remote().execute_get` over a stream it opens itself on a connection the pool hands out: iroh-blobs reports a stream that fails to open as a failure of the local store (iroh-blobs-007), and a connection the provider closed is the provider's failure. The fetch's future runs inside the task the live actor spawns into `download_tasks`, so dropping that task closes the request's stream and returns it to the provider's count. The fetch first asks the local store what it holds and requests only what is missing, off the live actor's loop: a payload another identity of the node fetched meanwhile completes at once and is reported as an insert that finds its payload whole is, with no `ContentReady`. A fetch iroh-blobs reports done asks the local store again and has landed only when the store holds the payload whole, since iroh-blobs drops a failure of the store's last write (iroh-blobs-008). `Engine::spawn` takes the limit in place of a `Downloader`, and `ProviderNodes` goes. The pool runs on iroh-util's default options but one: attempts to connect are bounded only as connections are, as in iroh-util 0.6.0, since an attempt the pool turns away fails as a connect does, and a provider that is no gossip neighbor is dropped for it.

**Example:** a3's fetch of payload P from Bob's phone b1, which accepts the request and sends nothing.

| t | the fetch task | b1's connection |
|---|---|---|
| 0 s | opens a stream and sends the request | 1 of 100 streams taken |
| 10 s | dropped by the live actor | the stream is reset; 0 of 100 taken |

**Rejected alternatives:**

- iroh-blobs' `Downloader`, with one provider per request
  - **Cons:** the downloader's own task notices a dropped receiver only at its next progress message, which a silent provider never causes, so the stream and the task stay
- The `Downloader` with a timeout around the handle
  - **Cons:** the same: the timeout drops only the receiving side

### D3. A queue per provider, each pair queued once

Every provider registered for a wanted payload has a first-in, first-out queue of the payloads it holds. Registering a provider for a payload appends the payload to that provider's queue unless the pair was registered before, so each pair of payload and provider enters a queue once while the payload is wanted. Whenever a provider has room and is not paused, it takes the next payload from its own queue, and drops from it a payload that is no longer wanted or already in flight toward another provider; a payload is in flight toward one provider at a time. A fetch that fails or is dropped puts its payload back at the end of the queue of every provider registered for it. `queued_hashes` keeps every wanted payload in flight or waiting, so `PendingContentReady` keeps its meaning. A leave removes the namespace from the payloads it wanted, and a payload no namespace wants any more is skipped when its turn comes. Every step is linear in the pairs registered and the fetches that failed.

**Example:** payloads P1, P2 and P3 wanted on a3; Alice's laptop a1 holds all three and b1 holds P2 and P3; the limit is 1 for the example.

| step | a1's queue | b1's queue | in flight |
|---|---|---|---|
| a1 registered | P1 P2 P3 | | P1 from a1 |
| b1 registered | P2 P3 | P2 P3 | P1 from a1, P2 from b1 |
| P1 arrives | P2 P3 | P3 | P3 from a1, P2 from b1: a1 skips P2, which is in flight |
| P2 and P3 arrive | | | nothing; b1 finds P3 no longer wanted |

**Rejected alternatives:**

- One queue for the engine, searched for a payload whose provider has room
  - **Cons:** a search past payloads whose providers are full costs a pass over the queue per fetch started, quadratic over a catch-up
- Payloads of live writes ahead of a catch-up's
  - **Cons:** no measurement asks for it, and the store has no rule that tells a live write's entry from a catch-up's

### D4. A fetch with no progress for 10 seconds is dropped

The fetch task reads the fetch's progress and drops the fetch when 10 seconds pass with no progress message. A request answered at all produces progress within one round trip, and 10 seconds is above a connect, at most 1 second in the pool, plus several round trips over the slowest path a node uses, and below the 15 seconds after which the transport abandons a path that went quiet. A dropped fetch keeps the bytes already written, so the payload's next fetch, from whichever provider, asks only for the rest.

**Example:** a3 fetches a 4 MiB payload from a1 over a link that carries 100 KiB a second and then pauses 12 seconds while the phone changes networks.

| t | progress on a3 | the fetch |
|---|---|---|
| 0 s to 20 s | 2 MiB | runs |
| 20 s to 30 s | none | dropped at 30 s; a1 pauses |
| 31 s | | the probe asks a1 for the remaining 2 MiB |

**Rejected alternatives:**

- A deadline on the whole fetch
  - **Cons:** a large payload over a slow link takes longer than any fixed bound while making progress the whole time
- A deadline scaled by the payload's size
  - **Cons:** it needs an assumed rate for every link

### D5. A provider that stalled pauses and is probed

A provider whose fetch was dropped, or whose connect failed while it is a gossip neighbor, starts a series of pauses: 1 second, each further one twice the one before up to 16 seconds, for at most 2 minutes from the first. During a pause no fetch goes to it; after each pause one fetch probes it, and a fetch from it that succeeds ends the series and gives it back its whole limit. The payload whose fetch was dropped goes back to the queue of every provider registered for it (D3), so a second provider takes it as soon as it has room and the only provider is asked for it again after its pause. A series that runs out empties the provider's queue: a payload no other provider holds is parked and waits for a session's end to register a provider again. A connect failure toward a provider that is no neighbor empties its queue in the same way, with no series, and a request such a provider fails once connected drops that one payload from it. One series per provider replaces the series per namespace and payload, `unreached_downloads`, and `retry_after_failure` goes, since a provider registered during a fetch has the payload in its own queue already; the reconciliation sessions spec's rule for a download toward a neighbor holds for a download that fails to connect, loses its connection or makes no progress, with a success from that provider ending its series and a try due after a leave fetching nothing for the left namespace. A provider's answer that it lacks a payload, whole or in part, drops that one payload from it, a neighbor as any other: a session's end registers its peer for every waiting payload without knowing which it holds, and a pause for each such answer would hold back the payloads it does hold. A fetch that fails on the node's own blob store parks its payload and starts no series, and so does one iroh-blobs reports done whose payload the store does not hold whole. The series is a plain structure that takes the time as an argument, so its tests set the time and run in no time.

**Example:** b1 accepts a3's request for payload P and answers nothing; a1, which holds P too, finishes a session with a3 at 5 s.

| t | b1 | a1 | a3 |
|---|---|---|---|
| 0 s | gets the request for P | | P in flight toward b1 |
| 5 s | | registered for P | P is in flight toward b1, so a1 drops it from its queue |
| 10 s | pauses for 1 s | asked for P | drops P's fetch from b1; P goes back to the queues of a1 and b1 |
| 10 s and a round trip | | answers | P arrives; b1's queue entry for P is dropped when its turn comes |
| 11 s | probed with the next payload in its queue, if one waits | | |

**Rejected alternatives:**

- Leave the provider for that payload
  - **Cons:** a payload whose only provider stalled once waits for the next session's end, up to a pod pass of 300 seconds away
- Ask the same provider again at once
  - **Cons:** a provider that answers nothing then holds the payload in turns of 10 seconds for as long as it stays connected, and takes a stream each turn
- The whole limit after each pause
  - **Cons:** up to 100 payloads wait out another 10 seconds at every pause of a silent provider; with one probe, one payload does

### D6. A session's end registers its peer without asking the blob store

The end of a session registers its peer for every payload of the namespace that is queued or parked, which appends the payload to the peer's queue when the pair is new and does nothing otherwise; the blob store is asked about a payload only by its fetch, off the loop. A payload that became whole through another route is found whole by its fetch, which then ends at once, with no `ContentReady`, as an insert that finds its payload whole reports none.

**Example:** a session between a3 and a1 ends while 19,000 payloads of "Family" wait, all of them queued toward a1 already.

| | as it stands | with this decision |
|---|---|---|
| blob store calls in the live actor's loop | 19,000 | none |
| queue entries added | | none: every pair is registered |

## Operating conditions

Several identities on one node change the outcome in one way: the identities share the node's blob store, so a payload one identity fetched completes another identity's fetch of it at once (D2), and each identity's engine keeps its own pool, queues and limit, a provider serving two identities of the node holding a connection for each. An unstable connection is D4's case: a fetch that stops for 10 seconds is dropped and resumed from the bytes written. A disk that fills changes which side is blamed: a fetch failing on the local store parks its payload and starts no series (D5), one whose transfer iroh-blobs reports done among them (D2). A device that restarts loses the queues and the series, which live in memory; the content scan at a namespace's first start parks what is missing, as it does now, and the first session's end registers its peer. A membership that moves changes which namespaces want a payload: a leave removes the namespace from them, and a payload no namespace wants is not fetched (D3). Clocks that disagree or step back change nothing: the deadline and the pauses are measured on the monotonic clock. Linking, one device or several, change nothing.

## Risks / Trade-offs

- [A provider that grants more streams than 100, a node of another build] → the engine uses 100 of them; every node of the platform builds its endpoint from the same constant.
- [A fetch dropped on a link that stalls for 10 seconds and recovers] → the probe after a pause of 1 second resumes it from the bytes written; the payload loses about 11 seconds.
- [A live write's payload waits behind a catch-up's queue toward the same provider] → it waits as long as it does now inside the transport, behind the same requests; no order is added.
- [The pool's connect timeout, 1 second, on a slow path] → as now: the downloader's pool used the same default; a connect that fails toward a neighbor starts a series.
- [More of pdn-store diverges from iroh-docs, whose engine drives iroh-blobs' downloader] → the store is the platform's own and its upstream pass reads the downloader's changes as it reads iroh-docs'.

## Measurements

A replica joins a namespace of 100,000 entries, each with a payload of its own, from one provider; both nodes run in one process on memory stores, a release build on an Apple M4 Max with 16 cores, and the figure is the peak growth of the process's resident memory from the join until the last payload arrived. With the provider answering at once over loopback, a fetch ends as fast as the entries arrive and no download waits, and the code before and after the change grow alike. With the provider answering every request 50 ms late, as a link of that round trip does, downloads wait: before the change one per payload still missing, after it 100 at a time.

**Example:** the same catch-up before and after the change.

| provider | before: memory grown | before: catch-up | after: memory grown | after: catch-up |
|---|---|---|---|---|
| answers at once | 493 MiB | 6.5 s | 495 MiB | 6.5 s |
| answers 50 ms late | 1,279 MiB | 134 s | 514 MiB | 56 s |

The memory the catch-up keeps after the change is the payloads in the joining node's memory store, the entries and the sessions; the 765 MiB it saves at 50 ms are about 8 KiB for each of the 100,000 payloads. The catch-up is faster too: 100 requests of 50 ms deliver 2,000 payloads a second, about what the 56 seconds show, while before the change 100,000 downloads competed for the provider's 100 streams.
