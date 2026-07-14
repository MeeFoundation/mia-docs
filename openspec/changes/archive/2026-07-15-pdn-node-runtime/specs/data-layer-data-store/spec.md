# Data store: entry listing

The runtime's data service needs enumeration; the data store gains listing as an issuer-addressed operation returning entry metadata, shaped after the `DataLayer` trait's `list_entries` so the later switch onto the trait stays mechanical.

## MODIFIED Requirements

### Requirement: Operations are addressed by issuer
Writing, reading, listing, and sharing SHALL address a data store by its issuer's `PdnId`; the node resolves the issuer to the backing replica registered at creation or import. Addressing an issuer with no created or imported data store on the node SHALL be an error distinguishable from transport and storage failures.

#### Scenario: Write and read under an issuer
- **WHEN** an entry is written under an issuer and read back under the same issuer
- **THEN** the written payload is returned

#### Scenario: Unknown issuer is a distinguishable error
- **WHEN** a read or a listing addresses an issuer with no data store on this node
- **THEN** the operation fails with the unknown-issuer error, not a generic failure

## ADDED Requirements

### Requirement: Entries are enumerable as metadata
An issuer's entries SHALL be enumerable as entry metadata — issuer, path, and payload length, no payload bytes — optionally filtered to paths whose leading components equal a given prefix path's components (prefix queries stand on the component structure of `EntryPath`, not on byte prefixes). Enumeration is record-level, consistent with record-first reads: an entry SHALL appear once its record is stored, whether or not its payload has been fetched yet.

#### Scenario: Listing returns metadata for all entries
- **WHEN** entries are written at several paths under an issuer
- **THEN** listing that issuer yields exactly those paths as metadata, with no payload bytes

#### Scenario: Prefix narrows the listing by whole components
- **WHEN** entries exist at `contacts/a`, `contacts/b`, `contactsx/c`, and `profile/name`, and the listing is filtered by the prefix `contacts`
- **THEN** exactly `contacts/a` and `contacts/b` are yielded
