# In-process sessions

## Purpose

Two identities of one node cannot reach each other over the network, because a node refuses to dial its own endpoint, so what two identities of one node exchange runs inside the process. The path carries the same protocol under the same classification, gate and filter as a session between two nodes, so co-located identities behave toward each other exactly as identities on separate nodes do.

## Requirements

### Requirement: A dial to this node's own address runs inside the process

A dial whose target address carries this node's own wire identity SHALL run the sync session inside the process, over the same protocol as a session between two nodes, with the same session setup, the same rights resolution, the same egress filter and the same ingest gate on both sides. The choice SHALL follow from the address alone, so a contact list, a ticket, or a device record that names this node reaches the path without a caller choosing it. No entry SHALL move between two identities of one node by any other route.

**Example:** Alice-leisure on node a1 dials the contacts of Alice-work's namespace; Alice-work runs on a1 and on a2.

| contact | the session runs |
|---|---|
| a2, as Alice-work | `connect_and_sync`: an iroh connection to a2 under `/iroh-sync/1` |
| a1, as Alice-work | a1 is this node's own id: `CoLocatedRequest::Dial { namespace, caller: Alice-leisure, callee: Alice-work }`, then `sync_in_process` over a pipe |
| either | the same `Init` frame, access provider call, egress filter and ingest gate |

#### Scenario: Two identities of one node converge a namespace both hold

- **WHEN** one hosted identity writes into a replica of a namespace a co-located identity also holds, with no other node reachable
- **THEN** the co-located identity's replica comes to carry that entry, payload included

#### Scenario: A co-located audience receives only what its grant covers

- **WHEN** one hosted identity grants a co-located identity one claim of its namespace and writes both that claim and another
- **THEN** the co-located identity's replica carries the granted claim alone, and the withheld one is absent from it

#### Scenario: A contact naming this node is reached after a restart

- **WHEN** a node whose two identities both hold one namespace restarts, and the contacts of one name this node's own address
- **THEN** the pair reconciles again with no dial failing, and no ceremony is repeated

### Requirement: A write reaches the co-located identities that hold its namespace

A write SHALL announce to the identities of its own node that hold the same namespace, which SHALL then reconcile over the in-process path; the announcement SHALL carry no entry content, so what the receiving identity obtains comes through the session and its filter. A write SHALL reach a co-located identity on the announcement, without waiting for the periodic pass.

**Example:** Alice-work writes `contact/email` and `notes/diary` on node a1; Alice-leisure, on a1 too, holds her namespace under a grant of `contact/email`.

| step | what reaches Alice-leisure |
|---|---|
| 1 Alice-work's engine sends `CoLocatedRequest::Announce { namespace, writer: Alice-work }` | a namespace and an identity: no key, no payload |
| 2 the node opens `sync_in_process` from Alice-work to Alice-leisure | at once, not at the next pass, 10 s apart by default |
| 3 the session runs through Alice-work's egress filter | `contact/email`; `notes/diary` stays out, existence included |

#### Scenario: A co-located identity sees a write without the periodic pass

- **WHEN** an identity writes an entry a co-located identity is granted, within one reconcile interval
- **THEN** the co-located identity reads that entry before the interval elapses

#### Scenario: The announcement carries nothing by itself

- **WHEN** a write outside a co-located identity's grant announces to that identity
- **THEN** that identity's replica gains no entry, and the withheld claim stays absent from it

### Requirement: The periodic pass leaves a quiet co-located pair alone

The periodic reconcile pass SHALL walk every pair of co-located identities that both hold a namespace, and SHALL open a session for a pair only when something has moved since the reading kept at the pair's last successful pass session; a pair where nothing has moved SHALL be left alone, so passes over a quiet namespace do not accumulate sessions. The reading SHALL be four write counts: the writes each identity's replica of the namespace has taken since its store opened and, for a data namespace, the writes each identity's connection metadata stores toward the other have taken, since a grant between the two is written and arrives there; for a connection metadata store both identities hold, the two replicas' counts are the whole reading. The two replicas are never compared with each other: a replica held under a claim-scoped grant lacks for good what the grant withholds, and a grant changes with no write to the namespace. The reading kept SHALL be the one taken before the session, and only a session that succeeded SHALL replace it. So the first pass after the node starts, or after two identities first hold a namespace in common, opens a session whatever the replicas hold, which heals an announcement that never arrived; every write counts, the ones a session delivered included, so a session that delivered something is followed by one more on the next pass; a failed session leaves the pair to the next pass; a pair whose replicas differ for good under a claim-scoped grant is left alone once nothing moves; and a write to the pair's connection metadata stores — a grant published, widened, narrowed or withdrawn — opens a session on the next pass with no write to the namespace. The pass's walk over pairs is all this requirement bounds: a tracked contact that names this node is dialed on every pass as any contact is, over the in-process path, whether or not anything moved.

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
