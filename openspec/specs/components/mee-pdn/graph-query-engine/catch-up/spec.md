# Catch-up

## Purpose

How the graph query engine brings its graph up to date with what pod-tools expose in the zones it reads ([ADR-0019](../../../../architecture/adr/0019-pods-read-through-a-graph-query-engine.md)): before it answers, from the records alone, adding what is new, replacing what changed and taking out what is gone, in bulk for a backlog and one key at a time after that. What a zone's nodes and relations are is the [materialization interface](../materialization-interface/spec.md)'s; this capability is when and how they reach the graph.

## Requirements

### Requirement: Each identity on a device has one graph for every pod it reads

Each identity hosted on a device SHALL have one graph, holding every pod and every zone that identity has read, and SHALL read no other identity's graph. Pods in one graph SHALL be kept apart by the pod each node, relation, subject and value carries, and zones by the zone each node, relation and value carries. A graph SHALL hold only the zones its handles were made for; which zones an identity's handles are made for is the application's, which makes none of a pod for an identity that is not its member. A node for some members alone SHALL be built only into the graphs of those members' identities, with the relations that lead from it.

**Example:** Alice and Bob are both members of "Ginger", and Alice alone of "Travel".

| identity | its graph holds | read through |
|---|---|---|
| Alice | "Ginger" and "Travel" | one graph |
| Bob | "Ginger" | a graph of his own, built from the same records of "Ginger" |
| Carol, a member of neither | nothing | — |

#### Scenario: One identity's pods share one graph

- **WHEN** Alice reads two pods she is a member of
- **THEN** both are in one graph, and Bob, a member of one of them, reads it from a graph of his own

#### Scenario: A node for some members is built only into their graphs

- **WHEN** Alice's direct message to Bob in "Ginger", a node for Alice and Bob, is caught up in the graphs of Alice, Bob and Dan, all members of "Ginger"
- **THEN** Alice's and Bob's graphs hold it, Dan's does not, and a relation to it from the group stream leads to nothing in Dan's graph

#### Scenario: Nothing is built of a zone no handle was made for

- **WHEN** Alice's graph has read "Ginger", and Carol's graph, made for no zone of "Ginger", is read
- **THEN** Carol's graph holds no pod

### Requirement: A read catches up first

Before it answers a read of nodes (a find, a count, a page, one node by its id or the relations of a node), of subjects or of the types present, a handle SHALL bring every zone it reads up to date with that zone's records, each zone read from its own records. Reading a type, a shape or a type's generalizations SHALL need no catch-up.

**Example:** Bob writes the note "Ginger hates the blue bowl" in "Ginger". Alice's next read of the `notes` zone applies Bob's record first and returns it among the notes, with nothing else asked of her code.

#### Scenario: A record written by another member is read on the next read

- **WHEN** Bob writes a record in a pod-tool's zone of a pod, and Alice then reads that zone
- **THEN** Alice reads what Bob's record stands for

### Requirement: Catching up adds what is new, replaces what changed and takes out what is gone

Catching a zone up SHALL apply each key whose records changed since it was last applied: what the key held SHALL be replaced by what the materialization returns for its records now, nodes and relations together, and a key no record is under any more SHALL hold nothing. A key whose records have not changed SHALL NOT be applied again, so catching up with records that have not changed applies nothing. A reader SHALL see a key's nodes and relations as they were before it was applied or as they are after, never part of each.

**Example:** a pod-tool's zone in pod `p`, one node per key, its catch-ups counted as the engine counts them.

| catch-up | keys | bulk | applied | skipped |
|---|---|---|---|---|
| first | 40 | 40 | 0 | 0 |
| second | the same 40, and 1 more | 0 | 1 | 0 |
| third | the same 41 | 0 | 0 | 0 |
| fourth | the same 41, one with a newer record | 0 | 1 | 0 |

#### Scenario: The same records twice apply nothing

- **WHEN** a zone is caught up with records it has already been caught up with
- **THEN** nothing is added, replaced or taken out

#### Scenario: A new key after the first load is applied on its own

- **WHEN** a record under a new key is added to a zone that holds 40 keys
- **THEN** that one key is applied, and the zone holds 41

#### Scenario: A key with a newer record is applied again, whole

- **WHEN** a newer record is written under a key whose node relates to another node, and the materialization now returns the node with a new value and no relation
- **THEN** the zone holds the node with its new value, and the relation is gone

### Requirement: A zone whose records have not changed is not read

Where the record store offers a version of a zone's records, a catch-up SHALL NOT read the records of a zone whose version is the one it was last caught up with, and SHALL read them when the version has moved. Where the record store offers no version, every catch-up SHALL read the zone's records.

**Example:** Alice reads the `notes` zone of "Ginger" twice, with nothing written between, then again after Bob writes a note.

| record store | second read | third read |
|---|---|---|
| offers a version per pod | does not read the records | reads them, and adds Bob's note |
| offers no version | reads the records, and applies nothing | reads them, and adds Bob's note |

#### Scenario: An unchanged zone is not read again

- **WHEN** a zone whose record store offers a version is read twice, with nothing written between
- **THEN** the second read does not read the zone's records

#### Scenario: A zone is read again once its version moves

- **WHEN** a record is written in that zone after it was caught up, and the zone is read
- **THEN** its records are read, and the new note is in the graph

### Requirement: What does not fit is left out

The engine SHALL leave out of the graph, and count as skipped:

- a node whose type its tool ontology does not declare or the registry does not hold, or whose value does not fit its type's shape;
- a node whose id another key of its zone also returns, from every key but the first of them in the byte order of the keys;
- a relation its tool ontology does not declare, and a relation that leads from a node left out or from a node of another type than the one it declares.

What is left out SHALL NOT keep out the nodes and relations beside it, and SHALL NOT be tried again until its key's records change. A relation whose target is not in the graph, or is neither of the type it declares nor of a type that extends it, SHALL be kept, and SHALL lead to nothing until a target of that type is there.

**Example:** 12 keys of a medication pod-tool, one node of `mee:PetMedicationRecord:v1` each, where the node of key 5 has `{"medication": "not a list"}` for its value and the node of key 6 the type `mee:NoSuchType:v1`. The catch-up loads 10 and skips 2; a second catch-up with the same records applies nothing.

#### Scenario: Two nodes that do not fit are skipped and the other ten load

- **WHEN** a zone is caught up with 12 keys, one whose node's value does not fit its type and one whose node's type the registry does not hold
- **THEN** 10 nodes load, 2 are skipped, and a catch-up with the same records tries neither again

#### Scenario: A node id two keys return is kept from the first key

- **WHEN** the keys `a` and `b` of one zone both return a node `x`
- **THEN** the zone holds the node `x` from key `a`, the one from key `b` is skipped, and every device keeps the same one

#### Scenario: A node id that moves to an earlier key is read from it

- **WHEN** the node `x` is caught up from key `b`, and a later catch-up brings key `a` returning `x` as well
- **THEN** the zone holds `x` from key `a`, the one from key `b` is skipped, the graph reads as one built from the same records anew, and the same records again apply nothing

#### Scenario: A time that is not a time costs its own node alone

- **WHEN** a zone of 12 calendar events is caught up, in one bulk load and key by key, and the event `e05` starts `next Tuesday`
- **THEN** 11 events load and `e05` is skipped, the same records try nothing again, and once `e05` gets a record starting `2026-11-28T10:00:00Z` it loads

#### Scenario: A relation to a zone not yet read leads to nothing until it is

- **WHEN** the text node `t1` of the zone `ocr` is `read-from` the photo `p7`, and Alice's graph has not read the zone `photos` yet
- **THEN** `t1` is in the graph, its relation leads to nothing, and it leads to `p7` once the zone `photos` is caught up

### Requirement: A backlog loads in bulk, and the rest one key at a time

A zone with nothing applied yet whose catch-up brings at least 32 nodes SHALL load its nodes and relations in one bulk load. Zones with nothing applied yet that are caught up together SHALL load in one bulk load when there are at least 2 of them and their nodes number at least 32 between them. Every other key SHALL be applied in a transaction of its own. A bulk load and applying key by key SHALL give the same graph. A bulk load that fails SHALL leave nothing it wrote, the subjects it made among them, and its zones SHALL then be applied key by key into the graph applying them key by key gives.

**Example:** with the threshold set to 10, five pods `a` to `e`, new to the graph, each bring 4 nodes to one catch-up. None reaches 10 alone; together they bring 20, and load in one bulk load. Each pod then reads the same nodes, relations and subjects as in a graph that applied the same keys one at a time.

#### Scenario: A pod new to the graph loads its backlog in bulk

- **WHEN** a pod new to the graph is caught up with 40 nodes, at a threshold of 10
- **THEN** all 40 load in one bulk load, and read back oldest first, each as it was written

#### Scenario: Many small new pods load together

- **WHEN** five pods new to the graph, of 4 nodes each, are caught up together at a threshold of 10
- **THEN** their 20 nodes load in one bulk load, and each pod reads as it does when its keys are applied one at a time

#### Scenario: Bulk-loaded and applied nodes are the same graph

- **WHEN** the same 40 keys, with relations between their nodes, are bulk-loaded into one graph and applied one at a time into another
- **THEN** both return the same nodes, relations, subjects, finds and counts

#### Scenario: A bulk load that fails after writing leaves nothing

- **WHEN** a pod new to the graph is caught up with 40 claims about 5 subjects, at a threshold of 10, and its bulk load fails after its subjects and nodes are written
- **THEN** the 40 keys are applied one at a time, each claim is read once, and the claims and the 5 subjects, each with its type, read as they do in a graph that applied the keys one at a time

#### Scenario: A bulk load that cannot stage its files falls back to one key at a time

- **WHEN** a pod new to the graph is caught up with 40 notes, at a threshold of 10, and the temporary directory cannot hold the bulk load's files, as on a full disk
- **THEN** the 40 keys are applied one at a time, and each note is read once
