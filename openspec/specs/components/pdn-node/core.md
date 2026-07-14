# Runtime core

## Purpose

The embeddable runtime core: identity, connections, data, and sync services as thin glue over `data-layer`. Each embedded runtime is one running node — a host embeds one, and in-process tests embed several to stand up several nodes; one runtime hosts any number of identities (per data-layer [multi-identity](../data-layer/multi-identity.md)), each added by an explicit act. The core adds no sync or authorization mechanics of its own: every operation delegates to a `data-layer` primitive, and access to a replica remains bounded by possession of its ticket until subset-rbsr and UWill land.

## Requirements

### Requirement: The core embeds as a library
The runtime core SHALL be usable as a library with no host attached: a process embeds it, drives every service in-process, and shuts it down. The core SHALL NOT depend on any host machinery (HTTP or otherwise); hosts depend on the core, never the reverse.

#### Scenario: In-process embedding
- **WHEN** a test embeds the runtime core directly and drives the identity, connections, data, and sync services
- **THEN** every operation completes without any host process or HTTP surface involved

### Requirement: Identity service creates and links identities
The identity service SHALL create an identity on its first device — minting a placeholder `PdnId` (no key material; a KERI-backed service is the future second implementation) and provisioning its store set (private metadata store, connections store, data namespace) — and SHALL add a device to an existing identity given that identity's [seed](../data-layer/device-linking.md) (its private-metadata-store ticket), one explicit linking act per identity.

#### Scenario: Create on one runtime, link on another
- **WHEN** an identity is created on runtime A and runtime B links with that identity's seed
- **THEN** B hosts the identity: it appears among B's hosted identities, and the identity's connections store converges on B

#### Scenario: Linking one identity imports nothing of another
- **WHEN** runtime B is linked into identity X while identity Y exists elsewhere
- **THEN** B hosts X only, and operations addressed to Y on B are refused as unknown

### Requirement: Connections service records and lists an identity's connections
The connections service SHALL record a connection between a hosted identity and a peer identity and SHALL list the identity's current connections, delegating to that identity's [connections store](../data-layer/connections-store.md). Recording is the current producer of connections; the establishment dialogue (pairing) becomes a producer in a later change.

#### Scenario: Recorded on one device, listed on a linked device
- **WHEN** device A of an identity records a connection to peer P and device B is linked into the same identity
- **THEN** B lists P once the connections store syncs

#### Scenario: Hosted identities' connection lists are disjoint
- **WHEN** identity X records a connection to peer P and identity Y on the same runtime records none
- **THEN** listing Y's connections yields nothing

### Requirement: Data service writes, reads, lists, and hands over namespace tickets
The data service SHALL write and read entries in a hosted issuer's [data namespace](../data-layer/data-store.md), SHALL list its entries as metadata (no payload bytes; optionally filtered by a path prefix), SHALL share a hosted namespace as a ticket, and SHALL import a peer's namespace from a ticket, after which its entries sync whole. Whole-store ticket handover is the interim access model (ticket possession); capability-scoped sharing replaces it in later changes, and this requirement changes with the mechanism.

#### Scenario: Write then read locally
- **WHEN** an entry is written under a hosted issuer at a path
- **THEN** reading that issuer and path returns the payload

#### Scenario: Listing yields exactly the written paths
- **WHEN** entries are written at two paths under a hosted issuer
- **THEN** listing that issuer yields exactly those two paths, without payload bytes

#### Scenario: Whole-store handover to a peer runtime
- **WHEN** runtime A shares issuer I's namespace as a ticket and runtime B imports it
- **THEN** B reads I's entries once synced

#### Scenario: Unhosted issuer is refused
- **WHEN** a read, write, or list addresses an issuer the runtime neither created nor imported
- **THEN** the operation fails with an unknown-issuer error, and nothing is read, written, or listed

### Requirement: Sync service reports the node id and the hosted identities
The sync service SHALL report the runtime's node id (its endpoint id) and the identities the runtime hosts — exactly those created or linked on it.

#### Scenario: Hosted identities follow create and link
- **WHEN** a fresh runtime reports its status, then creates one identity and links another
- **THEN** the report lists no identities first and afterwards exactly those two, with the node id unchanged throughout
