# Materialization interface

> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

## Purpose

The interface through which a [pod-tool](../../../../architecture/language/pod-tool.md) exposes its data to the graph query engine in a form the graph can hold ([ADR-0019](../../../../architecture/adr/0019-pods-read-through-a-graph-query-engine.md)). A pod-tool registers a materialization through it, and that materialization alone decides what each of the pod-tool's records stands for in the graph, or that it stands for nothing. The engine applies it on every device the same way, so every member's graph of a pod is built from the same records into the same claims. The engine depends on no pod-tool: pod-tools are consumers of this interface, and the materializations of the pod-tools the app ships with are specified with those pod-tools, not here.

The engine hands a materialization the pod-tool's records, each with a key the pod-tool chose, its author, its time, the device it was written on where the record says, and its bytes. A claim in the graph is the engine's unit of data: a typed value about a subject, in a pod and in one pod-tool's zone, the part of the pod's graph built from that pod-tool's records.

## ADDED Requirements

### Requirement: A pod-tool exposes its data by registering a materialization

A pod-tool whose data reaches the graph SHALL register a materialization made of three parts: its kind, which names its zone in every pod; its tool ontology, the types its zone holds, each marked embeddable or not; and a function that turns one of its records into the claim the record stands for, or into nothing. What a record stands for, and whether it stands for anything, SHALL be the materialization's alone: the engine SHALL NOT make a claim of a record by any other means, and SHALL read a pod-tool's records only to hand them to that pod-tool's materialization. A pod-tool that registers no materialization SHALL contribute nothing to the graph. Registering a materialization for a kind already registered SHALL replace the earlier one, from the next catch-up on. The tool ontologies a reader is told SHALL be those of the zones it may read.

**Example:** a pod-tool keeping flea-treatment notes registers its materialization, and this is what it makes of one record.

| part | value |
|---|---|
| kind | `flea-notes` |
| tool ontology | one type, `app:Note:v1`, embeddable |
| a record | key `n1`, author `alice`, bytes "Ginger's flea treatment is due on the 3rd" |
| its claim | id `flea-n1`, type `app:Note:v1`, about the subject `ginger`, value `{"content":"Ginger's flea treatment is due on the 3rd"}` |

#### Scenario: A pod-tool registered while the app runs is read like any other

- **WHEN** a pod-tool the engine was not built with, keeping flea-treatment notes as `app:Note:v1`, registers its materialization, and Alice writes the note "Ginger's flea treatment is due on the 3rd"
- **THEN** a reader of Alice's pod finds that note beside the data of the pod's other pod-tools, with nothing in the reader written for that pod-tool

#### Scenario: A reader is told the tool ontology of the zones it may read and no other

- **WHEN** two pod-tools of the pod "Ginger" have registered their materializations, and Alice may read both and Dan only the second
- **THEN** Alice is told both tool ontologies, and Dan only the second's

#### Scenario: A pod-tool that registers no materialization is not read

- **WHEN** a pod-tool writes records into a pod and registers no materialization
- **THEN** a reader of that pod finds none of them, and the zones it is told of do not include that pod-tool's

### Requirement: The engine depends on no pod-tool

The engine SHALL carry no pod-tool's materialization: every materialization it applies SHALL be one a pod-tool registered through this interface. With no pod-tool registered, the engine SHALL load its registry and answer every query, with no zone to read.

**Example:** a core of mee-pdn's record store and the engine alone, with no pod-tool. A reader of "Ginger" gets the shape of `mee:PetMedicationRecord:v1`; a find of that type in "Ginger" returns no claims, and its count is 0. A pod-tool registers its materialization, and the next read of "Ginger" finds that pod-tool's data.

#### Scenario: The engine answers with no pod-tool registered

- **WHEN** the engine runs with no materialization registered, and a reader asks for a type's shape and for the claims of a pod
- **THEN** it gets the shape, and no claims

### Requirement: The newest record under each key stands

The claims of a zone SHALL be what the pod-tool's materialization makes of the newest record under each key of its records, the newest being the one with the latest time and, at the same time, the greatest record id. A key whose newest record the materialization turns into nothing SHALL hold no claim, and so SHALL a key no record is under any more. A claim's author and time SHALL be its record's, as the record store holds them, and its device SHALL be the one the materialization names, or else the record's.

**Example:** a notes pod-tool's records in the pod "Ginger", written by Alice one after the other.

| step | records under `n1` | records under `n2` | the zone holds |
|---|---|---|---|
| Alice writes `n1` "vet on Friday" and `n2` "wet food at 07:30" | 1 | 1 | `n1` "vet on Friday", `n2` "wet food at 07:30" |
| Alice writes `n1` again: "vet on Saturday" | 2 | 1 | `n1` "vet on Saturday", `n2` "wet food at 07:30" |
| `n2` is deleted | 2 | 0 | `n1` "vet on Saturday" |

#### Scenario: An edited record replaces its claim

- **WHEN** a pod-tool writes a newer record under a key whose claim is in the graph
- **THEN** the zone holds one claim for that key, made from the newer record

#### Scenario: A deleted record takes its claim out

- **WHEN** the only record under a key is deleted
- **THEN** the zone holds no claim for that key, and every other claim stays

#### Scenario: The author is the record's

- **WHEN** Bob writes a record in a pod-tool's zone, and Alice reads that zone
- **THEN** the claim's author is `bob`, and its pod-tool is the one whose zone it is in

### Requirement: The same records give the same claims on every device

A materialization registered through this interface SHALL depend on the records alone, never on the device, the reader or the time it runs. The same records SHALL give the same claims in every member's graph, and a graph built again from the records SHALL read the same as the graph it replaces.

**Example:** Bob writes "vet on Friday" and Alice "I'll take her" in a pod-tool of "Ginger". Alice's graph and Bob's, built apart, each hold the same two claims, with the same ids, pod-tool, type, value and author; a graph built afresh from Alice's copy of the records reads the same as hers.

#### Scenario: Two members' graphs, built apart, read the same

- **WHEN** Alice and Bob each read a pod-tool's zone of a pod they are both members of, each from a graph of their own
- **THEN** both read the same claims

#### Scenario: A graph built again from the records reads the same

- **WHEN** a new graph is built from the records of a zone another graph has caught up with
- **THEN** both graphs read the same claims
