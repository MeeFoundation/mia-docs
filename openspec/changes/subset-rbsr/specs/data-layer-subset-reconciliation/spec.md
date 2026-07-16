# data-layer: subset reconciliation

Capability-filtered reconciliation — "subset-RBSR" — the read-side counterpart of the ADR-0008 ingest hook, enforcing Invariant 2: a serving node reveals only the claims the receiving peer is read-authorized for.

## ADDED Requirements

### Requirement: Reconciliation reveals only read-authorized claims

During reconciliation with a peer, a serving node SHALL compute range fingerprints, split boundaries, offers, and item transmissions over only the claims the peer is read-authorized for. A claim the peer is not authorized for SHALL NOT be fingerprinted, offered, or sent.

#### Scenario: Only the authorized subset is delivered

- **WHEN** an issuer holds claims c1, c2, c3 and a peer is authorized for c1, c2
- **THEN** the peer receives c1 and c2, and c3 is never transmitted

### Requirement: Withheld claims are hidden, not merely undelivered

The reconciliation transcript a peer observes SHALL depend only on the claims it is authorized for, so the existence of unauthorized claims is not revealed — no fingerprint or split boundary derived from them reaches the peer.

#### Scenario: Existence of an unauthorized claim is hidden

- **WHEN** an unauthorized claim c3 lies between authorized claims c2 and c4 in key order
- **THEN** the peer's session is indistinguishable from one in which c3 does not exist

### Requirement: The filter runs in pdn-store on the read side

Filtering SHALL run at reconciliation time inside `pdn-store`, per peer, distinct from the ingest-only `validate_entry` hook, and SHALL consume the peer's presented read capabilities.

#### Scenario: Read filter is independent of the ingest hook

- **WHEN** the egress filter runs while the fork's `validate_entry` hook has no validator installed
- **THEN** filtering applies unchanged, and it composes with any future ingest validator (ADR-0008) — read on egress, write on ingest, independently

### Requirement: Same-identity reconciliation is unfiltered

Reconciliation between devices of the identity a replica belongs to SHALL deliver every claim of that replica — all are read-authorized by Invariant 1 — so the filter does not restrict an identity's own devices. On a multi-identity node this SHALL be judged per replica: a node is an own device for the replicas of the identities it is linked into, and a scoped peer elsewhere.

#### Scenario: Own devices replicate in full

- **WHEN** two devices of one identity reconcile a replica bound to that identity
- **THEN** all claims replicate, with no capability presented

#### Scenario: Being an own device is per replica, not per node

- **WHEN** a node linked into identity A but not identity B reconciles a replica of B under a capability covering one claim
- **THEN** the filter applies — only that claim is delivered — even though the node is fully authorized for A's replicas

### Requirement: Delivery is gated before transfer

A claim SHALL be filtered out before transmission, never retracted after — Invariant 2 governs acquisition, not retention.

#### Scenario: An unauthorized claim never leaves the server

- **WHEN** a peer is not authorized for claim c3
- **THEN** c3 is absent from every message the server sends, at no point transmitted and then recalled

### Requirement: Scoped peers stay outside the gossip swarm

A peer whose access is capability-scoped SHALL NOT be a member of the replica's gossip swarm: gossip broadcasts full entries through relaying members, which is incompatible with per-claim authorization. The swarm SHALL consist of fully authorized members only (an identity's own devices), whose full-entry gossip is unchanged.

#### Scenario: A scoped peer receives nothing over gossip

- **WHEN** a claim is written into a replica whose swarm is the issuer's devices, while scoped peers hold capabilities on other claims
- **THEN** no scoped peer receives the claim or any digest of it over gossip, and the issuer's devices receive the claim itself
