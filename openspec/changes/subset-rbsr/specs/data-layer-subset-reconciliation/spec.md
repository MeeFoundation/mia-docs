# data-layer: subset reconciliation

Capability-filtered reconciliation — "subset-RBSR" — the read-side counterpart of the ADR-0008 ingest seam, enforcing Invariant 2: a serving node reveals only the records the receiving peer is read-authorized for.

## ADDED Requirements

### Requirement: Reconciliation reveals only read-authorized records

During reconciliation with a peer, a serving node SHALL compute range fingerprints, split boundaries, offers, and item transmissions over only the records the peer is read-authorized for. A record the peer is not authorized for SHALL NOT be fingerprinted, offered, or sent.

#### Scenario: Only the authorized subset is delivered

- **WHEN** an issuer holds records r1, r2, r3 and a peer is authorized for r1, r2
- **THEN** the peer receives r1 and r2, and r3 is never transmitted

### Requirement: Withheld records are hidden, not merely undelivered

The reconciliation transcript a peer observes SHALL depend only on the records it is authorized for, so the existence of unauthorized records is not revealed — no fingerprint or split boundary derived from them reaches the peer.

#### Scenario: Existence of an unauthorized record is hidden

- **WHEN** an unauthorized record r3 lies between authorized records r2 and r4 in key order
- **THEN** the peer's session is indistinguishable from one in which r3 does not exist

### Requirement: The filter runs in pdn-store on the read side

Filtering SHALL run at reconciliation time inside `pdn-store`, per peer, distinct from the ingest-only `validate_entry` hook, and SHALL consume the peer's presented read capabilities.

#### Scenario: Read filter is independent of the ingest seam

- **WHEN** the egress filter runs while the fork's `validate_entry` seam has no validator installed
- **THEN** filtering applies unchanged, and it composes with any future ingest validator (ADR-0008) — read on egress, write on ingest, independently

### Requirement: Same-identity reconciliation is unfiltered

Reconciliation between devices of the identity a replica belongs to SHALL deliver every record of that replica — all are read-authorized by Invariant 1 — so the filter does not restrict an identity's own devices. On a multi-identity node this SHALL be judged per replica: a node is an own device for the replicas of the identities it is linked into, and a scoped peer elsewhere.

#### Scenario: Own devices replicate in full

- **WHEN** two devices of one identity reconcile a replica bound to that identity
- **THEN** all records replicate, with no capability presented

#### Scenario: Being an own device is per replica, not per node

- **WHEN** a node linked into identity A but not identity B reconciles a replica of B under a capability covering one record
- **THEN** the filter applies — only that record is delivered — even though the node is fully authorized for A's replicas

### Requirement: Delivery is gated before transfer

A record SHALL be filtered out before transmission, never retracted after — Invariant 2 governs acquisition, not retention.

#### Scenario: An unauthorized record never leaves the server

- **WHEN** a peer is not authorized for record r3
- **THEN** r3 is absent from every message the server sends, at no point transmitted and then recalled

### Requirement: Scoped peers stay outside the gossip swarm

A peer whose access is capability-scoped SHALL NOT be a member of the replica's gossip swarm: gossip broadcasts full records through relaying members, which is incompatible with per-record authorization. The swarm SHALL consist of fully authorized members only (an identity's own devices), whose full-record gossip is unchanged.

#### Scenario: A scoped peer receives nothing over gossip

- **WHEN** a record is written into a replica whose swarm is the issuer's devices, while scoped peers hold capabilities on other records
- **THEN** no scoped peer receives the record or any digest of it over gossip, and the issuer's devices receive the record itself

### Requirement: Live updates for scoped peers are directed notifications

When a write lands in a replica, the serving node SHALL notify — directly, not by broadcast — exactly those scoped peers whose read capabilities cover the written record. The notification SHALL carry no record content; the notified peer fetches through filtered reconciliation. Notifications are best-effort: a missed notification SHALL be compensated by the next reconciliation, which remains the sole carrier of correctness.

#### Scenario: Only the covered peer is notified

- **WHEN** an issuer holds 10,000,000 records, 1,000 peers each hold a capability on 1 distinct record, and the issuer writes the record covered by peer B's capability
- **THEN** peer B receives 1 notification and fetches that record through filtered reconciliation, and the other scoped peers receive nothing

#### Scenario: An unshared write notifies no one

- **WHEN** the issuer writes a record covered by no scoped peer's capability
- **THEN** no scoped peer receives a notification, and the record replicates to the issuer's devices over their swarm's gossip as usual
