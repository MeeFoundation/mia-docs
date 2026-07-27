# Delta: pdn-node-core

## MODIFIED Requirements

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

#### Scenario: A mixed grant crosses as one record

- **WHEN** X publishes one grant toward P naming one claim read-only and another claim read-write
- **THEN** P's runtime reads one capability covering both claims, carrying write on exactly the second

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

#### Scenario: A write on a write-granted claim reaches the issuer

- **WHEN** a peer's grant carries write on a claim and the audience runtime writes that claim under the peer's issuer
- **THEN** the issuer's runtime eventually reads the written value, and the audience reads the same value back through its granted view

#### Scenario: A write outside the write set is refused up front

- **WHEN** the audience runtime writes, under the peer's issuer, a claim its grant covers read-only
- **THEN** the operation fails at the call site and the local replica is unchanged

#### Scenario: A bare ticket delivers nothing from an armed issuer

- **WHEN** runtime A shares issuer I's namespace as a ticket out of band and runtime B, holding no grant from I, imports it
- **THEN** the import itself succeeds as a local registration, and no entry of I's namespace ever reaches B — A refuses B's sessions as if the replica were not hosted

#### Scenario: Unhosted issuer is refused

- **WHEN** a read, write, or list addresses an issuer the runtime neither created nor imported
- **THEN** the operation fails with an unknown-issuer error, and nothing is read, written, or listed

## ADDED Requirements

### Requirement: The runtime surfaces retraction verdicts

The runtime SHALL expose a subscription to write-retraction events of its hosted identities: each event names the issuer, the path, the author, the timestamp, the content hash, and the deciding device of one retracted entry, as [write retraction](../data-layer/write-retraction.md) produces them. The subscription is the host's hook for user-facing surfacing; the runtime itself only reports.

#### Scenario: A verdict reaches the subscriber

- **WHEN** a hosted identity's write into a granted namespace is retracted
- **THEN** a subscriber on that runtime observes one event naming the retracted entry's issuer, path, author, timestamp, and content hash
