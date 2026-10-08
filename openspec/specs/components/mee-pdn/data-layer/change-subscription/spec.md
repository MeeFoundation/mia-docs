# Change subscription

## Purpose

What a subscription to a replica's events promises its consumer and costs the store — the runtime's connection armer and grant binder reading the private metadata store (PMS) and the connection metadata store's change streams, a PMS's catch-up wait, and any consumer of the store's event interface. Events are a hint to read the replica again, never a record of it: nothing a subscriber does, reading or not, holds up the store, and a subscriber that falls behind learns that it did.

## Requirements

### Requirement: A subscriber never holds up the store

A subscription to a replica's events SHALL NOT make the store wait for its subscriber. A subscription merges two buffers of 256 events each: one for the replica's inserts — an entry written on this device or arrived by sync — and one for the live events — a payload become readable, a session finished, a neighbor up or down. When either buffer is full, the store SHALL drop the event and SHALL follow the last event that buffer still delivers with a lag notice of that buffer's own; the subscriber reads a notice only after every event it stands for was emitted, so a subscriber that reads the replica again on the notice finds every entry those events reported. The guarantee holds per buffer: one burst can yield two lag notices, one from each buffer, and events of one buffer can arrive after the other buffer's notice. The sessions and the downloads a dropped event reported are not recorded anywhere and are lost. Only the store's own live engine subscribes with a delivery that waits for room, since what it does on an event — announcing a local write, queueing a download — has no other trigger; no interface outside the store offers that delivery. Without this, a subscriber that stops reading stops the store behind it: every replica of the identity stops answering, sessions to its siblings and its counterparties stall, and a caller holding a lock the subscriber waits on never gets its answer.

**Example:** a1 holds a subscription to Alice's PMS that it never reads; a2 connects 600 peers, one `connections/<peer-hex>` record each.

| step | a1's store | a1's subscription |
|---|---|---|
| a2's 600 records arrive | takes in all 600 | keeps the `InsertRemote` events that fit (the 256-slot insert buffer, its last slot for the `Lagged`, and 64 on the RPC stream), drops the rest; the live buffer does not fill, since the 600 records share one payload |
| a1 connects Bob | the write answers | — |
| a1 reads the subscription at last | — | the inserts that fitted, then their `Lagged`, with the live events merged in, some of them after it |
| a1 lists connections on the `Lagged` | all 601 records | a drop in either buffer after this read leaves a `Lagged` of that buffer's own |

#### Scenario: A subscriber that stops reading holds up no sync

- **WHEN** a device holds a subscription to its PMS that it never reads, and a sibling writes more records than the subscription buffers
- **THEN** the device takes in every record, its own writes and reads go on answering, and the subscription, read at last, yields a change

#### Scenario: An unread subscription holds up neither entries nor their content

- **WHEN** a node holds a subscription to a replica that it never reads, and a peer writes more entries of distinct content than the subscription buffers
- **THEN** every entry and its content become readable on the node

#### Scenario: Dropped events leave one notice behind per buffer

- **WHEN** a subscriber stops reading, and the store emits more events into one of the subscription's two buffers than it holds
- **THEN** the subscriber, reading again, receives that buffer's events that fitted and then one lag notice for them, with the other buffer's events merged in before or after it, and a drop in that buffer after the subscriber has read the notice leaves a notice of its own

### Requirement: The live engine takes its events while it waits on the store

The store's live engine SHALL keep taking the events of its waiting delivery while it waits for any answer of the store, and SHALL handle them in the order they arrived once the step that waited is over. The store waits for room in that delivery's buffer of 1,024 events and answers nothing meanwhile, so an engine that waited on the store without reading would leave both waiting for good as soon as the store had more events to emit ahead of the engine's request than the buffer holds. A first catch-up does exactly that: a node that holds nothing of a store receives all of the store's entries in one message, and the store inserts them in one step. While the engine waits on anything other than the store — gossip, the blob store — the store still waits for it, so a session cannot run ahead of the engine.

**Example:** Bob's node imports a ticket to a store of 2,000 entries, and its engine restarts the store's sync while the catch-up runs.

| step | Bob's store | Bob's engine |
|---|---|---|
| the catch-up message arrives | inserts its 2,000 entries in one step, one insert event each | asks the store for the store's recorded peers; the request waits behind the insert step |
| the 1,025th insert event | waits for room in the engine's buffer | takes events out of the buffer while it waits, and holds them |
| the insert step ends | answers the engine's request | handles the 2,000 held events in order, queueing a download for each entry |

#### Scenario: A catch-up larger than the engine's buffer finishes while the engine asks the store

- **WHEN** a node imports a store of more entries than the engine's buffer holds, and its engine asks the store for the store's recorded peers again and again during the catch-up
- **THEN** the node holds every entry, and each of the engine's requests is answered

### Requirement: A change stream reports every change, dropped ones by a lag notice

The change streams of the PMS and of the connection metadata store SHALL yield an item after every change of the replica — an entry written on this device, an entry arrived by sync, or a payload become readable — and SHALL yield each lag notice as one such item, so a consumer that reads the replica again on each item misses no change, and a burst the subscription could not buffer costs it one read for each of the two buffers the burst overflowed.

**Example:** a2, Alice's second device, reads the `changes()` stream of her PMS while a1 opens a connection to Bob.

| `LiveEvent` on a2's replica | item | `get_ticket("connection-metadata/<bob-hex>/own")`, read again |
|---|---|---|
| `InsertRemote`: a1's `tickets/connection-metadata/<bob-hex>/own` | `Ok(())` | `Ok(None)`: the payload is still syncing |
| `ContentReady`: that ticket's payload lands | `Ok(())` | `Ok(Some(ticket))` |
| `InsertLocal`: a2 writes `connections/<carol-hex>` | `Ok(())` | unchanged |
| `NeighborUp`, `NeighborDown`, `SyncFinished`, `PendingContentReady` | none | — |
| `Lagged`: events dropped past a buffer, one per buffer | `Ok(())` | every change the dropped events reported |

#### Scenario: A lag notice reads as a change

- **WHEN** a PMS's change stream was left unread while more changes arrived than it buffers
- **THEN** the PMS lists every record the dropped changes reported, and the stream yields an item when read
