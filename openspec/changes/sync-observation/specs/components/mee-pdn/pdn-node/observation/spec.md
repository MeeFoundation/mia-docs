# Observation

## Purpose

The runtime's observation surface for tests that measure sync in a [pod](../../../../architecture/language/pod.md) from outside the process: one subscription per hosted identity and pod, covering the pod's membership store and record store and yielding numbered records, a join that opens that subscription before the joiner's first session, and a record listing of the record store with each entry's verdict, which starts no session. It exists only with the runtime's test-only feature, and like every observation-only helper behind that feature it observes and never arranges ([product-path-arrangement](../../../../code-practices/product-path-arrangement.md)). The records are built from the store's ordered subscription ([change subscription](../../data-layer/change-subscription/spec.md)), the listing from the record view of the [pod stores](../../data-layer/pod-store/spec.md); the tests that read them are in `pdn-app/sync-test/`.

## ADDED Requirements

### Requirement: A subscription follows one hosted identity's stores of one pod

The runtime SHALL, behind the test-only feature, open a subscription to the stores of one pod held by one hosted identity — both stores, or the membership store alone on a tombstone — and SHALL refuse it when the identity is not hosted here or holds no store of that pod, whoever else on this node holds one. The runtime's state lock SHALL NOT be held while the subscription runs.

**Example:** a node hosts identities A and B; only B is a member of pod `ad58a3faa04cdc5576c8dc5823a347c6`.

| subscription asked for | answer |
|---|---|
| B, the pod | opened, on both stores |
| A, the pod | refused: A holds no store of it |
| C (not hosted), the pod | refused: not hosted |

#### Scenario: A member is served

- **WHEN** a hosted member of a pod subscribes to it, and another member then places a record
- **THEN** the subscription reports that record's remote insert on the record store

#### Scenario: A held state lock does not stall a subscription
- **WHEN** a subscription is open and the runtime's state lock is held by another call while the identity's replica receives a session
- **THEN** the subscription yields that session's records before the lock is released

#### Scenario: A co-located identity without the pod is refused

- **WHEN** another identity on the same node, holding no store of the pod, subscribes to it
- **THEN** the subscription is refused and reports nothing of the pod

### Requirement: Every record is numbered on its subscription

Each subscription SHALL carry an identifier new to it, and each record it yields SHALL carry that identifier and a sequence number counting from 0 by 1 within it, across both stores. A lag notice of either store SHALL become a `lagged` record naming that store, numbered like any other. Neighbour events SHALL be dropped before numbering. A consumer that sees the sequence skip a number SHALL be able to conclude that a record was lost after the runtime. Within one store the records SHALL keep the order of the store's ordered subscription; between the two stores no order is promised.

**Example:** a subscription whose record store dropped events, and a re-subscription.

| `sub` | `seq` | `store` | `kind` |
|---|---|---|---|
| `c41e0a9d7f22b813` | 0 | `records` | `insert_remote` |
| `c41e0a9d7f22b813` | 1 | `records` | `lagged` |
| `c41e0a9d7f22b813` | 2 | `membership` | `sync_finished` |
| `07b2f6e1a9d34c55` | 0 | `records` | `insert_remote` (a new subscription) |

#### Scenario: Records count from 0 without gaps

- **WHEN** a subscription yields records of both stores while its consumer keeps up
- **THEN** their sequence numbers are 0, 1, 2 and so on without a gap, all under one subscription identifier

#### Scenario: A store lag becomes a numbered record

- **WHEN** a store drops events on a subscription and reports a lag notice
- **THEN** the subscription yields a `lagged` record naming that store and carrying the next sequence number, and the numbering continues after it without a gap

#### Scenario: A new subscription has a new identifier

- **WHEN** a consumer subscribes again to the same pod
- **THEN** the new subscription carries an identifier different from the earlier one and counts from 0

### Requirement: The runtime stamps records as the stores produce them, whatever its consumer's pace

The runtime SHALL take events off each store's ordered subscription, stamp `t`, number them and turn them into records in a task of its own, which runs at the pace the stores produce events and never waits on the consumer. It SHALL hold the records for the consumer in a buffer of at most 262,144 records, which takes memory only for the records waiting in it; the consumer's next read SHALL take the oldest record from that buffer. When the buffer is full, the runtime SHALL drop the records that do not fit, without numbering them, and SHALL yield, as soon as the buffer has room, one `lagged` record for each store that lost records, numbered like any other. The task SHALL end when the consumer drops the subscription.

**Example:** a consumer that reads nothing from 10.0 to 15.0 seconds while a session inserts 300 entries between 10.2 and 10.9 seconds.

| record read at 15.0 seconds | its `t` |
|---|---|
| the session's first `insert_remote` | 10.2 seconds |
| the session's 300th `insert_remote` | 10.9 seconds |
| the session's `sync_finished` | 10.9 seconds |

#### Scenario: A consumer that reads late still receives the time of production

- **WHEN** a consumer reads nothing for 5 seconds while a peer's writes reach the replica, and then reads every record waiting for it
- **THEN** it receives every record with no `lagged` and no gap; the `t` of each insert lies after the first write and before the read, and the `t` of each finished session lies between that session's finish and the read — not at the time of the read

#### Scenario: A full buffer is reported as a lag

- **WHEN** more records wait for a consumer than the buffer holds
- **THEN** the consumer receives the records that fit, then a `lagged` record naming each store that lost records and carrying the next sequence number, and the numbering continues after it without a gap

### Requirement: An observed join subscribes before the joiner's first session

The runtime SHALL, behind the test-only feature, offer a join that observes: it SHALL run the product's join dialogue for one hosted identity on one invite, import both stores of the pod, open the subscription of that identity to the pod before either store's sync starts, then start both stores' sync and wait as the product's join waits, and SHALL answer the pod together with the open subscription. A catch-up that outlasts the join's wait SHALL leave the pod recorded, as the product's join does, and SHALL answer the pod and the subscription all the same, the catch-up going on in the subscription. A join refused or failed before the import SHALL answer as the product's join answers it and open no subscription. The acts the join performs, and the order of them, SHALL be the product join's; only the moment the observation starts differs.

**Example:** a phone joins a pod that holds 10,000 records; its first record-store session carries 6,000 of them and finishes at 9 seconds, when the join returns, and later sessions the rest by 15 seconds.

| join | what the joiner's subscription holds |
|---|---|
| the observed join | an `insert_remote` of every record from 0 seconds, the first 6,000 before the first record-store `sync_finished`; the last `content_ready` at about 15 seconds |
| the product's join, then a subscription | nothing of the first 6,000; the records of later sessions only |

#### Scenario: A joiner's first session is reported from its first insert

- **WHEN** a member joins a pod that holds records through the observed join
- **THEN** its subscription holds an `insert_remote` of every record the pod held, each before the record-store `sync_finished` of the session that carried it, the joiner's first session included, and the subscription's numbering starts at 0 with no gap

#### Scenario: A product join followed by a subscription misses the first session

- **WHEN** a member joins the same pod through the product's join and subscribes once the join returns
- **THEN** the subscription holds no `insert_remote` of the records the joiner's first session carried

#### Scenario: A refused observed join opens no subscription

- **WHEN** an identity asks for the observed join on an invite already consumed
- **THEN** the join is refused as the product's join refuses it, no subscription is opened, and no record of the pod is reported to it

### Requirement: A record carries what the sync tests read

A record SHALL carry its subscription identifier, its sequence number, its kind, the time the runtime took the event off the store's ordered subscription, the pod and the store (`membership` or `records`), and for each kind: for a local or remote insert (`insert_local`, `insert_remote`), the entry's key as text, its own timestamp, its content hash and length, and for a remote insert the sending node and the content status (`complete`, `incomplete` or `missing`); for a completed download (`content_ready`), the content hash; for the end of a session's downloads, `pending_content_ready` and nothing more; for a finished session (`sync_finished`), the counterpart node, the origin (`connect` or `accept`), the session id when there is one, the start and finish times, whether it succeeded, the error text and stage of a failure, and the counts sent and received when the store reports them. Every time SHALL be whole microseconds since the Unix epoch on this node's clock, every identifier and hash the lowercase text its type prints, and every key its UTF-8 text. The record SHALL have one JSON form, the same from every host. A completed download is reported once per content hash, and not at all for a payload the node already held; a test that reads arrival per record makes every record's payload unique, and reads a remote insert whose content is complete as ready at its own time.

**Example:** the serving side of the record-store session that carried `by/<w3>/immutable-document/<a>/1`, as one line.

```json
{"sub":"5e0d…","seq":3120,"kind":"sync_finished","t":1790000044051000,"pod":"ad58a3faa04cdc5576c8dc5823a347c6","store":"records","peer":"…","origin":"accept","session":"9f3a…","started":1790000043900000,"finished":1790000044050000,"ok":true,"sent":12,"received":0}
```

#### Scenario: A local insert carries the timestamp the entry carries

- **WHEN** a member places a record and another member later receives it
- **THEN** the writer's `insert_local` record and the reader's `insert_remote` record name the record store and carry the same key, the same content hash, and the same entry timestamp

#### Scenario: A session's two stores are told apart

- **WHEN** a member's session with another member's device reconciles the membership store and then the record store
- **THEN** the subscription yields a `sync_finished` naming `membership` and one naming `records`, each with that device's node as the counterpart

### Requirement: A store's stream closes with the store, and the subscription ends with the runtime

When a store's subscription ends while the runtime runs — the record store forgotten on a removal its member folds, or on a leave — the subscription SHALL yield a `closed` record naming that store and SHALL go on reporting the other store. A subscription opened on a tombstone SHALL yield `closed` for the record store as its first record. When the runtime stops, the subscription SHALL end with no further record. A subscription SHALL NOT resume: a pod joined again, or a runtime started again, is observed by a new subscription.

**Example:** owner w1 removes member k at 20 seconds. k's subscription:

| `seq` | `store` | `kind` |
|---|---|---|
| 310 | `membership` | `insert_remote` of the removaled event in k's chain |
| 311 | `records` | `closed`: k folded its own departure and forgot the record store |
| 312 | `membership` | `sync_finished`: the tombstone keeps reconciling |

#### Scenario: A removal closes the removaled member's record stream

- **WHEN** an owner removes a member and the removaled member's node folds the removal
- **THEN** the removaled member's subscription yields `closed` for the record store, no record placed in the pod afterwards reaches it, and its membership store's records continue

#### Scenario: A leave closes the record stream

- **WHEN** a member leaves the pod while subscribed to it
- **THEN** its subscription yields `closed` for the record store and goes on reporting the membership store

#### Scenario: A subscription on a tombstone starts closed

- **WHEN** a former member subscribes to the pod whose record store it has forgotten
- **THEN** the first record is `closed` for the record store, and the membership store's records follow

#### Scenario: A stopped runtime ends its subscriptions

- **WHEN** the runtime stops while a subscription is open
- **THEN** the subscription ends without a `closed` record, and a subscription on the runtime started again on the same directory carries a new identifier and counts from 0

### Requirement: The record listing reports every entry of the record store with its verdict and starts no session

The runtime SHALL, behind the test-only feature, list one hosted identity's record store of one pod as the record view holds it: one item per entry, never merged by key, each with its key, its author, its content hash, its length, whether its payload is present, the payload when it is and the caller asks for payloads, and its verdict — `counted`, `not_yet`, `for_nothing` or `outside_layout` — with the reason the record view names for any verdict other than `counted`. The hash and the length SHALL be reported whether or not the payload has arrived. A listing asked for without payloads SHALL read no payload and report everything else unchanged, so a reader of large records — a phone — lists its pod without holding every payload in memory at once. The listing SHALL start no session. It SHALL be refused when the identity is not hosted here or holds no record store of the pod, a tombstone included.

**Example:** the phone's listing after w3 placed 2 immutable-documents, one payload still on its way, and a forger wrote at the first one's key with an author no statement of w3 lists.

| `key` | `author` | `present` | `verdict` |
|---|---|---|---|
| `by/<w3>/immutable-document/<a>/1` | w3's device | yes, with its payload | `counted` |
| `by/<w3>/immutable-document/<b>/1` | w3's device | no, with its hash and length | `not_yet`, `payload` |
| `by/<w3>/immutable-document/<a>/1` | the forger's | yes, with its payload | `for_nothing`, `author_not_actor_device` |

#### Scenario: A placed record is listed counted, beside a forged entry at its key

- **WHEN** a member places a record and a forged entry is written at the same key under an author no statement of that member lists, and both reach a reader
- **THEN** the reader's listing holds both entries, the member's `counted` with its payload and the forged one `for_nothing`

#### Scenario: A listing without payloads reads none
- **WHEN** a reader that holds a placed record asks for the listing without payloads
- **THEN** the listing holds the record `counted` and present, with its hash and length and no payload

#### Scenario: An identity without the record store is refused the listing

- **WHEN** a co-located identity holding no store of the pod, or a removed member that has forgotten the record store, asks for the listing
- **THEN** the listing is refused and reports no entry

#### Scenario: The listing starts no session

- **WHEN** a member of a pod whose interval is 1 hour takes the record listing while its subscription is open
- **THEN** the subscription reports no session starting within 10 seconds of the listing, while a session asked for in the same arrangement is reported

### Requirement: The observation surface exists only with the test-only feature

The subscription, the observed join and the record listing SHALL be compiled only with the runtime's test-only feature, so a build without it does not contain them. With the feature they SHALL compile in a release build.

**Example:**

| build | subscription, observed join and listing |
|---|---|
| `cargo build -p pdn-node` | absent |
| `cargo build --release -p pdn-node --features test-util` | present |

#### Scenario: A product build contains none of the calls

- **WHEN** the runtime is built without its test-only feature
- **THEN** none of the subscription, the observed join and the record listing is part of its surface
