> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

## Context

[ADR-0019](../../specs/architecture/adr/0019-pods-read-through-a-graph-query-engine.md) puts a graph query engine between the graph database and all code that uses it. The engine is the crate `crates/graph-query-engine`:

- `src/db.rs` holds the graph on LadybugDB, its catch-up, its queries, the loading of the registry and the read handles.
- `src/materialize.rs` holds the materialization interface and the registry of materializations, which starts empty (D7); `src/record.rs` the interface the engine reads a zone's records through (D11).
- `src/lib.rs` holds the read interfaces `GraphReader`, `PodGraph` and `GraphView` and the types they return; `src/ontology.rs` the registry, `src/shape.rs` shapes, `src/query.rs` the query builder and `src/conform.rs` the check of a value against a shape.
- `src/vector.rs` holds the vector index.
- `build.rs` builds LadybugDB with its vector extension linked in.

Every scenario in this change's deltas is a test of the crate, on pod-tools its tests define, and the crate's tests need no application.

The code was written and tested before this specification, which states what it does.

## Goals / Non-Goals

**Goals:** specify the engine as a mee-pdn crate that knows nothing of the application built on it: what it does, through which interfaces, and what it is tested to do.

**Non-Goals:** the pod-tools' own materializations and writes; an application's use of the engine, and how it keeps records in mee-pdn's record store. The proposal lists them.

## Decisions

### D1. A pod-tool exposes its data through its materialization

A pod-tool registers a materialization, and it alone decides what the pod-tool's records stand for in the graph, or that they stand for nothing; a pod-tool can keep any of its data out of the graph that way. The engine reads a pod-tool's records only to hand them to that materialization, a key at a time, each record with the key the pod-tool chose, its member, its time, its device where it carries one, and its bytes. What a key holds in the graph is what the materialization makes of the key's records (D12). An edit is a newer record under the same key, and a removal a key whose records stand for nothing, or a key no record is under any more.

**Example:** a notes pod-tool's key `n1` holds "vet on Friday", then "vet on Saturday" written later. Its materialization takes the newer record, and its zone holds one note `n1`, "vet on Saturday".

**Rejected alternatives:**

- Every record a node of its own, with no key.
  - **Cons:** an edited note is read twice, as it was and as it is, and every reader has to work out which is current.
- The engine reading a pod-tool's records into nodes by a schema of its own.
  - **Cons:** the engine decides what a pod-tool's data means and what of it is readable, which is the pod-tool's to decide (ADR-0019).

### D2. One graph per identity on a device, with pods and zones as tags

Each identity hosted on a device has one graph, holding every pod it reads. Every node, relation, subject and value carries its pod, and every node, relation and value its zone. Every key in the graph is qualified by its pod, written with the pod id's length in front, so no pod id and node id run together into another pair's key. A query across pods is one query over one graph, filtered by pod and zone.

**Example:** the node `n1` of the pod-tool `notes` in the pod `ginger` is keyed `6:ginger/n1`, and that pod-tool's zone of the pod is `6:ginger/zone/notes`. Alice's graph holds "Ginger" and "Travel" side by side; Bob's, built from the same records of "Ginger", is a graph of his own.

**Rejected alternatives:**

- A graph per pod.
  - **Cons:** a query across pods becomes one query per pod, merged by the reader, and most of each graph is overhead, a pod being small.

### D3. The graph is held in memory and built from the records

The graph lives in memory, in the process that reads it, and is built from the records the first time each zone is read after the process starts. Nothing of it is kept across a restart, and nothing needs recovering after a kill: the records are the only state.

**Example:** the app starts on Alice's phone and opens "Ginger". The first read catches up every zone it reads from the records the phone holds; when the app is killed, the graph goes with it, and the next start builds it again.

**Rejected alternatives:**

- A graph kept on disk across restarts.
  - **Pros:** a start reads no backlog.
  - **Cons:** after a kill in the middle of a catch-up, the graph on disk and the records disagree, and the engine needs a way to tell how far the graph got.

### D4. A backlog loads in bulk; after it, one key per transaction

A zone with nothing applied yet that brings at least 32 nodes loads its nodes and relations in one bulk load: rows are staged as CSV files in a temporary directory and copied into the graph's tables. Zones with nothing applied yet caught up together load in one bulk load when there are at least 2 of them and 32 nodes between them. Every other key is applied in a transaction of its own, its nodes and relations together. A bulk load that fails clears what it loaded of its zones, and their keys are applied one by one.

**Example:** 500 pods of 10 records each, new to the graph, load in one bulk load of 5,000 nodes; the 5,001st record, written later, is applied on its own.

**Rejected alternatives:**

- Every key applied on its own.
  - **Cons:** each key's transaction commits on its own, some 50 ms a key on a phone's storage, so a backlog of 5,000 keys takes about 4 minutes.

### D5. A handle's pods and zones are fixed when it is made

A reader gets a handle from the code that serves it, made for a set of pods and, in each, the zones the reader may read. Every query through the handle is filtered to those pods and zones, and no query names others.

**Example:** the assistant's view of "Ginger" and "Travel" reads those two pods. A question that mentions a third pod still reads only those two.

**Rejected alternatives:**

- The pods named in each query.
  - **Cons:** whatever drives the query, a model reading a person's words among them, could name a pod its person did not let it read.

### D6. Types are read from the registry in the graph

The registry is loaded into the graph once, when the graph is made, and every type, shape and generalization is read from there.

**Example:** a reader asks for the shape of `mee:PetMedicationRecord:v1` and gets it from the graph's type tables, the same tables its nodes are typed by.

**Rejected alternatives:**

- Each reader reading the registry's files.
  - **Cons:** two places a type comes from, which can disagree.

### D7. The engine depends on no pod-tool

The engine carries no materialization of its own. Every pod-tool registers its materialization through the engine's interface, from its own code, which depends on the engine, never the reverse. The record store and the engine build and answer with no pod-tool present.

**Example:** mee-pdn built with the record store and the engine alone answers a reader's query for the shape of `mee:PetMedicationRecord:v1` and finds no nodes in any pod. A pod-tool registering its materialization makes that pod-tool's data readable with no change to the engine.

**Rejected alternatives:**

- The engine carrying the materializations of the pod-tools an application ships with.
  - **Pros:** no registration step for the pod-tools an application ships with.
  - **Cons:** the engine depends on those pod-tools and changes with each of them, and a pod-tool built in reads differently from one registered later.

### D8. The engine owns the graph database

The crate is the only code that depends on LadybugDB. Its interfaces carry none of LadybugDB's types, its query language or its schema, and no code outside it opens a LadybugDB database, for the graph or for anything else. The crate pins LadybugDB's version and builds it with the vector extension linked in, for every platform the app is built for.

**Example:** an application built on the crate names no `lbug`. Its pod-tools register materializations and check values through the crate, it makes each identity's graph through the crate, and it indexes and searches texts through the crate.

**Rejected alternatives:**

- The vector index left with the application, on a LadybugDB database of its own.
  - **Pros:** the engine stays about the graph alone.
  - **Cons:** a second client of LadybugDB outside the engine, which pins the version and links the vector extension a second time, and which a change of database breaks.
- A connection handed out for queries the engine does not offer.
  - **Cons:** every caller that takes it depends on the schema and the query language, and can read past the pod filter or write into the graph (ADR-0019).

### D9. Search by meaning is an index of its owner's

A vector index is a store of its own, apart from the graph, made by an owner that hands it texts with vectors it made. The engine makes no vectors and holds no model. An index lives in a temporary directory of its device, under an HNSW index by cosine distance, takes entries after it is made, and is removed when its owner lets go of it. A search keeps 1,000 candidates as it walks the index: LadybugDB's default of 200 lost the best match among 50,000 vectors that an exact search ranked first, and 500 found it, at 9 ms a search against 5 ms on the bench machine.

**Example:** the assistant indexes the texts it derived from Alice's pods, with vectors made by its own model, and asks for the 10 nearest to a question's vector. It gets 10 entries, each with the pod, text and labels it gave.

**Rejected alternatives:**

- Vectors kept on the graph's nodes.
  - **Cons:** the graph holds what pod-tools reflect, the same on every member's device (materialization interface). An index holds what one owner derived with one model and one model version, and differs from device to device.

### D10. Handles take no writes

A handle reads. A pod-tool that writes typed values checks each with the engine's value check (ontology registry), writes its record to the record store, and reads back through the engine what the record stands for.

**Example:** a pod-tool keeping medication records is asked to record `{"species": "cat"}` as `mee:PetMedicationRecord:v1`. The engine's check refuses it at `value.species`, and the pod-tool writes nothing.

**Rejected alternatives:**

- The engine writing a record for the pod-tool through the handle.
  - **Cons:** the engine writes records and knows a pod-tool's record format, which ADR-0019 and D7 rule out.

### D11. Records reach the engine through an interface the application implements

The engine reads a zone's records through its record-source interface, which the application implements for each zone it hands a handle: every record of that zone, each with the key its pod-tool chose, its member, its time, its device where it carries one, and its bytes, and, where it can tell, a version that grows whenever the zone's records change. The engine takes the member, the time and the device as the application gives them, orders a key's records by time and record id, and keeps nothing of a record but what its materialization makes of it. How the application keeps a pod-tool's records in mee-pdn's record store, and binds each pod-tool to its own records, is the application's.

**Example:** an application keeps the `notes` pod-tool's records in mee-pdn's record store. For the `notes` zone of "Ginger", it hands the engine every record of that pod-tool in "Ginger", 3 of them under the key `n1`, and the version of the pod's store. The engine hands the 3 records to the `notes` materialization, oldest first, and reads none of them again while the version stays the same.

**Rejected alternatives:**

- The engine reading mee-pdn's record store itself.
  - **Cons:** the engine would know how each application lays out a pod-tool's records in mee-pdn's record kinds, and change with it; and a host other than mee-pdn could not hand it records.

### D12. A materialization receives a key's records and returns typed graph data

A pod-tool reflects its data in whatever structure suits it. Claims are valued as data of high quality, and a pod-tool is not obliged to make them; other pod-tools understand its data through the tool ontologies pod-tools expose and share. A materialization receives every record under a key, oldest first, and returns the graph data they stand for: nodes, each of a type in its tool ontology with a value that conforms to that type's shape, and relations between them. A claim, a typed value about a subject, is one shape among them. A materialization that needs only the newest record takes it; one that merges a document's operations, or keeps a history, takes them all. The engine adds where each node comes from: its pod, its zone, its member, its time, and its device where the record carries one. The queries find nodes by type and field and follow their relations; finding by subject and reading subjects stay, for claims. The specification leads the code here: the engine is changed to D12 before it moves (Migration Plan).

**Example:** a chat pod-tool reflects each message as a node about no subject, linked to the message it follows. A notes pod-tool reflects "Ginger's flea treatment is due on the 3rd" as a claim about the subject `ginger`. A document pod-tool edited by two members at once reflects the document its operations merge into.

**Rejected alternatives:**

- One claim per key, from the key's newest record, as the engine does today.
  - **Cons:** every pod-tool's data becomes claims. Chat's messages are made claims about a subject named `conversation` that exists only to fill the slot, and a pod-tool that merges operations or keeps a history cannot, since it sees the newest record alone.

### D13. A node may be for some members alone

Not all of a pod-tool's data is for every member. A direct message in a pod's chat is a private conversation between two members, readable only by its participants, and one a member sends to their own agent in a pod's chat area stays theirs alone (mia-ontologies, `app-behavior.md`, "Chat Area" and "Pod Interface"). A materialization names, on such a node, the members it is for, from the records alone. The engine builds the node only into the graphs of those members' identities, with the relations that lead from it; a relation to it from a node every member reads leads to nothing in the other members' graphs. The materialization's output is the same on every device, and only the graphs it lands in differ. Keeping the records themselves off other members' devices is the application's; D13 is what the graph does with whichever records a device holds.

**Example:** in "Ginger", Alice sends Bob the direct message "Dan's birthday gift: the blue scarf". The node is in Alice's graph and Bob's, and not in Dan's: Dan's find of `app:Message:v1` in "Ginger" returns the group stream alone.

**Rejected alternatives:**

- A materialization that depends on its reader.
  - **Cons:** the same records give different nodes on different devices, and every catch-up needs the reader, which D1 and the materialization interface rule out.
- The node in every member's graph, filtered out at query time.
  - **Cons:** a query path that misses the filter reads every member's direct messages. A node that is not in a graph cannot leak from it.

## Operating conditions

- **Several identities on one node** changes the outcome: each identity has a graph of its own (catch-up, "Each identity on a device has one graph for every pod it reads").
- **One device or several** changes nothing in the engine, which builds each device's graph from the records that device holds, and a materialization depends on the records alone (materialization interface, "The same records give the same nodes and relations on every device").
- **The process ends without warning, the device restarts:** the graph is in memory (D3), so a kill loses nothing the records do not hold, and the first read after a start pays the catch-up of every zone it reads. A vector index goes with its process too, and its owner makes it again (D9).
- **The disk fills:** a bulk load stages its rows as files, and a full disk fails it. The engine then applies the keys one at a time, in memory. This path has no scenario yet (tasks, 2.3).
- **Clocks disagree, and step back:** a key's records are handed over oldest first by time, so for a materialization that takes the newest record, an edit made on a device whose clock is behind loses to an older edit made elsewhere. The record store orders a key's entries by the same dates, so the graph agrees with the store (Risks).
- **Membership moves:** a reader that is no member of a pod is refused a view of it. Nodes of that pod already in its graph stay in memory until the process ends (Open Questions).
- **An unstable connection, a device linking late:** no effect. The engine reads only what its device holds; what arrives later is read on the next read.

## Risks / Trade-offs

- **Pods kept apart by a filter.** Every query of a shared graph is filtered by pod and zone. A query path that misses the filter reads every pod on the device, so every read path has a test that a pod outside its scope contributes nothing.
- **Clock order decides edits.** Two members editing one key from devices whose clocks disagree keep the edit with the later date, which may be the earlier one in fact. The record store makes the same choice.
- **A materialization that depends on the device** makes two members' graphs differ, and nothing detects it.
- **A first read pays the backlog.** A device with many records builds its graph on its first read after every start.
- **A vector index is scoped by its owner alone.** A search reaches every entry its owner put in, with no pod filter of the engine's. An owner that indexes a pod its reader may not read lets that reader search it.
- **The vector extension's linking.** The crate's build script links the extension's archive with a link-library directive, which Cargo passes to every binary built against the crate, an application for Android among them; a link argument would reach the crate's own linking alone.
- **LadybugDB in the workspace's build.** The crate builds LadybugDB, a C++ library, from source, which lengthens every build of the workspace and adds its dependencies to the lockfile.

## Migration Plan

The crate is new, and nothing in mee-pdn depends on it or changes with it. An application adopts it by depending on it, registering its pod-tools' materializations and implementing the record-source interface for each zone it reads.

## Open Questions

**1. A handle made before its reader's removal.** A removed member gets no new view, and the nodes its graph holds of the pod stay in memory until the process ends. Whether a handle made before the removal reads them is untested. Recommendation: a test of it, and a requirement that matches.
