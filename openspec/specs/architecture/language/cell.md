# Cell

## Overview

A cell is a private space shared by its members, each a [Mee Identity](mee-identity.md): every member reads everything placed in it, its content stays with every member whether or not its author is online, and the relationship between two people is a cell of two members. A newcomer joins on one member's invitation and sees every member; no [connection](connection.md) between members is needed, and none is created.

A cell is identified by its cell id, 16 bytes derived from its creator's announcement key and a random nonce. The id carries no key material, and a cell signs nothing: every act inside a cell is the signed act of one of its members.

A cell is two stores, each held whole, as a replica of its own, by every member identity on every device that hosts it. The membership store holds who is a member, with what role, on which devices; the record store holds the records. Every member device relays what it holds, so any member device catches up from any other. The rules of both stores are in the [cell stores](../../components/mee-pdn/data-layer/cell-store/spec.md) spec, and the runtime's operations on a cell in the [cells](../../components/mee-pdn/pdn-node/cells/spec.md) spec.

## Records

A record is what a member places into a cell, under its own name, as one of three kinds chosen when it is placed. Every member reads every record: inside a cell there is no narrower audience. A record placed stays, and no member deletes or replaces one.

* **Claim** — a [claim](claim.md) placed into the cell, such as a driver's license or a parent's statement of a child's blood type: placed once and written only by its issuer.
* **Mergeable-document** — content the members edit, such as a note: every edit is an operation signed by its writer, any member appends operations to any mergeable-document, and merging the operations into one document happens above the platform.
* **Immutable-document** — content placed once, such as a PDF file: written by the member under whose name it sits and updated afterwards by no one.

## Roles

A cell has two roles, owner and member, and every owner is a member. The creator is the cell's first owner. A plain member reads every record, edits every mergeable-document and invites newcomers; an owner also acts on membership: it promotes a member to owner, demotes another owner, and kicks another member. A newcomer, and a member that joins again, is a plain member until an owner promotes it.

## Membership acts and their events

A membership act is what a member's device writes into the membership store; the event is what the act records in the chain of its subject, the member it is about. Each member's events form one sequence numbered from 1, and a member's state and role follow from its events in sequence order, never from when an event was written or when it arrived.

| act | written by | event in the subject's chain | the subject afterwards |
|---|---|---|---|
| found | the creator, when it creates the cell | founded | a member and an owner |
| invite | any member, once the newcomer presents the invite's one-time secret | joined | a plain member |
| leave | the member itself | left | no member |
| kick | an owner, on another member | kicked | no member |
| promote | an owner | promoted | an owner |
| demote | an owner, on another owner | demoted | a plain member |

A member that leaves, or learns it was kicked, forgets the record store and keeps the membership store as the cell's tombstone.

**Example:** Bob's chain in the cell "Family", which Alice created.

| sequence | act | event | Bob afterwards |
|---|---|---|---|
| 1 | Alice invites Bob | joined | a plain member |
| 2 | Alice promotes Bob | promoted | an owner |
| 3 | Bob leaves | left | no member |
| 4 | Carol invites Bob again | joined | a plain member, until an owner promotes him anew |
