# Change subscription

## Purpose

What a subscription to a replica's events promises its consumer and costs the store — the runtime's connection armer and grant binder reading the directory's and the connection metadata store's change streams, a directory's catch-up wait, and any consumer of the store's event interface. Events are a hint to read the replica again, never a record of it: nothing a subscriber does, reading or not, holds up the store, and a subscriber that falls behind learns that it did.

## Requirements

### Requirement: A subscriber never holds up the store

A subscription to a replica's events SHALL NOT make the store wait for its subscriber. When the subscriber's buffer is full, the store SHALL drop the event and SHALL follow the last event the subscriber still receives with a lag notice; the subscriber reads the notice only after every event it stands for was emitted, so a subscriber that reads the replica again on the notice finds every entry those events reported. The sessions and the downloads a dropped event reported are not recorded anywhere and are lost. Only the store's own live engine subscribes with a delivery that waits for room, since what it does on an event — announcing a local write, queueing a download — has no other trigger; no interface outside the store offers that delivery. Without this, a subscriber that stops reading stops the store behind it: every replica of the identity stops answering, sessions to its siblings and its counterparties stall, and a caller holding a lock the subscriber waits on never gets its answer.

#### Scenario: A subscriber that stops reading holds up no sync

- **WHEN** a device holds a subscription to its directory that it never reads, and a sibling writes more records than the subscription buffers
- **THEN** the device takes in every record, its own writes and reads go on answering, and the subscription, read at last, yields a change

#### Scenario: An unread subscription holds up neither entries nor their content

- **WHEN** a node holds a subscription to a replica that it never reads, and a peer writes more entries of distinct content than the subscription buffers
- **THEN** every entry and its content become readable on the node

#### Scenario: Dropped events leave one notice behind

- **WHEN** a subscriber stops reading, and the store emits more events than its buffer holds
- **THEN** the subscriber, reading again, receives the events that fitted and then one lag notice, and a drop after it has read that notice leaves a notice of its own

### Requirement: A change stream reports every change, a burst as one

The change streams of the directory and of the connection metadata store SHALL yield an item after every change of the replica — an entry written on this device, an entry arrived by sync, or a payload become readable — and SHALL yield a lag notice as one such item, so a consumer that reads the replica again on each item misses no change, and a burst the subscription could not buffer costs it one read.

#### Scenario: A lag notice reads as a change

- **WHEN** a directory's change stream was left unread while more changes arrived than it buffers
- **THEN** the directory lists every record the dropped changes reported, and the stream yields an item when read
