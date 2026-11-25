# Proposal: graph-query-engine

> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

## Why

[ADR-0019](../../specs/architecture/adr/0019-pods-read-through-a-graph-query-engine.md) puts a graph query engine between the readers of pod data and the graph that holds it: pod-tools write records, every device builds its own graph from them, and every reader queries that graph through the engine. This change specifies the engine, as the mee-pdn crate `graph-query-engine`.

The engine runs in pdn-agent, the assistant's prototype, and its tests pass there. This change is written from that implementation: the code came first, and the specification states what the code does and its tests prove. Code moves into `crates/graph-query-engine` only where it conforms to this specification in full, and each such move is opened as two pull requests, one here and one in mee-pdn, reviewed together.

**Example:** Alice opens the chat of "Ginger", which holds 50 messages. Her screen asks the engine for the newest 20; the engine applies what synced since its last read and returns "message 49" down to "message 30", and 50 in all. Bob's phone, asking its own engine, gets the same page from the same records.

## What Changes

- **Materialization interface.** A pod-tool exposes its data by registering a materialization, which alone decides what each of its records stands for in the graph, or that it stands for nothing, and which types its zone holds. The engine depends on no pod-tool. The newest record under each key stands, and the same records give the same claims on every device.
- **Catch-up.** One graph per identity on a device, holding every pod it reads. Before it answers, the engine adds what is new, replaces what changed and takes out what is gone; a backlog loads in bulk, the rest one claim at a time.
- **Ontology registry.** The graph is typed by mia-ontologies with the application ontology on top, loaded into the graph, a type read as each type it extends.
- **Queries.** A handle reaches only the pods and zones it was made for. Through it a reader finds, counts and pages through claims by type, field and subject, and every result says which pod, pod-tool, author, time and device it is from.

## Out of Scope (deferred)

- **Writing through the graph.** pdn-agent's Info writes claims through its graph handle into its records (`PodGraph::assert`). Every write here goes to the record store through a pod-tool, and that path stays in pdn-agent.
- **The pod-tools' own materializations.** The engine specifies only the interface a pod-tool registers through. In pdn-agent the engine carries chat's and Info's materializations built in, which this change does not allow: they stay in pdn-agent and register from there, until a later change specifies them for a crate of pod-tools.
- **Reads implemented and not specified here:** the types present in a view with their counts per pod, and the number of claims and type names a subject has. They move once they are specified.
- **Skipping a zone whose records have not changed**, by the record store's version. It needs a version mee-pdn's record store offers (design, Open Questions).
- **Embeddings and member-private data**, and anything of the assistant.
- **Operating conditions with no effect here:** an unstable connection and a device linking late change nothing in the engine, which reads only the records its device holds. The others are walked in the design.

## Capabilities

### New Capabilities

- `components/mee-pdn/graph-query-engine/materialization-interface`: how a pod-tool exposes its data to the engine, and what the engine does with it.
- `components/mee-pdn/graph-query-engine/catch-up`: how the graph is brought up to date with the records.
- `components/mee-pdn/graph-query-engine/ontology-registry`: the types the graph is typed by.
- `components/mee-pdn/graph-query-engine/queries`: what the engine answers, and within which pods and zones.

### Modified Capabilities

None.

## Impact

- **A new crate in mee-pdn**, `crates/graph-query-engine`, on LadybugDB ([ADR-0001](../../specs/architecture/adr/0001-ai-assistant-data-storage.md)), which brings a C++ library behind a foreign-function boundary into the workspace.
- **The record store's records, as a pod-tool's keyed records.** The engine reads a pod-tool's records by key, with author, time and device. mee-pdn's records carry no pod-tool and no key, and are never replaced or removed. How mee-pdn carries them is the first open question, and settling it comes before catch-up moves.
- **The SDK** exposes the engine's reads to the app; that is the SDK's change, not this one.
