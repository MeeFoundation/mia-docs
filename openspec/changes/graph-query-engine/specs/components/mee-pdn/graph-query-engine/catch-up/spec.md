# Catch-up

> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

## Purpose

How the graph query engine brings its graph up to date with what pod-tools expose in the zones it reads ([ADR-0019](../../../../architecture/adr/0019-pods-read-through-a-graph-query-engine.md)): before it answers, from the records alone, adding what is new, replacing what changed and taking out what is gone, in bulk for a backlog and one claim at a time after that. What a zone's claims are is the [materialization interface](../materialization-interface/spec.md)'s; this capability is when and how they reach the graph.

## ADDED Requirements

### Requirement: Each identity on a device has one graph for every pod it reads

Each identity hosted on a device SHALL have one graph, holding every pod and every zone that identity has read, and SHALL read no other identity's graph. Pods in one graph SHALL be kept apart by the pod each claim, subject and value carries, and zones by the zone each claim and value carries. Nothing of a pod SHALL be built into the graph of an identity that is not its member.

**Example:** Alice and Bob are both members of "Ginger", and Alice alone of "Travel".

| identity | its graph holds | read through |
|---|---|---|
| Alice | "Ginger" and "Travel" | one graph |
| Bob | "Ginger" | a graph of his own, built from the same records of "Ginger" |
| Carol, a member of neither | nothing | — |

#### Scenario: One identity's pods share one graph

- **WHEN** Alice reads two pods she is a member of
- **THEN** both are in one graph, and Bob, a member of one of them, reads it from a graph of his own

#### Scenario: Nothing of a pod is built for a non-member

- **WHEN** Carol, who is not a member of "Ginger", asks to read it
- **THEN** she is refused, and her graph holds no pod

### Requirement: A read catches up first

Before it answers a read of claims (a find, a count, a page or one claim by its id), of subjects or of the types present, a handle SHALL bring every zone it reads up to date with that zone's records, each zone read from its own records. Reading a type, a shape or a type's generalizations SHALL need no catch-up.

**Example:** Bob writes "Ginger hates the blue bowl" in the chat of "Ginger". Alice's next read of chat's zone applies Bob's record first and returns it among the claims, with nothing else asked of her code.

#### Scenario: A record written by another member is read on the next read

- **WHEN** Bob writes a message in a pod's chat, and Alice then reads chat's zone of that pod
- **THEN** Alice reads Bob's message

### Requirement: Catching up adds what is new, replaces what changed and takes out what is gone

Catching a zone up SHALL add each claim new to it, SHALL replace a claim whose record is newer than the record it was applied from, and SHALL take out a claim whose key holds no claim any more. A claim already applied from the same record SHALL NOT be applied again, so catching up with records that have not changed applies nothing.

**Example:** a zone of Info in pod `p`, its catch-ups counted as the engine counts them.

| catch-up | records | bulk | appended | skipped |
|---|---|---|---|---|
| first | 40 claims | 40 | 0 | 0 |
| second | the same 40, and 1 more | 0 | 1 | 0 |
| third | the same 41 | 0 | 0 | 0 |

#### Scenario: The same records twice apply nothing

- **WHEN** a zone is caught up with records it has already been caught up with
- **THEN** nothing is added, replaced or taken out

#### Scenario: A new record after the first load is added on its own

- **WHEN** one record is added to a zone that holds 40 claims
- **THEN** that one claim is added, and the zone holds 41

### Requirement: A claim that does not fit its type is left out

A claim whose type the registry does not hold, or whose value does not fit its type's shape, SHALL be left out of the graph and counted as skipped. It SHALL NOT keep the claims beside it out, and SHALL NOT be tried again until its record changes.

**Example:** 12 claims of `mee:PetMedicationRecord:v1`, of which claim 5 has `{"medication": "not a list"}` for its value and claim 6 the type `mee:NoSuchType:v1`. The catch-up loads 10 and skips 2; a second catch-up with the same records applies nothing.

#### Scenario: Two claims that do not fit are skipped and the other ten load

- **WHEN** a zone is caught up with 12 records, one whose value does not fit its type and one whose type the registry does not hold
- **THEN** 10 claims load, 2 are skipped, and a catch-up with the same records tries neither again

### Requirement: A backlog loads in bulk, and the rest one claim at a time

A zone with nothing applied yet whose catch-up brings at least 32 claims SHALL load them in one bulk load. Zones with nothing applied yet that are caught up together SHALL load in one bulk load when there are at least 2 of them and their claims number at least 32 between them. Every other claim SHALL be added in a transaction of its own, so a reader never sees part of a claim. A bulk load and adding claim by claim SHALL give the same graph. A bulk load that fails SHALL leave no claims of the zones it was loading, which are then added claim by claim.

**Example:** with the threshold set to 10, five pods `a` to `e`, new to the graph, each bring 4 claims to one catch-up. None reaches 10 alone; together they bring 20, and load in one bulk load. Each pod then reads the same claims and subjects as in a graph that added the same claims one at a time.

#### Scenario: A pod new to the graph loads its backlog in bulk

- **WHEN** a pod new to the graph is caught up with 40 claims, at a threshold of 10
- **THEN** all 40 load in one bulk load, and read back oldest first, each as it was written

#### Scenario: Many small new pods load together

- **WHEN** five pods new to the graph, of 4 claims each, are caught up together at a threshold of 10
- **THEN** their 20 claims load in one bulk load, and each pod reads as it does when its claims are added one at a time

#### Scenario: Bulk-loaded and added claims are the same graph

- **WHEN** the same 40 claims are bulk-loaded into one graph and added one at a time into another
- **THEN** both return the same claims, subjects, finds and counts
