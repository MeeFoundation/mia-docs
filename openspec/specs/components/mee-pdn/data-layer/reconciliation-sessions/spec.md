# Reconciliation sessions

## Purpose
What every reconciliation session on a hosted identity's private metadata store (PMS) and on a pod's two stores is served and admits, and the mechanics every such session shares: pdn-store takes, per session, an egress predicate and an ingest verdict from the data layer's access book (ADR-0014) and knows nothing of what they mean. Which caller a pod's store serves and what its entries count for is the [pod stores](../pod-store/spec.md) spec's.

## Requirements

### Requirement: A session's egress and ingest are decided above the store, per session

The store SHALL take, for every session and on both session roles, an access decision from the session access provider the node is assembled with: a refusal, or an egress predicate over entries — what the session may reveal, none standing for the whole store — together with an ingest verdict over every entry the peer offers, which accepts the entry or drops it in silence. pdn-store SHALL know neither the membership vocabulary nor the identity vocabulary: it compares the identities a session names as opaque bytes and applies the predicates it is handed. The egress predicate and the ingest verdict SHALL be independent, so what ingest drops neither widens nor narrows what egress reveals. A dropped entry SHALL be refused before it persists and SHALL NOT be remembered, so the sender keeps its own copy and offers the entry again in a later session; nothing about the drop is signalled to the sender.

**Example:** Alice's phone a1 serves the membership store of "Family" to Carol's phone c1; Alice removed Carol at Carol's sequence 2, and Dave joined afterwards; `<x>`: 64 lowercase hex chars of x's `PdnId`.

| key | egress predicate, on what a1 holds | ingest verdict, on what c1 offers |
|---|---|---|
| `member/<carol>/1/joined/<bob>/1` | `true`: in Carol's departure's past | `Accept`: in that past |
| `member/<carol>/2/removed/<alice>/3` | `true`: the departure itself | `Accept` |
| `member/<dave>/1/joined/<alice>/4` | `false`: withheld | `Drop` |

#### Scenario: Egress is independent of ingest

- **WHEN** a session's egress predicate runs while its ingest verdict drops an entry the peer offers
- **THEN** egress reveals what it would reveal without that verdict, and the dropped entry is not persisted

#### Scenario: A dropped entry is offered again

- **WHEN** a session's ingest verdict drops an entry the peer offers
- **THEN** the replica does not hold the entry, the sender still holds it, and the sender's next session offers it again

### Requirement: What a session's egress withholds is hidden, not merely undelivered

A session SHALL compute every range fingerprint, split boundary, offer and item it sends over the entries its egress predicate admits, and over nothing else. An entry the predicate withholds SHALL NOT be fingerprinted, offered or sent, and the transcript the peer observes SHALL depend only on the admitted entries, so neither a withheld entry nor the fact that it exists reaches the peer. An entry SHALL be withheld before transmission, never transmitted and then recalled.

**Example:** a1's store holds three entries of one author at keys k1 < k2 < k3, and the session's egress admits k1 and k3 — k2 is an event of the pod after the caller's departure; the caller holds k1 and opens with its fingerprint; `[x, y)` runs from x to y, wrapping past the end.

| a1 reads its store | split at | a1's reply |
|---|---|---|
| k2 withheld | k3, k1 | `RangeItem [k3, k1)`: k3; `RangeItem [k1, k3)`: k1 |
| k2 absent | k3, k1 | `RangeItem [k3, k1)`: k3; `RangeItem [k1, k3)`: k1 |
| not filtered | k2, k1 | `RangeFingerprint [k2, k1)` over k2 and k3; `RangeItem [k1, k2)`: k1 |

#### Scenario: Only the admitted entries are delivered

- **WHEN** a store holds entries e1, e2 and e3, and a session's egress admits e1 and e2
- **THEN** the peer receives e1 and e2, and e3 is never transmitted

#### Scenario: Existence of a withheld entry is hidden

- **WHEN** a withheld entry e3 lies between admitted entries e2 and e4 in key order
- **THEN** the peer's session is indistinguishable from one in which e3 does not exist

### Requirement: An identity's own devices and a pod's current members are served whole

A session on a PMS between devices of the identity it belongs to SHALL deliver every entry of it, since a PMS is bounded by its ticket (Invariant 1); a session on either of a pod's stores between devices of its current members SHALL deliver every entry of the store, since a pod has no audience narrower than its members. Being an own device or a member device SHALL be judged per replica: a node is an own device for the PMS of each identity it is linked into, and a member device for a pod's stores when the identity it names in the session is one of those identities and a current member of the pod. What a pod's store serves a caller that is neither — a former member's device its departure's past; a node no statement lists nothing, taking that member's statements alone — is stated by the [pod stores](../pod-store/spec.md) spec.

**Example:** callers reconcile with Bob's phone b1; Bob is a member of "Family", Carol was removed from it, and Alice's tablet a3 hosts Alice-leisure, a member, and Alice-work, no member.

| caller | names | replica on b1 | b1 delivers |
|---|---|---|---|
| b2, Bob's laptop | Bob | Bob's PMS | every entry |
| a3 | Alice-leisure | the record store of "Family" | every entry |
| a3 | Alice-work | the record store of "Family" | nothing: the session is refused |
| c1, Carol's phone | Carol | the membership store of "Family" | Carol's departure's past alone |

#### Scenario: Own devices replicate the PMS in full

- **WHEN** two devices of one identity reconcile that identity's PMS
- **THEN** every entry replicates between them

#### Scenario: Member devices of a pod replicate in full

- **WHEN** a device of member A and a device of member B reconcile either store of a pod both are current members of
- **THEN** every entry of that store replicates between them

### Requirement: A session's access is decided at setup and holds for the session

The node that dials SHALL decide its side's access only once the connection stands and the session's snapshot is open, never when the dial is asked for: a connect can wait, for as long as the peer is down, across a membership event, and access decided before it would serve from a later snapshot what was written after the event. The node that accepts SHALL decide before it opens the session's snapshot, so a caller it refuses never makes it commit its pending write batch, and SHALL decide again once the snapshot is open when a replica the first decision read — the PMS, and for a pod's store its membership store — was written in between, or when that decision read a membership entry whose payload had not yet arrived; the second decision then governs the session. The decision SHALL govern the session for its whole lifetime: a membership event or a device record arriving while a session runs SHALL NOT change what that session serves or admits, and governs the sessions set up after it. A departure therefore takes effect from the next session, and what the departed member's device obtained while it was a member stays with it.

**Example:** Carol's phone c1 reconciles the record store of "Family" with Alice's phone a1, and Alice removes Carol while the first session runs.

| t | Alice, on a1 | session S1, c1 → a1 | session S2, c1 → a1 |
|---|---|---|---|
| t0 | | set up: Carol a member, served the store whole | |
| t1 | removes Carol | still serves the store whole | |
| t2 | | ends; c1 holds what S1 brought | |
| t3 | | | refused with `AbortReason::NotFound`; c1 still reads what it holds |

#### Scenario: A departure refuses the next session and keeps delivered data

- **WHEN** a member is removed while a device of that member holds records it obtained as a member, and that device then requests a session on the record store from a device the removal has reached
- **THEN** the request is refused, and the records the removed member's device obtained stay readable on it

#### Scenario: An accept decision is asked again when what it read was written

- **WHEN** a replica an accepting node's decision read is written between that decision and the opening of the session's snapshot
- **THEN** the node decides again over the snapshot, and the second decision governs the session

#### Scenario: A session refused when asked again leaves its pair free

- **WHEN** an accepting node's second decision refuses a session the first decision admitted
- **THEN** the caller receives the uniform refusal, and the caller's next session with that node goes through once the node admits it, rather than meeting a session still holding the pair

### Requirement: A session serves a view frozen at session setup

A node SHALL serve one reconciliation session from a store snapshot taken at session setup: every fingerprint, split boundary, offer, and item the session derives SHALL reflect the store as of that moment, so a write landing mid-session neither shifts the served view between rounds nor reaches the peer within the session — it travels on the next one. What one view buys is consistency inside a session, not a prerequisite of reconciliation: the engine converges over a drifting store too, because reconciliation is anti-entropy and what one session misses the next one carries — for as long as a session can finish, which the bound below qualifies, and for what the set gains rather than what it loses, which the requirement on removals below states. It buys agreement among the things a single session derives — a fingerprint and the items behind it describe the same entries, and a split boundary still partitions the set it was computed over when a later round returns to it — and it puts the data half of the session's decisions on the footing the access half already stands on, since the session's access is decided at setup and holds for its lifetime. Opening the snapshot SHALL first commit the store's pending write batch, so every entry inserted before session setup is in the snapshot. Ingest SHALL stay on the live store: an entry the peer sends is judged against current state, so an older remote entry never overwrites a newer local write the snapshot predates. The snapshot SHALL be released when the session ends, on every exit path — completion, refusal, failure, and cancellation alike — and a session that neither completes nor fails is ended by the bound below, so no snapshot outlives its session and no session runs without end.

**Example:** a1 (Alice's device) serves session S1 to a2 (her other device); S1's snapshot is taken at setup, and a1 then takes in a newer `pods/ad58a3faa04cdc5576c8dc5823a347c6/1` from a3.

| read inside S1 | reads from | sees the newer entry |
|---|---|---|
| `get_first`, `get_range`, the fingerprints | the snapshot | no: the next session serves it |
| `put`, when a2 offers an older entry at that key | the live store | yes: the older entry is not inserted |

#### Scenario: A mid-session write travels on the next session

- **WHEN** a node writes an entry after a session's setup, while the session is still exchanging rounds
- **THEN** the session delivers the entries written before its setup only, and the next session delivers the new entry

#### Scenario: An older remote entry loses to a newer mid-session write

- **WHEN** a session's snapshot predates a newer local write to a key, and the peer transmits an older entry for that key
- **THEN** the older entry is not inserted — the ingest comparison reads the live store, not the frozen view

#### Scenario: A session's snapshot is released on every exit path

- **WHEN** a session ends — completed, refused, failed, or cancelled
- **THEN** its snapshot is released; a refused request opens none on the node that refused it, while the node that asked releases the one it opened before asking

### Requirement: A removal travels as the artefact it leaves

Reconciliation converges over a drifting store because what one session misses the next one carries, and that holds for what a set gains: a later session offers an entry an earlier one did not have. It does not hold for what a set loses. A session serves rows that a removal took out after its setup, and the next session carries no news of the removal — only the absence of what was removed, which a peer already holding it cannot tell from a set it is ahead on. What carries a removal is therefore the artefact the removal leaves behind, and every removal SHALL leave one whose reach covers every peer the removed rows can reach. A delete leaves an empty entry at the deleted key, which replicates as any entry does; it replaces its author's older entry at that key and SHALL NOT be replaced in turn by an older entry at that key, whichever side of a session offers first, so a replica that still holds the deleted entry converges on the delete instead of handing the entry back. A removal that would leave no such artefact SHALL instead end the open sessions of its namespace, because nothing else would converge on it. A frozen view therefore delays a removal by at most one session's lifetime and cannot lose it.

**Example:** Alice's devices a1, a2 and a3 hold her PMS; a4 began linking from a1 24 hours ago and never confirmed.

```
delete     a1's cleanup tombstones pending-devices/<a4-hex>, the record a1 wrote when a4 began linking
  leaves   an empty entry by a1's author at pending-devices/<a4-hex>: len 0, stamped at the delete
  spreads  as any entry does, to a2 and a3; the older record by a1's author, offered back, is not inserted
```

#### Scenario: A delete inside a session lands in two parts

- **WHEN** a node deletes an entry while a session it serves is exchanging rounds
- **THEN** that session serves the deleted entry and not the empty entry that deleted it, and the next session carries that empty entry, which deletes it at the peer

#### Scenario: A delete converges whichever side opens the session

- **WHEN** a replica deletes its author's entry at a key while another replica still holds that entry, and the deleting replica opens the next session between them
- **THEN** both replicas hold the delete after that session and after every later one, whichever side opens it

### Requirement: An entry affects only its own key

A write SHALL affect only the entry at its own key: the entry replaces the earlier entry its author wrote at that key and leaves every other key standing on every replica, a longer key beginning with the same bytes included. An entry arriving by sync SHALL be refused only by an entry of its author at its own key that is newer or equal, an empty one included. A zero-length payload is the store's deletion marker and SHALL NOT be written as a value: a local write of one SHALL fail, storing nothing and deleting nothing, so a layer above that needs "present but empty" encodes it as a payload of its own.

**Example:** Alice's tablet a3 holds the entry her phone a1 wrote at `pods/ad58a3faa04cdc5576c8dc5823a347c6/1` in her PMS, dated 10:00:05, the record of her joined event in "Family"; a1 and her laptop a2 write with one author each.

| entry at a3 | dated | at a3 |
|---|---|---|
| a1's, at `pods/ad58a3faa04cdc5576c8dc5823a347c6/1`, over sync | 10:00:03 | refused: a1's own entry at that key is newer |
| a1's, at `pods/ad58a3faa04cdc5576c8dc5823a347c6/12`, over sync | 10:00:01 | stored: the entry at the key ending in `/1` sits at another key, though its bytes begin this one |
| a2's, at `pods/ad58a3faa04cdc5576c8dc5823a347c6/1`, over sync | 10:00:01 | stored beside a1's |
| a zero-length payload, written on a3 at `tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/records` | | refused: `InsertError::EntryIsEmpty`; the ticket stored there stays |

#### Scenario: A write at a shorter key leaves the longer ones standing

- **WHEN** a device writes entries at two keys and then an entry at a key whose bytes begin both
- **THEN** every one of the three keys reads what was written at it, on that device and on the identity's other device once it syncs

#### Scenario: A zero-length write is refused

- **WHEN** a device writes a zero-length payload at a key, fresh or holding a value
- **THEN** the write fails, and the key holds what it held before

### Requirement: A session is bounded in time

A reconciliation session SHALL be bounded as a whole, and a session reaching that bound SHALL be ended rather than left running. Two things rest on the bound. A node runs one exchange per replica and peer and starts no other while one runs, so a session that never ends stops that pair from reconciling at all. And a session holds a store snapshot, whose read transaction holds back reclamation of every page freed while it lives, so the same bound is what bounds that. Bounding the wait between messages instead would bound neither, since a peer sending one message every few seconds keeps both for as long as it likes. A connection that goes dead rather than quiet is cut by the transport well inside the bound, so the bound is what answers for a peer that stays reachable and stops making progress.

A session cut short at the bound loses what it had not delivered, not what it had: entries already ingested are stored, and later sessions carry the rest. That holds while a session delivers something. It does not hold for a set whose transfer cannot finish inside the bound, because a message is ingested whole or not at all and a node holding nothing of a replica receives the served set as a single message: a cut then delivers nothing, the next session starts over, and reconciliation does not converge at all rather than converging slowly. Raising the bound moves that threshold rather than removing it; removing it wants a limit on the size of a transmitted set, which this layer does not impose.

**Example:** Carol's new phone c2 holds nothing of the record store of "Family", so Bob's phone b1 serves its 10,000 entries, about 2.8 MB, as one message; `SYNC_SESSION_TIMEOUT` is 300 s.

| link | the message takes | outcome |
|---|---|---|
| 75 kbit/s | about 299 s | lands inside the bound: 10,000 entries stored |
| 37.5 kbit/s | about 597 s | cut at 300 s with nothing stored; every later session starts over and is cut the same way |

#### Scenario: A stalled session is ended and its pair reconciles again

- **WHEN** a peer holds a session open without carrying it to completion
- **THEN** the session is ended at the bound, its snapshot is released, and that pair reconciles again on a later trigger

#### Scenario: A session cut short keeps what it delivered

- **WHEN** a session ends at the bound after delivering part of what it owed
- **THEN** the delivered entries are stored, and later sessions carry the rest

### Requirement: A gossip neighbor a dial cannot reach is tried again

A sync dial that fails to connect, and a payload download that fails to connect, loses its connection or makes no progress, toward a peer that is a gossip neighbor in some swarm of the node's engine for that identity SHALL be tried again 1 s after the failure, each further wait twice the one before up to 16 s, for at most 2 minutes after the first failure; an exchange with the pair that ends any way but a failed connection, the download succeeding, or the peer ceasing to be a neighbor in every swarm SHALL end the series. A series SHALL keep at most one try due: a failure that another trigger brings while a try is due schedules none of its own, and a series that has run its 2 minutes SHALL stay run out until what ends it, so no later failure starts it again. A try due when its replica is left SHALL dial and fetch nothing for it. A peer that is no neighbor SHALL NOT be retried this way: its next sync report or pass dials it. The transport sends a new connection's handshake on the path it last selected for a peer while any connection to that peer lives, and selects again only when a connection or one of its paths opens or a path is abandoned, so a device that restarts on a new port connects to the others at once while their dials keep going to its old port until it opens another connection. Without the retry, what a device places after a restart without a goodbye — a kill, a crash, a battery pulled — waits for the other members' next pod pass even when its announcement arrived; with it, the record follows the path's healing. A record whose announcement reached no neighbor still waits for that pass.

**Example:** Alice's tablet a3 is killed and starts again on port 48670, its old one 51650; Bob's phone b1 is the other member of "Family", and a3 is a gossip neighbor of b1 throughout.

| t | a3 | b1 |
|---|---|---|
| 0 s | starts, syncs "Family" with b1 from 48670, places "after" | takes the entry; the payload download goes to 51650 and fails |
| 1 s, 3 s, 7 s, 15 s, 31 s | | the download is tried again: 51650, fails |
| 44 s | its gossip connects to b1 again, from 48670 | the path is selected again: 48670 |
| 47 s | | the try 16 s after the one at 31 s downloads the payload; "after" reads |

#### Scenario: A dial toward a neighbor it cannot reach is tried again

- **WHEN** a sync dial fails to connect to a peer that is a gossip neighbor in the replica's swarm
- **THEN** the dial is tried again while the peer stays a neighbor, and the tries stop once it leaves

#### Scenario: A peer that is down is not dialed again

- **WHEN** a sync dial fails to connect to a peer that is no gossip neighbor of the node
- **THEN** no further dial is scheduled for it, and nothing the node started stays in flight

#### Scenario: Failures from other triggers keep one try due

- **WHEN** a sync dial toward a neighbor it cannot reach fails again, on another trigger, while a try of its series is due
- **THEN** no further try is scheduled for that failure

#### Scenario: A download from a neighbor is tried again until its replica is left

- **WHEN** a payload download from a provider that is a gossip neighbor in the replica's swarm loses its connection
- **THEN** the download is tried again, and a try due when the replica is left fetches nothing

### Requirement: A dial crossing one its pair refused goes through

When a dial arrives from a peer while this side's own dial of that pair runs, and the pair refused this side's last dial with the uniform refusal a node gives a caller it does not serve, the arriving dial SHALL take the pair over, whatever the tie-break between two crossing dials would decide; a session with the pair that goes through, in either direction, SHALL end that standing. Two crossing dials otherwise meet the tie-break, which keeps one side's dial and aborts the other's as already syncing. When the side whose dial is kept is the one the other refuses — a device that joined a pod a moment ago serves no member until its membership view counts one — and a pass or a queued resync keeps a dial of it in flight, every dial of the side that would be served is aborted and no session goes through, on a slow device for as long as the passes go on.

**Example:** Dave's phone d1 joins "Family" through Alice's laptop a1, on a device slow enough that each of a1's dials takes a second and a half to be refused, while a1's pass asks for a dial of d1 every half second, and the tie-break keeps a1's dial over d1's.

| t | a1 | d1 |
|---|---|---|
| 0 s | dials d1 | dials a1; a1 aborts it as already syncing, its own dial kept by the tie-break |
| 1.5 s | d1 refuses the dial: its membership view counts no member yet | |
| 1.6 s | dials d1 again | redials a1, while a1's new dial runs; a1 lets it through, since d1 refused a1's last dial, and serves it |
| 1.7 s | | d1's view counts Alice; d1 serves a1's dials from now on |

#### Scenario: A dial crossing one its pair refused takes the pair over

- **WHEN** a dial arrives from a peer while this side's own dial of the pair runs, the tie-break keeping this side's dial, and the pair refused this side's last dial
- **THEN** the arriving dial goes through, and with no refusal the same dial is aborted as already syncing

### Requirement: Payload downloads toward one provider are bounded

A payload's provider is a node registered as holding it: the sender of the entry that names it, when the sender holds it, the peer of a session that ends while it is wanted, or a gossip neighbor that announces it. A node's engine for an identity SHALL have at most 100 payload downloads in flight toward one provider, the number of bidirectional streams the node's endpoint grants a connection, and SHALL hold every other payload its replicas want as an entry of a queue rather than as a running download. A payload is wanted while an entry of one of the engine's replicas names it and no download of it has landed or found the blob store holding it whole; a payload another identity of the node has already fetched stays wanted until its turn in a queue comes. A waiting payload SHALL be fetched from a provider registered as holding it that has room, and a provider registered while the payload waits, by a session that ends or by an announcement, SHALL be one it can be fetched from. The limit SHALL NOT be a parameter of the node's host and SHALL NOT change while the node runs. A provider grants a connection no more streams than that, so a download beyond the limit would only wait inside the transport, holding the memory of a running download. A provider's answer that it lacks a payload, whole or in part, SHALL drop that payload from it alone: the provider keeps its limit and pauses for nothing, a gossip neighbor as any other, and is asked for that payload again once it is registered for it again. A session's end registers its peer for every payload the replica waits for without knowing which it holds, so in a young pod such answers are the rule, and a pause for each would hold back the payloads the provider does hold.

**Example:** Alice's tablet a3 joins "Family", a pod of 20,000 records whose payloads Alice's laptop a1 holds; Bob's phone b1, which holds them too, finishes a session with a3 midway.

| moment | downloads toward a1 | downloads toward b1 | payloads waiting on a3 |
|---|---|---|---|
| the session with a1 has brought every entry | 100 | 0 | 19,900 |
| a1 has answered one more request | 100 | 0 | 19,899 |
| b1's session with a3 has ended | 100 | 100 | 19,699 |

#### Scenario: A catch-up keeps the limit toward its provider

- **WHEN** a replica joins a namespace of 2,000 entries whose payloads one provider holds
- **THEN** the provider never has more of the replica's blob requests open at once than the limit, and every payload arrives

#### Scenario: A provider registered during a catch-up takes waiting payloads

- **WHEN** a second provider of the same payloads finishes a session with the replica while payloads wait
- **THEN** waiting payloads are fetched from both providers, at most the limit toward each, and every payload arrives

#### Scenario: A neighbor lacking a payload has its own fetched at once

- **WHEN** a provider that is a gossip neighbor of the replica answers that it lacks a payload the replica waits for, and then writes a record of its own
- **THEN** the record's payload is fetched from it at once, with no pause

### Requirement: A download that makes no progress is handed on

A payload download that receives nothing from its provider for 10 seconds SHALL be dropped, its stream with it, and the payload SHALL be fetched from another provider registered as holding it. The provider SHALL then pause: no download SHALL go to it for 1 second, each further pause twice the one before up to 16 seconds, for at most 2 minutes after the first; after each pause one download SHALL probe it, and a download from it that succeeds SHALL end the pauses and give it its limit back. A payload whose only provider stalled SHALL stay queued for that provider and SHALL be fetched from it again after its pause, with no session needed. A provider whose 2 minutes ran out SHALL be asked for nothing until a session with it ends, and a payload no other provider holds SHALL wait for that session. A download SHALL count as landed only once the blob store holds its payload whole. A download that fails on the node's own blob store SHALL pause no provider, and its payload SHALL wait as one no provider holds does, for the next session's end or an announcement of it: a disk that fills fails every payload alike, and a payload asked for again at once would only fail again. Without the bound, a provider that accepts a request and sends nothing holds the download for as long as its connection stays open, and the transport keeps a quiet connection open with a keep-alive every 5 seconds.

**Example:** Bob's phone b1 is the only provider of a payload P that Alice's tablet a3 wants, and b1 answers nothing for its first 25 seconds.

| t | a3 |
|---|---|
| 0 s | asks b1 for P |
| 10 s | drops the request; b1 pauses for 1 s |
| 11 s | probes b1 with P |
| 21 s | drops the probe; b1 pauses for 2 s |
| 23 s | probes b1 with P; b1 starts answering at 25 s |
| 25 s | P arrives; b1 may have 100 downloads in flight again |

#### Scenario: A silent provider's payloads come from another provider

- **WHEN** a provider accepts every blob request of a replica and answers none, while a second provider holds the same payloads
- **THEN** every payload arrives from the second provider, those first asked of the silent one after their requests were dropped

#### Scenario: The only provider, silent for a while, is asked again

- **WHEN** the only provider of a replica's payloads answers none of the requests it receives for 15 seconds, and serves those it receives after
- **THEN** every payload arrives once it serves, through requests made after the first ones were dropped, with no session between

#### Scenario: A provider silent for 2 minutes waits for a session

- **WHEN** a provider answers no request of a replica for 2 minutes
- **THEN** no download goes to it until a session with it ends, and its payloads are asked for again after that session

#### Scenario: A failure on the node's own blob store pauses no provider

- **WHEN** a download fails because the node's blob store cannot write the payload, before the transfer ends or after
- **THEN** no `ContentReady` reports the payload, its provider keeps its limit, and the payload is asked for again at the next session's end

### Requirement: The gossip topic carries no content

A replica's gossip topic SHALL carry only content-free announcements, never entries. A local insert SHALL broadcast a content-free author-head digest (a sync report) to neighbors, naming the identity whose replica sends it so a pull it triggers addresses that identity; the entry itself SHALL NOT be broadcast, and an entry received over gossip SHALL be dropped, never inserted. Content SHALL flow only over the classified reconciliation an announcement triggers — the receiver, seeing it has news, pulls, and re-announces to its own neighbors after pulling (the cascade). The report a session's end sends SHALL name only heads of entries the store took, never of one it refused ([iroh-docs-004](../../iroh-defects.md)), and SHALL fit the content gossip takes in one message, about 4,055 bytes: of the heads the session brought it names the newest that fit with the report around them, so a session that brought the entries of 100 authors or more still reports, and a neighbor behind only on an author it leaves out catches up at its own next pass ([iroh-docs-003](../../iroh-defects.md)). Because the topic id equals the namespace id and topic membership is unauthorized, a subscriber that knows the id obtains only activity metadata (author heads, timing, and the identity whose replica announces), never keys, hashes, or values, and the reconciliation an announcement would trigger is classified, so a subscriber the store's records admit to nothing obtains nothing at all. For a PMS the identity an announcement names is the PMS's own, which a holder of the namespace id knows already; in a pod's swarm a holder of the stores' tickets that is no member learns which members' replicas write, as the [threat model](../../threat-model.md) records. The content hash a fetch-hint announcement carries, and the blob channel behind it, are outside this requirement and recorded in the threat model.

**Example:** a1 and a2 are Alice's devices; a1 records a device in her PMS, and the topic of her PMS, whose id is the namespace id, carries this.

```
message:     Op::SyncReport(SyncReport { namespace, heads, identity })
encoded as:  107 bytes: 02 (Op variant 2), the 32-byte namespace id, 29 (length 41), then heads, then the 32-byte identity
heads:       one pair: the write's timestamp, an 8-byte varint, and a1's 32-byte author id, after a count of 1
identity:    Alice's PdnId, whose replica a1 holds, as a2 addresses its pull
not in it:   the key, its content hash, its value; a2 pulls them over the reconciliation the message triggers
received:    an Op::Put carrying an entry is dropped, never inserted
```

#### Scenario: An own device converges through the announcement, not a pushed entry

- **WHEN** an identity's device writes an entry into its PMS and another of its devices is a swarm member
- **THEN** the second device converges on the entry — obtained over the reconciliation the announcement triggered, not received as a broadcast entry

#### Scenario: A report names no entry the store refused

- **WHEN** a session's peer offers an entry the session's ingest verdict drops beside one it admits
- **THEN** the session's report names the admitted entry's author and not the dropped entry's

#### Scenario: A session that brought many authors still reports to the neighbors

- **WHEN** a session brings the entries of 150 authors
- **THEN** the report it sends to the replica's neighbors fits the content gossip takes in one message and names the newest heads that fit

#### Scenario: A topic subscriber that is no member obtains no content

- **WHEN** a party that knows the id of a pod's record store but is no member of the pod subscribes to its topic, and a member then writes
- **THEN** the subscriber obtains no key, hash, or value of the write — the topic carries only the content-free announcement, and the reconciliation it would trigger is refused

### Requirement: A store's swarm is its device set

The gossip swarm of a store SHALL consist of the store's device set: the identity's own devices for a PMS, and the devices of every current member for each of a pod's stores, a pod having no audience narrower than its members. A departed member's tombstone of a pod's membership store SHALL be out of the store's swarm while it stays open and reconciles with its own identity's devices. Membership conveys announcements, and every entry still flows over the classified reconciliation an announcement triggers, so swarm membership widens what no session serves.

**Example:** the swarms around Alice, whose devices are a1 and a2; Bob, on b1 and b2, and Carol, on c1, are the other members of "Family", and Dave was a member until he left.

| replica | its swarm |
|---|---|
| Alice's PMS | a1, a2 |
| both stores of "Family" | a1, a2, b1, b2, c1 |
| Dave's tombstone of the membership store of "Family", on his phone d1 | none: d1 reconciles it with Dave's own devices alone |

#### Scenario: Member devices of a pod form its swarm

- **WHEN** a member writes into a pod's record store while devices of the other members are subscribed to its topic
- **THEN** those devices converge on the entry through the content-free announcement and the pull it triggers

#### Scenario: A tombstone is out of its pod's swarm

- **WHEN** a member leaves a pod and its device keeps the membership store as the pod's tombstone
- **THEN** the tombstone is no member of the store's swarm, and a member's later write reaches it over no announcement

### Requirement: Unauthorized callers are refused uniformly

A sync request from a caller the records of the identity it names admit to nothing SHALL be refused indistinguishably from the replica not being hosted on this node, and so SHALL a request for a namespace the node does not host and one naming an identity the node does not host. A node SHALL serve a replica only in roles it can judge from its own records — a PMS to the identity's own devices by its ticket, a pod's store as the [pod stores](../pod-store/spec.md) spec states; every other caller SHALL be refused.

**Example:** callers ask Alice's phone a1 to sync; Dave holds the ticket of the record store of "Family" without being a member, and Erin holds nothing.

| caller and request | a1's answer on the wire |
|---|---|
| Erin, for the record store of "Family" | `00 00 00 02 02 00` |
| Dave, for the record store of "Family" | `00 00 00 02 02 00` |
| anyone, for a namespace a1 does not host | `00 00 00 02 02 00` |
| anyone, naming an identity a1's node does not host | `00 00 00 02 02 00` |
| decoded: frame length 2 (`u32` big-endian), `Message` variant 2 = `Abort`, `AbortReason` variant 0 = `NotFound` | |

#### Scenario: Every refusal is the frame an unhosted replica produces

- **WHEN** sessions are refused for a namespace the node does not host, for an identity the node does not host, and for a caller that is no member of the pod whose store it names
- **THEN** each refusal is the same frame, and none reveals a fingerprint, a count or the store's existence

### Requirement: A key longer than the store's bound is refused on every replica

The fork SHALL hold no key longer than 8,192 bytes, in any replica. A local write at a longer key SHALL be refused to its caller, and an entry at a longer key arriving over sync SHALL be dropped silently whatever the session admits, as the base validation drops an entry with a bad signature, while the session goes on with the rest. The longest key the platform writes is a mergeable-document's operation, `by/<pdnid>/mergeable-document/<id>/<pdnid>.<author>.<mseq>.<op>` with both sequences at their longest, 291 bytes. The bound is what keeps the first message a replica sends small: that message carries the replica's first key twice, and a peer reads it before anything classifies the caller ([node assembly](../node-assembly/spec.md)), so a replica holding a longer key would send a first message every peer refuses, and its sync would stop for every holder.

**Example:** a2, Alice's second device, is served her PMS whole, so the key's length alone decides at a1; a1's first message then carries at most two keys of 8,192 bytes, under the 32,768-byte ceiling (`MAX_OPENING_FRAME`) a peer reads it with.

| key length (bytes) | a1 writes it locally | a2 offers it to a1 over sync |
|---|---|---|
| 8,192 | stored | stored |
| 8,193 | refused: `ValidationFailure::KeyTooLong` | dropped silently; the session goes on |

#### Scenario: A local write at a key over the bound is refused

- **WHEN** a device writes an entry whose key is 8,193 bytes long
- **THEN** the write is refused, while a write at a key of 8,192 bytes succeeds

#### Scenario: An entry at a key over the bound is dropped at ingest

- **WHEN** a peer's replica holds an entry whose key is longer than 8,192 bytes beside an ordinary entry, and a device syncs with it
- **THEN** the device holds the ordinary entry and not the long one, and the session completes

### Requirement: An entry dated beyond the future window is dropped on every replica

The fork SHALL admit an entry dated up to 10 minutes ahead of the receiving device's clock and SHALL drop anything dated further ahead, whatever the session admits, as the base validation drops an entry with a bad signature. Within the window a device can date an entry forward, and the entry then outranks, by timestamp, every entry at its key dated before it; the window bounds how long that can last.

**Example:** a2, Alice's second device, writes into her PMS with its clock set forward; a1 is her other device.

| a1's clock | entry a2 offers | timestamp | on a1 |
|---|---|---|---|
| 12:00:00 | `devices/<a2-hex>` | 12:10:00 | admitted: exactly 10 minutes ahead |
| 12:00:00 | `devices/<a2-hex>`, rewritten | 12:10:01 | dropped: more than 10 minutes ahead (`TooFarInTheFuture`) |

#### Scenario: An entry dated beyond the window is refused regardless of the session

- **WHEN** an entry is dated more than 10 minutes ahead of the receiving device's clock
- **THEN** it is dropped by the base validation, whatever the session admits

### Requirement: An entry whose hash and length disagree on emptiness is dropped on every replica

The fork SHALL count an entry as empty exactly when its content hash is the hash of no bytes and its length is 0, and SHALL drop an entry arriving over sync whose hash and length disagree on that — the empty hash with a length, or another hash with a length of 0 — whatever the session admits, as the base validation drops an entry with a bad signature, while the session goes on with the rest. Only a modified node signs such an entry; held, it would read as a deletion to a reader that judges emptiness by the hash, as the store does, and as content to one that judges by the length. A record the fork reads back from its own store file is built without the check, since a store written before the check can hold one.

**Example:** Bob's modified phone b1, a member of "Family", offers Carol's phone c1 three entries in one session.

| entry b1 offers | content hash | length | on c1 |
|---|---|---|---|
| `whole` | the hash of `v` | 1 | stored |
| `empty-hash-with-a-length` | the hash of no bytes | 5 | dropped silently; the session goes on |
| `a-length-of-zero` | the hash of `v` | 0 | dropped silently |

#### Scenario: An entry whose hash and length disagree on emptiness is dropped at ingest

- **WHEN** a peer offers in one session an entry with the empty hash and a length, an entry with another hash and a length of 0, and a whole entry
- **THEN** the device holds the whole entry and neither of the other two, and the session completes
