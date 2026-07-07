# Data store

## Purpose

An issuer's data store: the domain role in an identity's store set — alongside the connections store and the private metadata store — holding all entries the issuer emits. The role is implemented as the issuer's single pdn-store namespace ([namespace-addressing.md](../pdn-node/namespace-addressing.md)): "data store" names the role, and below `data-layer` the word namespace keeps its mechanical meaning — the replication unit and gossip topic. A person's *personal datastore* ([north-star.md](../../north-star.md)) is, in these terms, the union of the data stores and private stores of that person's identities across their devices. Access is bounded by possession of the replica's ticket until subset-rbsr and UWill land ([multi-identity.md](multi-identity.md)), and author keys are node-local, not identity-bound, until UWill. Two operations are deliberately absent at this stage: deleting an entry, and discovering data stores during device linking (deferred — ADR-0009; tickets are handed over explicitly).

## Requirements

### Requirement: Operations are addressed by issuer
Writing, reading, and sharing SHALL address a data store by its issuer's `PdnId`; the node resolves the issuer to the backing replica registered at creation or import. Addressing an issuer with no created or imported data store on the node SHALL be an error distinguishable from transport and storage failures.

#### Scenario: Write and read under an issuer
- **WHEN** an entry is written under an issuer and read back under the same issuer
- **THEN** the written payload is returned

#### Scenario: Unknown issuer is a distinguishable error
- **WHEN** a read addresses an issuer with no data store on this node
- **THEN** the operation fails with the unknown-issuer error, not a generic failure

### Requirement: Entries are opaque payloads at validated paths
An entry SHALL live at an `EntryPath`: a non-empty, slash-separated path of at most 16 components, each between 1 and 256 bytes. The path structure and its bounds are a `data-layer` contract, not an inherited one — the underlying pdn-store key is arbitrary bytes. The two halves of the contract have different weight. The component structure (non-empty, slash-separated) is load-bearing: prefix queries stand on it. The numeric bounds are carried over unchanged from the single-device prototype and only keep sync messages predictably sized; they MAY be raised or dropped at will — keys replicate as raw bytes, so nodes with different bounds still sync — while lowering them becomes a breaking migration once data exists. The payload SHALL be treated as opaque bytes by `data-layer` — interpretation belongs to the layers above. An empty payload is not representable as a stored value: pdn-store reserves zero-length entries as its deletion marker (a convention inherited from iroh-docs), hides them from reads, and rejects writing one — a zero-length write SHALL fail, storing nothing and deleting nothing. "Present but empty" SHALL be encoded by the layers above through a non-empty representation; a deletion operation remains absent from this layer's surface.

#### Scenario: A valid path round-trips
- **WHEN** an entry is written at a multi-component path within the bounds
- **THEN** it is readable at exactly that path

#### Scenario: An invalid path is rejected at construction
- **WHEN** a path is empty, has an empty component, or exceeds the component bounds
- **THEN** `EntryPath` construction fails and no write is attempted

#### Scenario: An empty-payload write is rejected
- **WHEN** a zero-length payload is written at some path
- **THEN** the write fails, and a value previously stored at that path survives unchanged

### Requirement: Reads become available record-first
Reading an entry SHALL return its payload only once the payload bytes have arrived: an entry whose record has synced but whose payload has not yet been fetched SHALL read as absent. Entry records and payloads travel independently, so "stored" precedes "readable"; consumers poll until the payload lands.

#### Scenario: Record without payload reads as absent
- **WHEN** an entry's record has synced to a device but its payload bytes have not yet been fetched
- **THEN** reading it returns absent, and a later read (after the payload arrives) returns the payload

### Requirement: Mutations replicate between devices
Writes performed on one device SHALL become visible on every device holding the replica through standard pdn-store sync (set reconciliation for catch-up, gossip for live updates within the replica's [swarm](../../architecture/language/swarm.md)), with no additional transport or server.

#### Scenario: Pre-import write catches up
- **WHEN** an entry is written before another device imports the data store
- **THEN** the importing device eventually reads it

#### Scenario: Post-import write arrives live
- **WHEN** an entry is written after the importing device has joined the replica's sync (gossip) swarm
- **THEN** the other device eventually reads it

### Requirement: Concurrent writes converge
Concurrent writes to the same path on different devices SHALL resolve on every device to the entry with the newest timestamp (pdn-store per-key LWW across authors), with equal timestamps broken deterministically by content hash — so all devices converge to the same value, which is one of the written values.

#### Scenario: Contested path converges
- **WHEN** two devices write different payloads at the same path with no coordination and then sync
- **THEN** both devices eventually read the same payload, and it is one of the two written

### Requirement: The data store is shared by ticket
A data store SHALL be shareable as a ticket, and importing that ticket SHALL register the replica under the issuer on the importing node, joining it into the replica's sync. A write ticket admits writing through any local author; a read ticket admits replication only.

#### Scenario: Import joins the replica
- **WHEN** a node imports a data store from its ticket under the issuer
- **THEN** subsequent reads under that issuer on that node observe the replica's entries as they sync
