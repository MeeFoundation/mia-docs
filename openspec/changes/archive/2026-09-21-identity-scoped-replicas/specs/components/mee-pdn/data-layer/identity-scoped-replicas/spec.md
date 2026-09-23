# data-layer: identity-scoped replicas — delta for identity-scoped-replicas

## Purpose

A hosted identity owns its own half of the node: the replicas it acquired, the author its writes carry, and the sessions it takes part in. On the wire that party travels as 32 opaque bytes pdn-store compares and never interprets, filled here with the identity's `PdnId`: the store keeps the value, not the vocabulary that gives it meaning. What one identity holds is stored, written and served apart from what another identity of the same node holds, so co-location separates by where the bytes live rather than by a check at each read. ADR-0013 states the level of isolation this carries and what it leaves to a counterparty's observation.

## ADDED Requirements

### Requirement: Every replica is created and imported for a named identity

Every replica a node holds SHALL belong to exactly one hosted identity, and the act that brings it there — a create or an import, a private metadata directory and a connection metadata store included — SHALL name that identity. Two identities SHALL NOT share a replica, whether they acquired the same namespace under two grants of one issuer or hold the two ends of one connection's metadata pair. The runtime SHALL import the ticket a grant record carries only for the identity the grant is addressed to: it reads a connection's grants for the identity at that connection's end alone, and a record addressed to anyone else binds nothing there. An import the host makes explicitly SHALL land in the identity it names, whichever hosted identity that is, and SHALL bring that identity nothing it was not granted: a ticket carries no record of the grant or the connection it came from, so no import can tell a grant's ticket from any other, and what makes one useless to an identity the grant does not address is that the issuer answers only the audiences it granted and a replica one identity imports is served to nobody. A replica an identity holds is therefore no evidence that a grant was made to it.

#### Scenario: Two audiences of one issuer hold two replicas

- **WHEN** one issuer grants a claim to each of two identities hosted on one node
- **THEN** that node holds two replicas of the issuer's namespace, one per identity, each converging on its own

#### Scenario: A namespace one identity holds is unknown to the other

- **WHEN** an identity is granted a claim and a co-located identity holds no grant of that issuer
- **THEN** the co-located identity reads and lists nothing of that issuer, and is answered as it is for an issuer no identity here holds

#### Scenario: A grant's ticket imported for another identity brings it nothing

- **WHEN** the host imports the ticket a grant addressed to one identity carries, naming a co-located identity the grant does not address
- **THEN** the import lands in the named identity, which obtains nothing of the issuer's entries, and the replica the addressed identity holds is served to neither that identity nor any other node

### Requirement: A device-shared store starts syncing once it is armed

A private metadata directory or a connection metadata store imported for an identity SHALL start its sync only once it is armed for that identity's sessions — the directory when the identity is hosted on it, a connection's two halves when the connection is hosted. Until then this identity's own book knows nothing to judge the store's sessions by and refuses them, and a first session refused that way is retried by nothing before the next reconcile pass; two identities of one node share no gossip, so for them that pass is the only retry. The devices that hold one half of a connection hold the other, under the same identity each, so hosting a connection SHALL point the identity's own half at the devices its peer half is dialed at: whichever side of a connection arms second then reaches the first over both halves, including the one whose first session the earlier side lost.

#### Scenario: Both halves converge whichever side arms first

- **WHEN** two identities of one node import each other's half of a connection and arm it one after the other, on a node whose reconcile interval is far longer than the wait
- **THEN** each reads the other's published devices within that wait

#### Scenario: A co-located establishment reads the counterparty's devices at once

- **WHEN** two identities of one node establish a connection on a node whose reconcile interval is far longer than the wait
- **THEN** each reads the other's published devices within that wait, from the first session of the store the establishment imported

### Requirement: A sync session names the replica's identity and the caller's

A sync session SHALL name the identity whose replica is addressed and the identity the caller acts as, and the serving side SHALL admit the caller's named identity only when the records it holds of that identity list the caller's authenticated node id among its devices — that identity's own directory where the serving node is one of its devices, and the device set the counterparty published into their connection's metadata store where a hosted issuer serves a counterparty, the same resolution each already uses for read rights. A caller naming an identity it is not a device of SHALL be refused indistinguishably from the replica not being hosted, and so SHALL a session naming an identity the node does not host. The session's rights, its egress filter and its write admission SHALL follow the named identities alone.

#### Scenario: A caller naming an identity it is not a device of is refused

- **WHEN** a node that is a device of no identity of the caller's choosing names that identity in a session
- **THEN** the session is refused indistinguishably from the replica not being hosted, and no entry is served

#### Scenario: A device of the named identity is served

- **WHEN** a device listed in an identity's records names that identity and addresses a replica that identity holds
- **THEN** the session proceeds under that identity's rights

#### Scenario: An identity the node does not host is refused

- **WHEN** a session names an identity the serving node does not host
- **THEN** it is refused indistinguishably from the replica not being hosted

### Requirement: Rights are the named identity's and are never unioned across a node's identities

A serving node SHALL compute a session's rights from the identity the caller names alone, and SHALL NOT add to them the rights of any other identity the caller's node id resolves to. A node that hosts several identities granted by one issuer SHALL therefore receive, in each session, exactly what the identity named there was granted. What such a node can obtain across all its sessions SHALL be bounded by the identities it is genuinely a device of.

#### Scenario: Each audience receives its own claims

- **WHEN** an issuer grants one claim to one hosted identity and a different claim to a co-located one, and each identity's replica reconciles
- **THEN** each replica carries the claim granted to its own identity, and neither carries the other's

#### Scenario: Naming the other identity does not widen a session

- **WHEN** a node holding two grants of one issuer names one of its identities and asks for the claim granted to the other
- **THEN** the session serves nothing of that claim, and its absence is indistinguishable from the claim not existing
