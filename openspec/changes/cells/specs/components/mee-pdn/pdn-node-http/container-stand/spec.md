# pdn-node-http: container stand — delta for cells

## ADDED Requirements

### Requirement: The stand runs a cell across three containers with its paired denials

The stand SHALL run, across three containers, a cell's creation, an invitation by its creator and one by an invited member, a claim and a mergeable-document placed by the creator, and an operation on that document appended by another member; it SHALL promote a member to owner, kick a member through that owner, and restart a member's node. In the same scenario it SHALL assert the tightest denials: a plain member's deletion of another member's claim, its rename of the cell and its kick of a member are refused while the creator's deletion of its own claim goes through; a consumed invite secret is refused; a kicked member stops receiving records after the remaining members are shown to receive a later one; and a cell left before a restart stays left. What a modified node does — a forged entry, an entry outside the key layout, a rewritten event — is not reachable over HTTP, and the data layer's own tests hold it.

#### Scenario: Any member invites, and the cell reaches all three

- **WHEN** container A creates a cell and invites B, B joins and invites C, and C joins
- **THEN** all three list the same members, and a second join presenting B's consumed invite is refused with a client error

#### Scenario: A record and an edit reach every member

- **WHEN** A places a claim and a mergeable-document, and C appends an operation to A's document
- **THEN** B reads the claim and both A's and C's operations by repeating the read

#### Scenario: A plain member's owner-only acts are refused

- **WHEN** C, no owner, deletes A's claim, renames the cell and kicks B, and A deletes a second claim of its own
- **THEN** C's three requests are client errors and A's first claim, the name and B's membership are unchanged, while A's second claim no longer reads on any container

#### Scenario: A kicked member stops receiving

- **WHEN** A promotes B, B kicks C, and A places two records one after the other
- **THEN** B reads both, and C reads neither within the budget once B has read the second

#### Scenario: A member's node comes back with its cell

- **WHEN** B's container is stopped, A places a record, and B's container starts again on its state directory
- **THEN** B lists the cell and reads the record placed meanwhile, with no invite minted after the restart

#### Scenario: A cell left before a restart stays left

- **WHEN** B joins a second cell, leaves it, and its container restarts on its state directory
- **THEN** B lists no such cell, and requests addressing it are refused with a client error
