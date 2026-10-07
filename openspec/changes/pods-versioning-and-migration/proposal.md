# Proposal: pods-versioning-and-migration

## Why

Every device reads every entry of a pod by the one set of rules its build holds: nothing in either store, nor the fold over the membership store, names a version ([pod stores](../../specs/components/mee-pdn/data-layer/pod-store/spec.md)). A build that reads entries otherwise — a new event kind, a new record kind, a fold that resolves differently — reads the pods it finds by its own rules too, and an entry an older build does not understand is kept and used by nothing, as every entry outside the key layout is. Devices of one pod on two such builds then reach two memberships and two sets of readable records from the same entries: one serves a member the other refuses, one reads a record the other hides, and neither can tell. While pods run inside the company alone, a pod that splits is recreated and its content lost; this change lands before a pod carries data people outside the company depend on.

**Example:** Alice's phone a1 runs a later build than Carol's phone c1, and writes two entries into "Family" that the later build adds; `<alice>`, `<bob>`: 64 lowercase hex chars of each `PdnId`; `<lease>`: the id of Bob's lease scan.

| entry a1 writes | a1 | c1 |
|---|---|---|
| `member/<bob>/3/suspended/<alice>/1`: Alice suspends Bob's editing at his sequence 3 | Bob's operations naming his sequence 3 not counted | an entry outside the key layout, kept and used by nothing: the operations counted |
| an empty entry at `by/<bob>/immutable-document/<lease>`, deleting Bob's lease scan | the scan gone | an entry outside the key layout: the scan read as before |

## What Changes

Nothing is decided. The change settles how a pod's entries and the fold over them evolve from one build to the next, what an older build does with what a newer one writes, and how the pods created before it move over, then specifies and builds the answers. The questions stand under Open Questions, strongest option first.

## Open Questions

### What carries a version

- Each entry, in its key: the version of the rules it was written under. A build reads each entry by its own version's rules, and a later version adds kinds and rules for them while never changing what an entry of an earlier version means, so one set of entries stays the only source of truth: an older build's answers are the newer one's with some of them unknown, never different ones. A build carries the fold of every version it has shipped.
- Each pod, in its founding event, as a Matrix room fixes its room version in the event that creates it. Every entry of the pod reads by that version's rules, and a new version is a new pod — in Matrix, a new room, with a tombstone event in the old one naming its successor; a build that lacks a pod's version takes no part in it.
- The folded membership alone, compared between devices: a split is detected, and prevented nowhere.

**Example:** the suspension of Why under each option.

| option | where the version sits | a1, on the later build, and c1, on the earlier |
|---|---|---|
| each entry | `member/<bob>/3/suspended.2/<alice>/1`: version 2 | a1 counts none of Bob's operations naming his sequence 3; c1 answers unknown for them |
| each pod | the founding event of "Family", naming version 1 | a1 writes no suspension into "Family": a suspension takes a new pod of version 2 |
| the folded membership | the digest two devices compare | the digests differ, and each device goes on reading its own |

### What an older build does with what it cannot read

- Keeps it and answers "unknown" for what depends on it: a member's chain from such an entry's point on, a record with such an entry at its key or under it. It reconciles every entry and refuses nobody, and the application tells its person that an update shows the rest. The answer "unknown" and this rule have to be in the first build that reads versions, since a shipped build learns nothing later.
- Refuses to reconcile the pod until it is updated: simple, and a person whose phone updates late loses the pod meanwhile.
- Keeps it and ignores it, as entries outside the key layout are ignored: the split of Why.

**Example:** c1, on the earlier build, meets `member/<bob>/3/suspended.2/<alice>/1`.

| option | c1 lists Bob as | Bob's operation naming his sequence 3, on c1 | c1 syncs "Family" |
|---|---|---|---|
| keeps it, unknown | a member, his state unknown from his sequence 3 | unknown, shown as waiting for an update | yes |
| refuses until updated | — | — | no, until c1 is updated |
| keeps it, ignores it | a member | counted | yes |

### How far "unknown" reaches

Some rules read more than one chain, and an entry a build cannot read reaches everything those rules read. The guard over demotions reads every chain, so an unreadable entry that can touch the set of owners leaves the owners unknown for every act that needs one; a device statement in a form a build cannot read leaves every author it lists unresolved, and with them every entry those authors wrote.

- A later version may not change what the earlier rules read across chains: no new kind touches the set of owners or the device lists, which keep their first form, and a new kind reaches its subject's chain alone. The rule is one more property the folds are tested against.
- Unknown spreads as far as the rules reach, and an older build knows little of a pod once a newer one changes its owners or its device lists.

**Example:** a later version adds an act by which an owner hands its ownership to another member, and Alice, an owner of "Family", hands hers to Bob.

| option | on c1, on the earlier build |
|---|---|
| may not change what earlier rules read across chains | no such act exists: ownership changes by promotion and demotion alone, which c1 reads |
| unknown spreads as far as the rules reach | every act that needs an owner is unknown on c1 from then on |

### Whether a member whose state is unknown is served

- Refused, as a member the device does not list: the older device stops serving that member's devices, which sync with updated members only.
- Served by its last known state: nothing stops, and a member that a newer rule has since cut off reaches the record store through an older device.

**Example:** a later version adds an act that cuts a member off the record store sooner than a removal; Alice uses it on Bob, and c1, on the earlier build, holds it unread; Bob's phone b1 asks c1 for a session on the record store.

| option | c1 |
|---|---|
| refused | refuses b1, as for a store it does not host |
| served by its last known state | serves b1 the record store whole |

### How each version's fold is held to one meaning

The fold of each shipped version stays in the code as it shipped, and the next is written beside it. Each is held to every earlier one by properties over the answers the platform asks of a fold — whether an identity is a member at a sequence, an owner, which devices it has, whether an act counts, whether a record reads — since a later fold's state holds what an earlier one lacks: on a set of entries of versions up to k alone, every later fold answers every question as the fold of k does; on any set, whatever the fold of k answers yes or no, every later fold answers the same; and every fold answers the same whatever order the entries arrived in. Property tests run these over sets of entries from a generator that plays devices acting on partial views — disconnected from each other, acting at one point together, leaving and returning, forging entries — with seeds fixed in `just test`, a wide sweep in the nightly workflow, and each counterexample kept as a case test, since tests are deterministic. A shipped fold that answers wrong cannot be corrected in place, since correcting it changes an answer on a set of its own version; the correction goes the way the question on changing a meaning settles. What stays open is how a shipped fold is kept unchanged.

- A golden corpus: sets of entries with the answers the shipped fold gave them; a changed answer fails it, and a refactoring passes.
- A digest of the fold's source, recorded and compared by `just check`: any edit fails, a refactoring among them.

**Example:** a refactoring of the first fold, and a change to its precedence between events at one point, under each option.

| option | the refactoring, every answer unchanged | the change to the precedence |
|---|---|---|
| a golden corpus | passes | fails on the sets where a removal and a promotion share a point |
| a digest of the source | fails | fails |

### When a build starts writing a newer version's entries

Reading by a newer fold is safe at once, since it answers whatever the older one answered; writing a newer kind puts unknown answers on every older device.

- Once every device of every current member lists support for it: each device statement names the highest version its device reads — a field the first build that reads versions writes — and nothing unknown reaches a current member's device; one device never updated holds the pod back.
- Once an owner switches the pod over, seeing which devices lag.
- As soon as the build has it.

**Example:** in "Family", Alice's phone a1 and Bob's phone b1 read version 2, and Carol's phone c1 reads version 1; Alice suspends Bob on a1.

| option | the suspension |
|---|---|
| once every device lists support | refused on a1 with a typed error until c1 lists version 2 |
| once an owner switches the pod over | written once Alice, an owner, switches "Family" to version 2 |
| as soon as the build has it | written; c1 answers unknown for Bob's state from his sequence 3 |

### How a meaning changes

Some changes cannot keep what an earlier entry means: a shipped fold that answers wrong, and a rule that from some point on every act anchors in its author's key event log.

- A switch inside the pod: an owner's act names, for every member's chain, the point after which the new rules apply. Within one chain "after" is exact, so the entries stay one source of truth. The switch touches every chain, so a build has to know its kind from the first build that reads versions on, and to take it as the point where its own answers end.
- A new generation of the pod, as Matrix upgrades a room: the members join a new pod founded under the new rules, and the old one ends with an entry naming its successor. Records are copied across or read from the old pod, and a link to an old record resolves through it.

**Example:** "Family" adopts the anchoring rule; Bob's last act is at his sequence 4, and Carol's at her sequence 2.

| option | what happens |
|---|---|
| a switch inside the pod | Alice's act names Bob's sequence 4 and Carol's sequence 2: their later acts count only when anchored, and the earlier ones stand as they are |
| a new generation of the pod | a new pod is founded and every member joins it; "Family" holds an entry naming the new pod's id |

### What happens to the pods created before this change

- Read as the first version: an entry naming no version reads by the first version's rules, which are the rules every pod holds before this change, so every existing pod carries on; the key layout has to tell an entry naming no version from one naming a version.
- Dropped: every pod created before the change is recreated and its content lost, which costs nothing beyond those pods while they run inside the company alone.

**Example:** "Family", created before this change, holds 1,000 records.

| option | "Family" after the update |
|---|---|
| read as the first version | carries on, its 1,000 records read as before |
| dropped | recreated empty, the 1,000 records placed again by hand or lost |

### A digest of the fold between the two stores' sessions

A session reconciles the membership store before the record store, and between the two the devices can compare a digest of their folded membership, each at the highest version both read. Once the store has converged, equal folds of one version give equal digests, so a difference shows a split or a fold that is not a function of its entries — an iteration order, a difference between platforms.

- A signal: the difference counted, the full folded membership shown on the debug surface, asserted in tests; the record store's session goes on, since a write between the two sessions makes the digests differ harmlessly.
- A gate: the record store's session waits until the digests agree, and a write in between or a lagging device stalls it.
- None.

**Example:** Alice's phone a1 and Carol's phone c1 both read version 2, and c1's fold, built for another platform, orders two events at one point otherwise.

| option | the session between a1 and c1 |
|---|---|
| a signal | the record store reconciled; the difference counted and shown on both debug surfaces |
| a gate | the record store not reconciled until the fold is fixed |
| none | the record store reconciled; the split unseen |

## Operating conditions

Several identities on one node run one build, so their replicas of a pod read by the same rules. An identity's own devices update at different times, a phone when its owner lets it, so one identity can read a pod by two versions on two devices. An unstable connection stretches how long a newer entry takes to reach an older device. A restart, a disk that fills and clocks that disagree change nothing a version decides.

## Out of Scope

- The wire format of sessions, dialogues and tickets, and what a node owes a peer that speaks an older one.
- Versions of payloads above the data layer, which are the application's.

## Capabilities

None is settled. Every option touches `components/mee-pdn/data-layer/pod-store` and `components/mee-pdn/pdn-node/pods`; the digest between the two sessions touches `components/mee-pdn/data-layer/in-process-sessions` as well, and `components/mee-pdn/pdn-node-http/host` where the debug surface shows it.

## Impact

- **`crates/data-layer`**: a fold per version, the unknown answers, the gate's reading of versions, the digest between the two sessions.
- **`crates/pdn-node`**: when a build writes a newer version's entries, and the switch or the new generation of a pod.
- **`crates/pdn-store`**: the digest in the opening of the record store's session.
- **Tests**: property tests holding each fold to the earlier ones over a generator of entry sets, and the corpus or check that keeps a shipped fold unchanged.
