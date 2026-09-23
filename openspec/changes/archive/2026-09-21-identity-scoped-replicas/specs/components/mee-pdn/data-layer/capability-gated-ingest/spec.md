# data-layer: capability-gated ingest — delta for identity-scoped-replicas

## MODIFIED Requirements

### Requirement: The write set is frozen per session

The caller's write set SHALL be computed at session setup from the issuer's recorded grants toward the identity the caller names — the same resolution and the same records the read side uses — and SHALL hold for that session's lifetime. It SHALL be recorded per identity as well as per replica and caller, so a node hosting several identities granted by one issuer is admitted, in each session, exactly what the identity named there was granted.

#### Scenario: Rights are read at session setup

- **WHEN** a grant's write set changes after a session has started
- **THEN** the running session judges entries by the set read at its setup, and the next session judges by the changed set

#### Scenario: Two co-located audiences are admitted separately

- **WHEN** an issuer grants write on one claim to one identity and write on another claim to a co-located identity, and that node writes both claims, each under the identity that holds it
- **THEN** both entries are admitted at the issuer

#### Scenario: A write under the wrong identity is refused

- **WHEN** that node writes, under the identity granted write on the first claim, an entry for the claim only the co-located identity may write
- **THEN** the issuer's gate drops it and the writer retracts it
