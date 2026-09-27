# Proposal: unclassified-connection-bounds

## Why

A stranger who knows only a node's address can make the node spend memory without bound. No credential, identity, or ticket is needed: the endpoint accepts a connection from any key, iroh's router dispatches on ALPN before anything classifies the caller, and `accept_session` in pdn-store's `net.rs` holds the connection for up to 300 seconds (`SYNC_SESSION_TIMEOUT`) while it waits for a first message that may never come. The memory is spent before any handler has read a byte that would say who is calling.

Two levers stand before classification, and they multiply.

The first is what one connection buffers. The endpoint takes iroh's default transport configuration: a caller may open 100 bidirectional and 100 unidirectional streams at once, each with a receive window of 1,250,000 bytes, and the connection as a whole has no receive window at all (`VarInt::MAX`). The transport creates a stream when its first frame arrives and buffers that stream's data until the application reads it, whether or not the application ever accepts the stream. The sync handler accepts one bidirectional stream, so bytes sent on the other 199 sit in the transport's buffers for as long as the connection lives, and the product comes to 248,750,000 bytes, about 237 MiB, for a single connection. iroh documents the same worst case on its own configuration: memory use is proportional to the number of streams times the stream receive window, bounded above by the connection's receive window.

The second is the number of connections. Beyond what the transport buffers, each connection whose first message is still incomplete holds up to 32 KiB of the node's own buffer (`MAX_OPENING_FRAME`) for up to 300 seconds, and nothing limits how many connections one peer opens, so both figures multiply by a number the caller chooses.

Buffered bytes show up as resident memory one for one. Measured against a running node on the first message, before that message had a ceiling of its own: a message announced at 1 GiB grew the receiving node's resident memory in step with the bytes that arrived, about 523 MiB for 512 MiB sent, and the node answered nothing while the message was still incomplete. The first message now has its ceiling; the transport's buffers behind it do not.

Under [defect-reachability](../../specs/code-practices/defect-reachability.md) both levers are reachable over the network: the rule names the timing and number of a modified node's connections among the things it sends, and memory spent without bound as a denial of service. That obliges a fix. One option under each question below instead amends that rule, and choosing it is part of this change.

## What Changes

Nothing is decided. The change settles two questions — how much one connection may buffer before the node has read anything from it, and how many connections a node holds before it has classified them — and then specifies and builds the answer. The options for each are listed under Open Questions, and none of them is chosen.

## Open Questions

### How much one connection may buffer

`Endpoint::builder` takes a `QuicTransportConfig`, so every number below is one call in `bind_endpoint`. The first three combine; the question is which of them the node sets and to what value, and each trades against throughput, because a window smaller than what a link carries in one round trip caps that link's throughput.

- A connection receive window. `receive_window` bounds the bytes buffered across all streams of one connection at once, and it is `VarInt::MAX` today, which is what makes the product above unbounded rather than merely large. One number covers every protocol on the endpoint.
- A lower stream count, `max_concurrent_bidi_streams` and `max_concurrent_uni_streams`. This bounds the same product from the other side. The protocols on this endpoint open streams of their own — iroh-blobs opens a bidirectional stream per request, iroh-gossip a unidirectional stream per send — so a number below what they need stalls them, and each protocol's need is measured before one is chosen.
- A lower `stream_receive_window` than the default 1,250,000 bytes. The same trade, per stream rather than per connection.
- The defaults stay, and the memory an unclassified caller makes the node spend is recorded as accepted. This amends defect-reachability, which counts the number of a modified node's connections among its levers, and the amendment covers every later finding of the same kind.

### How many connections a node holds before it has classified them

- A count the node keeps and enforces where a connection enters. iroh's endpoint builder carries no connection limit: `ServerConfigBuilder::set_max_incoming` bounds only the connections waiting to be accepted, not the established ones, and it is reachable through `Incoming::accept_with`, which iroh's `Router` does not call. So a limit on established connections means either the node runs its own accept loop in place of the router, or the protocol handler counts what it already holds and closes a connection past the limit. An `Incoming` knows the remote address and not the remote node id, since the id arrives with the handshake, so a limit before the handshake is per address and a limit per remote node is enforced only once a handler holds a `Connection`.
- A budget for the first message shorter than the session's 300 seconds, since an honest first message follows right after the stream opens. This shortens how long each connection is held, not how many there are, and the budget has to survive an unstable connection.
- The count is left to the transport, once a connection's own buffer is bounded. What the node's own code holds per connection before classification, 32 KiB, is then of the same order as the transport's state for that connection, and the number of connections is the transport's to bound. This amends defect-reachability in the same way.

The two questions are not independent in one direction: the third option here rests on the first question having bounded what one connection buffers, because 237 MiB per connection is not of the order of 32 KiB. Answering the first question does not by itself answer the second — an unbounded count of cheap connections is still an unbounded sum.

## Operating conditions

Four conditions change the outcome of any option. Several identities on one node share one endpoint, so every honest device and counterparty of every hosted identity dials the same node, and the number of connections a node legitimately holds is the floor under any limit. A device with little memory is where the bound matters most, and any number has to be sized for it. An unstable connection stretches the arrival of an honest message and makes an honest peer redial, so a bound on time has to allow for the first and a bound on count for the second. A restart plays no part: nothing a connection holds survives it.

## Out of Scope

- The size of the messages a session reads after its first. That is the subject of the sync-resource-bounds change, and it concerns a caller the node has already classified and allowed.
- The ceiling on the first message and the bound on key length. Both are in place, in the [node assembly](../../specs/components/mee-pdn/data-layer/node-assembly/spec.md) and [capability-gated ingest](../../specs/components/mee-pdn/data-layer/capability-gated-ingest/spec.md) specs.
- The storage a peer the node syncs with makes it spend by publishing entries. Those are the peer's own writes, replicated by design, and the cells change records the platform's stance for a cell's members.
- The message ceilings and timeouts of the pairing and linking ceremonies, 64 KiB and 15 seconds for pairing establishment. They register on the same endpoint and are reachable by a stranger, so they share the transport configuration this change settles and they are counted by any limit on connections, but their own bounds stand.

## Capabilities

None is settled. Every option touches `components/mee-pdn/data-layer/node-assembly`, where the endpoint is bound and where the ceiling on the first message already stands; an amendment touches `specs/code-practices/defect-reachability.md`.

## Impact

- **`crates/data-layer`**: `bind_endpoint` and the router assembly in `src/node.rs`, and `SpawnOptions` if a value becomes a host's to set.
- **`crates/pdn-store`**: `protocol.rs`, if a connection is counted and closed in the handler, and `metrics.rs` for the count.
- **`specs/code-practices/defect-reachability.md`**: if an option amends it.
