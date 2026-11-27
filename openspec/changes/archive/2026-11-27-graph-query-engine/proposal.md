# Proposal: graph-query-engine

> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

## Why

[ADR-0019](../../../specs/architecture/adr/0019-pods-read-through-a-graph-query-engine.md) puts a graph query engine between the graph database and all code that uses it: pod-tools write records, every device builds its own graph from them, and every reader queries that graph through the engine. This change specifies the engine, as the mee-pdn crate `graph-query-engine`.

The engine is written and its tests pass: the specification states what its code does and its tests prove, and the code is added to mee-pdn as one crate, `crates/graph-query-engine`, in a pull request reviewed together with this change. The crate knows nothing of the application built on it: an application registers its pod-tools' materializations, hands the engine each zone's records, and reads the graph through the engine's handles, and none of LadybugDB is in what it sees.

**Example:** Alice opens the notes of "Ginger", which holds 50 of them. Her screen asks the engine for the newest 20; the engine applies what synced since its last read and returns "note 49" down to "note 30", and 50 in all. Bob's phone, asking its own engine, gets the same page from the same records.

## What Changes

- **Materialization interface.** A pod-tool exposes its data by registering a materialization, which alone decides what its records stand for in the graph, or that they stand for nothing, and which types and relations its zone holds. A pod-tool reflects its data in the structure that suits it, as nodes and relations; a claim, a node about a subject, is one shape among them. A materialization receives every record under a key, oldest first. The engine depends on no pod-tool, and the same records give the same nodes and relations on every device.
- **Catch-up.** One graph per identity on a device, holding every pod it reads. Before it answers, the engine adds what is new, replaces what changed and takes out what is gone; a backlog loads in bulk, the rest one key at a time. What does not fit its type or its tool ontology is left out. A zone whose records have not changed is not read again, where the record store offers a version.
- **Ontology registry.** The graph is typed by mia-ontologies with the application ontology on top, loaded into the graph, a type read as each type it extends. Any code can check a value against its type's shape.
- **Queries.** A handle reaches only the pods and zones it was made for. Through it a reader finds, counts and pages through nodes by type, field and subject, follows their relations, reads which types are present in each pod and how much is claimed about each subject, and every result says which pod, pod-tool, member, time and device it is from. A pod-tool reads other pod-tools' data through a view, never their records. A handle takes no writes.
- **Vector index.** An owner indexes texts with vectors it made, and finds the texts nearest to a vector. The index runs on every platform the app is built for, with nothing to install.

## Out of Scope (deferred)

- **Pod-tools' own materializations and writes.** The engine specifies only the interface a pod-tool registers through, and the check a pod-tool's value must pass; what a pod-tool's records stand for, and how it writes them, are that pod-tool's to specify.
- **An application's use of the engine:** what it indexes and how it makes vectors, what it asks, and how it carries a pod-tool's records in its record store.
- **Operating conditions with no effect here:** an unstable connection and a device linking late change nothing in the engine, which reads only the records its device holds. The others are walked in the design.

## Capabilities

### New Capabilities

- `components/mee-pdn/graph-query-engine/materialization-interface`: how a pod-tool exposes its data to the engine, and what the engine does with it.
- `components/mee-pdn/graph-query-engine/catch-up`: how the graph is brought up to date with the records.
- `components/mee-pdn/graph-query-engine/ontology-registry`: the types the graph is typed by, and the check of a value against its type.
- `components/mee-pdn/graph-query-engine/queries`: what the engine answers, and within which pods and zones.
- `components/mee-pdn/graph-query-engine/vector-index`: search by meaning over texts and the vectors their owner made.

### Modified Capabilities

None.

## Impact

- **A new crate in mee-pdn**, `crates/graph-query-engine`, on LadybugDB ([ADR-0001](../../../specs/architecture/adr/0001-ai-assistant-data-storage.md)), which brings a C++ library behind a foreign-function boundary into the workspace, built with its vector extension linked in. The crate is the only code that depends on LadybugDB; none of LadybugDB's types are in its interface.
- **Records reach the engine through an interface the application implements.** The engine reads each zone's records, each with the key its pod-tool chose, its member, its time, its device where it carries one, and its bytes; how the application keeps them in mee-pdn's record store is the application's (design, D11).
- **The workspace's build.** LadybugDB comes prebuilt, with the vector extension linked in, as a release of MeeFoundation/ladybug; the workspace's Cargo configuration names the release, and the lbug crate downloads its archive. CI and the rest of mee-pdn do not change.
- **The SDK** exposes the engine's reads to the app; that is the SDK's change, not this one.
