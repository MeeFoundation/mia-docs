# Node assembly: hosting the ceremony protocols

## Purpose

The assembled node (`SyncNode`) runs its protocols on one endpoint, keyed by application-layer protocol negotiation (ALPN) identifier: document sync, gossip, and blob transfer built in. ADR-0012 puts device linking on that same endpoint, and ADR-0015 puts a pod's join beside it; this capability is what lets them: a spawn-time registration point for the supplied handlers, a panic guard around each, and a dial handle onto the endpoint for the initiators' side. This registration point is protocol-agnostic (the handlers are opaque here) only because the ceremonies' semantics belong above in pdn-node, not because the assembly is a general protocol-extension facility. The stores and flows riding the assembly stay specified in the other `data-layer` specs; this capability covers the assembly itself.

## Requirements

### Requirement: The assembly accepts a supplied protocol handler
`SyncNode` SHALL accept, at spawn, zero or more externally supplied protocol handlers — today device linking ([ADR-0012](../../../../architecture/adr/0012-linking-over-raw-iroh.md)) and a pod's join ([ADR-0015](../../../../architecture/adr/0015-pod-join-over-raw-iroh.md)) — each keyed by an ALPN identifier, and SHALL serve them on its protocol router alongside the built-in protocols (document sync, gossip, blob transfer). A connection arriving under a registered supplied ALPN SHALL be dispatched to that handler as a raw bidirectional connection, not a document-sync session. Spawning with no supplied handler SHALL preserve the assembly exactly as it is without this surface.

**Example:** the ALPNs of a node pdn-node's `Runtime` spawns, and what a connection accepted under each reaches.

| ALPN | reaches |
|---|---|
| `/iroh-bytes/4` | built in: blob transfer |
| `/iroh-gossip/1` | built in: gossip |
| `/iroh-sync/1` | built in: `DocsDispatch` reads the `Init` and hands the session to the identity it names |
| `/pdn/linking/0` | supplied: `LinkingHandler`, given the raw bidirectional connection |
| `/pdn/pod-join/0` | supplied: `JoinHandler`, given the raw bidirectional connection |
| any other | the dial fails, and no handler runs |

#### Scenario: An extra protocol answers on its ALPN
- **WHEN** node A spawns with a test echo handler under a test ALPN and node B dials A's address under that ALPN and sends bytes
- **THEN** the bytes return over the same raw bidirectional connection, with no document-sync session involved

#### Scenario: The built-in stack is unaffected by extras
- **WHEN** node A spawns with an extra protocol and node B imports a replica from A's ticket
- **THEN** the replica converges between A and B exactly as it does between nodes spawned without extras

#### Scenario: A node that did not register the ALPN refuses it
- **WHEN** node B dials node A under an ALPN that A did not register
- **THEN** the dial fails, no connection is established, and no handler runs on A

#### Scenario: Two supplied handlers serve side by side
- **WHEN** a node spawns with two supplied handlers under distinct ALPNs and each is dialed in turn
- **THEN** each dial reaches its own handler, and neither handler observes the other's connections

### Requirement: ALPN registrations are unique
The ALPNs of supplied protocols SHALL be distinct from the built-in protocols' ALPNs and from each other. A spawn presenting a collision SHALL fail with no node started and nothing bound — a supplied protocol silently replacing the sync stack must be impossible.

**Example:** the supplied protocols handed to `SyncNode::spawn_with`, and its answer; a refusal comes before the storage directory is touched or a socket bound.

| supplied ALPNs | answer |
|---|---|
| `/pdn/linking/0`, `/pdn/pod-join/0` | a node serving both beside the three built-in ALPNs |
| `/iroh-sync/1` | `Err(AlpnTaken)`: "protocol ALPN already taken: /iroh-sync/1" |
| `/pdn/linking/0`, `/pdn/linking/0` | `Err(AlpnTaken)`: "protocol ALPN already taken: /pdn/linking/0" |

#### Scenario: A built-in ALPN is refused at spawn
- **WHEN** a node spawns with a supplied protocol claiming the document-sync ALPN
- **THEN** the spawn fails and no node starts

#### Scenario: A duplicate supplied ALPN is refused at spawn
- **WHEN** a node spawns with two supplied protocols claiming the same ALPN
- **THEN** the spawn fails and no node starts

### Requirement: One endpoint carries all protocols, exposed as a dial handle
All protocols — the built-in stack and every supplied handler — SHALL share the node's single endpoint, so the node presents one wire identity (its `NodeId`) regardless of how many it serves. `SyncNode` SHALL expose a narrow dial handle onto that endpoint for runtime code to dial a peer's address under a chosen ALPN and to read the node's own address and wire id. The dial handle SHALL NOT offer the endpoint's lifecycle controls (closing the socket, rewriting its ALPN set), so the node remains the sole owner of the endpoint's lifecycle (shutdown stays with the node).

#### Scenario: The dial handle carries the node's wire identity
- **WHEN** the dial handle's identifier is compared with the node's reported node id
- **THEN** they are equal

#### Scenario: Dialing out rides the node's own identity
- **WHEN** node B dials node A's supplied protocol through B's dial handle
- **THEN** the connection A's handler observes carries B's node id as the remote identity

### Requirement: One connection carries a gossip stream for each of up to 4,096 stores two nodes share

The endpoint SHALL let a peer hold up to 4,096 unidirectional streams open on one connection. Gossip holds one such stream for every [swarm](../../../../architecture/language/swarm.md) topic two nodes share, for as long as they share it, and a sender past the count sends that peer nothing on any topic, and once its queue for that peer fills, nothing to any peer; a [pod](../../../../architecture/language/pod.md)'s two stores are two topics, so the count SHALL NOT stop live delivery between two nodes until the stores they share exceed 4,096, about 2,000 pods. One connection SHALL buffer no more than 248,750,000 bytes across all its streams, the product of the 199 streams and the 1,250,000-byte stream window the transport's defaults allowed, so that the larger count gives a caller more streams and no more memory.

**Example:** Alice's phone a1 and Bob's phone b1 share 60 pods, 120 swarm topics; Bob places a claim in the first of them.

| unidirectional streams per connection | Bob's claim on a1 |
|---|---|
| 100, the transport's default | arrives only with the pod stores' pass, up to 5 minutes later, and after a burst of Bob's writes b1 stops answering |
| 4,096 | arrives over the swarm at once |

#### Scenario: Two nodes sharing more stores than the transport's default stream count keep live delivery

- **WHEN** two members on two nodes share 60 pods, the pod stores' passes out of reach, and each places a claim in the first and in the last of them
- **THEN** each claim reaches the other node over the swarm, and after a burst of writes the writer's node still creates a pod

### Requirement: A supplied handler's panic is contained
A panic in a supplied handler's accept path SHALL NOT tear down the node. It SHALL be caught, failing only that one connection, while the built-in protocols keep serving. (Under a `panic = "abort"` build no catch is possible; the spawn form's contract asks handlers not to panic.)

**Example:** a1's handler under `/pdn-test/panic/0` panics after reading b1's bytes.

| build | on a1 | on b1 |
|---|---|---|
| `panic = unwind` | `PanicGuarded` turns the panic into `AcceptError` "extra protocol handler panicked"; `/iroh-sync/1` serves on | that connection ends, maybe as a clean end-of-stream; a replica shared with a1 still converges |
| `panic = abort` | the process aborts | every protocol of a1 is gone |

#### Scenario: A panicking handler does not take down the node
- **WHEN** node A spawns with a handler that panics mid-accept, and node B dials it and drives a stream
- **THEN** that connection fails and node A still converges a replica with node B over the ordinary ticket flow

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

### Requirement: An accepted sync connection is dispatched to the hosted identity it names

The node SHALL read the [identity](../../../../architecture/language/mee-identity.md) an accepted sync connection names before the session reaches any replica, and SHALL hand the session to that hosted identity alone. A connection naming an identity the node does not host SHALL be refused indistinguishably from the replica not being hosted, and no hosted identity SHALL observe a session addressed to another.

What the node reads before it knows whom a connection addresses SHALL be bounded. The first message names the namespace, the two identities and a first range whose two boundaries carry one key each, so the largest one an honest node sends is fixed by the longest key a replica holds, 8,192 bytes, and comes to about 16 KiB. A first message whose length prefix announces more than 32 KiB SHALL be refused on the prefix alone, before its body is read, so a caller that holds no ticket and is no member makes the node hold no more than that per connection. The session a classified caller goes on to run reads its later messages under the session's own ceiling, since one message of a first sync often carries a replica's whole content.

**Example:** a session's first frame: a `u32` big-endian length prefix, then `Message::Init { namespace, identity, caller, message }` in postcard.

| length prefix | the accepting node |
|---|---|
| about 16 KiB | the largest an honest node sends: its first range's two boundaries carry one 8,192-byte key each |
| 32,768 (`MAX_OPENING_FRAME`) | reads the body, then dispatches to the identity the `Init` names |
| 32,769 | refuses on the prefix, "received message that is too large: 32769"; no body read, no replica touched |
| after the `Init` | frames up to 1,073,741,824 bytes (`MAX_MESSAGE_SIZE`, 1 GiB) |

#### Scenario: A session reaches the hosted identity it names

- **WHEN** a peer syncs a namespace two identities of one node hold, naming one of them
- **THEN** the entries it delivers land in the named identity's replica, and the other hosted identity's replica is unchanged by that session

#### Scenario: An oversized first message is refused before its body

- **WHEN** a peer opens a sync connection whose first message announces more than 32 KiB, and holds the stream open without sending the body
- **THEN** the node refuses the connection on the announced length, without waiting for the body, and no replica is touched

#### Scenario: The largest honest first message opens a session

- **WHEN** a replica whose first key is 8,192 bytes long opens a session with its first message
- **THEN** the message is read and the session proceeds

#### Scenario: A session past its first message reads larger messages

- **WHEN** a session opened with an ordinary first message goes on to carry a message larger than 32 KiB
- **THEN** that message is read, and a replica it carries whole reaches the other side whole

#### Scenario: An unknown identity is refused

- **WHEN** a session names an identity the node does not hold
- **THEN** it is refused indistinguishably from the replica not being hosted, and no replica is touched

### Requirement: The node removes the payloads no replica it holds references

The node SHALL run blob collection over its one blob store at an interval `SpawnOptions` sets, with a single protect callback that answers with the union of the payloads every hosted identity's replicas reference, so that a payload SHALL stay while any replica of any identity the node hosts references it and SHALL leave the blob store at the first run after none does. A payload an identity writes, or fetches for an entry it received, SHALL stay through every run whose read of the replicas predates that entry, so that a run already under way when the entry lands SHALL NOT remove its payload. A forgotten replica — a [pod](../../../../architecture/language/pod.md)'s record store — SHALL free its payloads with no removal of its own. On a node with a storage directory, collection SHALL start only once its host has hosted again the identities it means to, so that a start removes nothing of an identity recovery has yet to reach; a node in memory collects from its spawn.

**Example:** Carol leaves "Family" on her phone c1, which hosts Carol alone; the pod's record store held Bob's lease scan and a photo whose bytes Carol also placed in a pod of her own, "Carol".

| payload | referenced after the record store is forgotten by | on c1 after the next run |
|---|---|---|
| Bob's lease scan | nothing | removed |
| the photo | the record store of "Carol" | kept |

#### Scenario: A payload no replica references is removed

- **WHEN** a node forgets the only replica whose entries reference a payload, and a collection run passes
- **THEN** the blob store no longer holds the payload

#### Scenario: A restart removes nothing before its identities are hosted again

- **WHEN** a node on a storage directory restarts, and collection intervals pass before its host has hosted its identities again
- **THEN** the blob store still holds every payload those identities' replicas reference, and collection runs from the host's start on

#### Scenario: A payload a co-located identity references stays

- **WHEN** two identities hosted on one node hold replicas referencing one payload, one of them forgets its replica, and a collection run passes
- **THEN** the blob store still holds the payload, and the other identity reads it

#### Scenario: A payload written while a collection run is under way stays

- **WHEN** an identity writes an entry after a collection run has read the replicas and before that run removes anything
- **THEN** the blob store still holds the entry's payload after the run, and the entry reads

#### Scenario: A payload fetched while a collection run is under way stays

- **WHEN** an entry arrives from a peer after a collection run has read the replicas, and its payload is fetched before that run removes anything
- **THEN** the blob store still holds the payload after the run, and the entry reads

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
