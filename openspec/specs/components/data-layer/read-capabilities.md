# Read capabilities

## Purpose

The minimal read grant that drives capability-filtered reconciliation ([subset reconciliation](subset-reconciliation.md)): how a grant is issued, how the serving node resolves a caller's effective grants from its own records, and how they are evaluated per entry. Deliberately the single-link, degenerate precursor to UWill — no delegation chains, revocation, or token encoding; those arrive with the `uwill` module.

## Requirements

### Requirement: A read capability authorizes reading specific claims

A read capability SHALL name an issuer, an audience, and the set of claims it grants read on within the issuer's data. It SHALL be a single grant, not a delegation chain. It SHALL always grant read and MAY additionally grant write, mirroring UWill's flat command set; write enforcement is deferred to the ingest hook (ADR-0008).

#### Scenario: Issuing a read grant

- **WHEN** an issuer grants an audience read on a claim
- **THEN** a read capability exists naming that issuer, audience, and claim, and no other claim is covered by it

### Requirement: Claim identity is derived from the entry (interim)

Until the domain layer mints claim identities, the `ClaimId` of an entry SHALL be derived deterministically from the issuer and the entry path via a domain-separated key-derivation hash, so the identity is stable under payload edits and computable from the entry key alone (subset-rbsr D3).

#### Scenario: Identity survives value edits

- **WHEN** an issuer overwrites the payload at an entry path covered by a grant
- **THEN** the entry's claim identity is unchanged and the grant still covers it

#### Scenario: Evaluation needs no mapping

- **WHEN** read authorization is evaluated for an entry
- **THEN** the decision is computed from the entry key and the granted set alone, with no id-to-location table

### Requirement: The serving node evaluates rights it has recorded

Before a serving node filters what it reveals, it SHALL determine the caller's effective grants from the grants its identity recorded (its own replicas of the connection metadata stores), keyed by the caller's transport-authenticated node id resolved to an identity through the published device sets. It SHALL NOT trust capability material sent by the caller: the minimal grant is unsigned, so wire presentation is unverifiable and no presentation protocol exists until UWill.

#### Scenario: Evaluation precedes filtering

- **WHEN** a peer reconciles a replica
- **THEN** the claims it may receive are exactly those covered by its effective recorded grants

#### Scenario: A stale grant book fails closed

- **WHEN** the serving device has not yet replicated a freshly issued grant
- **THEN** the session reveals at most what the device's recorded grants cover, and a later session, after the grant replicates, reveals the granted claims

### Requirement: A grant's ticket carries exactly the granted authority

The ticket published alongside a grant SHALL match the grant's commands: a read-only grant SHALL carry a read ticket (no namespace secret — the holder cannot produce a valid entry), and a grant including write SHALL carry a write ticket (the namespace secret is the interim carrier of write authority until the ingest hook lands).

#### Scenario: Read-only audience cannot write by construction

- **WHEN** a holder of a read-only grant attempts a local write into the granted replica
- **THEN** the write fails for lack of the namespace secret, and no entry authored by the holder ever appears in the replica

#### Scenario: Write grant keeps the write scenario reachable

- **WHEN** an issuer grants a claim with write and the audience writes that claim
- **THEN** the audience's write reaches the issuer over reconciliation

### Requirement: Per-claim evaluation

Given a claim and a caller's effective grants, the mechanism SHALL decide read-authorized or not from the grants alone.

#### Scenario: Covered claim is authorized

- **WHEN** a claim is covered by an effective grant
- **THEN** it is read-authorized for that peer

#### Scenario: Uncovered claim is not authorized

- **WHEN** a claim is covered by none of the effective grants
- **THEN** it is not read-authorized for that peer

### Requirement: Own-identity data needs no capability

An identity's own device SHALL be read-authorized for all of that identity's data without any grant, composing with Invariant 1.

#### Scenario: A device reads its own identity's data

- **WHEN** a device reconciles a replica bound to its own identity
- **THEN** every claim is read-authorized without any grant
