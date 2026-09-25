## ADDED Requirements

### Requirement: A write affects only its own path
A write SHALL affect only the entry at its own path: the entry replaces the earlier entry its author wrote at that path and leaves every other path standing on every replica, a longer path beginning with the same components or with the same bytes included. An entry arriving by sync SHALL be refused only by an entry of its author at its own path that is newer or equal.

#### Scenario: A write at a shorter path leaves the longer ones standing

- **WHEN** a device writes entries at `contact/email` and `contacts/emergency` under one issuer, and then an entry at `contact`
- **THEN** listing that issuer yields all three paths, each reading the payload written at it, on that device and on the identity's other device once it syncs
