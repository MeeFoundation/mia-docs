# Proposal: sync-resource-bounds

## Why

A node reads the first message of an accepted sync session under a ceiling of 32 KiB (`MAX_OPENING_FRAME` in pdn-store's codec), before anything classifies the caller, and refuses a longer one on its length prefix ([node assembly](../../specs/components/mee-pdn/data-layer/node-assembly/spec.md)). Every later message of the session is read under `MAX_MESSAGE_SIZE`, 1 GiB, and the reader holds a message whole in its buffer until the last byte has arrived. The buffer grows with the bytes that arrive and reserves nothing in advance, so the memory a message costs is what its sender chooses to send, up to that ceiling.

Only a caller the node has classified and allowed reaches those later messages: a device of the identity itself, a counterparty's device serving or reading a replica under a grant or the connection metadata store of that connection, and every member device of a cell. A node that dials a peer reads the peer's answers under the same ceiling, so a peer the node chooses to sync with holds the same lever in the other direction.

The ceiling cannot simply come down. The reconciliation does not split a message by size: when one side of a first sync holds nothing, the other side sends every entry of the range in one message, so an honest message grows with the replica it carries. A lower ceiling alone would stop the first sync of every replica larger than it.

**Example:** Bob's phone b1 (read grant on Alice's store) in a session with her laptop a1; a frame is a 4-byte big-endian length prefix, then the body.

| frame | length prefix | a1 |
|---|---|---|
| the `Init` | `00 00 80 01` (32,769) | refuses it on the prefix: `MAX_OPENING_FRAME` is 32,768 |
| a later frame | `00 2A B9 80` (2,800,000) | reads it whole: about a first sync of 10,000 entries in one message |
| a later frame | `40 00 00 00` (1,073,741,824) | holds every byte that arrives and answers nothing, until the last byte or the session's 300 s (`SYNC_SESSION_TIMEOUT`) run out |
| a later frame | `40 00 00 01` (1,073,741,825) | refuses it on the prefix: `MAX_MESSAGE_SIZE` is 1,073,741,824 |

Measured against a running node on the first message, before that message had a ceiling of its own: a message announced at 1 GiB grew the receiving node's resident memory in step with the bytes that arrived, about 523 MiB for 512 MiB sent, and the node answered nothing while the message was still incomplete. Later messages go through the same reader.

Under [defect-reachability](../../specs/code-practices/defect-reachability.md) the lever is reachable over the network: the rule names a modified node's sync sessions and their messages among the things it sends, and memory spent without bound as a denial of service. That obliges a fix. One option instead amends that rule, and choosing it is part of this change.

## What Changes

Nothing is decided. The change settles how large a message a session holds after its first, and then specifies and builds the answer. The options are listed under Open Questions, and none of them is chosen.

## Open Questions

### How large a message a session holds after its first

- The reconciliation splits its messages by size, so no honest message passes a bound of a few MiB, and the session ceiling comes down to that bound. This changes the fork's reconciliation, and a first sync of a large replica takes more messages.
- A node-wide budget for the bytes held in unfinished messages, across every session of every hosted identity, past which a session is aborted. This bounds the sum without touching the reconciliation, but an honest large first sync can be aborted while other sessions are in flight, and the budget has to be sized for each kind of device.
- The ceiling stays at 1 GiB, and the memory a classified caller makes the node spend is recorded as inside the trust boundary, the stance the platform takes for a cell, whose every member is trusted with the storage it fills. This amends defect-reachability, which counts the messages of sync sessions among a modified node's levers, and the amendment covers every later finding of the same kind.

**Example:** b1 announces a later frame at 1,073,741,824 bytes; beside it runs an honest first sync of a replica of 100,000 entries, about 28,000,000 bytes in one message today.

| option | b1's frame | the honest first sync |
|---|---|---|
| messages split, ceiling down (4 MiB as a sample bound) | refused on its prefix | at least 7 messages of up to 4 MiB each |
| a node-wide budget | held until the bytes in unfinished messages across the node reach the budget, then its session is aborted | one message of 28,000,000 bytes, aborted if it and the sessions beside it pass the budget |
| the ceiling stays, recorded as inside the trust boundary | held, up to 1,073,741,824 bytes for up to 300 s | one message of 28,000,000 bytes |

Whichever option is taken applies to both directions of a session: the answers a dialed peer sends are read under the same ceiling as the messages of a caller.

## Operating conditions

Three conditions change the outcome of any option. Several identities on one node share one process, so a bound per session multiplies by the sessions of every hosted identity. A device with little memory is where the bound matters most, and any budget has to be sized for it. An unstable connection stretches the arrival of an honest message, and any bound on time has to allow for it. A restart plays no part: nothing a session holds survives it.

## Out of Scope

- What a connection costs before the node has classified its caller: the number of connections a node holds and the bytes the transport buffers for each. That is the subject of the unclassified-connection-bounds change.
- The ceiling on the first message and the bound on key length. Both are in place, in the [node assembly](../../specs/components/mee-pdn/data-layer/node-assembly/spec.md) and [capability-gated ingest](../../specs/components/mee-pdn/data-layer/capability-gated-ingest/spec.md) specs.
- The storage a peer the node syncs with makes it spend by publishing entries. Those are the peer's own writes, replicated by design, and a cell trusts every member with the storage it fills.

## Capabilities

None is settled. Every option touches `components/mee-pdn/data-layer/node-assembly`, where the ceiling on the first message stands; splitting messages touches the reconciliation as well. The amendment touches `specs/code-practices/defect-reachability.md`.

## Impact

- **`crates/pdn-store`**: the session ceiling in `net/codec.rs`, and the assembly of reconciliation messages in `ranger.rs` if messages are split.
- **`specs/code-practices/defect-reachability.md`**: if an option amends it.
