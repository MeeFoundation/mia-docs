# Delta: pdn-node-core

## ADDED Requirements

### Requirement: Granted namespaces bind and unbind with their grant record

The runtime SHALL keep the data namespaces behind a connection's live grants imported, without an explicit import act: for every open metadata pair of a hosted identity it SHALL watch the counterparty's replica and, as a grant record becomes readable there, import the namespace the record's ticket names. A grant whose ticket comes to name a different replica SHALL be re-imported onto it. A grant that disappears from the counterparty's replica SHALL take its namespace back out: the runtime SHALL forget what it imported under that grant, so the issuer resolves to nothing again rather than to a replica no grant justifies.

The runtime SHALL bound this to what it imported itself. A namespace imported by any other route SHALL never be forgotten by this mechanism, and the explicit import operation SHALL remain available for a ticket obtained out of band.

Watching SHALL include the counterparty replica's payload arrivals, not only its entry arrivals: a grant's ticket travels as a payload blob, so a record whose entry has replicated is not yet a ticket that can be acted on.

#### Scenario: A grant binds its namespace with no import act

- **WHEN** a connected peer publishes a grant of its data store toward a hosted identity, and the grant record and its ticket payload replicate to the identity's runtime
- **THEN** the runtime imports the granted namespace by itself and the granted entries become readable there, with no import operation invoked by the caller

#### Scenario: A linked device binds a grant established elsewhere

- **WHEN** a device is linked into an identity whose connection and grant were established on another of its devices, and the pair and grant records replicate to it
- **THEN** the newly linked device imports the granted namespace by itself, reaching it through the pair its directory carries

#### Scenario: A withdrawn grant unbinds its namespace

- **WHEN** the granting peer withdraws the grant and the tombstone replicates to the grantee's copy of the pair
- **THEN** the grantee forgets the namespace it imported under that grant, and operations addressing that issuer fail with an unknown-issuer error

#### Scenario: An out-of-band import is not unbound

- **WHEN** a runtime imports a namespace from a ticket obtained outside any grant, and no grant record for that issuer exists in any of its pairs
- **THEN** the imported namespace stays bound — the binding mechanism forgets only namespaces it imported itself

### Requirement: A granted replica's sibling contacts follow the audience directory

The runtime SHALL point a granted replica at the other devices of the identity the grant is addressed to, so the replica converges from a sibling while the issuer is unreachable. The contact set SHALL be derived from that identity's directory device records rather than kept beside them, and SHALL be re-derived as the directory changes, so a device linked after the namespace was imported is dialed too. Only the audience identity's directory SHALL be consulted: on a runtime hosting several identities, the devices of an unrelated hosted identity SHALL NOT become contacts of the replica.

#### Scenario: A sibling contact is dialed with the issuer offline

- **WHEN** a granted replica is imported on a device whose sibling holds the replica and a live grant record, and every device of the issuer is offline
- **THEN** the replica converges from the sibling

#### Scenario: An unrelated hosted identity's device is not a contact

- **WHEN** a runtime hosts a second identity that holds no grant from the issuer
- **THEN** that identity's devices do not appear among the granted replica's contacts

## MODIFIED Requirements

### Requirement: Connections service establishes, lists, and carries grants
The connections service SHALL produce connections through the establishment dialogue — minting invites for a hosted identity and establishing from an invite payload ([connection-establishment](connection-establishment.md)) — and SHALL list a hosted identity's current connections, delegating to the connections records of that identity's [directory](../data-layer/private-metadata-store.md). It SHALL carry data grants over the connection's [metadata pair](../data-layer/connection-metadata-store.md): publishing a grant of the identity's own namespace toward a connected peer — capability-scoped by an exact claim set, with optional write — withdrawing a published grant, and reading the grants a connected peer has published, opening the pair from the directory's tickets on demand, so linked devices reach it too. Manual one-sided recording is not offered: establishment is the producer of connections. Reading a grant yields the capability and the ticket it carries; the grantee runtime acts on that record by itself, so no import act is required of the caller.

A grant SHALL name the granting identity itself as the data issuer; publishing or withdrawing a grant of any other issuer's data SHALL be refused loudly, with nothing minted or written. Granting foreign data is delegation: the serving side evaluates grants from the records of the *data issuer's* own connections, so a grant recorded under a different granting identity could never be honored — without the refusal it would publish successfully, replicate, and enforce as nothing, a silent no-op on both sides. The grant keying by data issuer is untouched — it is the groundwork delegation chains use; the boundary lifts when `UWill` chains make a foreign issuer's grant provable.

(A grant's ticket mode follows its commands: a read-only grant ships a read ticket and cannot write at all — no namespace secret — while a grant carrying write ships a write ticket. The store's capability bounds swarm membership, not access; the read side is enforced by session classification, which serves each session exactly the granted claim set, and the write side stays unscoped until the ingest gate (ADR-0008) lands.)

#### Scenario: Hosted identities' connection lists are disjoint
- **WHEN** identity X on a runtime establishes a connection with peer P and identity Y on the same runtime establishes none
- **THEN** listing Y's connections yields nothing

#### Scenario: A grant crosses to the peer with no new pairing
- **WHEN** X publishes a grant of its namespace toward its established peer P, after establishment completed
- **THEN** P's runtime reads the grant from the metadata pair and, once the record and its payload have replicated, reads X's entries without any import act

#### Scenario: Connections operations on an unhosted identity are refused
- **WHEN** an invite, establishment, listing, or grant operation addresses an identity the runtime neither created nor linked
- **THEN** the operation fails with an unknown-identity error and nothing is minted, established, listed, published, or withdrawn

#### Scenario: Granting a foreign issuer's data is refused
- **WHEN** identity X publishes or withdraws a grant naming a data issuer other than X, even one hosted on the same runtime
- **THEN** the operation is refused as unsupported delegation, and no grant record for that issuer ever reaches the peer's view of the pair

### Requirement: Data service writes, reads, lists, and imports granted namespaces
The data service SHALL write and read entries in a hosted issuer's [data namespace](../data-layer/data-store.md), SHALL list its entries as metadata (no payload bytes; optionally filtered by a path prefix), SHALL share a namespace hosted here as a ticket, and SHALL import a peer's namespace from a ticket obtained out of band: the imported replica stays outside its gossip swarm and is re-served only to the devices of the grant's audience identity, per the locally replicated grant record ([subset reconciliation](../data-layer/subset-reconciliation.md)). A ticket is addressing, not access: an armed issuer serves a caller only per its recorded grants, so an out-of-band ticket with no grant behind it delivers nothing. The sanctioned transport for namespace access between connected identities is the connections service's grant surface above, which the runtime acts on by itself; the import operation remains for a ticket obtained out of band.

#### Scenario: Write then read locally
- **WHEN** an entry is written under a hosted issuer at a path
- **THEN** reading that issuer and path returns the payload

#### Scenario: Listing yields exactly the written paths
- **WHEN** entries are written at two paths under a hosted issuer
- **THEN** listing that issuer yields exactly those two paths, without payload bytes

#### Scenario: A bare ticket delivers nothing from an armed issuer
- **WHEN** runtime A shares issuer I's namespace as a ticket out of band and runtime B, holding no grant from I, imports it
- **THEN** the import itself succeeds as a local registration, and no entry of I's namespace ever reaches B — A refuses B's sessions as if the replica were not hosted

#### Scenario: Unhosted issuer is refused
- **WHEN** a read, write, or list addresses an issuer the runtime neither created nor imported
- **THEN** the operation fails with an unknown-issuer error, and nothing is read, written, or listed
