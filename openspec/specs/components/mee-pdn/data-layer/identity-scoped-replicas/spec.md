# Identity-scoped replicas

## Purpose

A hosted identity owns its own half of the node: the replicas it acquired, the author its writes carry, and the sessions it takes part in. On the wire that party is a [holder](../../../../architecture/language/holder.md) — 32 opaque bytes pdn-store compares and never interprets, filled here with the identity's `PdnId`. What one identity holds is stored, written and served apart from what another identity of the same node holds, so co-location separates by where the bytes live rather than by a check at each read. ADR-0013 states the level of isolation this carries and what it leaves to a counterparty's observation.

## Requirements

### Requirement: Every replica is created and imported for a named identity

Every replica a node holds SHALL belong to exactly one hosted identity, and the act that brings it there — a create or an import, a private metadata directory and a connection metadata store included — SHALL name that identity. Two identities SHALL NOT share a replica, whether they acquired the same namespace under two grants of one issuer or hold the two ends of one connection's metadata pair. A ticket carried by a grant record SHALL be imported for the identity the grant is addressed to, and the runtime SHALL refuse to import it into another; the refusal belongs where the grant is known, since a ticket handed over out of band carries no record of the connection it came from.

#### Scenario: Two audiences of one issuer hold two replicas

- **WHEN** one issuer grants a claim to each of two identities hosted on one node
- **THEN** that node holds two replicas of the issuer's namespace, one per identity, each converging on its own

#### Scenario: A namespace one identity holds is unknown to the other

- **WHEN** an identity is granted a claim and a co-located identity holds no grant of that issuer
- **THEN** the co-located identity reads and lists nothing of that issuer, and is answered as it is for an issuer no identity here holds

#### Scenario: An import naming another identity is refused

- **WHEN** a ticket carried by a grant addressed to one identity is imported naming a different hosted identity
- **THEN** the import is refused and neither identity holds a replica of it afterwards

### Requirement: A sync session names the replica's identity and the caller's

A sync session SHALL name, as holders, the identity whose replica is addressed and the identity the caller acts as, and the serving side SHALL admit the caller's named identity only when the records it holds of that identity list the caller's authenticated node id among its devices — that identity's own directory where the serving node is one of its devices, and the device set the counterparty published into their connection's metadata store where a hosted issuer serves a counterparty, the same resolution each already uses for read rights. A caller naming an identity it is not a device of SHALL be refused indistinguishably from the replica not being hosted, and so SHALL a session naming an identity the node does not host. The session's rights, its egress filter and its write admission SHALL follow the named identities alone.

#### Scenario: A caller naming an identity it is not a device of is refused

- **WHEN** a node that is a device of no identity of the caller's choosing names that identity in a session
- **THEN** the session is refused indistinguishably from the replica not being hosted, and no entry is served

#### Scenario: A device of the named identity is served

- **WHEN** a device listed in an identity's records names that identity and addresses a replica that identity holds
- **THEN** the session proceeds under that identity's rights

#### Scenario: A holder the node does not host is refused

- **WHEN** a session names a holder no identity on the serving node corresponds to
- **THEN** it is refused indistinguishably from the replica not being hosted

### Requirement: Rights are the named identity's and are never unioned across a node's identities

A serving node SHALL compute a session's rights from the identity the caller names alone, and SHALL NOT add to them the rights of any other identity the caller's node id resolves to. A node that hosts several identities granted by one issuer SHALL therefore receive, in each session, exactly what the identity named there was granted. What such a node can obtain across all its sessions SHALL be bounded by the identities it is genuinely a device of.

#### Scenario: Each audience receives its own claims

- **WHEN** an issuer grants one claim to one hosted identity and a different claim to a co-located one, and each identity's replica reconciles
- **THEN** each replica carries the claim granted to its own identity, and neither carries the other's

#### Scenario: Naming the other identity does not widen a session

- **WHEN** a node holding two grants of one issuer names one of its identities and asks for the claim granted to the other
- **THEN** the session serves nothing of that claim, and its absence is indistinguishable from the claim not existing
