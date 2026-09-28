# Proposal: cells-kicked-member-access

## Why

A kick under bearer tickets takes admission away and nothing else ([cell stores](../../specs/components/mee-pdn/data-layer/cell-store/spec.md)). Honest member devices refuse the kicked member's sessions as for a store they do not host, from the first session after the kicked event reaches them, and drop the entries it authors under a membership sequence at which it is no member. What the kicked member keeps: both stores' write tickets; both topic ids, which equal the stores' namespace ids, so it goes on receiving the content-free announcements of every write; and every payload hash it has seen, which any member device serves, since the blob store is the node's and its egress is ungated. A kicked member whose devices were offline during the kick learns nothing of it: its device shows a cell whose members seem offline and keeps writing entries nobody receives. Shedding a member entirely is a new cell today — a new pair of stores, the remaining members invited again, the content placed again.

**Example:** Alice, an owner of "Family", kicks Carol; Carol's phone c1 is online and keeps what it held.

| what c1 does after the kick | what it gets |
|---|---|
| asks Bob's phone b1 for a session on either store | `00 00 00 02 02 00`, the answer for a store b1 does not host |
| stays subscribed to the record store's topic | every content-free announcement: when members write, and how often |
| fetches from b1 the payload of a scan whose hash it saw before the kick | the payload |
| writes an entry naming her sequence 2, the kick's own | dropped on every honest member device |
| writes an entry after the kick naming her sequence 1 | admitted: a member's own history is taken on its word |

## What Changes

Nothing is decided. The change settles how a cell sheds a member entirely, whether payload bytes stop reaching a party outside the cell, and what a kicked member's offline device learns, and then specifies and builds the answers.

## Open Questions

### How a cell sheds a member entirely

- Identity-bound authorization: write authority leaves the ticket, and a store serves and admits by the identity a capability names, so a kicked member's tickets open nothing. It rests on UWill, and the topic ids stay known to the kicked member unless the stores move as well.
- Moving the cell to a new pair of stores: the owners mint new stores for the same cell, the remaining members' devices import them from the directory records that carry a cell's tickets, and the old stores are forgotten, so the kicked member holds tickets and topic ids of stores nobody serves. It costs a full copy of the cell per shedding, and every member device has to take the move.
- A new cell, as today: nothing to build; the members lose the cell id, every link into the cell, and the content's history.

**Example:** Alice sheds Carol from "Family", which holds 1,000 records.

| option | Carol's tickets and topic ids | the remaining members |
|---|---|---|
| identity-bound authorization | open nothing, the topic ids still carrying announcements to her | keep the cell and its stores |
| a new pair of stores | name stores nobody serves | keep the cell id; every device copies 1,000 records into the new stores |
| a new cell | name the old stores, which the members leave | a new cell id; the 1,000 records placed again, and links into the old cell broken |

### Payload bytes served by hash

- A gate on blob egress by identity: a payload is served only to a device of an identity entitled to a replica on the serving node that references its hash — iroh-blobs offers a hook for it — which rests on the node knowing who is asking. A kicked member fetches nothing.
- Accepted: a hash is a secret only as long as nobody outside the cell learns it, and a kicked member knows every hash it saw.

**Example:** c1, kicked, asks Bob's phone b1 for the payload of the scan whose hash it saw before the kick.

| option | b1 |
|---|---|
| a gate on blob egress | refuses: Carol is entitled to no replica on b1 that references the hash |
| accepted | serves the payload |

### What a kicked member's offline device learns

- Serve a kicked member's device its own kicked event before refusing: the cell's existence is no secret to it.
- Leave it to the application, which shows a cell unsynced for long as stale.

**Example:** Carol's phone c1 is offline for a week, during which Alice kicks her from "Family"; c1 then dials Bob's phone b1.

| option | c1's session with b1 | what c1 shows Carol |
|---|---|---|
| serve the kicked event before refusing | b1 hands c1 Carol's kicked event, then refuses | that she is out of "Family" |
| leave it to the application | b1 refuses as for a store it does not host | "Family" with every member offline, marked stale once long unsynced, while her new records reach nobody |

## Operating conditions

A device offline during the kick is the last question. Several identities on one node share one blob store, so a gate on blob egress has to judge by the identity asking, not the node. Once no member is left there is nobody even to refuse a kicked member's device.

## Capabilities

None is settled. Every option touches `components/mee-pdn/data-layer/cell-store`; moving the stores touches `components/mee-pdn/pdn-node/cells` and `components/mee-pdn/data-layer/private-metadata-store`; the blob gate touches `components/mee-pdn/data-layer/node-assembly`.

## Impact

- **`crates/data-layer`**: the cell stores' admission, the blob egress gate.
- **`crates/pdn-node`**: moving a cell to new stores, and the kicked event served before a refusal.
- **UWill**: identity-bound authorization, if a cell sheds a member through it.
