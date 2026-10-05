# pdn-node-http: container stand — delta for cells

## ADDED Requirements

### Requirement: The stand runs a cell across three containers with its paired denials

The stand SHALL run, across three containers, a [cell](../../../../architecture/language/cell.md)'s creation, an invitation by its creator and one by an invited member, a claim and a mergeable-document placed by the creator, and an operation on that document appended by another member; it SHALL promote a member to owner, kick a member through that owner, and restart a member's node. In the same scenario it SHALL assert the tightest denials: a plain member's promotion of itself and its kick of a member are refused while an owner's promotion and kick go through; a consumed invite secret is refused; a kicked member stops receiving records after the remaining members are shown to receive a later one; and a cell left before a restart stays left. What a modified node does — a forged entry, an entry outside the key layout — is not reachable over HTTP, and the data layer's own tests hold it.

**Example:** the scenario across containers A, B and C, hosting Alice, Bob and Carol, every step a request over HTTP.

| step | A | B | C |
|---|---|---|---|
| 1 | creates "Family" and invites B | joins and invites C | joins; B's invite presented again is a client error |
| 2 | places a claim and a note | | appends an operation to A's note |
| 3 | | reads the claim and both operations | promotes itself and kicks B: two 403s |
| 4 | promotes B: B is an owner on every container | kicks C | |
| 5 | places two records, one after the other | reads both | reads neither within the budget |
| 6 | places a record while B's container is stopped | starts again on its state directory, lists the cell and reads the record | |
| 7 | creates a second cell and invites B | joins it, leaves it and restarts: lists no such cell, and requests addressing it are 409 | |

#### Scenario: Any member invites, and the cell reaches all three

- **WHEN** container A creates a cell and invites B, B joins and invites C, and C joins
- **THEN** all three list the same members, and a second join presenting B's consumed invite is refused with a client error

#### Scenario: A record and an edit reach every member

- **WHEN** A places a claim and a mergeable-document, and C appends an operation to A's document
- **THEN** B reads the claim and both A's and C's operations by repeating the read

#### Scenario: A plain member's owner-only acts are refused

- **WHEN** C, no owner, promotes itself and kicks B, and A then promotes B
- **THEN** C's two requests are client errors, C stays a plain member and B's membership is unchanged, while B reads as an owner on every container

#### Scenario: A kicked member stops receiving

- **WHEN** A promotes B, B kicks C, and A places two records one after the other
- **THEN** B reads both, and C reads neither within the budget once B has read the second

#### Scenario: A member's node comes back with its cell

- **WHEN** B's container is stopped, A places a record, and B's container starts again on its state directory
- **THEN** B lists the cell and reads the record placed meanwhile, with no invite minted after the restart

#### Scenario: A cell left before a restart stays left

- **WHEN** B joins a second cell, leaves it, and its container restarts on its state directory
- **THEN** B lists no such cell, and requests addressing it are refused with a client error
