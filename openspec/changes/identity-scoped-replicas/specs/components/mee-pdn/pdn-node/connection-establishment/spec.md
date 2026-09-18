# pdn-node: connection establishment — delta for identity-scoped-replicas

## ADDED Requirements

### Requirement: Two identities of one node establish through the same dialogue

Two identities hosted on one node SHALL establish a connection through the dialogue this spec states, run inside the process ([in-process sessions](../../data-layer/in-process-sessions/spec.md)), because a node does not dial its own endpoint. The invite SHALL be one-time and short-lived and its secret SHALL be verified and burned as it is between two nodes, both identities SHALL record the connection in their own directories, and the connection's metadata pair SHALL be two replicas — one in each identity's scope — that converge without any peer being reachable.

#### Scenario: Two identities of one node connect and exchange a grant

- **WHEN** one hosted identity mints an invite and a co-located identity establishes from it, with no other node reachable
- **THEN** each lists the other as a connection, and a grant one publishes reads back on the other, its granted claim arriving

#### Scenario: The burned secret refuses a second attempt

- **WHEN** the same invite payload is presented again by the co-located identity
- **THEN** the establishment is refused and no second connection is recorded

#### Scenario: A third identity on the node sees nothing of the pair

- **WHEN** a third identity hosted on the same node lists its connections and reads grants toward the two
- **THEN** it lists no connection with either and reads nothing of what they published to each other
