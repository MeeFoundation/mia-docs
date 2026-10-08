# Proposal: pods-name

## Why

A pod is addressed by its pod id alone, 16 bytes written as 32 lowercase hexadecimal characters, and carries no name: `create` takes the identity and nothing else, and `list` answers the pods an identity is a member of by their ids ([pods](../../specs/components/mee-pdn/pdn-node/pods/spec.md)). People tell their pods apart by something they can read, and what that is has questions the product has not settled: whether every member sees one name, whether each member names a pod for itself, who may change a name every member sees, and how two changes made at once resolve. Nothing in a pod depends on a name — the pod id derives from the creator's `PdnId`, identity key and a nonce, and the created event carries those three and its signature — so a name added later is an addition, and a device that does not know it keeps the entries a later build writes for it and uses them for nothing, as it does every entry outside the key layout ([pod stores](../../specs/components/mee-pdn/data-layer/pod-store/spec.md)). Whatever carries a name, it stays among the pod's members: the pod id travels in notes to members of other pods, and a name may say more than an id.

**Example:** Alice's pods as `list` answers them on her phone a1.

| pod id | members |
|---|---|
| `ad58a3faa04cdc5576c8dc5823a347c6` | Alice, Bob, Carol |
| `684aad236ce530cd7b5dedb6ab6b755a` | Alice, Bob |
| Nothing on the platform tells Alice that the first is her family's and the second the one about her and Bob. | |

## What Changes

Nothing is decided. The change settles the questions below, strongest option first where a question has options, and then specifies and builds the answers: a call beside `create`, which stays as it is, that gives a pod its name, and the name in what `list` answers.

## Open Questions

### Whether a pod carries one name every member sees

- One shared name, optional. A pod carries at most one name, and every member reads the same one. A pod about the relationship between its two members, which each of them sees from their own side, carries none, and each member names it for itself (next question); the application, which knows what a pod is about, decides which pods carry a shared name.
- One shared name, always, from the pod's creation. The creator's name for a two-member pod reaches the other member, including a name meant for the creator's eyes alone.
- No shared name: every member names every pod for itself.

**Example:** Alice's pod with Bob, which she calls "Bob (landlord)", and "Family" with Alice, Bob and Carol, under each option.

| option | Alice's pod with Bob, on Bob's phone | "Family", on Carol's phone |
|---|---|---|
| one shared name, optional | no shared name: Bob's own name for it | "Family", as Alice named it |
| one shared name, always | "Bob (landlord)" | "Family" |
| no shared name | Bob's own name for it | Carol's own name for it, or none until she gives one |

### Where a member's own name for a pod lives, and whether it overrides a shared one

- The member's own data: a member's name for a pod, like the place it files the pod among its others, is the application's record in the identity's own data store, synced across the identity's own devices and never to another member; the platform carries nothing for it.
- A per-member name on the platform, in the identity's private metadata store (PMS) beside the pod's record, which the PMS carries to the identity's other devices.

Whichever holds it, a member's own name either stands in for a shared one — an alias the member sees instead of the name every member sees — or appears only where the pod carries none. A name of the member's own beside a shared one arises by itself where names repeat: an application that keeps the names of a member's pods unique side by side shows "Family1" to a member who already files a "Family" there.

**Example:** Carol already files a pod she calls "Family" when Alice's "Family" reaches her.

| a member's own name | where it is kept | what Carol sees for Alice's pod |
|---|---|---|
| an alias over the shared name | Carol's own data store | "Family1", while every other member sees "Family" |
| only where there is no shared name | — | "Family", beside her own "Family" |

### Who changes a shared name

- An owner, as the pod's other owner-only acts are.
- Any member.

Either way the rule is one admission check over the writer's role at the point its entry names, as for a membership act, so the answer changes one rule and nothing around it.

**Example:** Carol, a plain member of "Family", renames it "Carol's".

| option | on every member device |
|---|---|
| an owner | refused on Carol's device with a typed error, and an entry her modified device writes anyway counts for nothing: "Family" stays |
| any member | "Carol's" |

### Where a shared name sits, and how two changes made at once resolve

- In the membership store, under `name/<version>/<actor>/<aseq>`: `<version>` one above the highest the writing device holds, `<actor>` the writer and `<aseq>` its point, judged as a membership act is. The membership store is served before the record store, so a newcomer reads the name in its first session. Two changes at one version resolve by a deterministic pick, such as the lower author key: meaningless and harmless for a label, and a later change by anyone who saw both settles it.
- In the record store, as a record every member may edit, merged as a mergeable-document is; the name arrives with the records, after the membership.
- One entry, the newest by entry timestamp. A device whose clock runs behind loses its change to an earlier one, and one whose clock runs ahead wins every change for up to 10 minutes.

**Example:** changes to the name of "Family" under the first option, Alice and Bob both owners; `<alice>`: 64 lowercase hex chars of Alice's `PdnId`; `…`: the writer and its point.

| what happens | written | every member device reads |
|---|---|---|
| Alice names the pod on a1 | `name/1/<alice>/1`: "Family" | Family |
| Alice renames it | `name/2/<alice>/1`: "Walkers" | Walkers |
| Alice on a1 and Bob on b1, disconnected from each other, rename it | `name/3/…`: "Hikers" from a1 under Alice, "Ramblers" from b1 under Bob | one of the two, the same on every device |
| Bob, having seen both, renames it again | `name/4/…`: "Ramblers" | Ramblers |
| Carol's modified phone c1 writes a name | `name/5/…` | counts for nothing: Carol is no owner at the point she names |

### Whether an invite carries the name

- The invite payload carries the shared name as the inviter's word, so the newcomer sees what it joins before it presents the secret; the name is shown, never trusted, and whoever sees the invite sees the name.
- The invite carries none, as it carries no ticket, and the newcomer reads the name once the join returns.

**Example:** Bob shows Carol a QR code inviting her into "Family".

| option | what Carol's phone shows before she joins |
|---|---|
| the invite carries the name | "Join Family?" |
| it carries none | "Join `ad58a3faa04cdc5576c8dc5823a347c6`?" |

## Operating conditions

Clocks that disagree change the outcome under the timestamp option of the fourth question alone. Several identities on one node keep their own names apart: Alice-work and Alice-leisure, both members of "Wedding", each name it for themselves where the pod's name is a member's own. A device linked later reads the identity's own names as it reads every other record of the identity. An unstable connection, a restart and a disk that fills change nothing a name does.

## Out of Scope

- A pod's category, tags and place among a member's pods: the application's.
- A new name for the platform's term "pod".

## Capabilities

None is settled. A shared name touches `components/mee-pdn/data-layer/pod-store` and `components/mee-pdn/pdn-node/pods`; a per-member name on the platform touches `components/mee-pdn/data-layer/private-metadata-store`; the call that sets a name touches `components/mee-pdn/pdn-node-http/host` and the stand's pod scenario in `components/mee-pdn/pdn-node-http/container-stand`.

## Impact

- **`crates/data-layer`**: a shared name's entries and their admission in the pod stores.
- **`crates/pdn-node`**: the call that sets a name, and `list`.
- **`crates/pdn-node-http`**: the route that sets a name.
