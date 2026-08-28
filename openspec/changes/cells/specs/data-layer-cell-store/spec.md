# data-layer: cell store

A cell is a space shared by 0..n members — identities, of persons or organizations — identified by a cell id that carries no key material. Its content lives in one dedicated pdn-store replica, the **cell store**, held whole by every device of every member: no egress filter runs inside a cell, member devices form the replica's swarm, and any member device catches up from any other. What keeps a cell honest is admission: a session is served to member devices only, and an entry is admitted by its author — a claim from the devices of the member that issued it, a document per the mode it was shared under — judged on every member device, so that a forged entry stops at the first honest device it meets. The runtime's cells service ([pdn-node cells](../pdn-node-cells/spec.md)) creates and joins cell stores; this spec covers the store itself.

## ADDED Requirements

### Requirement: A cell is one dedicated replica

A cell SHALL be served by exactly one pdn-store replica, its cell store, separate from every data store, every directory, every connection metadata store and every other cell's store. Two cells SHALL NOT share a replica, whatever their member sets. The store SHALL be addressed by the cell id, and no domain namespace id is allocated for it.

#### Scenario: Creating a cell allocates a dedicated replica

- **WHEN** a node creates a cell store
- **THEN** a fresh pdn-store replica is created for it, reached through the cell id, and no domain namespace id is allocated

#### Scenario: Two cells with the same members are two replicas

- **WHEN** the same identities are members of two cells and an entry is written into one of them
- **THEN** the entry never appears in the other cell's store

### Requirement: The cell id carries no key material

A cell SHALL be identified by a 32-byte cell id minted at creation. The id SHALL carry no key material and SHALL NOT equal the replica's namespace id: knowing the cell id grants no access, and no operation on a cell requires a signature by the cell — every write into the store is signed by the writing device's author key, and every membership act is a member's act.

#### Scenario: The cell id is not the namespace id

- **WHEN** a cell store is created
- **THEN** its cell id and its replica's namespace id differ

#### Scenario: Knowing the cell id is not holding the store

- **WHEN** a party knows a cell's id but holds no ticket to its store and is a device of no member
- **THEN** it obtains no session, no entry and no existence signal for the store

### Requirement: Every member device holds the whole store and the write ticket

Every device of every member SHALL hold the cell store whole and SHALL hold its write ticket: a session between two member devices delivers every entry with no egress filter, and authority to write inside the cell is judged by the ingest gate per entry, never by ticket mode. Member devices SHALL form the replica's swarm, so a write reaches the other member devices through the content-free announcement and the pull it triggers, and a member device SHALL be able to catch up from any other member device, not only from an entry's author.

#### Scenario: A write reaches a member through another member

- **WHEN** member A writes an entry, A's devices go offline, and a device of member C — which never synced with A — reconciles with a device of member B that holds the entry
- **THEN** C's device receives the entry, payload included

#### Scenario: A write arrives live over the swarm

- **WHEN** a member writes an entry while devices of the other members are members of the store's swarm
- **THEN** every such device converges on the entry through the announcement and a pull, none of them holding a grant

### Requirement: Only member devices are served

A session for a cell store SHALL be served only to a caller that resolves, by authenticated node id, as a device of a current member; every other caller SHALL be refused indistinguishably from the store not being hosted — a holder of the store's ticket included. A device of a member removed from the cell SHALL be refused from the first session set up after the removal record reaches the serving device; what it obtained while a member is retained.

#### Scenario: A member device is served whole

- **WHEN** a device of a current member requests a session for the store
- **THEN** the session is served and delivers every entry

#### Scenario: A ticket holder that is no member obtains nothing

- **WHEN** a caller holding the store's ticket but a device of no member requests a session
- **THEN** the request is refused with the answer an unhosted replica would produce, and no fingerprint, count or existence signal is revealed

#### Scenario: A removed member is refused from the next session

- **WHEN** a member is removed and the removal record has reached a serving device, and a device of the removed member then requests a session
- **THEN** the request is refused as for an unhosted replica, while the remaining members' devices are still served, and what the removed device obtained while a member is still readable on it

### Requirement: Membership needs no connection

Access to a cell store SHALL rest on membership alone: no connection between two members is required for either to read what the other wrote, and joining a cell SHALL create no connection.

#### Scenario: Three identities share through a cell with no connections

- **WHEN** identities A, B and C hold no connection to one another, A creates a cell and invites B and C, and B writes an entry
- **THEN** C's device reads the entry, and no identity lists any connection

### Requirement: A claim is written only by its issuer

An entry that is a claim SHALL be admitted over sync only when it was authored by a device of the member the claim names as its issuer. A claim entry authored by a device of any other member SHALL be dropped before persisting, on every member device, silently — the verdict is on the entry's author, not on the session peer that carried it, so an entry relayed by a third member keeps the verdict its author earns.

#### Scenario: The issuer's own claim is admitted

- **WHEN** a device of member A writes a claim issued by A and a device of member B reconciles
- **THEN** B's device persists the claim

#### Scenario: Another member's entry under the issuer's claims is dropped

- **WHEN** a device of member B produces an entry that names A as the claim's issuer and reconciles with a device of A or of a third member
- **THEN** the entry is not persisted, no rejection is signalled, and A's own claim at that key survives unchanged

#### Scenario: A relayed claim is judged by its author

- **WHEN** a device of member C receives, from a device of member B, a claim authored by a device of A that names A as issuer
- **THEN** C's device persists it, although the session peer is B

### Requirement: A document's mode bounds who writes it

A document SHALL be shared with the whole cell in exactly one of two modes: read-only — only devices of the member that created it write it — or read-write — devices of any member write it. An entry in a read-only document authored by a device of any other member SHALL be dropped before persisting, silently, on every member device; an entry in a read-write document authored by any member's device SHALL be admitted and compete by per-key last-writer-wins across authors.

#### Scenario: Any member writes a read-write document

- **WHEN** member A shares a document read-write and a device of member B writes it
- **THEN** every member's devices converge on B's newer entry

#### Scenario: Only the creator writes a read-only document

- **WHEN** member A shares a document read-only and a device of member B produces an entry in it
- **THEN** no member device persists B's entry, and A's own entry survives unchanged, while a later write by A's device is admitted everywhere

### Requirement: A cell store can be forgotten

Forgetting a cell store SHALL stop reconciling its replica, leave its swarm, drop the replica, and remove the cell's registration together, so that operations addressed to that cell afterwards fail with an unknown-cell error distinguishable from transport and storage failures.

#### Scenario: Forgetting a cell unregisters it

- **WHEN** a node holds a cell store and forgets it
- **THEN** reading or writing under that cell fails with the unknown-cell error, and the node's other cell stores are unaffected
