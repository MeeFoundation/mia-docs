# Queries

> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

## Purpose

What the graph query engine answers, and for whom ([ADR-0019](../../../../architecture/adr/0019-pods-read-through-a-graph-query-engine.md)). A reader holds a handle, fixed when it is made to the pods and zones it reaches: one zone of one pod for a [pod-tool](../../../../architecture/language/pod-tool.md)'s own use, or the zones of several pods as one view for a reader that answers across pods. Through it the reader finds, counts and pages through claims, and reads who they are about. Every query runs in the graph, and every result says where it is from.

## ADDED Requirements

### Requirement: A handle reaches only the pods and zones it was made for

A handle SHALL read only the pods and zones fixed when it was made, whatever else the graph holds. A handle made for one zone of one pod SHALL read that zone of that pod; a view SHALL read the zones of the pods it was made for that its reader may read. A reader SHALL be refused a view of a pod it is not a member of. The same claim id in two pods SHALL be two claims, each read only through its own pod.

**Example:** "Ginger" (chat, Info) has Alice, Bob and Dan as members, Dan with Info alone; "Travel" (chat) has Alice alone. Bob has written "vet on Friday" in Ginger's chat, Alice "passport in the top drawer" in Travel's.

| handle | reads |
|---|---|
| Alice's view of "Ginger" and "Travel" | 2 claims |
| Alice's view of "Ginger", chat's zone | "vet on Friday", in "Ginger" |
| Alice's handle on Info's zone of "Ginger" | no claim and no subject, though chat's zone is in her graph |
| Dan's view of "Ginger" | no claim: chat's zone is not his to read |
| Carol's view of "Ginger" | refused: she is not a member |

#### Scenario: A pod reads only itself

- **WHEN** Alice reads one of two pods she is a member of, both in her graph
- **THEN** every claim she reads is in that pod

#### Scenario: A handle on one zone reads that zone alone

- **WHEN** chat's zone of a pod is in Alice's graph, and she reads through her handle on Info's zone of that pod
- **THEN** she reads no claim and no subject

#### Scenario: A zone the reader may not read is not in its view

- **WHEN** Dan, who may read Info and not chat, reads a view of a pod whose chat holds a message
- **THEN** he reads no claim, while Alice, who may read chat, reads the message

#### Scenario: A non-member is refused

- **WHEN** Carol, who is not a member of a pod, asks for a view of it
- **THEN** she is refused

#### Scenario: Two pods with the same claim ids keep them apart

- **WHEN** pods `a` and `b` in one graph hold claims with the same ids
- **THEN** each reads its own claims and subjects alone, and `b` has no claim `claim020` whatever `a` holds

### Requirement: Claims are found and counted by type, field and subject

A find SHALL return the active claims in scope, oldest first by time and then by claim id: of the query's type and matching every one of its filters when a query is given, about one of the given subjects when subjects are given, and at most the query's limit, 50 when the query sets none. A filter follows a path of fields into the claim's value and compares the value at its end: equal to, greater than, at least, less than or at most a given value, or, for a list, holding it. A count SHALL return how many claims in scope match the query, reading no value.

**Example:** 40 claims of `mee:PetMedicationRecord:v1` in pod `p`, about 5 subjects, half of them with the brand name "Clavamox".

| query | result |
|---|---|
| count, `medication.brand_name` equal to "Clavamox" | 20 |
| find, `medication.active_ingredient` holding "Ingredient 7" | `claim007` |
| find, about `subject-3` | 8 claims |
| find, limit 3 | 3 claims |

#### Scenario: Filters, subjects and limits are applied in the graph

- **WHEN** a reader finds and counts claims in a pod of 40 by a field's value, by a list holding a value, by a date at least a given one, by subject and with a limit
- **THEN** each find returns exactly the claims that match, oldest first and no more than the limit, and each count the number that match

### Requirement: A long list is read a page at a time

A page SHALL return, of the claims in scope (of one pod-tool where one is named, of one type where one is named), those after the offset in order, newest first or oldest first, at most the limit, and with them the number of claims in scope in all.

**Example:** Alice has written 50 messages, "message 00" to "message 49", in a pod's chat. The first page of 20, newest first, runs from "message 49" to "message 30" and says 50 in all; the page at offset 20 starts at "message 29" and holds 20.

#### Scenario: A list of 50 is read 20 at a time, newest first

- **WHEN** a reader asks for chat's messages 20 at a time, newest first, at offset 0 and then at offset 20
- **THEN** the first page runs from the newest message to the 20th newest, the second starts at the 21st newest, each holds 20, and both say 50 in all

### Requirement: Everything read says where it is from

Each claim read SHALL carry its pod, its pod-tool, its author, its time in RFC 3339 in UTC, the device it was written on where its record names one, its subject, its type and the type's name, its root value's id as readers address it, `<claim id>/value`, and its value as a document, as it was written. Each subject read SHALL carry its pod.

**Example:** the calendar's claim `e1` about Ginger, of type `app:CalendarEvent:v1`, written by Alice on her phone with the value `{"title": "vet", "starts_at": "2026-11-21T10:00:00Z", "place": "Linden Street clinic"}`, is read back with the same value, the pod-tool `calendar` and the device `phone`.

#### Scenario: An event with a time comes back as it went in

- **WHEN** a calendar event with a start time is caught up and read
- **THEN** its title and start time read as they were written, its pod-tool is `calendar` and its device is the one its record names

#### Scenario: A claim reads back exactly as it was written

- **WHEN** 40 claims with nested values and lists are caught up and read
- **THEN** each reads with its value tree intact, its author, its time, its subject and its root value id `<claim id>/value`
