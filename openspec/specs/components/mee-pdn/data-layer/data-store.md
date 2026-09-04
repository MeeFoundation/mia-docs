# Data store

## Purpose

An issuer's data store: the domain role in an identity's store set — alongside the private-metadata directory — holding all entries the issuer emits — each entry the stored form of one [claim](../../../architecture/language/claim.md) the issuer makes; this layer sees a path and an opaque payload, and the claim semantics live above. The role is implemented as the issuer's single pdn-store namespace ([namespace-addressing.md](../pdn-node/namespace-addressing.md)): "data store" names the role, and below `data-layer` the word namespace keeps its mechanical meaning — the replication unit and gossip topic. A person's *personal datastore* ([north-star.md](../../../north-star.md)) is, in these terms, the union of the data stores and private stores of that person's identities across their devices. Read access is classified per session — own devices whole, grantees per their recorded grants, other callers refused ([subset reconciliation](subset-reconciliation.md)); write access is gated per session too — the ingest hook (ADR-0008) admits a synced entry into a hosted issuer's replica only from that issuer's own devices or, per claim, per the sender's recorded write grant ([capability-gated ingest](capability-gated-ingest.md)). The namespace secret still travels to a write-granted audience as the entry-signing material — author keys are node-local, not identity-bound, until UWill — so a write outside the granted claims is producible but refused at the issuer and then retracted at the writer ([write retraction](write-retraction.md)). Deleting an entry is deliberately absent at this stage. A device of the identity obtains the data store through the linking reply, which carries a fresh write ticket next to the directory's ([device-linking.md](../pdn-node/device-linking.md)); handover to anyone else stays an explicit ticket act.

## Requirements

### Requirement: Operations are addressed by issuer
Writing, reading, listing, and sharing SHALL address a data store by its issuer's `PdnId`; the node resolves the issuer to the backing replica registered at creation or import. Addressing an issuer with no created or imported data store on the node SHALL be an error distinguishable from transport and storage failures.

#### Scenario: Write and read under an issuer
- **WHEN** an entry is written under an issuer and read back under the same issuer
- **THEN** the written payload is returned

#### Scenario: Unknown issuer is a distinguishable error
- **WHEN** a read or a listing addresses an issuer with no data store on this node
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

### Requirement: Entries are enumerable as metadata
An issuer's entries SHALL be enumerable as entry metadata — issuer, path, and payload length, no payload bytes — optionally filtered to paths whose leading components equal a given prefix path's components (prefix queries stand on the component structure of `EntryPath`, not on byte prefixes). Enumeration is record-level, consistent with record-first reads: an entry SHALL appear once its record is stored, whether or not its payload has been fetched yet.

#### Scenario: Listing returns metadata for all entries
- **WHEN** entries are written at several paths under an issuer
- **THEN** listing that issuer yields exactly those paths as metadata, with no payload bytes

#### Scenario: Prefix narrows the listing by whole components
- **WHEN** entries exist at `contact/email`, `contact/phone`, `contacts/emergency`, and `banking/iban`, and the listing is filtered by the prefix `contact`
- **THEN** exactly `contact/email` and `contact/phone` are yielded

### Requirement: Mutations replicate between devices
Writes performed on one device SHALL become visible on every device holding the replica through standard pdn-store sync (set reconciliation for catch-up, gossip for live updates within the replica's [swarm](../../../architecture/language/swarm.md)), with no additional transport or server.

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

### Requirement: A registered data namespace can be forgotten
Registering a data store under an issuer SHALL have a counterpart: forgetting an issuer's data namespace stops reconciling its replica, drops it, and removes the issuer's registration together — so operations addressed to that issuer afterwards fail with the unknown-issuer error, exactly as before the import, rather than resolving to a dropped replica. Dropping the replica without removing the registration is not sufficient and SHALL NOT be the surface offered: the issuer would still resolve, and its operations would fail as storage errors instead of the distinguishable refusal this store's addressing requirement mandates.

Forgetting an issuer is not, however, the rollback of an import: an issuer can already be bound when an import runs, and forgetting would then delete a replica that import never brought up — permanently, since dropping takes the entries with it. An import SHALL therefore report what it did, and be undoable by that report alone: undoing an import that bound a free issuer forgets the namespace, and undoing one that replaced an existing binding restores that binding, dropping the imported replica only when it is not the one the restored binding names. A rollback SHALL NOT destroy state that predates the act it rolls back. This is the rollback path for an import that must not survive the operation that made it ([device-linking](../pdn-node/device-linking.md)).

#### Scenario: Forgetting a namespace unregisters its issuer
- **WHEN** a node imports the data namespace of an issuer, then forgets it
- **THEN** the replica is no longer reconciled, and reading, writing, or listing under that issuer fails with the unknown-issuer error

#### Scenario: Undoing an import that replaced a binding restores it
- **WHEN** a node already bound to an issuer's namespace imports under that same issuer, and the import is then undone
- **THEN** the earlier binding resolves again and its entries are still readable — the undo restored it rather than forgetting the issuer

#### Scenario: Forgetting one issuer leaves the others addressable
- **WHEN** a node hosts the data namespaces of two issuers and forgets one
- **THEN** the other issuer's entries remain readable under its own `PdnId`
