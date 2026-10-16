# data-layer: in-process sessions — delta for pods

## MODIFIED Requirements

### Requirement: The periodic pass leaves a quiet co-located pair alone

The periodic reconcile pass SHALL walk every pair of co-located identities that both hold a namespace, and SHALL open a session for a pair only when something has moved since the reading kept at the pair's last successful pass session; a pair where nothing has moved SHALL be left alone, so passes over a quiet namespace do not accumulate sessions. The reading SHALL be four write counts: the writes each identity's replica of the namespace has taken since its store opened and, for a data namespace, the writes each identity's connection metadata stores toward the other have taken, since a grant between the two is written and arrives there; for a connection metadata store both identities hold, the two replicas' counts are the whole reading. For a [pod](../../../../architecture/language/pod.md) both identities are members of, the pair SHALL be the pod rather than one of its stores: the reading is the write counts of both identities' replicas of its membership store and of its record store, and a pass that finds any of them moved SHALL reconcile the membership store and then the record store, as the requirement on a pod's two stores inside the process orders them. The two replicas are never compared with each other: a replica held under a claim-scoped grant lacks for good what the grant withholds, and a grant changes with no write to the namespace. The reading kept SHALL be the one taken before the session, and only a session that succeeded SHALL replace it. So the first pass after the node starts, or after two identities first hold a namespace in common, opens a session whatever the replicas hold, which heals an announcement that never arrived; every write counts, the ones a session delivered included, so a session that delivered something is followed by one more on the next pass; a failed session leaves the pair to the next pass; a pair whose replicas differ for good under a claim-scoped grant is left alone once nothing moves; a write to the pair's connection metadata stores — a grant published, widened, narrowed or withdrawn — opens a session on the next pass with no write to the namespace; and a membership event reaching either identity's replica of a pod's membership store opens both of the pod's sessions on the next pass with no write to the record store. The pass's walk over pairs is all this requirement bounds: a tracked contact that names this node is dialed on every pass as any contact is, over the in-process path, whether or not anything moved.

**Example:** Alice-work grants Alice-leisure `contact/email` of her namespace, which also holds `notes/diary`; both are hosted on node a1, which restarts with the two replicas converged under the grant; Alice-leisure dials no contact; a pass every 10 s.

| pass | moved since the reading the pair's last pass session kept | the pass |
|---|---|---|
| 1 | no reading kept: a1 has just started | a session: nothing owed, nothing delivered |
| 2 | nothing | no session, though `notes/diary` is in one replica only |
| 3 | Alice-work widened the grant to cover `notes/diary` too: her store toward Alice-leisure took the record, the namespace took nothing | a session: `notes/diary` arrives |
| 4 | Alice-leisure's replica took `notes/diary` in session 3 | a session: nothing left to deliver |
| 5 | nothing | no session |

#### Scenario: A missed announcement is healed by the pass

- **WHEN** a co-located identity is brought up holding an older view of a namespace and no write follows
- **THEN** the next pass reconciles the pair and the identity converges

#### Scenario: A grant widened with no write reaches the co-located audience on the pass

- **WHEN** the pass has gone quiet over a pair of co-located identities, and the issuing identity widens its grant to the other with nothing written into the namespace
- **THEN** the next pass opens a session for the pair, and the claim the grant newly covers arrives

#### Scenario: The pass opens no session over a quiet pair

- **WHEN** two co-located identities hold a namespace, converged or differing for good under a claim-scoped grant, the pass has opened a session over them after the last write to the namespace and to their connection metadata stores, and nothing is written for several reconcile intervals
- **THEN** the pass opens no session for that pair in those intervals

#### Scenario: A membership event with no record written opens both of a pod's sessions

- **WHEN** co-located identities B and D are members of a pod, the pass has gone quiet over them, D's replica of the record store holds a record of member E that it reads nothing of, E's joined event having not reached D, and E's joined event then reaches B's replica of the membership store with nothing written to the record store
- **THEN** the next pass reconciles the membership store and then the record store between B and D, and D reads E's record

## ADDED Requirements

### Requirement: A pod's two stores reconcile inside the process in the order two nodes take them

Between two co-located identities that are both members of a pod, every reconciliation of the pod's record store SHALL follow a reconciliation of its membership store between the same two identities, to convergence, as a session between two nodes takes them ([pod stores](../pod-store/spec.md)) — on an announced write into either store, on a dialed contact that names this node and on the periodic pass alike — and the record store's session SHALL be served by the membership view built after that membership store's session.

**Example:** Alice's tablet a3 hosts Alice-leisure and Alice-work, both members of "Wedding"; Alice-leisure's replicas took Dave's joined event, his device statement and his first claim from Erin's phone e1, while Alice-work's replicas hold none of them, and a3 reaches no other node; `<dave>`: 64 lowercase hex chars of Dave's `PdnId`; `<id>`: the id `put_record` minted.

| step of the next pass on a3 | Alice-work's replicas |
|---|---|
| 1. the membership store reconciled inside the process | take Dave's joined event and his device statement, listing his phone d1 |
| 2. the membership view built | Dave a member at his sequence 1, writing on d1 |
| 3. the record store reconciled inside the process | take `by/<dave>/claim/<id>/1` from d1's author, which Alice-work's record view reads at Dave's sequence 1 in this pass |

#### Scenario: A co-located member takes a newcomer's record in the pass that brings its membership

- **WHEN** identities B and D, hosted on one node, are both members of a pod, B's replicas hold newcomer E's joined event and E's first claim, D's hold neither, and no other node is reachable
- **THEN** one pass brings D's replica of the membership store E's joined event and then D's replica of the record store E's claim, which D reads
