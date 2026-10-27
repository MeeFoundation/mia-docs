# In-process sessions

## Purpose

Two identities of one node cannot reach each other over the network, because a node refuses to dial its own endpoint, so what two identities of one node exchange runs inside the process. The path carries the same protocol under the same classification, egress predicate and ingest verdict as a session between two nodes, so co-located identities behave toward each other exactly as identities on separate nodes do.

## Requirements

### Requirement: A write reaches the co-located identities that hold its namespace

A write SHALL announce to the identities of its own node that hold the same namespace, which SHALL then reconcile over the in-process path; the announcement SHALL carry no entry content, so what the receiving identity obtains comes through the session and its classification. A write SHALL reach a co-located identity on the announcement, without waiting for the periodic pass.

**Example:** Alice-work and Alice-leisure, both on node a3, are members of "Wedding"; Alice-work places a claim, and Erin, also on a3, imported the stores' tickets without being a member.

| step | what reaches Alice-leisure | what reaches Erin |
|---|---|---|
| 1 Alice-work's engine sends `CoLocatedRequest::Announce { namespace, writer: Alice-work }` | a namespace and an identity: no key, no payload | the same |
| 2 the node opens `sync_in_process` from Alice-work to each identity holding the record store | at once, not at the next pass | at once |
| 3 the session runs through Alice-work's classification | the claim, the store being served whole to a member | nothing: the session is refused, Erin being no member |

#### Scenario: A co-located identity sees a write without the periodic pass

- **WHEN** an identity places a record in a pod a co-located identity is also a member of, within one reconcile interval
- **THEN** the co-located identity reads that record before the interval elapses

#### Scenario: The announcement carries nothing by itself

- **WHEN** a write into a pod's store announces to a co-located identity that holds the store's ticket and is no member of the pod
- **THEN** that identity's replica gains no entry

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

### Requirement: A session between two identities of one node runs inside the process

A dial whose target address carries this node's own wire identity SHALL run the sync session inside the process, over the same protocol as a session between two nodes, with the same session setup, the same access decision, the same egress and the same ingest on both sides. The choice SHALL follow from the address alone, so a contact list, a ticket, or a device statement that names this node reaches the path without a caller choosing it. No entry SHALL move between two identities of one node by any other route.

**Example:** Alice-leisure on node a3 dials the contacts of the record store of "Wedding"; Alice-work, also a member, runs on a3 and on a2.

| contact | the session runs |
|---|---|
| a2, as Alice-work | `connect_and_sync`: an iroh connection to a2 under `/iroh-sync/1` |
| a3, as Alice-work | a3 is this node's own id: `CoLocatedRequest::Dial { namespace, caller: Alice-leisure, callee: Alice-work }`, then `sync_in_process` over a pipe |
| either | the same `Init` frame, access provider call, egress and ingest |

#### Scenario: Two identities of one node converge a pod both are members of

- **WHEN** one hosted identity places a record in a pod a co-located identity is also a member of, with no other node reachable
- **THEN** the co-located identity's replica of the record store comes to carry that entry, payload included

#### Scenario: A co-located ticket holder that is no member takes nothing

- **WHEN** two identities of one node are members of a pod and a third identity of the node holds the stores' tickets without being a member
- **THEN** the two members converge, and the third identity's replicas take nothing from either

#### Scenario: A contact naming this node is reached after a restart

- **WHEN** a node whose two identities are both members of one pod restarts, and the contacts of one name this node's own address
- **THEN** the pair reconciles again with no dial failing, and no ceremony is repeated

### Requirement: The periodic pass leaves a quiet co-located pod alone

The periodic reconcile pass SHALL walk every [pod](../../../../architecture/language/pod.md) two co-located identities are both members of, and SHALL open a session for a pod only when something has moved since the reading kept at that pair's last successful pass session; a pod where nothing has moved SHALL be left alone, so passes over a quiet pod do not accumulate sessions. The reading SHALL be the write counts of both identities' replicas of the pod's membership store and of its record store, taken since each store opened, and a pass that finds any of them moved SHALL reconcile the membership store and then the record store, as the requirement on a pod's two stores inside the process orders them. The two identities' replicas are never compared with each other. The reading kept SHALL be the one taken before the session, and only a session that succeeded SHALL replace it. So the first pass after the node starts, or after two identities first hold a pod in common, opens a session whatever the replicas hold, which heals an announcement that never arrived; every write counts, the ones a session delivered included, so a session that delivered something is followed by one more on the next pass; a failed session leaves the pair to the next pass; and a membership event reaching either identity's replica of the membership store opens both of the pod's sessions on the next pass with no write to the record store. The pass's walk over pods is all this requirement bounds: a tracked contact that names this node is dialed on every pass as any contact is, over the in-process path, whether or not anything moved.

**Example:** Alice-work and Alice-leisure, both on node a3, are members of "Wedding" and hold converged replicas of its stores when a3 restarts; Erin's phone e1 is another member; a pass every 10 s.

| pass | moved since the reading the pair's last pass session kept | the pass |
|---|---|---|
| 1 | no reading kept: a3 has just started | both sessions: nothing owed, nothing delivered |
| 2 | nothing | no session |
| 3 | Erin's new claim reached Alice-work's replica of the record store from e1 | both sessions: the claim reaches Alice-leisure |
| 4 | Alice-leisure's replica took the claim in session 3 | both sessions: nothing left to deliver |
| 5 | nothing | no session |

#### Scenario: A missed announcement is healed by the pass

- **WHEN** a co-located identity is brought up holding an older view of a pod's stores and no write follows
- **THEN** the next pass reconciles the pair and the identity converges

#### Scenario: The pass opens no session over a quiet pod

- **WHEN** two co-located identities are members of a pod, the pass has opened a session over them after the last write to either of its stores, and nothing is written for several reconcile intervals
- **THEN** the pass opens no session for that pod in those intervals

#### Scenario: A membership event with no record written opens both of a pod's sessions

- **WHEN** co-located identities B and D are members of a pod, the pass has gone quiet over them, D's replica of the record store holds a record of member E that it reads nothing of, E's joined event having not reached D, and E's joined event then reaches B's replica of the membership store with nothing written to the record store
- **THEN** the next pass reconciles the membership store and then the record store between B and D, and D reads E's record
