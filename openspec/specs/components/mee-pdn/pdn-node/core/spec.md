# Runtime core

## Purpose

The embeddable runtime core: identity, connections, data, and sync services as thin glue over `data-layer`. Each embedded runtime is one running node — a host embeds one, and in-process tests embed several to stand up several nodes; one runtime hosts any number of identities (per data-layer [multi-identity](../../data-layer/multi-identity/spec.md)), each added by an explicit act. The core adds no sync or authorization mechanics of its own: every operation delegates to a `data-layer` primitive; read access is carried by session classification and the egress filter ([subset reconciliation](../../data-layer/subset-reconciliation/spec.md)), and the runtime registers everything it hosts, so its nodes are always armed.

## Requirements

### Requirement: The core embeds as a library
The runtime core SHALL be usable as a library with no host attached: a process embeds it, drives every service in-process, and shuts it down. The core SHALL NOT depend on any host machinery (HTTP or otherwise); hosts depend on the core, never the reverse.

#### Scenario: In-process embedding
- **WHEN** a test embeds the runtime core directly and drives the identity, connections, data, and sync services
- **THEN** every operation completes without any host process or HTTP surface involved

### Requirement: Identity service creates and links identities
The identity service SHALL create an identity on its first device — minting a placeholder `PdnId` (a random identifier with no key material behind it) and provisioning its store set: the private-metadata directory and the data namespace, with the data-namespace ticket published in the directory ([device-linking](../device-linking/spec.md)). It SHALL mint a linking invite for a hosted identity — the one-time secret and the bearer-free linking payload — and SHALL link this runtime into an existing identity from a scanned linking payload, one explicit linking act per identity; the payload names the identity, and a runtime already hosting it refuses before dialing.

#### Scenario: Create on one runtime, link on another
- **WHEN** an identity is created on runtime A and runtime B links from a linking invite minted on A
- **THEN** B hosts the identity: it appears among B's hosted identities, and the identity's directory and data namespace converge on B

#### Scenario: Linking one identity imports nothing of another
- **WHEN** runtime B is linked into identity X while identity Y exists elsewhere
- **THEN** B hosts X only, and operations addressed to Y on B are refused as unknown

### Requirement: Connections service establishes, lists, and carries grants
The connections service SHALL produce connections through the establishment dialogue — minting invites for a hosted identity and establishing from an invite payload ([connection-establishment](../connection-establishment/spec.md)) — and SHALL list a hosted identity's current connections, delegating to the connections records of that identity's [directory](../../data-layer/private-metadata-store/spec.md). It SHALL carry data grants over the connection's [metadata pair](../../data-layer/connection-metadata-store/spec.md): publishing a grant of the identity's own namespace toward a connected peer — capability-scoped by an exact claim set, naming per claim whether write accompanies read — withdrawing a published grant, reading the grants a connected peer has published, and reading the grants the identity has published toward a connected peer, opening the pair from the directory's tickets on demand, so linked devices reach it too. Manual one-sided recording is not offered: establishment is the producer of connections. Reading a peer's grant yields the capability and the ticket it carries; the grantee runtime acts on that record by itself, so no import act is required of the caller. Reading the identity's own published grant yields the capability alone: the caller is the issuer of the namespace the record addresses, so a ticket to it answers nothing.

Both reads SHALL report what is readable at the moment of the call and SHALL NOT wait for a record to arrive. A grant published on one device of an identity reaches that identity's other devices by replication of the pair, so a device that did not publish a grant reads it once the record and its payload have arrived, and reads nothing before then — the same waiting a peer does, for the same reason. Neither read is free of writes: opening a pair publishes the opening device's record into it and registers the connection, so "reports what is readable now" means the call does not wait and changes no grant, not that it writes nothing.

Both reads answer for the device they run on, and SHALL be described that way wherever a caller reads about them. The read reports what this device holds in the pair's replicas: on the device that published a grant it is evidence the record is here, never that it reached a sibling or the peer, and no read reports what the counterparty has received. Nothing on this surface carries that answer, which would need a per-peer synchronization progress out of the engine or an acknowledgement a sibling writes into the pair.

An empty answer therefore covers four states and SHALL NOT be presented as the fact that nothing is granted: this identity holds no connection to that peer, the pair's tickets have not replicated to this device yet, a grant record is here whose payload cannot be read yet, and nothing is granted toward that peer. The peer-side read answers the same way for the same reason, and refusing wherever no pair opens would turn a linked device's catching-up into failures rather than into an answer that changes when the directory arrives.

Both reads SHALL resolve the pair through the acting identity's own directory. An identity hosted beside another therefore reaches only its own pairs, and a third party on another node reaches none of them at all: the pair's stores are addressed by the tickets the two sides exchanged, and only those two sides hold them.

A grant SHALL name the granting identity itself as the data issuer; publishing or withdrawing a grant of any other issuer's data SHALL be refused loudly, with nothing minted or written. Granting foreign data is delegation: the serving side evaluates grants from the records of the *data issuer's* own connections, so a grant recorded under a different granting identity could never be honored — without the refusal it would publish successfully, replicate, and enforce as nothing, a silent no-op on both sides. The grant keying by data issuer is untouched — it is the groundwork delegation chains use; the boundary lifts when `UWill` chains make a foreign issuer's grant provable.

(A grant's ticket mode follows its commands as a whole: a grant with no write on any claim ships a read ticket and cannot write at all — no namespace secret — while a grant carrying write on any claim ships a write ticket. The store's capability bounds swarm membership, not access; the read side is enforced by session classification, which serves each session exactly the granted claim set, and the write side is enforced per claim by the ingest gate at the issuer's devices ([capability-gated ingest](../../data-layer/capability-gated-ingest/spec.md)).)

#### Scenario: Hosted identities' connection lists are disjoint
- **WHEN** identity X on a runtime establishes a connection with peer P and identity Y on the same runtime establishes none
- **THEN** listing Y's connections yields nothing

#### Scenario: A grant crosses to the peer with no new pairing
- **WHEN** X publishes a grant of its namespace toward its established peer P, after establishment completed
- **THEN** P's runtime reads the grant from the metadata pair and, once the record and its payload have replicated, reads X's entries without any import act

#### Scenario: An identity reads what it published, and the read carries no ticket
- **WHEN** X publishes a grant of its namespace toward its established peer P and then reads its own published grants toward P
- **THEN** the read reports the granted issuer, the exact claim set, and the write right of each claim, and carries no ticket

#### Scenario: A republication and a withdrawal are both visible to the issuer
- **WHEN** X republishes the grant toward P with a different claim set, and later withdraws it
- **THEN** X's own read reports the second claim set after the republication and reports no grant for that issuer after the withdrawal

#### Scenario: A sibling device reads a grant it did not publish
- **WHEN** X publishes a grant toward P on one of its devices, and X's own published grants are read on another device of X
- **THEN** the second device reads nothing until the record and its payload have replicated to it, and reads the same capability afterwards

#### Scenario: Connections operations on an unhosted identity are refused
- **WHEN** an invite, establishment, listing, or grant operation — a peer's grants or the identity's own — addresses an identity the runtime neither created nor linked
- **THEN** the operation fails with an unknown-identity error and nothing is minted, established, listed, published, or withdrawn

#### Scenario: A co-hosted identity reads none of another identity's published grants
- **WHEN** identity Y, hosted on the same runtime as X and holding no connection to P, reads its own published grants toward P
- **THEN** it obtains nothing, because the read resolves the pair through the acting identity's own directory, which holds no pair toward P — and X's grants toward P stay readable to X on the same runtime

#### Scenario: Two identities connected to one peer read their own grants and no other's
- **WHEN** X and Y are hosted on the same runtime, both hold a connection to P, both have published a grant toward P, and each reads its own published grants toward P
- **THEN** each reads the claim set it published itself and never the other's, because each read resolves its own pair through its own directory

#### Scenario: Granting a foreign issuer's data is refused
- **WHEN** identity X publishes or withdraws a grant naming a data issuer other than X, even one hosted on the same runtime
- **THEN** the operation is refused as unsupported delegation, and no grant record for that issuer ever reaches the peer's view of the pair

### Requirement: Data service writes, reads, lists, and imports granted namespaces
Every data operation SHALL name the identity performing it, and SHALL act for that identity alone. The data service SHALL write and read entries in a hosted issuer's [data namespace](../../data-layer/data-store/spec.md), SHALL list its entries as metadata (no payload bytes; optionally filtered by a path prefix), SHALL share a namespace the identity issues as a ticket, and SHALL import a peer's namespace from a ticket obtained out of band for the identity named: the imported replica stays outside its gossip swarm and is re-served only to the devices of the grant's audience identity, per the locally replicated grant record ([subset reconciliation](../../data-layer/subset-reconciliation/spec.md)). An import under the identity's own id SHALL be refused, whatever namespace its ticket names: an identity holds its own data as its issuer, and a binding under a grant would take that replica out of its swarm and away from its own devices, or drop it for the ticket's replica. A ticket is addressing, not access: an armed issuer serves a caller only per its recorded grants, so an out-of-band ticket with no grant behind it delivers nothing. The sanctioned transport for namespace access between connected identities is the connections service's grant surface above, which the runtime acts on by itself; the import operation remains for a ticket obtained out of band. A namespace imported that way has no grant record behind it, so this node re-serves it to no one — not to another holder of the same ticket and not to the importing identity's own devices, which import their own ticket if they want it — while its entries stay readable to the identity that imported it. A namespace the identity holds under a grant or imported out of band SHALL NOT be shared. A ticket minted there would add no reader: this node serves such a replica only to the audience identity's own devices, which the grant binder already reaches, and serves an out-of-band import to no one. Minting it would also restart the replica's sync as if the identity issued it — back in the gossip swarm, and naming the identity instead of the issuer to every peer the engine recorded, which the issuer's devices refuse as not hosted. A write addressed at a granted namespace SHALL be refused up front when the local grant record's write set does not cover the claim — the error arrives at the call site, before the replica is touched. The refusal SHALL rest on a grant this node has actually read: a record whose payload is still replicating says nothing about what it covers, and refusing there would turn a courtesy into a denial of writes the issuer would keep. The enforcement proper is the issuer-side ingest gate, and the writer-side outcome of a bypass is [write retraction](../../data-layer/write-retraction/spec.md).

#### Scenario: Write then read locally
- **WHEN** an entry is written under a hosted issuer at a path, by the identity that issues it
- **THEN** reading that issuer and path as that identity returns the payload

#### Scenario: Listing yields exactly the written paths
- **WHEN** entries are written at two paths under a hosted issuer
- **THEN** listing that issuer as the identity that issues it yields exactly those two paths, without payload bytes

#### Scenario: A co-located identity reads nothing of another's granted namespace
- **WHEN** one hosted identity holds a namespace under a grant and a co-located identity, holding no grant of that issuer, reads and lists the same issuer
- **THEN** both operations fail with the unknown-issuer error, and nothing of that namespace is returned

#### Scenario: A bare ticket delivers nothing from an armed issuer
- **WHEN** runtime A shares issuer I's namespace as a ticket out of band and an identity on runtime B, holding no grant from I, imports it
- **THEN** the import itself succeeds as a local registration held for that identity, and no entry of I's namespace ever reaches B — A refuses B's sessions as if the replica were not hosted

#### Scenario: What was imported out of band is re-served to nobody

- **WHEN** an identity imports a namespace from a ticket obtained out of band, and a sibling device of that identity or another holder of the same ticket asks this node to sync it
- **THEN** the request is refused indistinguishably from the replica not being hosted, and the entries stay readable to the identity that imported them

#### Scenario: An import under the identity's own id is refused

- **WHEN** an identity imports a ticket under its own id, naming its own namespace or another identity's
- **THEN** the import is refused, and the identity still shares its own namespace and reads its own entries

#### Scenario: A namespace held as a grantee is not shared
- **WHEN** an identity asks to share a namespace it holds under a grant, or one it imported out of band
- **THEN** the operation is refused before the replica is touched, while the issuer shares the same namespace

#### Scenario: A write on a write-granted claim reaches the issuer
- **WHEN** a peer's grant carries write on a claim and the audience identity writes that claim under the peer's issuer
- **THEN** the issuer's runtime eventually reads the written value, and the audience reads the same value back through its granted view

#### Scenario: A write outside the write set is refused up front
- **WHEN** the audience identity writes, under the peer's issuer, a claim its grant covers read-only
- **THEN** the operation fails at the call site and the local replica is unchanged

#### Scenario: Unhosted issuer is refused
- **WHEN** a read, write, or list names an identity and an issuer that identity neither created nor imported
- **THEN** the operation fails with an unknown-issuer error, and nothing is read, written, or listed

### Requirement: The runtime surfaces retraction verdicts

The runtime SHALL expose a subscription to write-retraction events of its hosted identities: each event names the issuer, the path, the author, the timestamp, the content hash, and the deciding device of one retracted entry, as [write retraction](../../data-layer/write-retraction/spec.md) produces them. The subscription is the host's hook for user-facing surfacing; the runtime itself only reports.

#### Scenario: A verdict reaches the subscriber
- **WHEN** a hosted identity's write into a granted namespace is retracted
- **THEN** a subscriber on that runtime observes one event naming the retracted entry's issuer, path, author, timestamp, and content hash

### Requirement: A granted replica's sibling contacts follow the audience directory

The runtime SHALL point a granted replica at the other devices of the identity it is held for, so the replica converges from a sibling while the issuer is unreachable. The contact set SHALL be derived from that identity's directory device records rather than kept beside them, and SHALL be re-derived as the directory changes, so a device linked after the namespace was imported is dialed too. The directory of any other hosted identity SHALL NOT be consulted for this replica, whether that identity holds a grant of the same issuer or none at all.

#### Scenario: A sibling contact is dialed with the issuer offline

- **WHEN** a granted replica is imported on a device whose sibling holds the replica and a live grant record, and every device of the issuer is offline
- **THEN** the replica converges from the sibling

#### Scenario: An unrelated hosted identity's device is not a contact

- **WHEN** a runtime hosts a second identity that holds no grant from the issuer
- **THEN** that identity's devices do not appear among the granted replica's contacts

#### Scenario: A co-located audience's devices are not contacts either

- **WHEN** a runtime hosts a second identity granted by the same issuer, holding a replica of its own
- **THEN** each replica's contacts are its own identity's devices and the issuer devices its own connection publishes
### Requirement: Sync service reports the node id and the hosted identities
The sync service SHALL report the runtime's node id (its endpoint id) and the identities the runtime hosts — exactly those created or linked on it. It SHALL also answer a storage check from the replica store itself — the read a host's readiness probe rests on ([host](../../pdn-node-http/host/spec.md)) — because every other report here is in-memory bookkeeping, which a store that stopped answering leaves untouched.

#### Scenario: Hosted identities follow create and link
- **WHEN** a fresh runtime reports its status, then creates one identity and links another
- **THEN** the report lists no identities first and afterwards exactly those two, with the node id unchanged throughout
### Requirement: A granted namespace binds and unbinds for the identity its grant addresses

The runtime SHALL keep the data namespaces behind a connection's live grants imported, without an explicit import act: for every open metadata pair of a hosted identity it SHALL watch the counterparty's replica and, as a grant record becomes readable there, import the namespace the record's ticket names for that identity. A grant whose ticket comes to name a different replica SHALL be re-imported onto it, and the replica it bound before SHALL be forgotten in that import, so a counterparty that keeps moving its grant leaves no replica behind. A grant that disappears from the counterparty's replica SHALL take its binding back out, and the replica it bound SHALL be forgotten with it, so the issuer resolves to nothing for that identity again.

The replica belongs to the identity the grant addresses, and one pair binds one issuer there: a grant names its own identity as the data issuer, and an identity holds one connection per counterparty. A withdrawal therefore decides from the pair it swept alone, and a co-located identity granted by the same issuer holds a replica of its own that the withdrawal leaves untouched.

The import bookkeeping SHALL be an optimization, not the arbiter. An issuer already resolving in that identity to the very namespace a grant names SHALL be adopted into the bookkeeping rather than re-imported: each import holds one more open handle on the replica, and the drop at the end of its life must find exactly one. An issuer resolving to nothing SHALL be re-imported even when the bookkeeping names exactly the namespace the grant carries, so a replica forgotten while the bookkeeping survived comes back on the pair's next sweep instead of being skipped forever.

The runtime SHALL bound this to what it imported itself. A namespace imported by any other route SHALL never be forgotten by this mechanism, and the explicit import operation SHALL remain available for a ticket obtained out of band. Nor SHALL such a namespace be displaced: while an issuer resolves in that identity to a replica an import of another route bound, a grant whose ticket names a different replica waits, and the binding follows the grant only once that import is forgotten or the grant comes to name the replica the issuer already resolves to — re-importing over it would have two owners displace each other on every sweep.

Watching SHALL include the counterparty replica's payload arrivals, not only its entry arrivals: a grant's ticket travels as a payload blob, so a record whose entry has replicated is not yet a ticket that can be acted on.

#### Scenario: A grant binds its namespace with no import act

- **WHEN** a connected peer publishes a grant of its data store toward a hosted identity, and the grant record and its ticket payload replicate to the identity's runtime
- **THEN** the runtime imports the granted namespace for that identity by itself and the granted entries become readable there, with no import operation invoked by the caller

#### Scenario: A linked device binds a grant established elsewhere

- **WHEN** a device is linked into an identity whose connection and grant were established on another of its devices, and the pair and grant records replicate to it
- **THEN** the newly linked device imports the granted namespace by itself, reaching it through the pair its directory carries

#### Scenario: A withdrawn grant unbinds its namespace

- **WHEN** the granting peer withdraws the grant and the tombstone replicates to the grantee's copy of the pair
- **THEN** the grantee forgets the namespace it imported under that grant, and operations addressing that issuer as that identity fail with an unknown-issuer error

#### Scenario: A withdrawal toward one audience spares the co-hosted other

- **WHEN** one node hosts two identities granted by the same issuer, and the issuer withdraws the grant toward one of them
- **THEN** the withdrawn identity's replica is forgotten and its issuer resolves to nothing for it, while the co-located identity goes on reading its own replica and receiving the issuer's fresh writes there

#### Scenario: A forgotten replica re-imports on the next sweep

- **WHEN** a bound replica is forgotten while the binder's bookkeeping still names its import, and the pair's replica changes next
- **THEN** the runtime re-imports the granted namespace and its entries are readable again

#### Scenario: A grant moved onto another replica replaces the one it bound

- **WHEN** the counterparty's grant record comes to carry a ticket of a namespace other than the one it bound, and the record replicates to the grantee's copy of the pair
- **THEN** the grantee imports the namespace the record now names, and the replica the grant bound before is no longer held or reconciled

#### Scenario: A grant waits while an out-of-band import holds its issuer

- **WHEN** a runtime has imported a namespace out of band under an issuer, and that issuer's grant naming a different namespace then becomes readable in the pair
- **THEN** the grant's sweep neither imports the granted namespace nor forgets the one imported out of band

#### Scenario: An out-of-band import is not unbound

- **WHEN** a runtime imports a namespace from a ticket obtained outside any grant, and no grant record for that issuer exists in any of its pairs
- **THEN** the imported namespace stays bound — the binding mechanism forgets only namespaces it imported itself

#### Scenario: A withdrawal leaves an out-of-band import that holds the issuer

- **WHEN** a runtime holding a grant's namespace imports another namespace out of band under that grant's issuer, and the grant is then withdrawn
- **THEN** the namespace imported out of band stays bound and held — the withdrawal forgets only the replica the grant bound, and that one had already been replaced

### Requirement: A granted replica reaches the issuer devices its own connection publishes

The runtime SHALL point a granted replica at the devices the issuing identity has published in the connection metadata store of the connection whose grant bound this replica, in addition to the addresses the grant's ticket carried and the holding identity's own siblings. The whole contact set SHALL be re-derived from those records as they change, so a device the issuer links later is dialed and one the issuer withdraws leaves the contact set — the publishing device included, since the ticket's addressing is kept only for devices the issuer still publishes.

A grant's ticket names whichever device published the grant, so without this a granted replica has exactly one reachable device of its issuer. The published device set is the issuer's own statement of who acts for it toward this counterparty — the same set the runtime already consults to decide whose writes it may retract — so reaching a sibling asks nothing new of the issuer and reveals nothing the counterparty was not already told. The issuer's own directory is not a source here: it is device-internal and the audience cannot read it.

Leaving the contact set is what this requirement governs. The sync engine keeps its own short record of peers that once served the replica and may redial such a peer until that record ages out, so a withdrawn device's reach is bounded by the re-derived set rather than cut at the very next dial; what any session delivers is governed by classification either way.

The set published by a counterparty SHALL be used only for namespaces that counterparty issues. It is the issuer's device set exactly while the two are the same identity, which the grant surface holds today by refusing to publish a grant of another identity's data; a delegated grant would need the originating issuer's set, and this requirement does not supply it.

One node may host several identities granted by the same issuer, and each holds a replica with stores of its own: the contact set of each SHALL come from that identity's own connection alone, and the device set the runtime consults to decide whose writes it may retract SHALL be read from the same one connection. A withdrawal a counterparty publishes toward one identity therefore governs that identity's replica and leaves the co-located one as it was.

#### Scenario: The audience converges from a device that did not publish the grant

- **WHEN** an identity publishes a grant from one of its devices, the granted data reaches its other device by device replication, and the publishing device then goes offline
- **THEN** the audience converges on the granted claims from the other device

#### Scenario: A device published after the grant is dialed too

- **WHEN** the issuing identity links a further device and that device publishes itself in the connection metadata store after the audience already imported the granted replica
- **THEN** the audience's replica comes to count the new device among its contacts, without re-importing and without a new grant

#### Scenario: A withdrawn device stops being a contact

- **WHEN** the issuing identity withdraws a device's published record from the connection whose grant bound the replica
- **THEN** that device is no longer among that replica's contacts, while the still-published device remains

#### Scenario: A withdrawal toward one audience leaves the co-located one alone

- **WHEN** one node hosts two identities granted by the same issuer and the issuer withdraws a device's record from one of the two connections only
- **THEN** that device leaves the contacts of that identity's replica and stays among the contacts of the co-located identity's replica

#### Scenario: Another counterparty's devices are not contacts

- **WHEN** the audience holds connections with two peers, each granting its own data namespace, and one peer publishes a further device
- **THEN** that device becomes a contact of that peer's granted replica only, and not of the other peer's

#### Scenario: The publishing device is not special

- **WHEN** the grant is published from a device the issuer linked later — the founder never touches the grant surface — and the publishing device then goes offline
- **THEN** the audience converges on the granted claims from the founder

#### Scenario: Audiences hosted together keep separate replicas

- **WHEN** one node hosts two identities and one issuer grants each of them a claim of its namespace
- **THEN** the node holds a replica per identity, each carrying the claim its own grant names and dialing its own contacts

#### Scenario: A re-grant after withdrawal rebuilds the contacts

- **WHEN** a grant is withdrawn — the audience's binder forgets the namespace — and the issuer grants the same claim anew
- **THEN** the audience converges again, and the fresh import's contact set counts the issuer's other devices as before
