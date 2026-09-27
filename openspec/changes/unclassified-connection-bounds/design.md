## Context

The node serves blobs, gossip, docs, pairing and linking on one iroh endpoint, assembled by `bind_endpoint` and `SyncNode::spawn_with` in data-layer's `node.rs`. iroh's `Router` dispatches on ALPN, so a connection from an unknown key reaches its handler with nothing known about the caller but its node id. pdn-store's `accept_session` then reads the first message under a 32 KiB ceiling and a 300 second timeout, and a stranger that sends a valid Init spawns a task in `running_sync_accept` that holds the connection for the rest of that budget.

What iroh 1.1 exposes decides which options are open. `Endpoint::builder` takes a `QuicTransportConfig`, so `receive_window`, `stream_receive_window`, `max_concurrent_bidi_streams` and `max_concurrent_uni_streams` are the node's to set and are left at their defaults today. There is no connection limit on the builder. `ServerConfigBuilder::set_max_incoming` bounds only the connections waiting to be accepted, and it is applied through `Incoming::accept_with`, which the `Router` does not call — the router accepts every incoming connection it is handed. An `Incoming` carries the remote address, not the remote node id, so anything enforced before the handshake is per address.

The protocols on the endpoint open streams of their own: iroh-blobs a bidirectional stream per request, iroh-gossip a unidirectional stream per send. Any number set on the transport configuration applies to them as well as to sync.

The `running_sync_connect` and `download_tasks` JoinSets are node-initiated — a stranger cannot trigger them.

## Goals / Non-Goals

**Goals:**
- Bound the memory a stranger can make the node spend before classification, both per connection and in total.
- Keep every bound sized for a node that hosts several identities and serves all their devices and counterparties at once.
- Preserve the 300 second bound on the exchange as a whole, which covers a first sync of a large store over a slow link.

**Non-Goals:**
- The size of the messages a classified session reads after its first (the sync-resource-bounds change).
- The ceiling on the first message, in place at 32 KiB.
- The message ceilings and timeouts of the pairing and linking ceremonies, which carry their own.

## Open question: how much one connection may buffer

Nothing is decided. The options are in the proposal; what follows is the recommendation the change carries into the decision.

Set `receive_window` on the endpoint's transport configuration, and leave the stream count and the per-stream window alone until a measurement says otherwise.

- It replaces an unbounded product with one number, and that number is the whole of what a stranger makes the node hold per connection.
- It costs no honest peer its data: a receive window paces a sender and never drops or aborts an exchange. A lower stream count instead makes a peer wait for a stream slot, and blobs and gossip are the callers that would wait.
- It bounds the buffer where the buffer is, by the transport's own limit on the transport's own memory, rather than compensating for it afterwards in a handler.
- The value is not guessed. A window below what a link carries in one round trip caps that link's throughput, so it is chosen against the largest blob transfer the product expects and checked on a high-latency path.

Leaving the defaults is the weakest of the four. It keeps the change small and inside its scope, and pays for that with the whole exposure the proposal measures; it is worth taking only if a measurement shows the throughput a bound costs is worth more than the memory it saves.

## Open question: how many connections a node holds before it has classified them

A count per remote node id, kept by the protocol handler and enforced by closing a connection past the limit, with any node-wide ceiling set high enough that honest peers never meet it.

- A per-remote limit bounds one stranger and touches nobody else. A node-wide limit alone does not: a stranger that fills the table shuts out every honest peer, which is the denial of service the bound exists to prevent, arriving by another door.
- The node already holds these connections in one place, the `running_sync_accept` JoinSet, so a node-wide ceiling is its length and a per-remote limit is a count beside it.
- It costs the handshake and the transport state of one connection before the limit applies, which is why it pairs with the first question rather than replacing it.
- Running the node's own accept loop in place of iroh's `Router` would enforce a limit earlier, per address, at the cost of owning code iroh maintains. It is worth taking only if a measurement shows a stranger can exhaust the node through handshakes alone.
- Leaving the count to the transport rests on a connection being cheap, which holds only once the first question is answered, and even then the sum over an unbounded count is unbounded. The argument for it has to be about the transport's own accounting, not about 32 KiB.

## Operating conditions

- **Several identities on one node.** Every honest device and counterparty of every hosted identity dials the same endpoint, so the floor under a node-wide limit is the sum across identities, not a per-identity figure. A per-remote limit is unaffected by the count of identities, which is part of why it is recommended.
- **One device or several.** A counterparty with several devices opens a connection from each, so a per-remote limit is per device and a per-identity reading of it would be wrong.
- **An unstable connection.** An honest peer redials after a drop, and the connection it left behind is closed by the transport later than the redial arrives, so a per-remote limit needs room for more than one connection per device.
- **A device with little memory.** The number that bounds a connection's buffer is sized here, and a device that cannot afford the default product is the reason the bound exists.
- **A restart.** Plays no part: nothing a connection holds survives it, and a limit is rebuilt from the connections that are open.

## Risks / Trade-offs

- A receive window sized for a fast link still bounds nothing useful on a small device, and one sized for a small device slows blob transfer everywhere. A single number for every device is the risk; a value per storage profile is the fallback if measurement shows one number cannot serve both.
- A per-remote limit that is too tight blocks a legitimate peer that reconnects rapidly over an unstable link.
- Counting in the handler leaves the handshake unbounded, so a stranger that opens connections and never sends an Init is bounded only by what the transport spends per connection.
