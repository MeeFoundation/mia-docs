---
status: accepted
date: 2026-11-23
---
# Pods and the assistant read Pod data through a graph query engine

> **Created by Claude, proofread by Max.**

## Context and Problem Statement

A pod's data is written as records into the pod's record store, and the record store is what syncs among the pod's members. Each [pod-tool](../language/pod-tool.md), the part of the app that keeps one kind of pod content, writes its own records: chat its messages, Info its claims, and later notes, the calendar and attachments.

Reading that data takes more than looking records up. A pod's screen shows one pod-tool's data a page at a time, newest first. A search in the app finds a word in chat and in attachments at once. The assistant fills its context with what several pods hold about one subject, by type and by field. These are queries over typed data and the relations between it, and [ADR-0001](0001-ai-assistant-data-storage.md) chose the graph database that holds it.

That graph is derived from the records. Each device builds its own from the records it holds, so the same records give the same graph on every member's device, and a graph that is lost is built again from them. One graph on a device holds every pod its person is in, which is what lets the assistant ask one question across pods. Both properties break if readers reach the graph database themselves. A reader that writes into the graph creates data no other device has and the next rebuild loses. A reader that leaves out a pod filter reads every pod on the device. And every reader depends on the database's schema and query language, so a change to either touches all of them.

How do pods and the assistant query pod data as a graph without reaching the graph itself?

## Decision Drivers

* A pod's data reaches only a party entitled to it: a pod's screens and pod-tools read that pod alone, and the assistant reads only the pods its person let it use.
* The record store is the only thing that syncs. The graph on each device follows from the records, and nothing else writes it.
* One query reaches the data of several pod-tools and, for the assistant, of several pods.
* A pod-tool decides which of its data is represented in the graph and how, and may keep some of it out. A pod-tool added later reaches every reader this way, with no reader changed.
* The engine depends on no pod-tool. Pod-tools use the engine's interface, and the record store and the engine work with no pod-tool present.
* Readers do not depend on the graph database's schema or query language.

## Considered Options

* A graph query engine between the readers and the graph.
* Readers query the graph database directly.
* Each pod-tool answers queries over its own records, with no shared graph.
* The graph syncs among the pod's members, and each reader queries its copy.

## Decision Outcome

Chosen option: "A graph query engine between the readers and the graph", because it is one place that keeps the graph derived from the records and every read within the pods its reader was given, and it answers a query across pod-tools and pods as one query.

The graph query engine is the only way to the graph:

* **It holds what pod-tools expose.** Each pod-tool exposes its data to the engine in a form the graph can hold, through the engine's interface. Which data is exposed, and as what, is the pod-tool's to decide; the engine takes only what a pod-tool exposes and never reaches into a pod-tool's data on its own. Before it answers, the engine brings the graph up to date with what was exposed.
* **It depends on no pod-tool.** Pod-tools are consumers of the engine's interface, not parts of the engine. The record store and the engine work with no pod-tool present, and a pod-tool is added or removed with no change to the engine.
* **It answers queries.** It finds, counts and pages through the data by type, field, subject, pod-tool and pod, and reads the types the data is typed by.
* **It scopes every query.** The pods and pod-tools a reader reaches are fixed when the reader is handed its access, by the code that hands it over, and no query widens them.
* **It writes no records and takes no writes into the graph.** A write goes to the record store, through the pod-tool that owns it.

**Example:** Alice opens the chat of her pod "Ginger", which holds 50 messages, some written by Bob on his laptop. Her screen asks the engine for chat's newest 20. The engine first applies the messages that synced since it last read, then returns "message 49" down to "message 30" and a total of 50. Bob's phone, asking the same of its own engine, gets the same page from the same records.

### Consequences

* Good, because the record store stays the only thing that syncs, and a device's graph can be built again from it at any time.
* Good, because which pods a read reaches is decided in one place, for every reader, the assistant included.
* Good, because a query across pod-tools or across pods is one query.
* Good, because the graph database and its schema can change behind the engine with no reader changed.
* Bad, because a read waits until the engine has applied the records it has not seen. A device with a large backlog pays for that on its first read.
* Bad, because pods in one shared graph are kept apart by a filter the engine applies to every query. A query path that misses it reads every pod on the device, so every path needs a test that a pod outside its scope contributes nothing.
* Neutral, because a pod-tool's data is readable only as far as the pod-tool exposes it to the engine. Pod-tools offer no other way to read their data, so what a pod-tool keeps out of the graph no other reader reaches.

## Validation

The decision holds when no reader reaches the graph database except through the engine, a pod outside a reader's scope contributes nothing to any of its reads, a graph built again from the same records reads the same, and the record store and the engine build and answer queries with no pod-tool present.

## Pros and Cons of the Options

### A graph query engine between the readers and the graph

* Good, because access, consistency with the records and the query language are each handled once.
* Bad, because every reader goes through one component, which must offer every kind of query a reader needs.

### Readers query the graph database directly

* Good, because a reader has the whole query language.
* Bad, because every reader applies the pod filter itself, and one that forgets it reads every pod on the device.
* Bad, because a reader can write into the graph, and what it writes exists on one device only and is gone after a rebuild.
* Bad, because every reader depends on the schema and the query language.

### Each pod-tool answers queries over its own records, with no shared graph

* Good, because there is no graph to keep apart from the records.
* Bad, because a search across pod-tools is one query per pod-tool, merged by the reader.
* Bad, because a pod-tool with more than a screenful of records needs indexes and paging, so each pod-tool ends up with a query engine of its own.

### The graph syncs among the pod's members, and each reader queries its copy

* Good, because a new device receives a graph already built.
* Bad, because two things sync where one is enough, and the two can disagree.
* Bad, because a pod's graph on one device holds data that belongs to one member only, such as that member's embeddings, and it would have to be kept out of what syncs.
