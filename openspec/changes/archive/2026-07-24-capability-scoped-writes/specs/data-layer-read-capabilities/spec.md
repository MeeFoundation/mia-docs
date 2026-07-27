# Delta: data-layer-read-capabilities

## MODIFIED Requirements

### Requirement: A read capability authorizes reading specific claims

A read capability SHALL name an issuer, an audience, and the set of claims it grants read on within the issuer's data — and, per claim, whether write is granted alongside read. It SHALL be a single grant, not a delegation chain. Every granted claim SHALL grant read; write is optional per claim, mirroring UWill's flat command set (one delegation per claim, its commands beside it). Write enforcement is the ingest gate ([capability-gated ingest](../data-layer-capability-gated-ingest/spec.md)); read enforcement stays the egress filter.

#### Scenario: Issuing a read grant

- **WHEN** an issuer grants an audience read on a claim
- **THEN** a read capability exists naming that issuer, audience, and claim, and no other claim is covered by it

#### Scenario: Issuing mixed rights in one grant

- **WHEN** an issuer grants an audience one claim read-only and another claim read-write
- **THEN** one capability covers both claims, carrying write on exactly the second

### Requirement: A grant's ticket carries exactly the granted authority

The ticket published alongside a grant SHALL match the grant's commands as a whole: a grant carrying no write on any claim SHALL carry a read ticket (no namespace secret — the holder cannot produce a valid entry), and a grant carrying write on any claim SHALL carry a write ticket. The namespace secret is the transport interim of write authority: it lets the audience produce valid entries, and the scope of what the issuer keeps is the ingest gate's, judged per claim from this same grant.

#### Scenario: Read-only audience cannot write by construction

- **WHEN** a holder of a read-only grant attempts a local write into the granted replica
- **THEN** the write fails for lack of the namespace secret, and no entry authored by the holder ever appears in the replica

#### Scenario: Write grant keeps the write scenario reachable

- **WHEN** an issuer grants a claim with write and the audience writes that claim
- **THEN** the audience's write reaches the issuer over reconciliation

#### Scenario: A write ticket does not widen the write scope

- **WHEN** a grant carries write on one claim only and the audience produces an entry at another claim over the write ticket's secret
- **THEN** the issuer's gate refuses that entry, although the ticket that shipped with the grant carries the namespace secret
