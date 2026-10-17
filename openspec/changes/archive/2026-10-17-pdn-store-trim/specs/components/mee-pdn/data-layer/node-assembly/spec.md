## ADDED Requirements

### Requirement: A peer that restarts with the same node id is a neighbor again at once
A node SHALL take a peer back into a store's swarm as soon as the peer, killed and started again with the same node id, joins that swarm again, while the node still holds the peer's previous connection open and counts the peer among its neighbors. The node's gossip SHALL answer that peer's `Join` with a `Neighbor` message, so the peer counts the node as a neighbor too and its announcements reach the node. iroh-gossip 0.101.0, the latest release, sends no `Neighbor` in that case: the node keeps a neighbor request to the peer pending from the moment they first met — a `Neighbor` it sent in answer to the peer's own, which the peer never answers — and the pending entry suppresses every later `Neighbor` to that peer, while the old connection's eventual timeout is never reported as the peer's loss once a newer connection to the peer exists. Upstream fixed it on its `main` branch (pull request #161, "answer a join from a peer that is already a neighbor", 2026-10-09) without a release, so the workspace takes iroh-gossip from that branch at a fixed revision through `[patch.crates-io]` until a release carries the fix.

**Example:** Alice's node a1 and Bob's node b1 share "Family"; a1 is killed and starts again 12 s later.

| moment | iroh-gossip 0.101.0 | the revision the workspace takes |
|---|---|---|
| a1 starts and sends `Join` to b1 | b1 counts a1 as a neighbor already and has a request to it pending: it sends nothing | b1 answers `Neighbor` |
| a1 places a claim at once | announced to no neighbor: a1 has none | announced to b1 |
| about 30 s later, a1's old connection times out on b1 | a newer connection to a1 exists, so nothing reports a1 gone; b1 keeps sending a1 `Shuffle` as to a neighbor, and a1 drops each connection it arrives on | |
| b1 reads the claim | at b1's next pod pass, up to 300 s | within seconds |

#### Scenario: A killed member's node is a neighbor of its peer again at once
- **WHEN** a member's node is killed without grace and started again on its own state directory while the pod's other member's node still holds its previous connection open
- **THEN** the other member reads a record the restarted node placed right after its start within the convergence budget, two minutes, rather than at its next pod pass

### Requirement: A peer that restarts at a new address is reached at it
A node SHALL send to a peer on a path the peer still receives on. Of its paths to the peer, the node SHALL prefer one that some of its connections to the peer have received on over one that none has; then a primary path over a relay; then, within a tier, the path received on by more of those connections, whatever their round-trip times. Between paths alike in all three, it SHALL choose as iroh's default selector does: the current one until another is at least 5 ms faster, IPv6 counted 3 ms faster than it is. Selecting again with nothing changed SHALL keep the path selected. A path counts as received on by a connection once that connection has received a datagram on it, so a dial whose handshake never completed counts for nothing. The node's endpoint SHALL install this selector, `ReceivingPathSelector` in the data layer's `path_selector.rs`, through iroh's `path_selector` hook, which iroh offers only behind its `unstable-custom-transports` feature and outside its semantic versioning; the unit tests in `path_selector.rs` and `a_killed_node_is_the_same_node_and_a_fresh_one_holds_nothing` in the host's `tests/stand_restart.rs` are what holds it across iroh releases.

iroh's default selector, `BiasedRttPathSelector` in iroh 1.3.0, keeps a path once selected until a path of the same tier is at least 5 ms faster by its last measured round-trip time. A peer killed and started again listens on a new port, and the old path to it is dead but keeps the last round-trip time it measured, 1.9 ms on the stand, while its previous connection lives on until its idle timeout. On a local network no path is 5 ms faster than that, so every new connection the node opens to the peer sends its handshake to the dead port — the node's sync dials and payload downloads toward the restarted peer time out — while the connections the peer opens toward the node work. iroh selects again only when the last connection to the peer closes, and the node's own failed dials keep a connection on the dead path, so that can take minutes.

**Example:** b1's paths to Alice's node a1 after a1 was killed and started on port 33947, its old port 57771, as b1's endpoint logs them.

| path | connections that received on it | last round-trip time | iroh 1.3.0 | `ReceivingPathSelector` |
|---|---|---|---|---|
| `172.18.0.2:57771` | 1, the connection from before the kill | 1.9 ms | kept: the new path is not 5 ms faster | left |
| `172.18.0.2:33947` | 3, the connections a1 opened after its start | 0.4 ms | | selected |

#### Scenario: A killed member's node is reached at its new port
- **WHEN** a member's node is killed without grace and started again on a new port while the pod's other member's node still holds a connection to its old one
- **THEN** the other member's dials and payload downloads reach the restarted node, and it reads a record the restarted node placed after its start, payload included, within the convergence budget

#### Scenario: The path more connections receive on is selected
- **WHEN** a path to a peer is received on by more of the node's connections to it than the selected path of the same tier, whatever their round-trip times, or the selected path is received on by none of them while another is
- **THEN** the node selects that path; and when the selected path is received on by as many connections as any other of its tier, the node keeps it against one less than 5 ms faster

#### Scenario: A relay does not displace a primary path a connection receives on
- **WHEN** a relay path to a peer is received on by more of the node's connections to it than a primary path that at least one of them receives on
- **THEN** the node selects the primary path, and leaves the relay for it when the relay is the one selected

#### Scenario: Selecting again keeps the path selected
- **WHEN** the node selects a path to a peer and then selects again with no path, connection or reception changed
- **THEN** it keeps the path it selected

## MODIFIED Requirements

### Requirement: Shutdown stops every protocol side by side, and a late call fails
The node's shutdown SHALL stop every hosted identity's engine before the router, SHALL stop a supplied handler beside the built-in stack rather than before it, and SHALL close the blob store only once the router's shutdown has returned: the router shuts every protocol down at once, gossip among them, and then awaits every connection's handler. iroh-blobs answers a read reaching a file store that is shutting down by panicking on its own task ("poisoned storage should not be used" in its `bao_file.rs`); a running engine starts downloads that read the blob store, so the engines stop first, and the router shuts its protocols down before it cancels their connections, so a store the router closed would meet a request a handler had already read. A supplied handler whose work in flight writes through the node's stores therefore SHALL be let finish by its owner before the node's shutdown is called — a wait inside the handler's own shutdown runs against stores already going away. A call into a replica store that reaches it after its shutdown began, including one already queued behind the shutdown, SHALL fail rather than wait: its caller would otherwise wait for as long as any handle to the store lives.

**Example:** `Runtime::shutdown` in pdn-node, whose linking and join handlers write through the node's stores.

| step | the stores |
|---|---|
| 1 serving halves of both ceremonies finish, up to `SHUTDOWN_SERVING_BUDGET` (10 s); one arriving later refuses | open |
| 2 cleanup tasks finish, up to 10 s | open |
| 3 `SyncNode::shutdown`: the reconcile pass stops, then each identity's engine shuts down and starts no further download | the replica stores going away |
| 4 the router shuts down every protocol at once, gossip among them, and awaits every connection's handler; then the blob store closes and the storage lock is released | closed: a call queued behind a store's shutdown fails at once |

#### Scenario: A request queued behind the store's shutdown fails
- **WHEN** a request to a replica store is queued behind that store's shutdown
- **THEN** the shutdown completes and the request's caller receives an error rather than waiting

#### Scenario: A node stopped with a payload fetch under way stops without a panic
- **WHEN** a node on a directory stops while it fetches a payload from a member device that serves none, so the fetch is tried again until the stop
- **THEN** the stop completes and no thread of the process panics

#### Scenario: A node stopped while a peer asks for its payloads stops without a panic
- **WHEN** a node on a directory stops while a peer, over a connection opened before the stop, asks for one of its payloads again as soon as each answer arrives
- **THEN** the stop completes and no thread of the process panics
