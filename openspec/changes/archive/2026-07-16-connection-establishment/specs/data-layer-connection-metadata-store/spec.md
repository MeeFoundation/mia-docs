# Connection metadata store

The cross-identity channel of a [connection](../../architecture/language/connection.md): for each connection there are two of these stores, one per direction. The store issued by identity A toward its counterparty B carries A's grants to B — tickets to data stores, and read capabilities once those exist — written only by A's devices and read, whole, by B's devices (Invariant 3). The mechanism is the one the other device stores already use: a dedicated pdn-store replica gated by ticket possession — no new sync machinery, and no domain `NamespaceId`. In code the pair at one side is `ConnectionMetadata { own, peer }`: `own` the replica this side issues, `peer` the counterpart's. The counterparty is the audience of the whole replica, so no per-entry filtering applies inside it — filtered reconciliation (subset-rbsr) matters for the data stores grants point at, not here. Establishment ([connection-establishment](../pdn-node/connection-establishment.md)) creates and exchanges these stores; the [private-metadata directory](private-metadata-store.md) carries their tickets to each identity's other devices.

## ADDED Requirements

### Requirement: Each direction of a connection lives in a dedicated replica
A connection between identities A and B SHALL be served by two dedicated pdn-store replicas: one issued by A toward B and one issued by B toward A. Each SHALL be separate from every data store, from the device stores (connections store, private-metadata directory), and from every other connection's metadata stores; no domain `NamespaceId` is allocated — the store handle returned at creation or import is how the replica is addressed. Metadata stores of several connections and several identities SHALL coexist on one node without sharing a replica.

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
A grant SHALL live under the key prefix `grants/<issuer-hex>` (64 lowercase hex chars of the granted data store's issuer `PdnId`): the ticket to that issuer's data store at `grants/<issuer-hex>/ticket`, and the read capability at `grants/<issuer-hex>/cap` — a reserved slot, unwritten until the read-capability mechanism lands. The interim grant is the whole-store ticket alone. Capability payloads SHALL be treated as opaque bytes at this layer.

#### Scenario: A grant round-trips
- **WHEN** the issuer publishes a grant carrying a data-store ticket and the counterparty reads it after sync
- **THEN** the ticket read equals the ticket published, keyed by the data store's issuer

#### Scenario: A grant published later needs no new pairing
- **WHEN** establishment completed earlier and the issuer publishes a new grant into `own`
- **THEN** the counterparty reads it from `peer` without any further pairing dialogue

#### Scenario: A withdrawn grant reads as absent
- **WHEN** the issuer deletes a grant entry from `own`
- **THEN** the counterparty eventually reads that grant as absent (withdrawal of the entry replicates; whether previously delivered data is retained is outside this store — Invariant 2 governs acquisition, not retention)

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
