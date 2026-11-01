## MODIFIED Requirements

### Requirement: The debug surface covers identities, linking and pods
When enabled, the debug surface SHALL make identity creation and linking, what became of a linking invite, [pods](../../../../architecture/language/pod.md), node status, and hosted identities reachable over HTTP. A pods operation SHALL name the identity performing it as well as the pod, so a caller reaches exactly what that identity holds. Each route SHALL delegate to a runtime service call and add no orchestration of its own. The pods routes SHALL cover every operation of the pods service, one route each: creating and listing pods and listing a pod's members; inviting, what became of an invite, and joining; the membership acts; placing records, appending operations, reading and listing records; and listing the entries outside the key layout.

**Example:** two requests to the host on Alice's tablet a3, which hosts Alice-leisure, a member of the pod `ad58a3faa04cdc5576c8dc5823a347c6`, and Alice-work, no member; `<alice-leisure>`, `<alice-work>`: 64 lowercase hex chars of each `PdnId`.

| request | answer |
|---|---|
| `GET /debug/identities/<alice-leisure>/pods/ad58a3faa04cdc5576c8dc5823a347c6/records` | the records Alice-leisure's replica holds, from one `list_records` call |
| `GET /debug/identities/<alice-work>/pods/ad58a3faa04cdc5576c8dc5823a347c6/records` | 409: Alice-work is no member, whoever else the tablet hosts |

#### Scenario: A device joins over HTTP
- **WHEN** a linking payload is minted on 1 host and consumed on a second
- **THEN** the second host reports the identity as hosted and reads a record the identity placed before the link

#### Scenario: A read as a co-located identity that is no member is refused
- **WHEN** a host hosting two identities is asked, over HTTP, to read a pod one identity is a member of, naming the other identity
- **THEN** the response is a client error and no record is returned

#### Scenario: A pod scenario runs over HTTP alone
- **WHEN** 3 hosts are driven only over HTTP through creating a pod, two invitations, a record placed by one member and an operation appended to it by another
- **THEN** every member reads the record and the operation without an in-process call into any runtime

#### Scenario: An invite's state is read over HTTP
- **WHEN** a pod invite and a linking invite are minted on 1 host and each is consumed on a second, over HTTP alone
- **THEN** the first host answers each invite as pending before it is consumed and as used afterwards, naming the joiner's identity and the newcomer's node id
