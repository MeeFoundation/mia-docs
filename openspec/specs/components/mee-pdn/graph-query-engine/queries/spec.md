# Queries

## Purpose

What the graph query engine answers, and for whom ([ADR-0019](../../../../architecture/adr/0019-pods-read-through-a-graph-query-engine.md)). A reader holds a handle, fixed when it is made to the pods and zones it reaches: one zone of one pod for a [pod-tool](../../../../architecture/language/pod-tool.md)'s own use, or the zones of one or several pods as one view, for a reader that answers across pods or a pod-tool that reads other pod-tools' data. A pod-tool never reads another pod-tool's records; it reads that pod-tool's data in the graph, through a view. Through a handle the reader finds, counts and pages through nodes, follows their relations, and reads the subjects claims are about. Every query runs in the graph, and every result says where it is from.

## Requirements

### Requirement: A handle reaches only the pods and zones it was made for

A handle SHALL read only the pods and zones fixed when it was made, whatever else the graph holds. A handle made for one zone of one pod SHALL read that zone of that pod, and a view the zones it was made for. Which pods and zones a reader's handle is made for is the application's: it makes a reader handles on the zones it may read, and none on a pod it is not a member of. The same node id in two pods SHALL be two nodes, each read only through its own pod.

**Example:** "Ginger" (pod-tools `notes` and `meds`) has Alice, Bob and Dan as members, Dan with `meds` alone; "Travel" (`notes`) has Alice alone. Bob has written the note "vet on Friday" in "Ginger", Alice "passport in the top drawer" in "Travel".

| handle | reads |
|---|---|
| Alice's view of "Ginger" and "Travel" | 2 notes |
| Alice's view of "Ginger", the `notes` zone | "vet on Friday", in "Ginger" |
| Alice's handle on the `meds` zone of "Ginger" | no node and no subject, though the `notes` zone is in her graph |
| Dan's view of "Ginger", made for the `meds` zone alone | no node: the `notes` zone is not his to read |
| Carol | no handle on "Ginger": she is not a member |

#### Scenario: A pod reads only itself

- **WHEN** Alice reads one of two pods she is a member of, both in her graph
- **THEN** every node she reads is in that pod

#### Scenario: A handle on one zone reads that zone alone

- **WHEN** one pod-tool's zone of a pod is in Alice's graph, and she reads through her handle on another pod-tool's zone of that pod
- **THEN** she reads no node and no subject

#### Scenario: A zone a view was not made for is not read

- **WHEN** Dan's view of a pod is made for its `meds` zone alone, and the pod's `notes` zone holds a note
- **THEN** he reads no node, while Alice's view, made for both zones, reads the note

#### Scenario: A pod-tool reads another pod-tool's zone through a view

- **WHEN** a pod-tool of "Ginger" reads a view of "Ginger" for Alice, and the `notes` pod-tool's zone holds "vet on Friday"
- **THEN** it reads the note, though the note is not in its own zone

#### Scenario: Two pods with the same node ids keep them apart

- **WHEN** pods `a` and `b` in one graph hold nodes with the same ids
- **THEN** each reads its own nodes and subjects alone, and `b` has no node `claim020` whatever `a` holds

### Requirement: Nodes are found and counted by type, field and subject

A find SHALL return the nodes in scope, oldest first by time and then by node id: of the query's type and matching every one of its filters when a query is given, about one of the given subjects when subjects are given, and at most the query's limit, 50 when the query sets none. A find by subject SHALL return claims alone, since no other node is about a subject. A filter follows a path of fields into the node's value and compares the value at its end: equal to, greater than, at least, less than or at most a given value, or, for a list, holding it. A count SHALL return how many nodes in scope match the query, reading no value.

**Example:** 40 claims of `mee:PetMedicationRecord:v1` in pod `p`, about 5 subjects, half of them with the brand name "Clavamox", and the 2 messages of a chat, about no subject.

| query | result |
|---|---|
| count, `medication.brand_name` equal to "Clavamox" | 20 |
| find, `medication.active_ingredient` holding "Ingredient 7" | `claim007` |
| find, about `subject-3` | 8 claims |
| find, limit 3 | 3 nodes |
| find, `app:Message:v1` | the 2 messages |

#### Scenario: Filters, subjects and limits are applied in the graph

- **WHEN** a reader finds and counts nodes in a pod of 40 by a field's value, by a list holding a value, by a date at least a given one, by subject and with a limit
- **THEN** each find returns exactly the nodes that match, oldest first and no more than the limit, and each count the number that match

#### Scenario: Nodes about no subject are found by their type

- **WHEN** a reader finds the nodes of `app:Message:v1` in a pod whose chat holds 2 messages about no subject
- **THEN** it gets both messages, and a find of the same pod by any subject returns neither

### Requirement: A node's relations are followed

A reader SHALL follow the relations of a node in scope: the nodes its relations of a given name lead to, and the nodes whose relations of a given name lead to it, oldest first by time and then by node id. A relation SHALL lead only to a node in scope: one that leads into a zone or a pod the handle does not reach, or to a node the graph does not hold, SHALL return nothing.

**Example:** in "Ginger", the chat's message `m2` `follows` `m1`, and the text `t1` of the zone `ocr` is `read-from` the photo `p7` of the zone `photos`.

| reader | follows | gets |
|---|---|---|
| Alice's view of "Ginger" | `m2`, `follows` | `m1` |
| Alice's view of "Ginger" | to `m1`, `follows` | `m2` |
| Alice's view of "Ginger" | `t1`, `read-from` | `p7` |
| a handle on the `ocr` zone alone | `t1`, `read-from` | nothing |

#### Scenario: A relation is followed both ways

- **WHEN** a reader follows `follows` from the message `m2`, and to the message `m1`
- **THEN** it gets `m1` the first time and `m2` the second

#### Scenario: A relation out of scope leads to nothing

- **WHEN** a handle on the zone `ocr` alone follows `read-from` from `t1`, whose target is in the zone `photos`
- **THEN** it gets nothing, and a view that reaches both zones gets `p7`

### Requirement: The types present are counted per pod

A view SHALL say which types its nodes are of, within its pods and zones, each type with how many nodes each pod holds of it, by type name and then by pod. A type no node in scope is of SHALL NOT be listed.

**Example:** Alice's view of "Ginger" and "Travel", where Dan may read only the `meds` zone of "Ginger".

| type | "Ginger" | "Travel" |
|---|---|---|
| `app:Note:v1` | 3 | 1 |
| `mee:PetMedicationRecord:v1` | 2 | — |

Dan's view of "Ginger" lists `mee:PetMedicationRecord:v1` alone, with 2.

#### Scenario: The types present are counted per pod, within the view

- **WHEN** Alice's view of two pods asks which types are present, and so does Dan's view of one of them, who may read one of its zones
- **THEN** Alice gets each type with its count in each pod, and Dan only the types of the zone he may read, with their counts

### Requirement: A subject says how much is claimed about it

Each subject read SHALL carry its pod, the number of claims in scope about it, and the names of the types of those claims, each once, in the order of the oldest claim of each type. The same subject id in two pods SHALL be two subjects. A node about no subject SHALL make no subject.

**Example:** in "Ginger", Alice wrote a note about Ginger, then a medication record, then another note. The subject `ginger` reads with 3 claims and the types `Note`, then `PetMedicationRecord`.

#### Scenario: A subject carries its claim count and its types

- **WHEN** three claims of two types are about one subject of a pod, and a reader reads that pod's subjects
- **THEN** the subject carries its pod, 3 claims, and the two type names, oldest first

### Requirement: A long list is read a page at a time

A page SHALL return, of the nodes in scope (of one pod-tool where one is named, of one type where one is named), those after the offset in order, newest first or oldest first, at most the limit, and with them the number of nodes in scope in all.

**Example:** Alice has written 50 notes, "note 00" to "note 49", in a pod's `notes` zone. The first page of 20, newest first, runs from "note 49" to "note 30" and says 50 in all; the page at offset 20 starts at "note 29" and holds 20.

#### Scenario: A list of 50 is read 20 at a time, newest first

- **WHEN** a reader asks for a pod-tool's 50 notes 20 at a time, newest first, at offset 0 and then at offset 20
- **THEN** the first page runs from the newest note to the 20th newest, the second starts at the 21st newest, each holds 20, and both say 50 in all

### Requirement: Everything read says where it is from

Each node read SHALL carry its pod, its pod-tool, its member, its time in RFC 3339 in UTC, the device it was written on where its record carries one, its type and the type's name, its subject where it is a claim, the members it is for where it names them, its root value's id as readers address it, `<node id>/value`, and its value as a document, as it was written. Each subject read SHALL carry its pod.

**Example:** the calendar's node `e1` about Ginger, of type `app:CalendarEvent:v1`, written by Alice on her phone with the value `{"title": "vet", "starts_at": "2026-11-21T10:00:00Z", "place": "Linden Street clinic"}`, is read back with the same value, the pod-tool `calendar` and the device `phone`.

#### Scenario: An event with a time comes back as it went in

- **WHEN** a calendar event with a start time is caught up and read
- **THEN** its title and start time read as they were written, its pod-tool is `calendar` and its device is the one its record carries

#### Scenario: A node reads back exactly as it was written

- **WHEN** 40 claims with nested values and lists are caught up and read
- **THEN** each reads with its value tree intact, its member, its time, its subject and its root value id `<node id>/value`

#### Scenario: A message reads with no subject

- **WHEN** a chat message about no subject is caught up and read
- **THEN** it reads with its pod, pod-tool, member, time, type and value, and no subject
