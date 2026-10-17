## ADDED Requirements

### Requirement: An entry whose hash and length disagree on emptiness is dropped on every replica

The fork SHALL count an entry as empty exactly when its content hash is the hash of no bytes and its length is 0, and SHALL drop an entry arriving over sync whose hash and length disagree on that — the empty hash with a length, or another hash with a length of 0 — whatever the session admits, as the base validation drops an entry with a bad signature, while the session goes on with the rest. Only a modified node signs such an entry; held, it would read as a deletion to a reader that judges emptiness by the hash, as the store does, and as content to one that judges by the length. A record the fork reads back from its own store file is built without the check, since a store written before the check can hold one.

**Example:** Bob's modified phone b1, a member of "Family", offers Carol's phone c1 three entries in one session.

| entry b1 offers | content hash | length | on c1 |
|---|---|---|---|
| `whole` | the hash of `v` | 1 | stored |
| `empty-hash-with-a-length` | the hash of no bytes | 5 | dropped silently; the session goes on |
| `a-length-of-zero` | the hash of `v` | 0 | dropped silently |

#### Scenario: An entry whose hash and length disagree on emptiness is dropped at ingest

- **WHEN** a peer offers in one session an entry with the empty hash and a length, an entry with another hash and a length of 0, and a whole entry
- **THEN** the device holds the whole entry and neither of the other two, and the session completes
