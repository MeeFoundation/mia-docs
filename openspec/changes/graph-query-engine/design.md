> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

## Context

[ADR-0019](../../specs/architecture/adr/0019-pods-read-through-a-graph-query-engine.md) puts a graph query engine between the readers of pod data and the graph. The engine runs in pdn-agent, the assistant's prototype: `src/sdk/ladybug.rs` holds the graph, its catch-up and its queries, `src/sdk/materialize.rs` the registration of materializations, `src/graph/ontology.rs` the registry and `src/graph/mod.rs` the read handles, `GraphView` and `PodGraph`. The registry of materializations carries chat's (`pod_tool::chat::Materialize`) and Info's (`ladybug::Claims`) built in; D7 does not allow that, so neither moves with the engine: both stay in pdn-agent and register from there. Its tests are `tests/ladybug.rs` and `tests/materialize.rs`, and every scenario in this change's deltas is one of them.

The specification follows the code here, the reverse of the usual order. It states what the code does, the code moves into mee-pdn's `crates/graph-query-engine` where it conforms in full, and what the code does beyond the specification stays in pdn-agent until it is specified.

## Goals / Non-Goals

**Goals:** specify the engine as it runs, so its parts can move into mee-pdn one by one, each checked against the specification; name what stands between it and mee-pdn's record store.

**Non-Goals:** writing through the graph; the pod-tools' own materializations; reads the code has and this change does not specify; anything of the assistant. The proposal lists them.

## Decisions

### D1. A pod-tool exposes its data through its materialization, and the newest record under each key stands

A pod-tool registers a materialization, and it alone decides what each of the pod-tool's records stands for in the graph, or that it stands for nothing; a pod-tool can keep any of its data out of the graph that way. The engine reads a pod-tool's records only to hand them to that materialization, each with the key the pod-tool chose, its author, its time, its device where it names one, and its bytes. Under each key the newest record stands, by time and then by record id, and the claim is what the pod-tool's materialization makes of it; a key whose newest record stands for nothing holds no claim. An edit is a newer record under the same key, and a removal a key that holds no claim any more.

**Example:** chat's key `m1` holds "vet on Friday", then "vet on Saturday" written later. Chat's zone holds one claim `m1`, "vet on Saturday".

**Rejected alternatives:**

- Every record a claim of its own.
  - **Cons:** an edited note is read twice, as it was and as it is, and every reader has to work out which is current.
- The engine reading a pod-tool's records into claims by a schema of its own.
  - **Cons:** the engine decides what a pod-tool's data means and what of it is readable, which is the pod-tool's to decide (ADR-0019).

### D2. One graph per identity on a device, with pods and zones as tags

Each identity hosted on a device has one graph, holding every pod it reads. Every claim, subject and value carries its pod, and every claim and value its zone. Every key in the graph is qualified by its pod, written with the pod id's length in front, so no pod id and claim id run together into another pair's key. A query across pods is one query over one graph, filtered by pod and zone.

**Example:** chat's claim `m1` in the pod `ginger` is keyed `6:ginger/m1`, and chat's zone of that pod is `6:ginger/zone/chat`. Alice's graph holds "Ginger" and "Travel" side by side; Bob's, built from the same records of "Ginger", is a graph of his own.

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

### D4. A backlog loads in bulk; after it, one claim per transaction

A zone with nothing applied yet that brings at least 32 claims loads them in one bulk load: rows are staged as CSV files in a temporary directory and copied into the graph's tables. Zones with nothing applied yet caught up together load in one bulk load when there are at least 2 of them and 32 claims between them. Every other claim is added in a transaction of its own. A bulk load that fails clears the claims of the zones it was loading, and they are added claim by claim.

**Example:** 500 pods of 10 records each, new to the graph, load in one bulk load of 5,000 claims; the 5,001st record, written later, is added on its own.

**Rejected alternatives:**

- Every claim added on its own.
  - **Cons:** each claim's transaction commits on its own, some 50 ms a claim on a phone's storage, so a backlog of 5,000 claims takes about 4 minutes.

### D5. A handle's pods and zones are fixed when it is made

A reader gets a handle from the code that serves it, made for a set of pods and, in each, the zones the reader may read. Every query through the handle is filtered to those pods and zones, and no query names others.

**Example:** the assistant's view of "Ginger" and "Travel" reads those two pods. A question that mentions a third pod still reads only those two.

**Rejected alternatives:**

- The pods named in each query.
  - **Cons:** whatever drives the query, a model reading a person's words among them, could name a pod its person did not let it read.

### D6. Types are read from the registry in the graph

The registry is loaded into the graph once, when the graph is made, and every type, shape and generalization is read from there.

**Example:** a reader asks for the shape of `mee:PetMedicationRecord:v1` and gets it from the graph's type tables, the same tables its claims are typed by.

**Rejected alternatives:**

- Each reader reading the registry's files.
  - **Cons:** two places a type comes from, which can disagree.

### D7. The engine depends on no pod-tool

The engine carries no materialization of its own. Every pod-tool registers its materialization through the engine's interface, from its own code, which depends on the engine, never the reverse. The record store and the engine build and answer with no pod-tool present.

**Example:** mee-pdn built with the record store and the engine alone answers a reader's query for the shape of `mee:PetMedicationRecord:v1` and finds no claims in any pod. Registering chat's materialization makes chat's messages readable with no change to the engine.

**Rejected alternatives:**

- The engine carrying the materializations of the pod-tools the app ships with, as pdn-agent does.
  - **Pros:** no registration step for chat and Info.
  - **Cons:** the engine depends on those pod-tools and changes with each of them, and a pod-tool built in reads differently from one registered later.

## Operating conditions

- **Several identities on one node** changes the outcome: each identity has a graph of its own (catch-up, "Each identity on a device has one graph for every pod it reads").
- **One device or several** changes nothing in the engine, which builds each device's graph from the records that device holds, and a materialization depends on the records alone (materialization interface, "The same records give the same claims on every device").
- **The process ends without warning, the device restarts:** the graph is in memory (D3), so a kill loses nothing the records do not hold, and the first read after a start pays the catch-up of every zone it reads.
- **The disk fills:** a bulk load stages its rows as files, and a full disk fails it. The engine then adds the claims one at a time, in memory. This path has no scenario yet (tasks).
- **Clocks disagree, and step back:** the newest record under a key is the one with the latest time. An edit made on a device whose clock is behind loses to an older edit made elsewhere. The record store orders a key's entries by the same dates, so the graph agrees with the store (Risks).
- **Membership moves:** a reader that is no member of a pod is refused a view of it. Claims of that pod already in its graph stay in memory until the process ends (Open Questions).
- **An unstable connection, a device linking late:** no effect. The engine reads only what its device holds; what arrives later is read on the next read.

## Risks / Trade-offs

- **Pods kept apart by a filter.** Every query of a shared graph is filtered by pod and zone. A query path that misses the filter reads every pod on the device, so every read path has a test that a pod outside its scope contributes nothing.
- **Clock order decides edits.** Two members editing one key from devices whose clocks disagree keep the edit with the later date, which may be the earlier one in fact. The record store makes the same choice.
- **A materialization that depends on the device** makes two members' graphs differ, and nothing detects it.
- **A first read pays the backlog.** A device with many records builds its graph on its first read after every start.

## Migration Plan

Each capability moves on its own, into `crates/graph-query-engine`. For each one: the pdn-agent code is compared with the specification, requirement by requirement; the parts that conform move, with their tests; the parts that do not stay in pdn-agent until the specification or the code changes. Each move is two pull requests, this specification's change in mia-docs and the code in mee-pdn, reviewed together and approved or rejected together. Ontology registry and queries move first. The materialization interface and catch-up wait for the first open question, since they read the record store. The interface moves without chat's and Info's materializations (D7), which pdn-agent registers until a later change gives them a crate.

## Open Questions

**1. How mee-pdn carries a pod-tool's keyed records.** mee-pdn's record is a claim, a mergeable-document or an immutable-document, placed under its member's name at a fresh id. It names no pod-tool and no key, and stays once placed.

- **An envelope in each record:** every write of a pod-tool places an immutable-document whose payload names the pod-tool, the key and the device, around the bytes. This is how pdn-agent's PDN binding writes, and it needs nothing of mee-pdn. Its cost: every edit is one record more, and none goes away.
- **A pod-tool and a key on mee-pdn's record:** the pods capability gains both, and the record store can list a pod-tool's records by key.

**Example:** Alice edits the note `n1` three times. With an envelope, the pod holds 3 immutable-documents naming `notes` and `n1`, and the engine keeps the newest. With a key on the record, the pod holds whatever mee-pdn makes of a record placed 3 times under one key, which mee-pdn does not define today.

Recommendation: the envelope. It runs today, needs no change below the engine, and a removal is a newer record under the key that the pod-tool's materialization turns into nothing. Over mee-pdn, pdn-agent's binding removes nothing today, so removal through it is untested.

**2. A version of a pod-tool's records.** pdn-agent skips the records of a zone whose store is at the version it last caught up with. mee-pdn's record store offers no such version; its change subscription reports every change of a replica. Recommendation: specify the skip once mee-pdn offers a count of changes per pod.

**3. The reads not yet specified:** the types present in a view, with their counts per pod, and each subject's number of claims and type names. Recommendation: specify them with the assistant's use of them, then move them.

**4. A handle made before its reader's removal.** A removed member gets no new view, and the claims its graph holds stay in memory until the process ends. Whether a handle made before the removal reads them is untested. Recommendation: a test of it, and a requirement that matches.
