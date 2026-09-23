# data-layer: reconcile trigger

A capability-scoped peer — authorized (per subset-rbsr) to read only a subset of a replica, not all of it — stays outside the replica's gossip swarm and receives claims only through a reconciliation it initiates itself; nothing tells it when a claim it may read has changed. This spec adds that missing signal: a **reconcile trigger**, a small content-free message the serving node sends on a covered write to exactly the peers whose capabilities cover the written claim, prompting each to reconcile promptly. The claim itself still flows through subset-rbsr's filtered reconciliation, which remains the sole carrier of correctness; the trigger is best-effort latency only, and a missed one is healed by the next reconciliation on contact.

## ADDED Requirements

### Requirement: A covered write triggers the covered scoped peers

When a write lands in a replica, the serving node SHALL trigger — directly, not by broadcast — exactly those scoped peers whose read capabilities cover the written claim. A peer SHALL be addressed as a node together with the identity holding the replica there, since one node may hold one issuer's namespace for two identities at once, each under its own grant; an addressed identity hosted on the sending node itself SHALL be triggered inside the process, where its reconciliation already runs. The trigger SHALL carry no claim content; the triggered peer fetches through filtered reconciliation. Triggers are best-effort: a missed trigger SHALL be compensated by the next reconciliation, which remains the sole carrier of correctness.

#### Scenario: Only the covered peer is triggered

- **WHEN** an issuer holds 1,000,000 claims, 1,000 peers each hold a capability on 1 distinct claim, and the issuer writes the claim covered by peer B's capability
- **THEN** peer B receives 1 trigger and fetches that claim through filtered reconciliation, and the other scoped peers receive nothing

#### Scenario: A node holding the namespace for two identities is triggered per identity

- **WHEN** one node holds one issuer's namespace for two identities it hosts, each granted a different claim, and the issuer writes the claim covered by the first identity's grant
- **THEN** the first identity's replica is triggered and the second one's is not, although both replicas sit on one node

#### Scenario: An unshared write triggers no one

- **WHEN** the issuer writes a claim covered by no scoped peer's capability
- **THEN** no scoped peer is triggered, and the claim replicates to the issuer's devices over their swarm's gossip as usual

### Requirement: Triggers coalesce per peer

Consecutive covered writes SHALL collapse into at most one pending trigger per peer until that peer reconciles, so a peer's trigger volume is bounded by its own reconciliation cadence, not the write rate. A reconciliation SHALL clear only the triggers its session can actually serve. A session serves a view frozen at its setup — the rule stated by subset reconciliation in the data-layer specs — so a write landing after a session is already under way is not carried by it; the trigger for that write SHALL stay pending and prompt a further reconciliation, or the peer would learn of the write only on its next periodic pass.

#### Scenario: A burst coalesces into one tick

- **WHEN** several claims covered by peer B are written before B reconciles
- **THEN** B has at most one pending trigger, and reconciling once delivers all the covered writes

#### Scenario: A write during a running session keeps its trigger pending

- **WHEN** a claim covered by peer B is written while B's reconciliation session is already exchanging rounds, so the session's frozen view cannot carry it
- **THEN** B's trigger for that write survives the session it did not travel on, and B reconciles again and receives the claim
