# Proposal: pods-removed-member-access

## Why

A removal under bearer tickets takes admission away and nothing else ([pod stores](../../specs/components/mee-pdn/data-layer/pod-store/spec.md)). Honest member devices refuse the removed member's devices the record store as a store they do not host, from the first session after the removed event reaches them, serve them the membership store only up to the removal, so a device offline during the removal learns of it at its first session, and read none of the entries it authors under a membership sequence at which it is no member. What the removed member keeps: both stores' write tickets, and both topic ids, which equal the stores' namespace ids, so it goes on receiving the content-free announcements of every write. Shedding a member entirely is a new pod today — a new pair of stores, the remaining members invited again, the content placed again.

**Example:** Alice, an owner of "Family", removes Carol; Carol's phone c1 is online and keeps what it held.

| what c1 does after the removal | what it gets |
|---|---|
| asks Bob's phone b1 for a session on the record store | `00 00 00 02 02 00`, the answer for a store b1 does not host |
| asks b1 for a session on the membership store | its removed event and the entries it rests on, and nothing written after |
| stays subscribed to the record store's topic | every content-free announcement: when members write, and how often |
| writes an entry naming her sequence 2, the removal's own | held on every honest member device and read by none |
| writes an entry after the removal naming her sequence 1 | read: a member's own history is taken on its word |

## What Changes

Nothing is decided. The change settles how a pod sheds a member entirely, and then specifies and builds the answer.

## Open Questions

### How a pod sheds a member entirely

- Identity-bound authorization: write authority leaves the ticket, and a store serves and admits by the identity a capability names, so a removed member's tickets open nothing. It rests on UWill, and the topic ids stay known to the removed member unless the stores move as well.
- Moving the pod to a new pair of stores: the owners mint new stores for the same pod, the remaining members' devices import them from the directory records that carry a pod's tickets, and the old stores are forgotten, so the removed member holds tickets and topic ids of stores nobody serves. It costs a full copy of the pod per shedding, and every member device has to take the move.
- A new pod, as today: nothing to build; the members lose the pod id, every link into the pod, and the content's history.

**Example:** Alice sheds Carol from "Family", which holds 1,000 records.

| option | Carol's tickets and topic ids | the remaining members |
|---|---|---|
| identity-bound authorization | open nothing, the topic ids still carrying announcements to her | keep the pod and its stores |
| a new pair of stores | name stores nobody serves | keep the pod id; every device copies 1,000 records into the new stores |
| a new pod | name the old stores, which the members leave | a new pod id; the 1,000 records placed again, and links into the old pod broken |

## Operating conditions

Once no member is left there is nobody even to refuse a removed member's device. A device offline during the removal changes nothing here: it learns of the removal at its first session with a member device.

## Capabilities

None is settled. Every option touches `components/mee-pdn/data-layer/pod-store`; moving the stores touches `components/mee-pdn/pdn-node/pods` and `components/mee-pdn/data-layer/private-metadata-store`.

## Impact

- **`crates/data-layer`**: the pod stores' admission.
- **`crates/pdn-node`**: moving a pod to new stores.
- **UWill**: identity-bound authorization, if a pod sheds a member through it.
