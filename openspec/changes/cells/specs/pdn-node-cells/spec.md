# pdn-node: cells

The cells service of the runtime: creating a cell for a hosted identity, inviting and joining, ownership, reaching a member's other devices, removing and leaving, writing records — claims and documents — into the cell, and recovering hosted cells across a restart. The store underneath is the data layer's [cell store](../data-layer-cell-store/spec.md); this spec covers the runtime surface and the ceremonies. A cell has owners — the creator the first of them (cells D11); the ownership requirement below is the only one whose acts sit with owners, and every other operation is available to every member alike.

## ADDED Requirements

### Requirement: The cells service creates a cell for a hosted identity

The cells service SHALL create a cell for a hosted identity: it mints the cell id, creates the cell store, records the creating identity as the first member, and carries the given name with the cell. The name is a string, not an address — two cells of one identity MAY carry the same name, and only the cell id addresses a cell. Creating a cell for an identity the runtime does not host SHALL be refused with an unknown-identity error and no state created.

#### Scenario: A created cell is listed with its creator as member

- **WHEN** a hosted identity creates a cell named "Family"
- **THEN** the identity lists a cell with that name and a fresh cell id, whose members are exactly that identity

#### Scenario: Two cells with one name coexist

- **WHEN** a hosted identity creates two cells both named "Family"
- **THEN** both are listed, with different cell ids, and each is addressed by its own id

#### Scenario: Creating for an unhosted identity is refused

- **WHEN** a cell is requested for an identity the runtime neither created nor linked
- **THEN** the operation fails with the unknown-identity error and no cell store exists

### Requirement: Any member invites; a newcomer joins after a one-time secret is verified and burned

Any member's device SHALL mint a cell invite: a fresh one-time, short-lived secret pending on the inviting runtime, and a self-contained payload carrying a format version, the inviting device's node address, the secret and the cell id — no ticket and no identity proof. A newcomer SHALL join by presenting the secret in a dialogue with the inviter; the inviter SHALL verify and burn the secret atomically before any state change, then record the newcomer as a member and hand it the cell store's ticket. A refused presentation — wrong, expired or already burned — SHALL leave no observable state and SHALL NOT burn a live pending invite, and refusals SHALL be uniform. After joining, the newcomer's device holds the store, catches up on its existing content, and every member's devices list the newcomer.

#### Scenario: A newcomer joins and catches up

- **WHEN** a member invites and a hosted identity on another runtime joins with the invite
- **THEN** the newcomer reads the entries written before it joined, and the inviter's and the newcomer's devices both list the newcomer among the members

#### Scenario: An invited member invites in turn

- **WHEN** A invites B, and B then invites C from B's own device
- **THEN** C joins, and A's devices list C among the members without any act by A

#### Scenario: A replayed secret is refused without state

- **WHEN** a join completed against an invite and a second join presents the same secret
- **THEN** the second attempt is refused, and the cell's members and store are exactly as the first join left them

#### Scenario: A wrong secret burns nothing

- **WHEN** a dialer presents a secret that was never minted while an invite is pending
- **THEN** the attempt is refused with no observable state, and a subsequent join with the pending invite's real secret succeeds

### Requirement: A cell reaches a member's other devices

A cell created or joined on one device of an identity SHALL become reachable from that identity's other devices without a second join: the identity's directory carries what its other devices need to open the cell store, and a device that opens the cell from its directory registers itself into the cell's member device records. A device that resolves only as a device of an identity that is no member — a co-hosted identity on the same node included — SHALL NOT reach the cell.

#### Scenario: A linked device reaches the cell

- **WHEN** identity B joins a cell on its phone while B's laptop is linked into B
- **THEN** the laptop eventually lists the cell, reads its entries, and its own device is served by the other members

#### Scenario: A co-hosted non-member identity does not reach the cell

- **WHEN** a node hosts identity B, a member, and identity D, a non-member, and a caller resolves only as a device of D
- **THEN** D lists no such cell, and the caller is refused as for an unhosted store

### Requirement: The creator is the first owner; owners make and unmake owners

A created cell SHALL record its creating identity as the cell's first owner. An owner SHALL be able to make any member an owner, and taking ownership from a member SHALL be available only to another owner. An ownership act by a member that is no owner SHALL be refused with a typed error and change no state. A member whose ownership is taken remains a member.

#### Scenario: The creator is listed as owner

- **WHEN** a hosted identity creates a cell
- **THEN** the cell's owners are exactly the creating identity

#### Scenario: An owner makes a member an owner

- **WHEN** owner A makes member B an owner and the record reaches member C's devices
- **THEN** C lists both A and B among the owners

#### Scenario: A plain member's ownership act is refused

- **WHEN** member C, no owner, attempts to make a member an owner or to take owner B's ownership away
- **THEN** the act is refused with a typed error and every member still lists the owners unchanged

#### Scenario: An owner takes ownership from another owner

- **WHEN** owner A takes owner B's ownership away and the record reaches the members' devices
- **THEN** B is listed among the members and not among the owners

### Requirement: Any member removes a non-owner; an owner is removed only by another owner; leaving is forgetting

Any member's device SHALL be able to remove any member that is no owner, itself included. Removing an owner SHALL be available only to another owner: the attempt by a member that is no owner SHALL be refused with a typed error and change no state. A removal record replicates like every cell entry; the remaining members' devices refuse the removed member's devices from the next session, per the cell store's admission rule. A member that leaves SHALL forget the cell store on its own devices, so the cell is no longer listed there, while the remaining members are unaffected.

#### Scenario: A member removes another

- **WHEN** B removes C, neither an owner, from a cell with members A, B and C, and the removal reaches A's devices
- **THEN** A and B still sync the cell, and C's next session is refused

#### Scenario: A plain member cannot remove an owner

- **WHEN** member C, no owner, attempts to remove owner A
- **THEN** the attempt is refused with a typed error, A is still listed as member and owner, and every member's sessions continue

#### Scenario: An owner removes another owner

- **WHEN** owners A and B both own the cell and A removes B
- **THEN** B's next session is refused, and B is listed by no remaining member

#### Scenario: A member leaves

- **WHEN** C leaves the cell from one of its devices
- **THEN** C's devices no longer list the cell, and A and B still read each other's entries

### Requirement: A claim is immutable; a document carries a mode

The cells service SHALL write a claim into a cell as an immutable entry: it offers no operation that changes a stored claim's payload, and a write addressed at an existing claim SHALL be refused with a typed error, the stored payload surviving. A document SHALL be written with its mode — read-only or read-write — and read back by every member. Reading SHALL be by cell id, and reading a cell the identity is no member of SHALL fail with the unknown-cell error.

#### Scenario: A claim round-trips unchanged

- **WHEN** member A writes a claim into a cell and member B reads it
- **THEN** B reads the bytes A wrote

#### Scenario: A claim cannot be overwritten

- **WHEN** a write is addressed at an existing claim
- **THEN** it is refused with a typed error and every member still reads the original bytes

#### Scenario: A read-write document is edited by another member

- **WHEN** A writes a document read-write and B writes a new value into it
- **THEN** A reads B's value

### Requirement: Hosted cells survive a restart

A directory-configured runtime SHALL host again, after a restart, every cell its hosted identities are members of, from durable state alone — the cell store keeps replicating and its members' devices are served — while a memory runtime's cells end with the process.

#### Scenario: A cell is hosted again after a restart

- **WHEN** a runtime on a storage directory hosts a member of a cell, stops, and starts again on the same directory, while another member wrote an entry in between
- **THEN** the identity lists the cell, and the entry written meanwhile arrives
