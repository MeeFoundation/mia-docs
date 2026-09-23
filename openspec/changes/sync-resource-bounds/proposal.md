# Proposal: sync-resource-bounds

## Why

A node reads the first message of an accepted sync session under a ceiling of 32 KiB (`MAX_OPENING_FRAME` in pdn-store's codec), before anything classifies the caller, and refuses a longer one on its length prefix ([node assembly](../../specs/components/mee-pdn/data-layer/node-assembly/spec.md)). Every later message of the session is read under `MAX_MESSAGE_SIZE`, 1 GiB, and the reader holds a message whole in its buffer until the last byte has arrived. The buffer grows with the bytes that arrive and reserves nothing in advance, so the memory a message costs is what its sender chooses to send, up to that ceiling.

Only a caller the node has classified and allowed reaches those later messages: a device of the identity itself, a counterparty's device serving or reading a replica under a grant or the connection metadata store of that connection, and, in the cells change, every member of a cell. A node that dials a peer reads the peer's answers under the same ceiling, so a peer the node chooses to sync with holds the same lever in the other direction.

The ceiling cannot simply come down. The reconciliation does not split a message by size: when one side of a first sync holds nothing, the other side sends every entry of the range in one message, so an honest message grows with the replica it carries. A lower ceiling alone would stop the first sync of every replica larger than it.

Before classification the lever is the number of connections. Each connection whose first message is still incomplete holds at most 32 KiB for up to 300 seconds (`SYNC_SESSION_TIMEOUT`), and the endpoint does not limit how many incoming connections it accepts, so the memory held is what one connection holds times the number of connections a peer opens.

Measured against a running node on the first message, before that message had a ceiling of its own: a message announced at 1 GiB grew the receiving node's resident memory in step with the bytes that arrived, about 523 MiB for 512 MiB sent, and the node answered nothing while the message was still incomplete. Later messages go through the same reader.

Under [defect-reachability](../../specs/code-practices/defect-reachability.md) both levers are reachable over the network: the rule names a modified node's sync sessions and their messages, and the timing and number of its connections, among the things it sends, and memory spent without bound as a denial of service. That obliges a fix. One option under each question below instead amends that rule, and choosing it is part of this change.

## What Changes

Nothing is decided. The change settles two questions — how large a message a session holds after its first, and how many connections a node holds before it has classified them — and then specifies and builds the answer. The options for each are listed under Open Questions, and none of them is chosen.

## Open Questions

### How large a message a session holds after its first

- The reconciliation splits its messages by size, so no honest message passes a bound of a few MiB, and the session ceiling comes down to that bound. This changes the fork's reconciliation, and a first sync of a large replica takes more messages.
- A node-wide budget for the bytes held in unfinished messages, across every session of every hosted identity, past which a session is aborted. This bounds the sum without touching the reconciliation, but an honest large first sync can be aborted while other sessions are in flight, and the budget has to be sized for each kind of device.
- The ceiling stays at 1 GiB, and the memory a classified caller makes the node spend is recorded as inside the trust boundary, the stance the cells change takes for the storage a member fills. This amends defect-reachability, which counts the messages of sync sessions among a modified node's levers, and the amendment covers every later finding of the same kind.

Whichever option is taken applies to both directions of a session: the answers a dialed peer sends are read under the same ceiling as the messages of a caller.

### How many connections a node holds before it has classified them

- A limit on incoming connections, per endpoint and per remote node, in the endpoint's configuration. The node assembly exposes no such setting, and its values have to fit a node that hosts several identities and serves all their devices and counterparties at once.
- A budget for the first message shorter than the session's 300 seconds, since an honest first message follows right after the stream opens. This shortens how long each connection is held, not how many there are, and the budget has to survive an unstable connection.
- The count is left to the transport. What the node's own code holds per connection before classification, 32 KiB, is of the same order as the transport's own state for that connection, so the number of connections is the transport's to bound. This amends defect-reachability in the same way, since the rule names the number of a modified node's connections as a lever.

The two questions are independent: any answer to one combines with any answer to the other.

## Operating conditions

Three conditions change the outcome of any option. Several identities on one node share one process, so a bound per session multiplies by the sessions of every hosted identity. A device with little memory is where the bound matters most, and any budget has to be sized for it. An unstable connection stretches the arrival of an honest message, and any bound on time has to allow for it. A restart plays no part: nothing a session holds survives it.

## Out of Scope

- The ceiling on the first message and the bound on key length. Both are in place, in the [node assembly](../../specs/components/mee-pdn/data-layer/node-assembly/spec.md) and [capability-gated ingest](../../specs/components/mee-pdn/data-layer/capability-gated-ingest/spec.md) specs.
- The storage a peer the node syncs with makes it spend by publishing entries. Those are the peer's own writes, replicated by design, and the cells change records the platform's stance for a cell's members.

## Capabilities

None is settled. Every option touches `components/mee-pdn/data-layer/node-assembly`, where the ceiling on the first message stands; splitting messages touches the reconciliation as well, and an amendment touches `specs/code-practices/defect-reachability.md`.

## Impact

- **`crates/pdn-store`**: the session ceiling in `net/codec.rs`, and the assembly of reconciliation messages in `ranger.rs` if messages are split.
- **`crates/data-layer`**: the node assembly, if a limit on connections becomes part of the endpoint's configuration.
- **`specs/code-practices/defect-reachability.md`**: if an option amends it.
