# pdn-node: cells

The cells service of the runtime: creating a cell for a hosted identity, inviting and joining, ownership, reaching a member's other devices, removing and leaving, writing records — claims and documents — into the cell, and recovering hosted cells across a restart. The two stores underneath — the membership store and the record store — are the data layer's [cell stores](../../data-layer/cell-store/spec.md); this spec covers the runtime surface and the ceremonies. A cell has two roles, owner and member — the creator the first owner. Who may do what by role is in the tables below: on the cell itself, then on each kind of record, where "own" is a record under one's own name — a record is created under one's own name only, and replacing is deleting and creating anew under one's own name.

**Cell**

|                               | Cell owner | Cell member |
| ----------------------------- | ---------- | ----------- |
| Rename cell for all members   | yes        | no          |
| Invite member to a cell       | yes        | yes         |
| Leave cell                    | yes        | yes         |
| Delete cell for all members   | no         | no          |
| Promote member to owner       | yes        | no          |
| Demote owner to member        | yes        | no          |
| Remove member from cell       | yes        | no          |
| Remove owner-member from cell | yes        | no          |

**Immutable document** — attachments, for example a PDF file.

|                                                          | Cell owner | Cell member |
| -------------------------------------------------------- | ---------- | ----------- |
| Read own document                                        | yes        | yes         |
| Read another member's document                           | yes        | yes         |
| Create own document                                      | yes        | yes         |
| Create a document as if it is authored by another member | no         | no          |
| Update own document                                      | no         | no          |
| Update another member's document                         | no         | no          |
| Delete own document                                      | yes        | yes         |
| Delete another member's document                         | yes        | no          |

**Mergeable document** — for example a note.

|                                                                 | Cell owner | Cell member |
| --------------------------------------------------------------- | ---------- | ----------- |
| Read own document                                               | yes        | yes         |
| Read another member's document                                  | yes        | yes         |
| Create own document                                             | yes        | yes         |
| Create a document as if it is authored by another member        | no         | no          |
| Edit own document                                               | yes        | yes         |
| Edit another member's document (preserving per-edit authorship) | yes        | yes         |
| Delete own document                                             | yes        | yes         |
| Delete another member's document                                | yes        | no          |

**Claim**

|                                                    | Cell owner | Cell member |
| -------------------------------------------------- | ---------- | ----------- |
| Read own claim                                     | yes        | yes         |
| Read another member's claim                        | yes        | yes         |
| Issue own claim                                    | yes        | yes         |
| Issue a claim as if it is issued by another member | no         | no          |
| Update own claim                                   | no         | no          |
| Update another member's claim                      | no         | no          |
| Delete own claim                                   | yes        | yes         |
| Delete another member's claim                      | yes        | no          |

## ADDED Requirements

### Requirement: The cells service creates a cell for a hosted identity

The cells service SHALL create a cell for a hosted identity: it mints the cell id, creates the membership store and the record store, records the creating identity as the first member, and carries the given name with the cell. The name is a string, not an address — two cells of one identity MAY carry the same name, and only the cell id addresses a cell. Creating a cell for an identity the runtime does not host SHALL be refused with an unknown-identity error and no state created.

#### Scenario: A created cell is listed with its creator as member

- **WHEN** a hosted identity creates a cell named "Family"
- **THEN** the identity lists a cell with that name and a fresh cell id, whose members are exactly that identity

#### Scenario: Two cells with one name coexist

- **WHEN** a hosted identity creates two cells both named "Family"
- **THEN** both are listed, with different cell ids, and each is addressed by its own id

#### Scenario: Creating for an unhosted identity is refused

- **WHEN** a cell is requested for an identity the runtime neither created nor linked
- **THEN** the operation fails with the unknown-identity error and no store exists for it

### Requirement: Any member invites; a newcomer joins after a one-time secret is verified and burned

Any member's device SHALL mint a cell invite: a fresh one-time, short-lived secret pending on the inviting runtime, and a self-contained payload carrying a format version, the inviting device's node address, the secret and the cell id — no ticket and no identity proof. A newcomer SHALL join by presenting the secret in a dialogue with the inviter; the inviter SHALL verify and burn the secret atomically before any state change, then record the newcomer as a member — a plain member, no owner — and hand it the write tickets of both stores. A refused presentation — wrong, expired or already burned — SHALL leave no observable state and SHALL NOT burn a live pending invite, and refusals SHALL be uniform. After joining, the newcomer's device holds the store, catches up on its existing content, and every member's devices list the newcomer.

#### Scenario: A newcomer joins and catches up

- **WHEN** a member invites and a hosted identity on another runtime joins with the invite
- **THEN** the newcomer reads the entries written before it joined, and the inviter's and the newcomer's devices both list the newcomer among the members

#### Scenario: An invited member invites in turn

- **WHEN** A invites B, and B then invites C from B's own device
- **THEN** C joins, and A's devices list C among the members without any act by A

#### Scenario: A replayed secret is refused without state

- **WHEN** a join completed against an invite and a second join presents the same secret
- **THEN** the second attempt is refused, and the cell's members and store are exactly as the first join left them

#### Scenario: A former member joins again

- **WHEN** C left the cell or was removed from it, and a member invites C again and C joins
- **THEN** C reads the cell, its earlier records among what it reads, and a new record C writes reaches every member

#### Scenario: A wrong secret burns nothing

- **WHEN** a dialer presents a secret that was never minted while an invite is pending
- **THEN** the attempt is refused with no observable state, and a subsequent join with the pending invite's real secret succeeds

### Requirement: A cell reaches a member's other devices

A cell created or joined on one device of an identity SHALL become reachable from that identity's other devices without a second join: the identity's directory carries what its other devices need to open both stores — the announcement secret beside their tickets — and a device that opens the cell from its directory registers itself by writing the identity's newest device statement into the membership store. A device that resolves only as a device of an identity that is no member — a co-hosted identity on the same node included — SHALL NOT reach the cell.

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

### Requirement: Only an owner removes a member; leaving is forgetting

Removing a member — an owner or a plain member alike — SHALL be available only to an owner's device; the attempt by a member that is no owner SHALL be refused with a typed error and change no state. A removal event replicates like every cell entry; the remaining members' devices refuse the removed member's devices from the next session, per the cell stores' admission rule. A member that leaves SHALL forget both stores on its own devices, so the cell is no longer listed there, while the remaining members are unaffected and everything the member wrote — its records, its operations on other members' documents — stays in the cell.

#### Scenario: An owner removes a member

- **WHEN** owner A removes member C from a cell with members A, B and C, and the removal reaches B's devices
- **THEN** A and B still sync the cell, and C's next session is refused

#### Scenario: A plain member removes nobody

- **WHEN** member C, no owner, attempts to remove member B
- **THEN** the attempt is refused with a typed error, B is still listed by every member, and B's devices are still served

#### Scenario: An owner removes another owner

- **WHEN** owners A and B both own the cell and A removes B
- **THEN** B's next session is refused, and B is listed by no remaining member

#### Scenario: A member leaves

- **WHEN** C leaves the cell from one of its devices
- **THEN** C's devices no longer list the cell, A and B still read each other's entries, and C's records and operations are still read by A and B

### Requirement: A claim and an immutable-document are placed once; a mergeable-document is edited by every member

The cells service SHALL write a claim into a cell as an immutable entry: it offers no operation that changes a stored claim's payload, and a write addressed at an existing claim SHALL be refused with a typed error, the stored payload surviving. A document SHALL be placed with its type — mergeable-document or immutable-document — under the placing identity's name and read back by every member. An immutable-document SHALL be placed once, like a claim: a write addressed at an existing one SHALL be refused with a typed error, whoever the caller is, the placing identity included. An edit of a mergeable-document SHALL be accepted from any member, each operation under the writer's own signature; an edit by an identity that is no member SHALL fail with the unknown-cell error. A claim or an immutable-document is replaced by deleting it and placing a new one: the deletion SHALL be available to the identity under whose name the record sits and to any owner, and refused to any other member with a typed error; the new record sits under the replacer's name with a new id. Reading SHALL be by cell id, and reading a cell the identity is no member of SHALL fail with the unknown-cell error.

#### Scenario: A claim round-trips unchanged

- **WHEN** member A writes a claim into a cell and member B reads it
- **THEN** B reads the bytes A wrote

#### Scenario: A claim cannot be overwritten

- **WHEN** a write is addressed at an existing claim
- **THEN** it is refused with a typed error and every member still reads the original bytes

#### Scenario: An immutable-document is not updated, by its member either

- **WHEN** member B places an immutable-document and B's device writes to it again
- **THEN** the write is refused with a typed error and every member still reads the bytes B placed first

#### Scenario: Any member edits another member's mergeable-document

- **WHEN** member B places a mergeable-document and member C, no owner, appends an operation to it
- **THEN** B's devices hold C's operation, authored by C

#### Scenario: A non-member edits nothing

- **WHEN** a hosted identity that is no member of the cell appends an operation to its mergeable-document
- **THEN** the edit fails with the unknown-cell error and no member's device holds such an operation

#### Scenario: An owner replaces a member's record

- **WHEN** member B places a claim and an immutable-document, and owner A deletes each and places its own in their place
- **THEN** every member reads A's records under ids different from B's, with A as their issuer and placing member, and B's records are no longer read

#### Scenario: A member replaces its own record

- **WHEN** member B, no owner, places an immutable-document, deletes it and places a new one
- **THEN** every member reads the new document under a new id, and the old one is no longer read

#### Scenario: A plain member deletes no other member's record

- **WHEN** member C, no owner, attempts to delete B's claim or B's immutable-document
- **THEN** the attempt is refused with a typed error and every member still reads B's records

### Requirement: Hosted cells survive a restart

A directory-configured runtime SHALL host again, after a restart, every cell its hosted identities are members of, from durable state alone — both stores keep replicating and its members' devices are served — while a memory runtime's cells end with the process.

#### Scenario: A cell is hosted again after a restart

- **WHEN** a runtime on a storage directory hosts a member of a cell, stops, and starts again on the same directory, while another member wrote an entry in between
- **THEN** the identity lists the cell, and the entry written meanwhile arrives
