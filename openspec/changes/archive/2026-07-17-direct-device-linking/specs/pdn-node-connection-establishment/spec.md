## MODIFIED Requirements

### Requirement: Establishment records the connection for both identities, on all their devices
On a completed dialogue each side SHALL record the counterparty among the connections records of its private-metadata directory, assemble the metadata pair — creating its own store if none exists toward this peer, importing the counterpart's from the received read ticket — and publish the pair's tickets in the same directory. Establishment performed on one device of each identity SHALL thereby reach the identities' other devices: the directory replicates, and a linked device opens the pair from the directory's tickets on demand.

#### Scenario: Both sides list each other
- **WHEN** runtime B establishes with an invite from runtime A
- **THEN** A's identity lists B's among its connections and B's lists A's

#### Scenario: The connection is visible from linked devices
- **WHEN** establishment ran between A's phone and B's phone, and each identity has a laptop linked
- **THEN** each laptop eventually lists the counterparty among its identity's connections and reads the counterpart's metadata store opened from its directory

### Requirement: Re-establishment converges, whichever side invites
A fresh invite between identities that already share establishment state — a completed connection, or the residue of a handshake that failed after the burn — SHALL establish cleanly and converge: each identity's directory holds one connection record per counterparty, each side's own metadata store toward the peer is reused (the directory yields the same replica, so tickets from different attempts address the same namespace), and no duplicate replicas exist — regardless of which side mints the fresh invite.

#### Scenario: Establishing twice yields one connection
- **WHEN** A and B establish, and later establish again from a fresh invite
- **THEN** each lists the other exactly once, and each side's own metadata store is the same replica both times

#### Scenario: The retry may swap directions
- **WHEN** the first establishment ran from A's invite and the second runs from B's invite
- **THEN** the outcome converges identically — one connection, the same metadata pair, no duplicates
