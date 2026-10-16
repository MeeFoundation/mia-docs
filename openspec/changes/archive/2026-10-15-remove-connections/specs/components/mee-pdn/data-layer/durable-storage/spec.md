## MODIFIED Requirements

### Requirement: One author per hosted identity, persisted with that identity's stores
Every store a hosted identity holds SHALL write with that identity's one author, and that author SHALL be persisted with the identity's replicas, so a node that restarts writes each identity's entries as the author it wrote them as before. An author minted per store or per start makes a rewritten key accumulate one live record per author: replacement and deletion are scoped to the writing author and to one key, so every superseded copy stays live in the replica and replicates. A device record written under one author and withdrawn under another likewise stays in the replica; the set still reads the device as absent, because the latest-per-key collapse sees the tombstone before empty entries are excluded — a query behavior the withdrawal scenario pins. Two identities of one node SHALL write with two different authors, so what a pod binds to an identity on this device is that identity's author and not the node's.

**Example:** a1 writes its device record `devices/<a1-hex>` into Alice's PMS, the node restarts, and it writes the record again; A1 and A2 are authors.

| | author persisted in `default-author` | author minted per start |
|---|---|---|
| before the restart | `(A1, devices/<a1-hex>)` | `(A1, devices/<a1-hex>)` |
| after the rewrite | `(A1, devices/<a1-hex>)`, the newer one | `(A1, devices/<a1-hex>)`, `(A2, devices/<a1-hex>)` |
| live records at the key | 1 | 2, and the stale one replicates |

#### Scenario: A rewritten key keeps one live record
- **WHEN** a hosted identity writes a path, the node restarts, and it writes the same path again
- **THEN** the replica holds one live record for that path, carrying the newer value

#### Scenario: A withdrawn device does not come back with a restart
- **WHEN** a device is withdrawn from an identity's device set, and a device of that identity restarts
- **THEN** the withdrawn device is absent from the set as read after the restart

#### Scenario: Two identities on one node write as two authors
- **WHEN** two identities hosted on one node each write an entry
- **THEN** the two entries carry two different authors, and each identity's later writes carry the one it wrote with before
