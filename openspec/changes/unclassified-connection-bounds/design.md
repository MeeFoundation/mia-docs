## Context

The node serves blobs, gossip, docs, pairing and linking on one iroh endpoint, assembled by `bind_endpoint` and `SyncNode::spawn_with` in data-layer's `node.rs`. iroh's `Router` dispatches on ALPN, so a connection from an unknown key reaches its handler with nothing known about the caller but its node id. The router runs each connection's handler in a task of its own, and in that task pdn-store's `accept_session` reads the first message under a 32 KiB ceiling and a 300 second timeout; the node keeps no count of these tasks. A first message naming an identity the node does not host is refused in the same task (`refuse_session`). One naming a hosted identity is handed to that identity's engine and spawned in its `running_sync_accept` JoinSet — one per hosted identity — which serves or refuses it (`handle_session`). Either way the node then waits for the caller to close its side, for up to another 300 seconds.

What iroh 1.1 exposes decides which options are open. `Endpoint::builder` takes a `QuicTransportConfig`, so `receive_window`, `stream_receive_window`, `max_concurrent_bidi_streams` and `max_concurrent_uni_streams` are the node's to set and are left at their defaults today. There is no connection limit on the builder. `ServerConfigBuilder::set_max_incoming` bounds only the connections waiting to be accepted, and it is applied through `Incoming::accept_with`, which the `Router` does not call. Two hooks stand before any handler instead. `RouterBuilder::incoming_filter` decides on every `Incoming` before the TLS handshake — accept, refuse, ignore, or ask for a retry — and an `Incoming` on a direct path carries the caller's IP address and nothing else that names it, so anything enforced there is per address. `EndpointHooks::after_handshake`, installed on the endpoint builder, sees the remote node id and the ALPN of every connection, of every protocol, and can close one before its handler runs.

A node id names a caller without costing it anything: it is a key the caller makes for itself, and an endpoint bound without one makes a fresh key, as `bind_endpoint` does for a node without a storage directory. A stranger can therefore dial under a new node id every time.

The protocols on the endpoint open streams of their own. iroh-blobs opens a bidirectional stream per request. iroh-gossip's send loop opens one unidirectional stream per topic on a connection and keeps it for all of that topic's messages until the topic disconnects, and pdn-store gossips one topic per namespace, so two nodes hold one such stream in each direction for every namespace whose gossip passes between them. The send loop writes its messages in order: when a stream count stops it in `open_uni`, it sends that peer nothing on any topic, and once its queue of 64 messages is full, the node's gossip actor waits with it, for every peer. Any number set on the transport configuration applies to these protocols as well as to sync.

The `running_sync_connect` and `download_tasks` JoinSets are node-initiated — a stranger cannot trigger them.

## Goals / Non-Goals

**Goals:**
- Bound the memory a stranger can make the node spend before classification, both per connection and in total.
- Keep every bound sized for a node that hosts several identities and serves all their devices and counterparties at once.
- Preserve the 300 second bound on the exchange as a whole, which covers a first sync of a large store over a slow link.

**Non-Goals:**
- The size of the messages a classified session reads after its first (the sync-resource-bounds change).
- The ceiling on the first message, in place at 32 KiB.
- The serving halves of the pairing and linking ceremonies, `PairingHandler::serve` and `LinkingHandler::serve`, which a stranger reaches on the same endpoint. Each reads its request under a 64 KiB ceiling but waits in `accept_bi` and `read_message` with no timeout, since the 15 second `ESTABLISHMENT_DIALOGUE_TIMEOUT` bounds only the pairing scanner's dialogue, so a stranger's quiet connection there is held for as long as iroh's keep-alive keeps it open. The count this design recommends, kept in the sync handler, does not see those connections; the gap stays open outside this change.

## Open question: how much one connection may buffer

Nothing is decided. The options are in the proposal; what follows is the recommendation the change carries into the decision.

Set `receive_window` on the endpoint's transport configuration, and leave the stream count and the per-stream window alone until a measurement says otherwise.

- It replaces an unbounded product with one number, and that number is the whole of what a stranger makes the node hold per connection.
- It costs no honest peer its data: a receive window paces a sender and never drops or aborts an exchange. A lower stream count instead makes a blob request wait for a stream slot, and it caps the namespaces two nodes gossip about: a gossip stream stays open for as long as its namespace is shared, so its slot does not come back, and a sender past the count stops gossiping to that peer altogether.
- It bounds the buffer where the buffer is, by the transport's own limit on the transport's own memory, rather than compensating for it afterwards in a handler.
- The value is not guessed. A window below what a link carries in one round trip caps that link's throughput, so it is chosen against the largest blob transfer the product expects and checked on a high-latency path.

Leaving the defaults is the weakest of the four. It keeps the change small and inside its scope, and pays for that with the whole exposure the proposal measures; it is worth taking only if a measurement shows the throughput a bound costs is worth more than the memory it saves.

**Example:** Bob's phone b1 fetches a 100,000,000-byte blob from Alice's laptop a1 on one stream over a 300 ms round trip, while Carol (outsider) holds a connection to a1 full. The proposal's sample settings, the same on both nodes.

| option | Carol's connection holds | b1's blob takes at least |
|---|---|---|
| `receive_window` 12,500,000 (recommended) | 12,500,000 | 24 s: its one stream is paced by the stream window, 1,250,000 bytes a round trip |
| 5 bidirectional and 5 unidirectional streams | 11,250,000 | 24 s, and a sixth concurrent request of b1's waits for a stream slot |
| `stream_receive_window` 62,500 | 12,437,500 | 480 s |
| the defaults | 248,750,000 | 24 s |

## Open question: how many connections a node holds before it has classified them

A ceiling across the whole node on the sync connections whose first message has not arrived, kept by the sync handler around `accept_session` and enforced by closing a connection past it, together with a first-message budget far shorter than the session's 300 seconds.

- Against a stranger only a count across the node or per address holds, since a stranger can dial under a new node id every time. A ceiling across the node bounds the memory whatever the stranger does. Its cost is that a stranger who fills it keeps honest peers from starting a session, which is the denial of service the bound exists to prevent, arriving by another door.
- The budget is what makes the ceiling expensive to fill. An honest first message follows its stream within a round trip, so the connections an honest node holds unclassified at once are few, and a short budget turns every slot over quickly: to keep a ceiling of 1,000 full, a stranger completes 100 handshakes a second, every second, under a 10 second budget, and 3.3 a second under today's 300 seconds. Neither half stands alone: without the ceiling the count is the stranger's rate times the budget, and the rate is the stranger's to choose.
- Which connection a full ceiling closes is part of the decision. Closing the new one leaves the stranger racing the budget; closing the oldest unclassified one makes it race an honest first message instead, 1,000 connections within one 300 ms round trip.
- The sync handler reads the first message, so it is the one place that knows when a connection stops counting; the router's filter and the endpoint's hook see a connection only as it enters. Counting there costs the handshake and the transport state of each connection before the ceiling applies, which is why it pairs with the first question rather than replacing it.
- A limit per address in the router's `incoming_filter` applies before any handshake and keeps iroh's `Router`. It is only as strong as an address is costly, and honest callers behind one address translator share it, so it adds to the ceiling and does not replace it.
- A limit per node id bounds only a caller that keeps its id, which a stranger does not.
- Leaving the count to the transport rests on a connection being cheap, which holds only once the first question is answered, and even then the sum over an unbounded count is unbounded. The argument for it has to be about the transport's own accounting, not about 32 KiB.

**Example:** Carol (outsider) opens 10 connections a second to a1, each under a node id she makes for it and each with an incomplete first message; Bob's phone b1 loses its link and dials a1 again. A ceiling of 1,000 and a 10 s budget are sample values; where a row names no budget, the first message has today's 300 s.

| option | held for Carol at once | b1's new connection |
|---|---|---|
| a ceiling of 1,000 across the node, with a 10 s budget (recommended) | 10 × 10 = 100, each for up to 10 s | served |
| a count per node id, with or without a ceiling across the node | 3,000, or the ceiling if lower: no id opens a second connection | refused when the ceiling is below 3,000 |
| a ceiling of 1,000 across the node alone | 1,000 after 100 s, each for up to 300 s | refused |
| a limit per address, in the router's filter | the per-address limit, before any handshake | served, unless b1 shares Carol's address |
| the count left to the transport | 10 × 300 = 3,000 | served, while a1's memory lasts |

## Operating conditions

- **Several identities on one node.** Every honest device and counterparty of every hosted identity dials the same endpoint, so the floor under a ceiling across the node is the sum across identities, not a per-identity figure. The recommended ceiling counts only connections whose first message has not arrived, so that floor is how many of them arrive within one first-message delay of each other, not how many connections the node holds.
- **One device or several.** A counterparty with several devices opens a connection from each, so the floor counts devices, not identities.
- **An unstable connection.** An honest peer redials after a drop, and a change of network can make every peer of a1 redial at once, so the floor is sized for that burst. A slow or lossy link stretches an honest first message, and the budget has to allow for it.
- **A device with little memory.** The number that bounds a connection's buffer is sized here, and a device that cannot afford the default product is the reason the bound exists.
- **A restart.** Plays no part: nothing a connection holds survives it, and a limit is rebuilt from the connections that are open.

## Risks / Trade-offs

- A receive window sized for a fast link still bounds nothing useful on a small device, and one sized for a small device slows blob transfer everywhere. A single number for every device is the risk; a value per storage profile is the fallback if measurement shows one number cannot serve both.
- A ceiling across the node can still be filled: a stranger that completes handshakes as fast as the budget frees slots keeps honest peers from starting a session for as long as it keeps going, and a shorter budget and a higher ceiling only raise what that costs it. A ceiling sized too low meets the honest burst of redials after a change of network.
- Counting in the sync handler leaves the handshake uncounted, so a stranger that starts handshakes and never completes them is bounded only by what the transport spends on each; the router's filter is where that is bounded, per address.
