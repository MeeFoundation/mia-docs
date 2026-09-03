# The error table covers a failed verification

Linking gains an outcome the host has never seen: the material the inviting device presented did not line up. It is a refusal of the operation, not an internal failure, and the closed table says so rather than falling through to its default.

## MODIFIED Requirements

### Requirement: A refused operation is reported as a refusal
The host SHALL report a runtime refusal with its allow-listed client-error status and SHALL NOT report it as success. A refusal SHALL remain distinguishable from an absent route and an internal or transport failure. A linking attempt that fails because the presented verification material did not line up SHALL map to a refusal, not to the table's unrecognized-failure default; the host SHALL NOT convey the typed reason to the caller beyond what the refusal status carries, since a stand's client has no decision to make with it.

#### Scenario: An unhosted identity is refused, not absent
- **WHEN** a request addresses an identity the runtime does not host
- **THEN** the response is a client error other than 404

#### Scenario: An absent entry is reported as absent
- **WHEN** a request reads a missing entry under a hosted issuer
- **THEN** the response is HTTP 404

#### Scenario: A write outside the grant's write set is refused
- **WHEN** a grantee writes a read-only claim
- **THEN** the response is a client error and the previous value remains

#### Scenario: A burnt invite secret is refused
- **WHEN** a consumed invite payload is presented again
- **THEN** the response is a client error and no second connection is recorded

#### Scenario: A failed verification is a refusal, not a server error
- **WHEN** a link request fails because the inviting device's chain does not reach the payload's identity
- **THEN** the response is the refusal status, not the unrecognized-failure status

### Requirement: The surface offers no path the runtime's own callers lack
The surface SHALL NOT expose namespace ticket handover, forced reconciliation, or direct store access, and SHALL NOT return a namespace ticket when reading a grant. It SHALL NOT offer a state reset of its own — no route that discards or rewrites state the runtime does not itself discard through a service call. The runtime's own forget operation is therefore exposable and is exposed: it is a service call with its own semantics, not a reset the host invents, and the distinction is what the prohibition is about.

#### Scenario: A granted namespace arrives with no ticket crossing the surface
- **WHEN** a connected peer publishes a grant and the grantee reads the entry over HTTP
- **THEN** the entry eventually reads back without any route handing over or accepting a namespace ticket

#### Scenario: Convergence is waited for, not forced
- **WHEN** a caller waits for a value written on another node
- **THEN** repeating the read is the only available wait mechanism

#### Scenario: Discarding state goes through the runtime's own operation
- **WHEN** the stand discards an identity
- **THEN** it does so through the route that calls the runtime's forget operation, and no route offers a reset the runtime itself does not provide

### Requirement: The debug surface covers the embedded runtime's operations
When enabled, the debug surface SHALL make identity creation and linking, explicit identity forgetting, connection establishment, grants, entry operations, node status, and hosted identities reachable over HTTP. Each route SHALL delegate to a runtime service call and add no orchestration of its own. The forgetting route SHALL forget exactly what the service forgets and report a refusal for an identity the runtime never knew.

#### Scenario: A whole scenario runs over HTTP alone
- **WHEN** 2 hosts are driven only over HTTP through identity creation, establishment, a grant, a write, and a grantee read
- **THEN** the grantee reads the granted entry without an in-process call into either runtime

#### Scenario: A device joins over HTTP
- **WHEN** a linking payload is minted on 1 host and consumed on a second
- **THEN** the second host reports the identity as hosted and reads entries written before the link

#### Scenario: A forgotten identity can be linked again from the stand
- **WHEN** the stand forgets an identity and then links into it again with a fresh invite
- **THEN** both requests succeed, and the second linking pins the history it verifies

#### Scenario: Forgetting an unknown identity is a refusal
- **WHEN** the stand forgets an identity the runtime never hosted or attempted
- **THEN** the response is a client error, not a success and not a server error
