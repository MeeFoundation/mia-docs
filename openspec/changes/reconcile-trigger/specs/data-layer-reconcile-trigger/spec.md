# data-layer: reconcile trigger

A capability-scoped peer — authorized (per subset-rbsr) to read only a subset of a replica, not all of it — stays outside the replica's gossip swarm and receives claims only through a reconciliation it initiates itself; nothing tells it when a claim it may read has changed. This spec adds that missing signal: a **reconcile trigger**, a small content-free message the serving node sends on a covered write to exactly the peers whose capabilities cover the written claim, prompting each to reconcile promptly. The claim itself still flows through subset-rbsr's filtered reconciliation, which remains the sole carrier of correctness; the trigger is best-effort latency only, and a missed one is healed by the next reconciliation on contact.

## ADDED Requirements

### Requirement: A covered write triggers the covered scoped peers

When a write lands in a replica, the serving node SHALL trigger — directly, not by broadcast — exactly those scoped peers whose read capabilities cover the written claim. The trigger SHALL carry no claim content; the triggered peer fetches through filtered reconciliation. Triggers are best-effort: a missed trigger SHALL be compensated by the next reconciliation, which remains the sole carrier of correctness.

#### Scenario: Only the covered peer is triggered

- **WHEN** an issuer holds 1,000,000 claims, 1,000 peers each hold a capability on 1 distinct claim, and the issuer writes the claim covered by peer B's capability
- **THEN** peer B receives 1 trigger and fetches that claim through filtered reconciliation, and the other scoped peers receive nothing

#### Scenario: An unshared write triggers no one

- **WHEN** the issuer writes a claim covered by no scoped peer's capability
- **THEN** no scoped peer is triggered, and the claim replicates to the issuer's devices over their swarm's gossip as usual

### Requirement: Triggers coalesce per peer

Consecutive covered writes SHALL collapse into at most one pending trigger per peer until that peer reconciles, so a peer's trigger volume is bounded by its own reconciliation cadence, not the write rate.

#### Scenario: A burst coalesces into one tick

- **WHEN** several claims covered by peer B are written before B reconciles
- **THEN** B has at most one pending trigger, and reconciling once delivers all the covered writes
