# Proposal: hash-providers-bound

## Why

Every engine of pdn-store keeps a map from a payload's hash to the nodes known to hold it, `holders` of `Fetches` in `src/engine/live/fetches.rs`, and a payload the engine wants is queued for fetching at every node the map names. The map has no bound and loses nothing: `Fetches::register` adds the node to the hash's set before it checks anything, and no path removes a hash — not a finished fetch, not a leave of the replica, which stops wanting that namespace's payloads and leaves the map alone, since it is keyed by hash alone. It lives as long as the engine, which is as long as the node hosts the identity.

A node is registered for a remote insert whose sender holds the payload, at the end of a session for every payload parked or waiting, for what the content scan after a restart finds missing, and for every `Op::ContentReady` a gossip neighbor sends. The last needs no entry at all: the receive loop hands the announcement to the live actor, `register_provider` registers its sender for the hash it names, and with the hash neither waiting nor parked nothing is fetched. The threat model places in a pod's swarm a holder of its tickets that is no member, a removed member above all, so such a device grows the map of every member's node it is a neighbor of, by one hash per message, while those nodes store and download nothing. Gossip relays a message sent to the whole swarm, and the receive loop handles it whatever its scope, so one such message reaches every member's node in the swarm, each registering the node that delivered it.

**Example:** Bob's phone b1, removed from "Family", stays in the record store's swarm and sends Alice's laptop a1 `Op::ContentReady` messages, each naming a fresh hash.

| b1 sends | a1 downloads | a1's map holds afterwards |
|---|---|---|
| one message of a few dozen bytes | nothing: no entry of a1's names the hash | one more hash of 32 bytes, beside a set of its own holding b1's node id, 32 bytes |
| 1,000 messages a second for an hour | nothing | 3,600,000 more hashes, until the node restarts |

Honest use grows the map too, without bound over the node's uptime: every hash registered stays in it after its download, and after the pod is left.

Under defect-reachability the defect is reachable over the network: a modified node's gossip makes an honest node spend memory without bound. That obliges a fix.

## What Changes

Nothing is decided. The change settles what the map holds and when a hash leaves it, and then specifies and builds the answer. The options are listed under Open Questions, and none of them is chosen.

## Open Questions

### What the map holds

- Providers of wanted content only. An announcement registers its sender only for a hash queued for download or parked, as the other registrations name only hashes that an entry the replica stored wants, and a hash leaves the map when its fetch succeeds and when no replica of the engine wants it any more, after a leave or a drop. The map is then bounded by the content the replicas lack, which only entries that an admitted session stored put there. An announcement that comes before the entry it belongs to is forgotten, and the entry's payload then waits for a session with a node that holds it, or for another announcement.
- A bound with eviction: past a fixed count of hashes, the least recently used goes. Memory is bounded by the count; a stream of fresh hashes evicts the honest ones, and a download then knows only the provider its own trigger registered.
- Wanted content as in the first option, and announcements for content not yet wanted kept apart, a bounded number per neighbor, which a hash consults when it is parked. An early announcement is kept as long as its neighbor's list keeps it, and the memory is bounded by the neighbors the swarm gives a node, times the length of the list.

**Example:** b1's 3,600,000 messages, and then Carol's laptop c1 announces payload P, which it has downloaded, before a1 receives P's entry from Alice's tablet a3, which does not hold P yet.

| option | a1's map after b1's messages | P on a1 |
|---|---|---|
| the map as it stands | 3,600,000 more hashes | fetched from c1 when the session with a3 ends: c1 is registered by its announcement |
| wanted content only | no hash of b1's | parked until a session with a node holding P ends, or until another node announces P |
| a bound of 10,000 hashes | 10,000 hashes, all b1's | as under wanted content only, if b1's messages after c1's announcement evicted it; fetched from c1 otherwise |
| early announcements kept apart, 64 per neighbor | 64 hashes of b1's | fetched from c1 when the session with a3 ends, as long as c1 announced fewer than 64 hashes after P |

## Operating conditions

Several identities on one node multiply the growth: each identity's engine keeps a map of its own, so a node whose identities share a swarm with b1 grows a map for each of them, and a bound per engine multiplies by the identities the node hosts. A membership that moves is the case itself: a removed member's device that does not leave the swarm keeps sending. A restart empties every map, which is why the growth lasts until the node restarts and no longer. Linking, an unstable connection, a disk that fills and clocks leave the outcome as it is: the map is in memory and keyed by hash alone.

## Out of Scope

- The time each announcement costs the live actor's loop, which the live-actor-loop-priority change weighs.
- What a removed member's device learns and fetches from the announcements in the swarm, which the blob-egress-gate change weighs.

## Capabilities

None is settled. Whichever option is taken touches `crates/pdn-store` alone. No spec states what a neighbor's `ContentReady` makes a node do; the change writes that requirement if it puts one in the spec tree, and the threat model's section on payloads, which names what a removed member's device in the swarm learns from these announcements, gains what it can make a node hold.

## Impact

- **`crates/pdn-store`**: `Fetches` in `src/engine/live/fetches.rs` — its `holders`, `register` and `unwant` — and `register_provider`, `leave` and `end_retries_toward` in `src/engine/live.rs`.
