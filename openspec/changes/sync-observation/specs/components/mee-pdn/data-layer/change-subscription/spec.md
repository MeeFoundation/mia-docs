# Change subscription

## ADDED Requirements

### Requirement: An ordered subscription reports a session's entries before the session

The store SHALL offer an ordered subscription to one replica the live sync holds open, and SHALL refuse one for a replica it does not. The store SHALL also open an ordered subscription together with the start of a replica's sync, registered before the replica is opened for sync and before its first dial, so no event of that sync precedes it; for a replica whose sync is already running, it is the ordered subscription a caller takes alone. The ordered subscription SHALL report every local and remote insert of the replica, every finished session, every completed download and every end of a session's downloads, in one sequence in which each remote insert a session made comes before that session's end, each download's completion comes after the remote insert that asked for it, and no remote insert of a pair's later session comes before the end of that pair's earlier one. A session between 2 identities of one node SHALL be reported in the same order as a session over the network. The ordered subscription SHALL end when the replica is dropped. The subscription "A subscriber never holds up the store" describes SHALL keep its 2 buffers and their order.

**Example:** one session of the reader with member device w5 on a pod's record store inserts 1,000 entries, and the pair's next session inserts one more.

| position in the sequence | event |
|---|---|
| 1 to 1,000 | remote inserts of the first session |
| 1,001 | the first session finished, ok |
| later | downloads of those entries' payloads complete, each after its insert |
| after 1,001 | the remote insert of the next session |

#### Scenario: A 1,000-entry session is reported entries first

- **WHEN** a reader holding an ordered subscription runs one session that delivers 1,000 entries
- **THEN** all 1,000 remote inserts are reported before that session's end, and none is missing

#### Scenario: A pair's later session follows the end of its earlier one
- **WHEN** a replica holds 2 consecutive sessions with one peer, the first dialed by this node and the second accepted from it, each carrying entries
- **THEN** every remote insert of the second session comes after the first session's end in the ordered subscription

#### Scenario: A payload the node already holds completes no download
- **WHEN** 2 entries with one payload arrive in one session, and a third entry arrives with a payload the node held before the session
- **THEN** the ordered subscription reports one completed download for the shared payload and none for the third, whose remote insert reports its content as complete

#### Scenario: A download completes after its entry

- **WHEN** a session delivers an entry whose payload the reader then downloads
- **THEN** the download's completion is reported after that entry's remote insert

#### Scenario: An ordered subscription taken with the start of sync reports the first session

- **WHEN** a reader imports a replica whose writer holds entries and starts its sync with an ordered subscription attached
- **THEN** every remote insert of the reader's first session is reported before that session's end, and none is missing

#### Scenario: A replica not held open for sync is refused

- **WHEN** an ordered subscription is asked for a replica the live sync does not hold open
- **THEN** it is refused, rather than opened on a replica whose inserts it would never report

#### Scenario: A dropped replica ends its ordered subscription

- **WHEN** a replica with an open ordered subscription is dropped
- **THEN** the subscription ends after the events reported before the drop, and an entry written to the same namespace by a peer afterwards reaches no subscriber of it

### Requirement: An ordered subscription holds what its caller asked for, and reports what it drops

An ordered subscription SHALL be created with the capacity its caller names and SHALL follow the lag rule of "A subscriber never holds up the store" past it: events beyond the capacity are dropped, one lag notice follows the last event the subscriber still receives, and the live actor does not wait. The store's other subscriptions keep their fixed capacity of 256.

**Example:** the runtime's observation asks for 4,096. A 1,000-entry session produces at most 2,002 events: 1,000 remote inserts, at most 1,000 completed downloads, the session's end, and the end of its downloads.

| subscriber | outcome |
|---|---|
| reads nothing until the session and its downloads have ended | receives all 2,002 events, no lag notice |
| reads nothing across more than 4,096 events | receives the first events that fit, then a lag notice |

#### Scenario: A subscriber that reads nothing during a 1,000-entry session loses nothing

- **WHEN** a subscriber with a capacity of 4,096 reads nothing while the reader runs one session that delivers 1,000 entries, and reads only after that session and its downloads end
- **THEN** it receives every event of the session and no lag notice

#### Scenario: A subscriber that falls behind its capacity is told

- **WHEN** more events are produced than the ordered subscription's capacity while its subscriber reads nothing
- **THEN** the subscriber receives a lag notice after the last event that fit, and the reader's sync is not delayed by it

### Requirement: A session event names its session, its stage and its counts

The event reporting a finished session SHALL carry, beside the counterpart node, the origin, the start and finish times and the result: a session id, when the session ran over a network connection, that both ends derive from that connection's keying material and that is the same on both ends and different for every connection; for a failure, the stage it failed at, one of `connect`, `remote_abort`, `sync` and `close`, named by the error's variant; and the counts of entries sent and received whenever the session's rounds completed, which is every success and every failure at `close`. A session between 2 identities of one node SHALL carry no session id and SHALL name the node itself as its counterpart. A session refused as already syncing SHALL be reported by neither side, and a session the accepting side refuses before the pair registers SHALL be reported only by the dialing side, at `remote_abort`.

**Example:** the reader dials member device w5 three times.

| reader's event | w5's event |
|---|---|
| failed at `connect`, no session id | none |
| failed at `remote_abort`, session id `51c0…` | none: refused before the pair registered |
| ok, received 12, session id `9f3a…` | ok, sent 12, session id `9f3a…` |

#### Scenario: Both sides of one session carry one session id

- **WHEN** a reader dials a writer and the session completes
- **THEN** the reader's event and the writer's event carry the same session id and no other session carries it, and the reader's count received equals the writer's count sent

#### Scenario: A refused dial is reported by the dialer alone

- **WHEN** a party holding the writer's replica ticket, whom the writer's access provider refuses, dials the writer
- **THEN** the dialer reports the session failed at `remote_abort` with a session id, and the writer reports no session and serves nothing

#### Scenario: A failed teardown keeps the counts

- **WHEN** a session's rounds complete and its teardown then fails on one side
- **THEN** that side reports failure at `close` with the counts of its completed rounds, and they equal the counts the other side reports for the same session id

#### Scenario: A dial that never connects carries no session id

- **WHEN** a reader dials a writer it cannot reach
- **THEN** the reader reports failure at `connect` with no session id, and the writer reports nothing

#### Scenario: A session between two identities of one node carries no session id

- **WHEN** 2 identities hosted on one node, both holding a replica of one namespace, run a session in process
- **THEN** both report it with the node's own id as the counterpart and no session id
