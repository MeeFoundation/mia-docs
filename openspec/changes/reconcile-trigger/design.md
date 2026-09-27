# Design: reconcile-trigger

## Context

subset-rbsr puts capability-scoped peers outside the gossip swarm and makes filtered reconciliation their only data path and the sole carrier of correctness. Without a live path a scoped peer sees new claims only when it next reconciles. This change adds a reconcile trigger — a directed, content-free message that prompts a covered peer to reconcile promptly — without the side channel a broadcast tick would open. subset-rbsr's worked examples (Example 1, a personal store with sparse sharing; Example 2, coordination inside a small-or-medium business) make the cost and the side channel concrete; this design does not repeat them.

A scoped peer reconciles a replica it holds under a grant on the node's periodic reconcile pass, once every `SpawnOptions::reconcile_interval` (10 s by default), and when a read or a list of the replica starts a filtered reconciliation, which the read does not wait for (`nudge_scoped` in `crates/data-layer/src/node.rs`). Every session between two nodes runs on a connection of its own: `connect_and_sync` in `crates/pdn-store/src/net.rs` opens it with `Endpoint::connect` and drops it when the session ends. A scoped peer is outside the swarm, so between two sessions no connection joins the serving node to it, and reaching it means dialing it.

What a session reveals is judged when the session is set up: the access book reads the grant record the issuer wrote toward the session's counterparty in their connection metadata store, checks the dialing device against the device set the counterparty publishes there, and builds the egress filter from the grant's claims (`AccessBook::classify_issued` in `crates/data-layer/src/access.rs`). Nothing indexes the grants by claim.

Two identities of one node already reach each other on a write. The writer's engine sends `CoLocatedRequest::Announce { namespace, writer }` on every local insert, and `serve_co_located` hands it to `reconcile_with_co_located` in `crates/data-layer/src/node.rs`, which opens `Engine::sync_in_process` from the writer to every other identity of the node that tracks the namespace, whether its grant covers the written claim or not; the session's egress filter then withholds what the grant does not cover.

That announcement can leave a write to the periodic pass in two ways. `announcements_in_flight` drops an announcement for a pair while the pair's previous one is in flight — from the moment the node takes it up until the co-located identity has read its session's first message — and the writer froze that session's snapshot before sending the message, so a write landing in between travels only on a later session. And when an announced session finds its pair already running, the engine marks the pair for a replay once the session ends (`resync_requested` in `crates/pdn-store/src/engine/state.rs`); the replay goes through `sync_with_peer`, which dials the node's own id as the identity a contact or a running session names for it, or else as the replica's default identity — on the issuer's own namespace that is the writer itself, and `reconcile_with_co_located` never reconciles an identity with itself.

## Goals / Non-Goals

**Goals:**

- A covered write promptly prompts exactly the covered scoped peers to reconcile.
- No side channel: a scoped peer is triggered only about activity on claims it can read.

**Non-Goals:**

- Carrying correctness or confidentiality — reconciliation does that (subset-rbsr). Triggers are best-effort latency only.
- Delivering claim content — a trigger is content-free; data flows through the filtered reconciliation.

## Decisions

### D1. Directed at the covered peers, resolved from the grant records

On a write, the serving node resolves the scoped peers whose grants cover the written claim from the records its access book judges their sessions by: for each connection the issuer's identity hosts, the grant it wrote toward that counterparty and the device set the counterparty publishes. Each device of each covering counterparty is sent a content-free trigger over a connection the serving node dials for it, or, when that device is the serving node itself, as D2 describes. The trigger and the egress filter read one source, so a peer is triggered exactly when a session it opens would carry the claim. The resolution reads one grant record per connection on every write, and the access book's grant cache keeps a record decoded until its content hash changes.

A peer is a node and the identity holding the replica there, never a node alone (ADR-0013). One node may hold one issuer's namespace for two identities at once, each under its own grant, and the trigger names the covering identity — the audience the grant record names.

**Example:** Alice (issuer) writes `contact/email` on her laptop a1. Bob holds a read grant on `contact/email`, Carol one on `contact/phone`; Bob publishes the devices b1 (his phone) and t1 (the family tablet), Carol publishes t1.

| addressee (node, identity) | grant a1 wrote toward the identity | a1 sends |
|---|---|---|
| (b1, Bob) | covers `contact/email` | a trigger, on a connection it dials to b1 |
| (t1, Bob) | covers `contact/email` | a trigger naming Bob, on a connection it dials to t1 |
| (t1, Carol) | covers `contact/phone` alone | nothing |
| t1 reconciles Bob's replica alone; Carol's replica there hears nothing of the write, not even that one happened. | | |

**Rejected alternatives:**

- A broadcast tick to every scoped peer.
  - **Cons:** wakes every scoped peer on every write and shows each the issuer's whole write rate, far wider than any one peer's grant (subset-rbsr, Example 1).
- A trigger addressed to the node alone.
  - **Cons:** on a node holding the namespace for two identities, each under its own grant, it reaches the wrong replica or both.
- An index from claim to audience, kept for the trigger.
  - **Pros:** one lookup per write, whatever the number of connections.
  - **Cons:** a second copy of every grant, which each publish, narrowing and withdrawal has to update in step, or the trigger and the filter disagree.

### D2. A co-located peer is triggered by the write announcement, narrowed to the entitled

A trigger whose addressee is hosted on the sending node is the write announcement the node already raises (Context): the writer's engine sends `CoLocatedRequest::Announce`, and the node opens `Engine::sync_in_process` from the writer to the addressed identity, the way a contact naming the node's own id is reached. On a data namespace the announcement reaches the issuer and the addressees D1 resolves on this node, and no other identity that holds the namespace. A directory and a connection metadata store are read whole by every identity that holds them (Invariants 1 and 3), so a write to one still reaches each of its co-located holders. An announcement the pair cannot take at once, because its previous session is still being set up or is running, is that pair's pending trigger under D3, and it is replayed to that same pair once the session ends.

**Example:** Alice's laptop a1 hosts Alice, Bob and Erin. Bob (read grant on `contact/email`) holds her namespace on a1 and on his phone b1; Erin (read grant on `contact/phone`) holds it on a1. Alice writes `contact/email` on a1.

| addressee | its node | what a1 does |
|---|---|---|
| (a1, Bob) | a1's own endpoint id | `Announce`, then `Engine::sync_in_process` from Alice to Bob, as for a contact naming a1 |
| (a1, Erin) | a1's own endpoint id | nothing: her grant does not cover `contact/email`, so no session opens |
| (b1, Bob) | another node | dials b1 with a trigger; b1 then reconciles with a1 in a session on `/iroh-sync/1` |

**Rejected alternatives:**

- Announcing to every co-located identity that holds the namespace, as the node does today.
  - **Cons:** an identity the write does not cover takes a session on each of the issuer's writes; the session carries nothing, yet it tells that replica a write happened — the side channel D1 keeps shut between nodes.
- Dropping an announcement while the pair's previous one is in flight, as the node does today.
  - **Pros:** the rest of a batch costs no task, pipe or message through the actor's inbox.
  - **Cons:** a write landing after the writer froze that session's snapshot waits for the next periodic pass.

### D3. Coalescing

A peer holds at most one pending trigger until it reconciles; consecutive covered writes collapse into that one pending tick. So what a peer receives is bounded by its own reconciliation cadence, not the write rate (subset-rbsr, Example 2: about 100 covered writes a day become a few ticks, never a flood).

**Example:** Alice (issuer) writes three times on a1 to claims Bob's grant covers before his phone b1 reconciles.

| step | a1 | trigger for (b1, Bob) | b1 |
|---|---|---|---|
| 1 | writes `contact/email` | pending, sent to b1 | |
| 2 | writes `contact/phone` | still pending, nothing more sent | |
| 3 | writes `contact/email` again | still pending, nothing more sent | |
| 4 | | cleared | reconciles once: receives `contact/phone` and the latest `contact/email` |

### D4. Best-effort; reconciliation heals

A trigger is never required for correctness: an unreachable or missed peer is left to reconciliation-on-contact, which subset-rbsr names the sole carrier of correctness. Delivery is best-effort, so the retry policy is a latency knob, not a correctness one.

**Example:** Bob's phone b1 (read grant on `contact/email`) is offline when Alice (issuer) writes `contact/email` on a1.

| time | a1 | b1 |
|---|---|---|
| t0 | writes `contact/email`; its dial to b1 fails, and the trigger to (b1, Bob) is not delivered | offline |
| t1 | | back online |
| t2 | | its reconcile pass dials a1, as it does every `reconcile_interval` (10 s by default): receives `contact/email` |

## Risks

- An identity of the writer's node that a write does not cover still learns that the write happened, one interval late: the periodic co-located pass (`reconcile_co_located`) reconciles a pair whenever either replica's write count has moved since the pair last reconciled, covered or not, and D2 narrows only the announcement.

## Open Questions

- Transport: which message carries the trigger — a small frame on the docs ALPN, or a dedicated protocol — and how it names the addressed identity, which every transport has to carry. Either way the serving node dials the peer for each trigger it sends, and the reconciliation the trigger prompts dials back, so one prompted reconciliation costs two connections.
- Retry policy: how long to keep retrying an unreachable peer before leaving it to reconciliation-on-contact.

**Example:** Transport: a1 triggers (b1, Bob) for Alice's namespace; no connection joins the two between sessions, so a1 dials b1.

| option | a1 dials b1 on | b1 reads the trigger | a build of b1 without it |
|---|---|---|---|
| a frame on the docs ALPN | `/iroh-sync/1` | as a session's first frame, under `MAX_OPENING_FRAME` (32,768 bytes) | fails to decode the frame and closes the connection with no terminal frame |
| a dedicated protocol | an ALPN of its own, beside `/pdn/pairing/0` and `/pdn/linking/0` | with a reader and a ceiling of its own | fails the handshake: it offers no such ALPN |
