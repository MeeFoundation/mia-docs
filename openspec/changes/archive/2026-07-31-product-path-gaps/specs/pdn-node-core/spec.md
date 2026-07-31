# pdn-node: runtime core

A granted replica today knows two kinds of contact: whatever addresses rode in the grant's ticket, and the audience identity's own devices. The first is one device — whichever called publish — so the issuer's other devices are reachable to nobody, and a grant published from a phone goes dark with that phone. This delta gives the replica the issuer's device set, which the issuer already publishes to this very audience. The sibling-contacts requirement is modified in one clause: two hosted identities granted by the same issuer bind one replica, so its contact set consults every such audience's directory — consulting only one would have each identity's sweep strip the other's siblings. The issuer's device set is unioned across those audiences' connections for the same reason, and so is the device set the retraction tracker follows, which is keyed by the same shared replica.

## MODIFIED Requirements

### Requirement: A granted replica's sibling contacts follow the audience directory

The runtime SHALL point a granted replica at the other devices of the identities the grants on it are addressed to, so the replica converges from a sibling while the issuer is unreachable. The contact set SHALL be derived from those identities' directory device records rather than kept beside them, and SHALL be re-derived as the directories change, so a device linked after the namespace was imported is dialed too. Only the directories of hosted identities holding a grant of this issuer SHALL be consulted: the devices of a hosted identity unrelated to the replica — no grant of this issuer names it — SHALL NOT become its contacts.

#### Scenario: A sibling contact is dialed with the issuer offline

- **WHEN** a granted replica is imported on a device whose sibling holds the replica and a live grant record, and every device of the issuer is offline
- **THEN** the replica converges from the sibling

#### Scenario: An unrelated hosted identity's device is not a contact

- **WHEN** a runtime hosts a second identity that holds no grant from the issuer
- **THEN** that identity's devices do not appear among the granted replica's contacts

## ADDED Requirements

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
