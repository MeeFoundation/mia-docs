# pdn-node: runtime core

The connections service reads the grants a peer published and offers no way to read the grants the identity published itself. A host can therefore show a person what others share with them and not what they share with others, which leaves the withdrawal of a grant as an act with nothing to name — and leaves the one question a person asks of a sovereignty product, "what am I sharing right now", answerable only from what a host happens to remember publishing, which is wrong on a second device and stale after a sibling withdraws.

The right to the reading is [Invariant 3](invariants.md): a connection metadata store is written only by its issuing identity's devices, and read by those devices and the counterparty's. Every device of the identity already holds the instrument as well — the pairing ceremony publishes the own-side store's write ticket in the identity's directory under its own kind, so a device that replicated the directory opens that store without asking anyone. The operation exposes nothing that was not already the identity's to read.

## MODIFIED Requirements

### Requirement: Connections service establishes, lists, and carries grants
The connections service SHALL produce connections through the establishment dialogue — minting invites for a hosted identity and establishing from an invite payload ([connection-establishment](connection-establishment.md)) — and SHALL list a hosted identity's current connections, delegating to the connections records of that identity's [directory](../data-layer/private-metadata-store.md). It SHALL carry data grants over the connection's [metadata pair](../data-layer/connection-metadata-store.md): publishing a grant of the identity's own namespace toward a connected peer — capability-scoped by an exact claim set, naming per claim whether write accompanies read — withdrawing a published grant, reading the grants a connected peer has published, and reading the grants the identity has published toward a connected peer, opening the pair from the directory's tickets on demand, so linked devices reach it too. Manual one-sided recording is not offered: establishment is the producer of connections. Reading a peer's grant yields the capability and the ticket it carries; the grantee runtime acts on that record by itself, so no import act is required of the caller. Reading the identity's own published grant yields the capability alone: the caller is the issuer of the namespace the record addresses, so a ticket to it answers nothing.

Both reads SHALL report what is readable at the moment of the call and SHALL NOT wait for a record to arrive. A grant published on one device of an identity reaches that identity's other devices by replication of the pair, so a device that did not publish a grant reads it once the record and its payload have arrived, and reads nothing before then — the same waiting a peer does, for the same reason. Neither read is free of writes: opening a pair publishes the opening device's record into it and registers the connection, so "reports what is readable now" means the call does not wait and changes no grant, not that it writes nothing.

Both reads answer for the device they run on, and SHALL be described that way wherever a caller reads about them. The read reports what this device holds in the pair's replicas: on the device that published a grant it is evidence the record is here, never that it reached a sibling or the peer, and no read reports what the counterparty has received. Nothing on this surface carries that answer, which would need a per-peer synchronization progress out of the engine or an acknowledgement a sibling writes into the pair.

An empty answer therefore covers four states and SHALL NOT be presented as the fact that nothing is granted: this identity holds no connection to that peer, the pair's tickets have not replicated to this device yet, a grant record is here whose payload cannot be read yet, and nothing is granted toward that peer. The peer-side read answers the same way for the same reason, and refusing wherever no pair opens would turn a linked device's catching-up into failures rather than into an answer that changes when the directory arrives.

Both reads SHALL resolve the pair through the acting identity's own directory. An identity hosted beside another therefore reaches only its own pairs, and a third party on another node reaches none of them at all: the pair's stores are addressed by the tickets the two sides exchanged, and only those two sides hold them.

A grant SHALL name the granting identity itself as the data issuer; publishing or withdrawing a grant of any other issuer's data SHALL be refused loudly, with nothing minted or written. Granting foreign data is delegation: the serving side evaluates grants from the records of the *data issuer's* own connections, so a grant recorded under a different granting identity could never be honored — without the refusal it would publish successfully, replicate, and enforce as nothing, a silent no-op on both sides. The grant keying by data issuer is untouched — it is the groundwork delegation chains use; the boundary lifts when `UWill` chains make a foreign issuer's grant provable.

(A grant's ticket mode follows its commands as a whole: a grant with no write on any claim ships a read ticket and cannot write at all — no namespace secret — while a grant carrying write on any claim ships a write ticket. The store's capability bounds swarm membership, not access; the read side is enforced by session classification, which serves each session exactly the granted claim set, and the write side is enforced per claim by the ingest gate at the issuer's devices ([capability-gated ingest](../data-layer/capability-gated-ingest.md)).)

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
