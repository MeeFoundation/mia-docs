# data-layer: subset reconciliation

Capability-filtered reconciliation — "subset-RBSR" — the read-side counterpart of the ingest gate, enforcing Invariant 2: a serving node reveals only the records the receiving peer is read-authorized for.

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

#### Scenario: Read filter and ingest gate compose
- **WHEN** a peer both receives data (egress-filtered by read capabilities) and writes data (ingest-gated per ADR-0008)
- **THEN** both checks apply independently — read on egress, write on ingest

### Requirement: Same-identity reconciliation is unfiltered
Reconciliation between devices of one identity SHALL deliver every record — all are read-authorized by Invariant 1 — so the filter does not restrict an identity's own devices.

#### Scenario: Own devices replicate in full
- **WHEN** two devices of one identity reconcile a replica bound to that identity
- **THEN** all records replicate, with no capability presented

### Requirement: Delivery is gated before transfer
A record SHALL be filtered out before transmission, never retracted after — Invariant 2 governs acquisition, not retention.

#### Scenario: An unauthorized record never leaves the server
- **WHEN** a peer is not authorized for record r3
- **THEN** r3 is absent from every message the server sends, at no point transmitted and then recalled
