# pdn-node-http: host — delta for cells

## MODIFIED Requirements

### Requirement: The debug surface covers the embedded runtime's operations
When enabled, the debug surface SHALL make identity creation and linking, connection establishment, grants, entry operations, cells, node status, and hosted identities reachable over HTTP. An entry operation SHALL name the identity performing it as well as the issuer addressed, and a cells operation the identity performing it as well as the cell, so a caller reaches exactly what that identity holds. Each route SHALL delegate to a runtime service call and add no orchestration of its own. The cells routes SHALL cover every operation of the cells service, one route each: creating and listing cells, renaming a cell and listing its members; inviting and joining; the membership acts; placing records, appending operations, reading and listing records; and listing the entries outside the key layout.

**Example:** two requests to the host on the family tablet, which hosts Bob, a member of the cell `eead8ef96aa1254969d63c12631b799c`, and Erin, no member; `<bob>`, `<erin>`: 64 lowercase hex chars of each `PdnId`.

| request | answer |
|---|---|
| `GET /debug/identities/<bob>/cells/eead8ef96aa1254969d63c12631b799c/records` | the records Bob's replica holds, from one `list_records` call |
| `GET /debug/identities/<erin>/cells/eead8ef96aa1254969d63c12631b799c/records` | 409: Erin is no member, whoever else the tablet hosts |

#### Scenario: A whole scenario runs over HTTP alone
- **WHEN** 2 hosts are driven only over HTTP through identity creation, establishment, a grant, a write, and a grantee read
- **THEN** the grantee reads the granted entry without an in-process call into either runtime

#### Scenario: A device joins over HTTP
- **WHEN** a linking payload is minted on 1 host and consumed on a second
- **THEN** the second host reports the identity as hosted and reads entries written before the link

#### Scenario: A read as a co-located identity is refused
- **WHEN** a host hosting two identities is asked, over HTTP, to read an issuer one identity holds under a grant, naming the other identity
- **THEN** the response is a client error and no entry is returned

#### Scenario: A cell scenario runs over HTTP alone
- **WHEN** 3 hosts are driven only over HTTP through creating a cell, two invitations, a record placed by one member and an operation appended to it by another
- **THEN** every member reads the record and the operation without an in-process call into any runtime

### Requirement: A refused operation is reported as a refusal
The host SHALL report a runtime refusal with its allow-listed client-error status and SHALL NOT report it as success. A refusal SHALL remain distinguishable from an absent route and an internal or transport failure.

**Example:** cells requests on the family tablet, which hosts Carol, a plain member of `eead8ef96aa1254969d63c12631b799c`, and Erin, no member; `<alice>`, `<carol>`, `<erin>`: 64 lowercase hex chars of each `PdnId`; `<absent>`: an id the cell does not hold.

| request | answer |
|---|---|
| `PUT /debug/identities/<carol>/cells/eead8ef96aa1254969d63c12631b799c/name` | 403; the cell's name is unchanged |
| `GET /debug/identities/<erin>/cells/eead8ef96aa1254969d63c12631b799c/members` | 409 |
| `GET /debug/identities/<carol>/cells/eead8ef96aa1254969d63c12631b799c/records/<alice>/claim/<absent>` | 404 |

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

#### Scenario: A cell the identity is no member of is refused, not absent
- **WHEN** a request addresses a cell the identity is no member of
- **THEN** the response is a client error other than 404

#### Scenario: A refusal by role is reported as a refusal
- **WHEN** a plain member renames the cell
- **THEN** the response is a client error and every member lists the cell under its name unchanged

#### Scenario: An absent record is reported as absent
- **WHEN** a member reads a record the cell does not hold
- **THEN** the response is HTTP 404
