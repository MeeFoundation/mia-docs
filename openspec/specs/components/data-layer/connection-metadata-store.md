# Connection metadata store

## Purpose

The cross-identity channel of a [connection](../../architecture/language/connection.md): for each connection there are two of these stores, one per direction. The store issued by identity A toward its counterparty B carries A's grants to B — whole-store tickets and capability-scoped read grants — and A's published device set, written only by A's devices and read, whole, by B's devices (Invariant 3). The mechanism is the one the private-metadata directory already uses: a dedicated pdn-store replica gated by ticket possession — no new sync machinery, and no domain `NamespaceId`. In code the pair at one side is `ConnectionMetadata { own, peer }`: `own` the replica this side issues, `peer` the counterpart's. The counterparty is the audience of the whole replica, so no per-entry filtering applies inside it — filtered reconciliation ([subset reconciliation](subset-reconciliation.md)) matters for the data stores grants point at, not here. Establishment ([connection-establishment](../pdn-node/connection-establishment.md)) creates and exchanges these stores; the [private-metadata directory](private-metadata-store.md) carries their tickets to each identity's other devices.

## Requirements

### Requirement: Each direction of a connection lives in a dedicated replica
A connection between identities A and B SHALL be served by two dedicated pdn-store replicas: one issued by A toward B and one issued by B toward A. Each SHALL be separate from every data store, from the private-metadata directory, and from every other connection's metadata stores; no domain `NamespaceId` is allocated — the store handle returned at creation or import is how the replica is addressed. Metadata stores of several connections and several identities SHALL coexist on one node without sharing a replica.

#### Scenario: Creating the store allocates a dedicated replica
- **WHEN** a node creates a connection metadata store
- **THEN** a fresh pdn-store replica is created for it, reached through the returned store handle, and no domain `NamespaceId` is allocated

#### Scenario: The two directions are distinct replicas
- **WHEN** a connection between A and B is assembled
- **THEN** the store issued by A toward B and the store issued by B toward A are two distinct replicas, and an entry written in one never appears in the other

#### Scenario: One identity's connections do not share a replica
- **WHEN** identity A holds connections to B and to C
- **THEN** A's store toward B and A's store toward C are two distinct replicas, and a grant written toward B is invisible in the store toward C

### Requirement: The pair assembles as own plus peer
At each side of a connection the metadata pair SHALL consist of `own` — the replica this identity issues, created by it — and `peer` — the counterpart's replica, imported from the read ticket received at establishment. The same replica is `own` at its issuer and `peer` at the counterparty: entries written into `own` SHALL become readable in the counterpart's `peer` through standard pdn-store sync. Importing the read ticket SHALL bind the local replica to the issuing namespace immediately — the pair is structurally complete when assembly ends, and `peer`'s content converges asynchronously.

#### Scenario: A write to own is read from the counterpart's peer
- **WHEN** identity A writes a grant entry into its `own` store toward B
- **THEN** B eventually reads that entry in its `peer` store of the same connection

#### Scenario: Import binds before content arrives
- **WHEN** B imports A's read ticket as its `peer`
- **THEN** the store handle is usable at once, reads return absent until sync delivers content, and later reads return the synced entries

### Requirement: The issuer writes; the counterparty reads the whole store; others observe nothing
Write access SHALL be bounded by the store's write ticket, which circulates only through the issuing identity's private-metadata directory — so only the issuer's devices write. Read access SHALL be bounded by the read ticket handed to the counterparty at establishment; the counterparty reads the replica whole — it is the store's entire audience, and no per-entry filtering applies inside it. The replica's namespace identifier and tickets SHALL travel nowhere beyond the establishment dialogue and the two identities' directories, so to any other party the store is not observable — its existence included. (Tickets are bearer tokens today, as in Invariant 1; identity-bound access lands with UWill.)

#### Scenario: A linked device of the issuer writes a grant
- **WHEN** the issuer's second device opens `own` from the directory's write ticket and writes a grant entry
- **THEN** the write succeeds and the counterparty eventually reads the entry

#### Scenario: The counterparty cannot write
- **WHEN** the counterparty, holding only the read ticket, attempts to write an entry into its `peer` store
- **THEN** the write is refused and no entry is created in the replica

#### Scenario: A third identity observes nothing
- **WHEN** identity C is itself connected to A while A also holds a connection to B
- **THEN** C's node holds no replica of A's store toward B and no ticket to it, and nothing readable by C reveals that the store exists

### Requirement: Grants are keyed by data-store issuer
A grant SHALL live as one record at `grants/<issuer-hex>` (64 lowercase hex chars of the granted data store's issuer `PdnId`), whose payload names its own width explicitly: the interim whole-store grant — the data store's ticket alone — or a capability-scoped grant carrying the capability and its ticket together. In one directional store at most one grant of one width SHALL exist per issuer at any moment: publishing either width replaces the record wholesale, and withdrawal SHALL be one tombstone over that one record — so no ordering of separate entries, locally or across replicating devices, can ever expose a wider grant than the last one published. A grant record that is absent, whose payload has not yet replicated, or whose payload a build cannot decode SHALL be treated as no grant — width is never inferred from absence or from partial state. The whole-store grant's ticket is a write ticket (the store's capability bounds swarm membership, not access — read and write are the capability mechanism's to state); a scoped grant's ticket mode follows its commands. Capability payloads inside the record SHALL be treated as opaque bytes at this layer.

#### Scenario: A grant round-trips
- **WHEN** the issuer publishes a grant carrying a data-store ticket and the counterparty reads it after sync
- **THEN** the ticket read equals the ticket published, keyed by the data store's issuer

#### Scenario: A grant published later needs no new pairing
- **WHEN** establishment completed earlier and the issuer publishes a new grant into `own`
- **THEN** the counterparty reads it from `peer` without any further pairing dialogue

#### Scenario: Publishing the other width replaces the record wholesale
- **WHEN** a scoped grant for an issuer is followed by a whole-store grant for the same issuer, or the reverse
- **THEN** the counterparty eventually reads exactly the later grant's width, and the earlier record is gone — no stale capability or ticket survives beside the new record to mask it

#### Scenario: Withdrawal is one act whatever the width
- **WHEN** the issuer withdraws the grant for an issuer
- **THEN** one tombstone removes it; the issuer's own book reads it as absent at once, the counterparty eventually reads no grant of either width, and at no intermediate state does either side read a grant wider than the last published record

### Requirement: Each side publishes its device set into its directional store

An identity SHALL publish the node ids of its devices as `devices/<node-id-hex>` records in every connection-metadata store it issues, with the directory's device-record semantics (marker payload, LWW, tombstone on revocation), and SHALL keep them current as devices are linked and revoked — so the counterparty can resolve a transport-authenticated node id to this identity. The identity is authoritative over its own device set; the records widen no access beyond what the connection already grants.

Publication on opening the pair SHALL be assert-once: a device asserts its record only when the set carries no record of it at all — a live record is left untouched, and a *withdrawn* record (tombstone) is never re-asserted as a side effect of opening. Re-asserting a withdrawn device is a deliberate publication act, distinct from opening. Without this, every pair opening would re-sign the record with a fresh wall-clock timestamp, and a revoked-but-still-running device would out-bid any tombstone the moment it next touched the connection. Revoking the *ability to write* is deferred, recorded in the design (subset-rbsr D9).

#### Scenario: Devices published at establishment

- **WHEN** a connection is established
- **THEN** each side's own store carries a `devices/<node-id-hex>` record for each of that identity's devices

#### Scenario: Linking propagates to every connection

- **WHEN** an identity links a new device
- **THEN** a `devices/<node-id-hex>` record for it appears in the own store of every connection of that identity, and the counterparty can then classify calls from that device

#### Scenario: A foreign device is not resolvable

- **WHEN** a node id appears in no connection's published device set and no directory of the serving node's identities
- **THEN** the serving node resolves it to no identity, and the caller is treated as a stranger

#### Scenario: Opening a pair does not resurrect a withdrawn device

- **WHEN** a device's record is withdrawn and that device — or any machinery on its node — opens the pair again
- **THEN** the record stays withdrawn; only a deliberate publication act re-asserts it

### Requirement: Grant reads wait for content
Reading a grant SHALL return it only once its payload bytes have arrived: an entry whose record has synced but whose payload has not SHALL read as absent, and a later read (after the payload lands) SHALL return the grant. Entry records and payloads travel independently; consumers poll, as they do for the directory's tickets.

#### Scenario: Record without payload reads as absent
- **WHEN** a grant entry's record has synced to the counterparty but its payload bytes have not yet been fetched
- **THEN** reading that grant returns absent, and a later read returns the grant

### Requirement: Mutations replicate across both identities' devices
Entries written into `own` on one of the issuer's devices SHALL become visible on the issuer's other devices (each holding `own` through the directory's write ticket) and on the counterparty's devices (each holding `peer` through the directory's read ticket) via standard pdn-store sync, with no additional transport.

#### Scenario: Written on the issuer's phone, read on the counterparty's laptop
- **WHEN** the issuer's phone writes a grant while the issuer's laptop and the counterparty's two devices hold the pair from their directories
- **THEN** the issuer's laptop and both of the counterparty's devices eventually read the grant

### Requirement: Concurrent edits resolve by last-writer-wins
Concurrent writes to the same key from different devices of the issuer SHALL resolve on every replica to the entry with the newest timestamp (pdn-store per-key last-writer-wins across authors), with equal timestamps broken deterministically by content hash.

#### Scenario: Concurrent grant updates converge
- **WHEN** two devices of the issuer concurrently update the same grant key and then sync
- **THEN** every device of both identities resolves to the same single entry
