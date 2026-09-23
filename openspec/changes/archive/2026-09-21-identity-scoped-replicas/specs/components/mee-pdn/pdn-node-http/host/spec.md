# pdn-node-http: host — delta for identity-scoped-replicas

## MODIFIED Requirements

### Requirement: The debug surface covers the embedded runtime's operations
When enabled, the debug surface SHALL make identity creation and linking, connection establishment, grants, entry operations, node status, and hosted identities reachable over HTTP. An entry operation SHALL name the identity performing it as well as the issuer addressed, so a caller reaches exactly what that identity holds. Each route SHALL delegate to a runtime service call and add no orchestration of its own.

#### Scenario: A whole scenario runs over HTTP alone
- **WHEN** 2 hosts are driven only over HTTP through identity creation, establishment, a grant, a write, and a grantee read
- **THEN** the grantee reads the granted entry without an in-process call into either runtime

#### Scenario: A device joins over HTTP
- **WHEN** a linking payload is minted on 1 host and consumed on a second
- **THEN** the second host reports the identity as hosted and reads entries written before the link

#### Scenario: A read as a co-located identity is refused
- **WHEN** a host hosting two identities is asked, over HTTP, to read an issuer one identity holds under a grant, naming the other identity
- **THEN** the response is a client error and no entry is returned
