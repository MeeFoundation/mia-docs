# data-layer: reconcile trigger

## Purpose

A capability-scoped peer on another node — authorized (per subset-rbsr) to read only a subset of a replica, not all of it — stays outside the replica's gossip swarm and receives claims only through a reconciliation it initiates itself, on each periodic reconcile pass and when a read or a list of the replica starts one; nothing tells it when a claim it may read has changed. This spec adds that missing signal: a **reconcile trigger**, a small content-free message the serving node sends on a covered write to exactly the peers whose capabilities cover the written claim, prompting each to reconcile promptly; for a peer on the serving node itself, the trigger is the write announcement that node already raises for its co-located identities. The claim itself still flows through subset-rbsr's filtered reconciliation, which remains the sole carrier of correctness; the trigger is best-effort latency only, and a missed one is healed by the next reconciliation on contact.

## ADDED Requirements

### Requirement: A covered write triggers the covered scoped peers

When a write lands in a replica, the serving node SHALL trigger — directly, not by broadcast — exactly those scoped peers whose read capabilities cover the written claim. A peer SHALL be addressed as a node together with the identity holding the replica there, since one node may hold one issuer's namespace for two identities at once, each under its own grant; an addressed identity hosted on the sending node itself SHALL be triggered by the write announcement, which reaches only the co-located identities entitled to read the written entry ([in-process sessions](../in-process-sessions/spec.md)). The trigger SHALL carry no claim content; what the triggered peer obtains comes through filtered reconciliation. Triggers are best-effort: a missed trigger SHALL be compensated by the next reconciliation, which remains the sole carrier of correctness.

**Example:** Alice (issuer) writes `contact/email` on her laptop a1, which also hosts Dave and Erin; a2 is her phone. Bob and Dave hold read grants on `contact/email`, Carol and Erin on `contact/phone`; the family tablet t1 hosts Bob and Carol.

| addressee (node, identity) | covered | what a1 does |
|---|---|---|
| (a2, Alice) | issuer | nothing: a2 is in the swarm, learns of the write there and pulls it by reconciliation |
| (b1, Bob) | yes | dials b1 and triggers it |
| (t1, Bob) | yes | dials t1 and triggers it, naming Bob |
| (t1, Carol) | no | nothing |
| (a1, Dave) | yes | announces the write: an in-process session from Alice to Dave |
| (a1, Erin) | no | nothing: no in-process session opens |
| No trigger carries any part of `contact/email`; each triggered replica obtains it through filtered reconciliation. | | |

#### Scenario: Only the covered peer is triggered

- **WHEN** an issuer holds 1,000,000 claims, 1,000 peers each hold a capability on 1 distinct claim, and the issuer writes the claim covered by peer B's capability
- **THEN** peer B receives 1 trigger and fetches that claim through filtered reconciliation, and the other scoped peers receive nothing

#### Scenario: A node holding the namespace for two identities is triggered per identity

- **WHEN** one node holds one issuer's namespace for two identities it hosts, each granted a different claim, and the issuer writes the claim covered by the first identity's grant
- **THEN** the first identity's replica is triggered and the second one's is not, although both replicas sit on one node

#### Scenario: An unshared write triggers no one

- **WHEN** the issuer writes a claim covered by no scoped peer's capability
- **THEN** no scoped peer is triggered, and the issuer's devices learn of the write over their swarm and pull it by reconciliation, as they do without a trigger

### Requirement: Triggers coalesce per peer

Consecutive covered writes SHALL collapse into at most one pending trigger per peer until that peer reconciles, so a peer's trigger volume is bounded by its own reconciliation cadence, not the write rate. A reconciliation SHALL clear only the triggers its session can actually serve. A session serves a view frozen at its setup — the rule stated by subset reconciliation in the data-layer specs — so a write landing after a session is already under way is not carried by it; the trigger for that write SHALL stay pending and prompt a further reconciliation, or the peer would learn of the write only on its next periodic pass. A peer on the serving node itself is held to the same rule ([in-process sessions](../in-process-sessions/spec.md)).

**Example:** S1, S2: sessions Bob's phone b1 opens with Alice's laptop a1. Alice (issuer) writes claims Bob's grant covers.

| step | a1 | trigger for (b1, Bob) | b1 |
|---|---|---|---|
| 1 | writes `contact/email` | pending, sent to b1 | |
| 2 | writes `contact/phone` | still pending, nothing more sent | |
| 3 | | | sets up S1: its view freezes with steps 1 and 2 |
| 4 | writes `contact/email` again | pending: S1's view lacks this write | S1 exchanging rounds |
| 5 | | stays pending for step 4 | S1 ends: receives steps 1 and 2 |
| 6 | | cleared | sets up S2: receives step 4 |

#### Scenario: A burst coalesces into one tick

- **WHEN** several claims covered by peer B are written before B reconciles
- **THEN** B has at most one pending trigger, and reconciling once delivers all the covered writes

#### Scenario: A write during a running session keeps its trigger pending

- **WHEN** a claim covered by peer B is written while B's reconciliation session is already exchanging rounds, so the session's frozen view cannot carry it
- **THEN** B's trigger for that write survives the session it did not travel on, and B reconciles again and receives the claim
