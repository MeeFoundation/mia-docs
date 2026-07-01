# data-layer: read capabilities

The minimal read-capability that drives capability-filtered reconciliation: how a read grant is issued, presented by a peer, and evaluated per record. Deliberately the single-link, degenerate precursor to UWill — no delegation chains, revocation, or token encoding; those arrive with the `uwill` module.

## ADDED Requirements

### Requirement: A read capability authorizes reading specific records
A read capability SHALL name an issuer, an audience, and the set of records it grants read on within the issuer's data. It SHALL be a single grant, not a delegation chain.

#### Scenario: Issuing a read grant
- **WHEN** an issuer grants an audience read on a record
- **THEN** a read capability exists naming that issuer, audience, and record, and no other record is covered by it

### Requirement: A peer presents its read capabilities
Before a serving node filters what it reveals, the receiving peer SHALL present the read capabilities under which it requests data, and the serving node SHALL evaluate only presented capabilities.

#### Scenario: Presentation precedes filtering
- **WHEN** a peer reconciles a replica
- **THEN** the records it may receive are exactly those covered by the capabilities it presented

### Requirement: Per-record evaluation
Given a record and a peer's presented capabilities, the mechanism SHALL decide read-authorized or not from the capabilities alone.

#### Scenario: Covered record is authorized
- **WHEN** a record is covered by a presented capability
- **THEN** it is read-authorized for that peer

#### Scenario: Uncovered record is not authorized
- **WHEN** a record is covered by none of the presented capabilities
- **THEN** it is not read-authorized for that peer

### Requirement: Own-identity data needs no capability
An identity's own device SHALL be read-authorized for all of that identity's data without presenting a capability, composing with Invariant 1.

#### Scenario: A device reads its own identity's data
- **WHEN** a device reconciles a replica bound to its own identity
- **THEN** every record is read-authorized without any presented capability
