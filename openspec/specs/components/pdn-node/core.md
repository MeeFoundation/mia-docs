# Runtime core

## Purpose

The embeddable runtime core: identity, connections, data, and sync services as thin glue over `data-layer`. Each embedded runtime is one running node — a host embeds one, and in-process tests embed several to stand up several nodes; one runtime hosts any number of identities (per data-layer [multi-identity](../data-layer/multi-identity.md)), each added by an explicit act. The core adds no sync or authorization mechanics of its own: every operation delegates to a `data-layer` primitive; read access is carried by session classification and the egress filter ([subset reconciliation](../data-layer/subset-reconciliation.md)), and the runtime registers everything it hosts, so its nodes are always armed.

## Requirements

### Requirement: The core embeds as a library
The runtime core SHALL be usable as a library with no host attached: a process embeds it, drives every service in-process, and shuts it down. The core SHALL NOT depend on any host machinery (HTTP or otherwise); hosts depend on the core, never the reverse.

#### Scenario: In-process embedding
- **WHEN** a test embeds the runtime core directly and drives the identity, connections, data, and sync services
- **THEN** every operation completes without any host process or HTTP surface involved

### Requirement: Identity service creates and links identities
The identity service SHALL create an identity on its first device — minting a placeholder `PdnId` (no key material; a KERI-backed service is the future second implementation) and provisioning its store set: the private-metadata directory and the data namespace, with the data-namespace ticket published in the directory ([device-linking](device-linking.md)). It SHALL mint a linking invite for a hosted identity — the one-time secret and the bearer-free linking payload — and SHALL link this runtime into an existing identity from a scanned linking payload, one explicit linking act per identity; the payload names the identity, and a runtime already hosting it refuses before dialing.

#### Scenario: Create on one runtime, link on another
- **WHEN** an identity is created on runtime A and runtime B links from a linking invite minted on A
- **THEN** B hosts the identity: it appears among B's hosted identities, and the identity's directory and data namespace converge on B

#### Scenario: Linking one identity imports nothing of another
- **WHEN** runtime B is linked into identity X while identity Y exists elsewhere
- **THEN** B hosts X only, and operations addressed to Y on B are refused as unknown

### Requirement: Connections service establishes, lists, and carries grants
The connections service SHALL produce connections through the establishment dialogue — minting invites for a hosted identity and establishing from an invite payload ([connection-establishment](connection-establishment.md)) — and SHALL list a hosted identity's current connections, delegating to the connections records of that identity's [directory](../data-layer/private-metadata-store.md). It SHALL carry data grants over the connection's [metadata pair](../data-layer/connection-metadata-store.md): publishing a grant of the identity's own namespace toward a connected peer — capability-scoped by an exact claim set, naming per claim whether write accompanies read — withdrawing a published grant, and reading the grants a connected peer has published, opening the pair from the directory's tickets on demand, so linked devices reach it too. Manual one-sided recording is not offered: establishment is the producer of connections. Reading a grant yields the capability and the ticket it carries; the grantee runtime acts on that record by itself, so no import act is required of the caller.

A grant SHALL name the granting identity itself as the data issuer; publishing or withdrawing a grant of any other issuer's data SHALL be refused loudly, with nothing minted or written. Granting foreign data is delegation: the serving side evaluates grants from the records of the *data issuer's* own connections, so a grant recorded under a different granting identity could never be honored — without the refusal it would publish successfully, replicate, and enforce as nothing, a silent no-op on both sides. The grant keying by data issuer is untouched — it is the groundwork delegation chains use; the boundary lifts when `UWill` chains make a foreign issuer's grant provable.

(A grant's ticket mode follows its commands as a whole: a grant with no write on any claim ships a read ticket and cannot write at all — no namespace secret — while a grant carrying write on any claim ships a write ticket. The store's capability bounds swarm membership, not access; the read side is enforced by session classification, which serves each session exactly the granted claim set, and the write side is enforced per claim by the ingest gate at the issuer's devices ([capability-gated ingest](../data-layer/capability-gated-ingest.md)).)

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
The data service SHALL write and read entries in a hosted issuer's [data namespace](../data-layer/data-store.md), SHALL list its entries as metadata (no payload bytes; optionally filtered by a path prefix), SHALL share a namespace hosted here as a ticket, and SHALL import a peer's namespace from a ticket obtained out of band: the imported replica stays outside its gossip swarm and is re-served only to the devices of the grant's audience identity, per the locally replicated grant record ([subset reconciliation](../data-layer/subset-reconciliation.md)). A ticket is addressing, not access: an armed issuer serves a caller only per its recorded grants, so an out-of-band ticket with no grant behind it delivers nothing. The sanctioned transport for namespace access between connected identities is the connections service's grant surface above, which the runtime acts on by itself; the import operation remains for a ticket obtained out of band. A write addressed at a granted namespace SHALL be refused up front when the local grant record's write set does not cover the claim — the error arrives at the call site, before the replica is touched. The refusal SHALL rest on a grant this node has actually read: a record whose payload is still replicating says nothing about what it covers, and refusing there would turn a courtesy into a denial of writes the issuer would keep. The enforcement proper is the issuer-side ingest gate, and the writer-side outcome of a bypass is [write retraction](../data-layer/write-retraction.md).

#### Scenario: Write then read locally
- **WHEN** an entry is written under a hosted issuer at a path
- **THEN** reading that issuer and path returns the payload

#### Scenario: Listing yields exactly the written paths
- **WHEN** entries are written at two paths under a hosted issuer
- **THEN** listing that issuer yields exactly those two paths, without payload bytes

#### Scenario: A bare ticket delivers nothing from an armed issuer
- **WHEN** runtime A shares issuer I's namespace as a ticket out of band and runtime B, holding no grant from I, imports it
- **THEN** the import itself succeeds as a local registration, and no entry of I's namespace ever reaches B — A refuses B's sessions as if the replica were not hosted

#### Scenario: A write on a write-granted claim reaches the issuer
- **WHEN** a peer's grant carries write on a claim and the audience runtime writes that claim under the peer's issuer
- **THEN** the issuer's runtime eventually reads the written value, and the audience reads the same value back through its granted view

#### Scenario: A write outside the write set is refused up front
- **WHEN** the audience runtime writes, under the peer's issuer, a claim its grant covers read-only
- **THEN** the operation fails at the call site and the local replica is unchanged

#### Scenario: Unhosted issuer is refused
- **WHEN** a read, write, or list addresses an issuer the runtime neither created nor imported
- **THEN** the operation fails with an unknown-issuer error, and nothing is read, written, or listed

### Requirement: The runtime surfaces retraction verdicts

The runtime SHALL expose a subscription to write-retraction events of its hosted identities: each event names the issuer, the path, the author, the timestamp, the content hash, and the deciding device of one retracted entry, as [write retraction](../data-layer/write-retraction.md) produces them. The subscription is the host's hook for user-facing surfacing; the runtime itself only reports.

#### Scenario: A verdict reaches the subscriber
- **WHEN** a hosted identity's write into a granted namespace is retracted
- **THEN** a subscriber on that runtime observes one event naming the retracted entry's issuer, path, author, timestamp, and content hash

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

The runtime SHALL point a granted replica at the other devices of the identities the grants on it are addressed to, so the replica converges from a sibling while the issuer is unreachable. The contact set SHALL be derived from those identities' directory device records rather than kept beside them, and SHALL be re-derived as the directories change, so a device linked after the namespace was imported is dialed too. Only the directories of hosted identities holding a grant of this issuer SHALL be consulted: the devices of a hosted identity unrelated to the replica — no grant of this issuer names it — SHALL NOT become its contacts.

#### Scenario: A sibling contact is dialed with the issuer offline

- **WHEN** a granted replica is imported on a device whose sibling holds the replica and a live grant record, and every device of the issuer is offline
- **THEN** the replica converges from the sibling

#### Scenario: An unrelated hosted identity's device is not a contact

- **WHEN** a runtime hosts a second identity that holds no grant from the issuer
- **THEN** that identity's devices do not appear among the granted replica's contacts

### Requirement: A granted replica reaches the issuer's other devices

The runtime SHALL point a granted replica at the devices the issuing identity has published in the connection metadata stores of the connections whose grants bind this issuer here, in addition to the addresses the grant's ticket carried and the audience identities' own siblings. The whole contact set SHALL be re-derived from those records as they change, so a device the issuer links later is dialed and one the issuer withdraws leaves the contact set — the publishing device included, since the ticket's addressing is kept only for devices the issuer still publishes.

A grant's ticket names whichever device published the grant, so without this a granted replica has exactly one reachable device of its issuer. The published device set is the issuer's own statement of who acts for it toward this counterparty — the same set the runtime already consults to decide whose writes it may retract — so reaching a sibling asks nothing new of the issuer and reveals nothing the counterparty was not already told. The issuer's own directory is not a source here: it is device-internal and the audience cannot read it.

Leaving the contact set is what this requirement governs. The sync engine keeps its own short record of peers that once served the replica and may redial such a peer until that record ages out, so a withdrawn device's reach is bounded by the re-derived set rather than cut at the very next dial; what any session delivers is governed by classification either way.

The set published by a counterparty SHALL be used only for namespaces that counterparty issues. It is the issuer's device set exactly while the two are the same identity, which the grant surface holds today by refusing to publish a grant of another identity's data; a delegated grant would need the originating issuer's set, and this requirement does not supply it.

One node may host several identities granted by the same issuer; with one namespace per issuer they bind one replica, and the replica's contact set SHALL union every such audience's siblings and every such connection's published issuer devices, rather than carry whichever set the last sweeping identity read. Each connection's records replicate on their own, so their statements of the issuer's device set differ while one lags, and one connection's word taken as the whole set would strip a device the issuer never withdrew. A device therefore leaves the contact set once no connection whose grant binds this issuer publishes it, not at the first withdrawal; while any of them still names the device it stays a route to the one replica, and what a session delivers is governed by classification as ever.

The same union SHALL govern the device set the runtime consults to decide whose writes it may retract, which is per replica for the same reason: a set read from one connection alone would leave a rejection from a device the others publish unhonored, and a provisional write standing that the issuer refused.

#### Scenario: The audience converges from a device that did not publish the grant

- **WHEN** an identity publishes a grant from one of its devices, the granted data reaches its other device by device replication, and the publishing device then goes offline
- **THEN** the audience converges on the granted claims from the other device

#### Scenario: A device published after the grant is dialed too

- **WHEN** the issuing identity links a further device and that device publishes itself in the connection metadata store after the audience already imported the granted replica
- **THEN** the audience's replica comes to count the new device among its contacts, without re-importing and without a new grant

#### Scenario: A withdrawn device stops being a contact

- **WHEN** the issuing identity withdraws a device's published record from every connection whose grant binds this issuer on the audience node
- **THEN** that device is no longer among the granted replica's contacts, while the still-published device remains

#### Scenario: A device withdrawn in one audience's connection stays while another publishes it

- **WHEN** one node hosts two identities granted by the same issuer and the issuer withdraws a device's record from one of the two connections only
- **THEN** that device remains among the replica's contacts, and leaves once the record is withdrawn from the other connection too

#### Scenario: Another counterparty's devices are not contacts

- **WHEN** the audience holds connections with two peers, each granting its own data namespace, and one peer publishes a further device
- **THEN** that device becomes a contact of that peer's granted replica only, and not of the other peer's

#### Scenario: The publishing device is not special

- **WHEN** the grant is published from a device the issuer linked later — the founder never touches the grant surface — and the publishing device then goes offline
- **THEN** the audience converges on the granted claims from the founder

#### Scenario: Audiences hosted together keep both sibling sets

- **WHEN** one node hosts two identities and one issuer grants each of them a claim of its namespace
- **THEN** the one bound replica's contact set holds the issuer's devices and both identities' siblings at once

#### Scenario: A re-grant after withdrawal rebuilds the contacts

- **WHEN** a grant is withdrawn — the audience's binder forgets the namespace — and the issuer grants the same claim anew
- **THEN** the audience converges again, and the fresh import's contact set counts the issuer's other devices as before

### Requirement: Sync service reports the node id and the hosted identities
The sync service SHALL report the runtime's node id (its endpoint id) and the identities the runtime hosts — exactly those created or linked on it.

#### Scenario: Hosted identities follow create and link
- **WHEN** a fresh runtime reports its status, then creates one identity and links another
- **THEN** the report lists no identities first and afterwards exactly those two, with the node id unchanged throughout
