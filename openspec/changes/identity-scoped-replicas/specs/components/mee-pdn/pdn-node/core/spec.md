# pdn-node: core — delta for identity-scoped-replicas

## MODIFIED Requirements

### Requirement: Data service writes, reads, lists, and imports granted namespaces
Every data operation SHALL name the identity performing it, and SHALL act in that identity's scope alone. The data service SHALL write and read entries in a hosted issuer's [data namespace](../../data-layer/data-store/spec.md), SHALL list its entries as metadata (no payload bytes; optionally filtered by a path prefix), SHALL share a namespace hosted here as a ticket, and SHALL import a peer's namespace from a ticket obtained out of band into the named identity's scope: the imported replica stays outside its gossip swarm and is re-served only to the devices of the grant's audience identity, per the locally replicated grant record ([subset reconciliation](../../data-layer/subset-reconciliation/spec.md)). A ticket is addressing, not access: an armed issuer serves a caller only per its recorded grants, so an out-of-band ticket with no grant behind it delivers nothing. The sanctioned transport for namespace access between connected identities is the connections service's grant surface above, which the runtime acts on by itself; the import operation remains for a ticket obtained out of band. A write addressed at a granted namespace SHALL be refused up front when the local grant record's write set does not cover the claim — the error arrives at the call site, before the replica is touched. The refusal SHALL rest on a grant this node has actually read: a record whose payload is still replicating says nothing about what it covers, and refusing there would turn a courtesy into a denial of writes the issuer would keep. The enforcement proper is the issuer-side ingest gate, and the writer-side outcome of a bypass is [write retraction](../../data-layer/write-retraction/spec.md).

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
- **THEN** the import itself succeeds as a local registration in that identity's scope, and no entry of I's namespace ever reaches B — A refuses B's sessions as if the replica were not hosted

#### Scenario: A write on a write-granted claim reaches the issuer
- **WHEN** a peer's grant carries write on a claim and the audience identity writes that claim under the peer's issuer
- **THEN** the issuer's runtime eventually reads the written value, and the audience reads the same value back through its granted view

#### Scenario: A write outside the write set is refused up front
- **WHEN** the audience identity writes, under the peer's issuer, a claim its grant covers read-only
- **THEN** the operation fails at the call site and the local replica is unchanged

#### Scenario: Unhosted issuer is refused
- **WHEN** a read, write, or list names an identity and an issuer that identity neither created nor imported
- **THEN** the operation fails with an unknown-issuer error, and nothing is read, written, or listed

### Requirement: A granted replica's sibling contacts follow the audience directory

The runtime SHALL point a granted replica at the other devices of the identity whose scope holds it, so the replica converges from a sibling while the issuer is unreachable. The contact set SHALL be derived from that identity's directory device records rather than kept beside them, and SHALL be re-derived as the directory changes, so a device linked after the namespace was imported is dialed too. The directory of any other hosted identity SHALL NOT be consulted for this replica, whether that identity holds a grant of the same issuer or none at all.

#### Scenario: A sibling contact is dialed with the issuer offline

- **WHEN** a granted replica is imported on a device whose sibling holds the replica and a live grant record, and every device of the issuer is offline
- **THEN** the replica converges from the sibling

#### Scenario: An unrelated hosted identity's device is not a contact

- **WHEN** a runtime hosts a second identity that holds no grant from the issuer
- **THEN** that identity's devices do not appear among the granted replica's contacts

#### Scenario: A co-located audience's devices are not contacts either

- **WHEN** a runtime hosts a second identity granted by the same issuer, holding a replica of its own
- **THEN** each replica's contacts are its own identity's devices and the issuer devices its own connection publishes

## ADDED Requirements

### Requirement: A granted replica reaches the issuer devices its own connection publishes

The runtime SHALL point a granted replica at the devices the issuing identity has published in the connection metadata store of the connection whose grant bound this replica, in addition to the addresses the grant's ticket carried and the holding identity's own siblings. The whole contact set SHALL be re-derived from those records as they change, so a device the issuer links later is dialed and one the issuer withdraws leaves the contact set — the publishing device included, since the ticket's addressing is kept only for devices the issuer still publishes.

A grant's ticket names whichever device published the grant, so without this a granted replica has exactly one reachable device of its issuer. The published device set is the issuer's own statement of who acts for it toward this counterparty — the same set the runtime already consults to decide whose writes it may retract — so reaching a sibling asks nothing new of the issuer and reveals nothing the counterparty was not already told. The issuer's own directory is not a source here: it is device-internal and the audience cannot read it.

Leaving the contact set is what this requirement governs. The sync engine keeps its own short record of peers that once served the replica and may redial such a peer until that record ages out, so a withdrawn device's reach is bounded by the re-derived set rather than cut at the very next dial; what any session delivers is governed by classification either way.

The set published by a counterparty SHALL be used only for namespaces that counterparty issues. It is the issuer's device set exactly while the two are the same identity, which the grant surface holds today by refusing to publish a grant of another identity's data; a delegated grant would need the originating issuer's set, and this requirement does not supply it.

One node may host several identities granted by the same issuer, and each holds a replica in its own scope: the contact set of each SHALL come from that identity's own connection alone, and the device set the runtime consults to decide whose writes it may retract SHALL be read from the same one connection. A withdrawal a counterparty publishes toward one identity therefore governs that identity's replica and leaves the co-located one as it was.

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

## REMOVED Requirements

### Requirement: A granted replica reaches the issuer's other devices
**Reason**: With a replica per scope, the contact set of a granted replica is its own connection's, so the requirement's union across every co-hosted audience's connections describes a replica that no longer exists.
**Migration**: The same reachability, stated per scope, is "A granted replica reaches the issuer devices its own connection publishes"; a node that held one replica for several audiences holds one per audience, each dialing the devices its own connection publishes.
