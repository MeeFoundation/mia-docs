# Vector index

> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

## Purpose

The graph query engine's search by meaning ([ADR-0019](../../../../architecture/adr/0019-pods-read-through-a-graph-query-engine.md)): an index of texts and their vectors that finds the texts nearest to a given vector. An index has an owner, the code that made it, which hands it each text with a vector it made itself: the engine makes no vector and holds no model. Like the graph, an index is the engine's, held by its device alone and never synced; no code outside the engine reaches the database it is kept in.

## ADDED Requirements

### Requirement: An index holds what its owner puts in it

An index SHALL be made for vectors of one dimension, empty or with entries, and SHALL take more entries after it is made. An entry SHALL be an id, the pod it is from, its text, two labels of the owner's (what kind of text it is, and what a citation of it names) and its vector, and the engine SHALL return an entry's id, pod, text and labels as they were given. A search SHALL reach only the entries its owner put into that index: nothing of the graph, and nothing of another index.

**Example:** an index of 3 dimensions, made with three entries.

| id | pod | text | vector |
|---|---|---|---|
| `passport` | Travel | Alice's passport expires 2027-09-01 | [0.9, 0.1, 0.0] |
| `licence` | Travel | Alice's licence expires 2026-12-15 | [0.8, 0.3, 0.1] |
| `ginger` | Ginger | Ginger takes amoxicillin | [0.0, 0.2, 0.9] |

#### Scenario: An entry added after the index was made is found

- **WHEN** an index is made with 200 entries, and one entry is added whose vector is unlike any of theirs
- **THEN** a search for that vector finds the added entry first, and the index holds 201

#### Scenario: An index made empty takes its first entries

- **WHEN** an index is made with no entries, and one entry is added
- **THEN** a search for that entry's vector finds it

### Requirement: A search returns the nearest entries, nearest first

A search SHALL return at most the number of entries asked for, those nearest to the given vector by cosine distance, nearest first, each with its distance. It SHALL keep at least 1,000 candidates as it walks the index. A search of an index with no entries SHALL return nothing.

**Example:** in the index above, a search for the 2 entries nearest to [1.0, 0.1, 0.0] returns `passport`, then `licence`, and not `ginger`.

#### Scenario: The two nearest come back, nearest first

- **WHEN** an index holds the passport, the licence and Ginger's medicine, and a search asks for the 2 entries nearest to a vector close to the passport's
- **THEN** it returns the passport, then the licence

#### Scenario: An empty index finds nothing

- **WHEN** a search runs on an index with no entries
- **THEN** it returns no entry

### Requirement: An index is made and searched with nothing to install

The engine SHALL carry the graph database's vector search in its own build, on every platform the app is built for, Android among them, so that making and searching an index fetches and installs nothing at run time.

**Example:** the app built for Android against the engine makes its index on Alice's phone and searches it, with no extension of the graph database downloaded or installed there.

#### Scenario: An index is made and searched in a plain build

- **WHEN** an index is made and searched in a build of the engine, on a machine where nothing of the graph database is installed
- **THEN** the index is made, and the search returns the nearest entries

### Requirement: An index is held on its device and leaves nothing behind

An index SHALL be held by the device it was made on, SHALL NOT sync, and SHALL leave nothing on the device once its owner lets go of it. An owner that needs an index again after its process restarts SHALL make it again.

**Example:** the assistant on Alice's phone and the assistant on her laptop each make an index of their own from what each device holds. When the app on the phone ends, the phone's index and its files are gone; the next start makes it again.

#### Scenario: An index leaves no files behind

- **WHEN** an owner makes an index, searches it and lets go of it
- **THEN** nothing of the index is left on the device
