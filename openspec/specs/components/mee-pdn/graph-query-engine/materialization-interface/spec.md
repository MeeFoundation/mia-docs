# Materialization interface

## Purpose

The interface through which a [pod-tool](../../../../architecture/language/pod-tool.md) exposes its data to the graph query engine in a form the graph can hold ([ADR-0019](../../../../architecture/adr/0019-pods-read-through-a-graph-query-engine.md)). A pod-tool registers a materialization through it, and that materialization alone decides what the pod-tool's records stand for in the graph, or that they stand for nothing. The engine applies it on every device the same way, so every member's graph of a pod is built from the same records into the same nodes and relations. The engine depends on no pod-tool: pod-tools are consumers of this interface, and the materializations of the pod-tools the app ships with are specified with those pod-tools, not here.

A pod-tool reflects its data in the structure that suits it. The graph holds that data as nodes and relations in the pod-tool's zone, the part of the pod's graph built from the pod-tool's records. A node is of a type and holds a value of that type's shape, and a relation leads from one node to another. A claim is a node about a subject: the graph values claims as data of high quality, and no pod-tool is obliged to make them. Pod-tools understand each other's data through the types and relations their tool ontologies declare.

The engine hands a materialization the pod-tool's records one key at a time, each record with the key the pod-tool chose, its member, its time, the device it was written on where the record says, and its bytes.

## Requirements

### Requirement: A pod-tool exposes its data by registering a materialization

A pod-tool whose data reaches the graph SHALL register a materialization made of three parts. The first is its kind, which names its zone in every pod. The second is its tool ontology: the types its zone holds, each marked embeddable or not, and the relations its zone holds, each with its name, the type it leads from and the type it leads to. The third is a function that turns the records under one key into the nodes and relations they stand for, or into nothing. What records stand for SHALL be the materialization's alone: the engine SHALL NOT make a node or a relation of a record by any other means, and SHALL read a pod-tool's records only to hand them to that pod-tool's materialization. A pod-tool that registers no materialization SHALL contribute nothing to the graph. Registering a materialization for a kind already registered SHALL replace the earlier one, from the next catch-up on. A view SHALL tell its reader the tool ontologies of the zones it was made for, and no others.

**Example:** a pod-tool keeping flea-treatment notes registers its materialization, and this is what it makes of one key's records.

| part | value |
|---|---|
| kind | `flea-notes` |
| tool ontology | one type, `app:Note:v1`, embeddable, and no relation |
| the records under the key `n1` | one, by Alice, with the bytes "Ginger's flea treatment is due on the 3rd" |
| what they stand for | the node `n1` of type `app:Note:v1`, about the subject `ginger`, with the value `{"content":"Ginger's flea treatment is due on the 3rd"}`: a claim |

#### Scenario: A pod-tool registered while the app runs is read like any other

- **WHEN** a pod-tool the engine was not built with, keeping flea-treatment notes as `app:Note:v1`, registers its materialization, and Alice writes the note "Ginger's flea treatment is due on the 3rd"
- **THEN** a reader of Alice's pod finds that note beside the data of the pod's other pod-tools, with nothing in the reader written for that pod-tool

#### Scenario: A view tells the tool ontologies of its zones and no other

- **WHEN** two pod-tools of the pod "Ginger" have registered their materializations, Alice's view is made for both zones and Dan's for the second alone
- **THEN** Alice is told both tool ontologies, with their types and relations, and Dan only the second's

#### Scenario: A pod-tool that registers no materialization is not read

- **WHEN** a pod-tool writes records into a pod and registers no materialization
- **THEN** a reader of that pod finds none of them, and the zones it is told of do not include that pod-tool's

### Requirement: A pod-tool reflects its data in the structure that suits it

A materialization SHALL return nodes and relations. Each node SHALL have an id of the materialization's choosing, unique within its zone, a type its tool ontology declares, and a value. A node MAY name a subject, by the subject's id, name and type, and a node that names one is a claim. A node that names no subject SHALL be found, counted and followed like any other node. A node MAY name the members of the pod it is for; a node that names none is for every member who may read its zone. Each relation SHALL have a name its tool ontology declares, SHALL lead from a node the same records make, and SHALL lead to a node of the same pod, named by its zone and its id, in the pod-tool's own zone or in another pod-tool's.

**Example:** a chat pod-tool declares the type `app:Message:v1` and the relation `follows`, from `app:Message:v1` to `app:Message:v1`. A pod-tool that reads text from photos declares `app:UnstructuredText:v1` and the relation `read-from`, from `app:UnstructuredText:v1` to `app:Attachment:v1`. In "Ginger":

| zone | key | its records | what they stand for |
|---|---|---|---|
| `chat` | `m1` | Alice: "vet on Friday?" | the node `m1`, an `app:Message:v1` about no subject |
| `chat` | `m2` | Bob: "I'll take her" | the node `m2`, an `app:Message:v1` about no subject, and `m2` `follows` `m1` |
| `photos` | `p7` | Alice's photo of the vet's invoice | the node `p7`, an `app:Attachment:v1` |
| `ocr` | `t1` | the text read from `p7` | the node `t1`, an `app:UnstructuredText:v1`, and `t1` `read-from` the node `p7` of the zone `photos` |

#### Scenario: Messages are read with no subject

- **WHEN** the chat pod-tool's materialization turns two messages into the nodes `m1` and `m2`, with `m2` following `m1`
- **THEN** a reader finds both by their type, follows `m2` to `m1`, finds no claim among them, and no subject is made for them

#### Scenario: A direct message is for its two participants

- **WHEN** the chat pod-tool's materialization turns Alice's direct message to Bob into a node for Alice and Bob
- **THEN** Alice and Bob read the message, and Carol, a member of the same pod, does not

#### Scenario: A relation leads into another pod-tool's zone

- **WHEN** the text node `t1` of the zone `ocr` is `read-from` the photo `p7` of the zone `photos`
- **THEN** a reader that may read both zones follows `t1` to `p7`, and a reader that may read `ocr` alone follows it to nothing

### Requirement: The engine depends on no pod-tool

The engine SHALL carry no pod-tool's materialization: every materialization it applies SHALL be one a pod-tool registered through this interface. With no pod-tool registered, the engine SHALL load its registry and answer every query, with no zone to read.

**Example:** a core of mee-pdn's record store and the engine alone, with no pod-tool. A reader of "Ginger" gets the shape of `mee:PetMedicationRecord:v1`; a find of that type in "Ginger" returns no nodes, and its count is 0. A pod-tool registers its materialization, and the next read of "Ginger" finds that pod-tool's data.

#### Scenario: The engine answers with no pod-tool registered

- **WHEN** the engine runs with no materialization registered, and a reader asks for a type's shape and for the nodes of a pod
- **THEN** it gets the shape, and no nodes

### Requirement: A key's records are handed over together, oldest first

A materialization SHALL receive every record under a key, oldest first by time and, at the same time, by record id, and what the key holds in the graph SHALL be what the materialization returns for those records. A materialization that needs the newest record alone SHALL take the last; one that merges operations or keeps a history SHALL take them all. A key whose records the materialization turns into nothing SHALL hold nothing, and so SHALL a key no record is under any more. Each node SHALL take its member, its time and its device from the record of its key the materialization names for it, or else from the newest record under its key; its device SHALL be the one that record carries, and it SHALL have none where the record carries none.

**Example:** two pod-tools of "Ginger". The notes pod-tool's materialization takes the newest record under a key; the document pod-tool's merges every operation under a key into one document.

| step | records under `n1` | records under `n2` | records under `d1` | the zones hold |
|---|---|---|---|---|
| Alice writes `n1` "vet on Friday" and `n2` "wet food at 07:30" | 1 | 1 | 0 | `n1` "vet on Friday", `n2` "wet food at 07:30" |
| Alice writes `n1` again: "vet on Saturday" | 2 | 1 | 0 | `n1` "vet on Saturday", `n2` "wet food at 07:30" |
| `n2` is deleted | 2 | 0 | 0 | `n1` "vet on Saturday" |
| Alice writes the operation "title: Ginger's diet" under `d1`, then Bob "add: no fish" | 2 | 0 | 2 | `n1` "vet on Saturday", and `d1` "Ginger's diet: no fish" |

#### Scenario: An edited note replaces what its key held

- **WHEN** the notes pod-tool writes a newer record under a key whose note is in the graph
- **THEN** its materialization receives both records, oldest first, and the zone holds one note for that key, made from the newer record

#### Scenario: A document is made from every operation under its key

- **WHEN** Alice and then Bob write an operation under the document key `d1`
- **THEN** the document pod-tool's materialization receives both, Alice's first, and the zone holds the one document they merge into

#### Scenario: A deleted record takes out what its key held

- **WHEN** the only record under a key is deleted
- **THEN** the zone holds nothing for that key, and everything else in it stays

#### Scenario: The member is the record's

- **WHEN** Bob writes a record in a pod-tool's zone, and Alice reads that zone
- **THEN** the node's member is `bob`, and its pod-tool is the one whose zone it is in

### Requirement: The same records give the same nodes and relations on every device

A materialization registered through this interface SHALL depend on the records alone, never on the device, the reader or the time it runs. The same records SHALL give the same nodes and relations in every member's graph, except that a node for some members alone is only in their graphs, and a graph built again from the records SHALL read the same as the graph it replaces.

**Example:** Bob writes "vet on Friday" and Alice "I'll take her" in the chat of "Ginger". Alice's graph and Bob's, built apart, each hold the same two messages, with the same ids, pod-tool, type, value and member, and the same relation between them; a graph built afresh from Alice's copy of the records reads the same as hers.

#### Scenario: Two members' graphs, built apart, read the same

- **WHEN** Alice and Bob each read a pod-tool's zone of a pod they are both members of, each from a graph of their own
- **THEN** both read the same nodes and relations

#### Scenario: A graph built again from the records reads the same

- **WHEN** a new graph is built from the records of a zone another graph has caught up with
- **THEN** both graphs read the same nodes and relations
