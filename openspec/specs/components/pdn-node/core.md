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
The identity service SHALL create an identity on its first device — minting a placeholder `PdnId` (no key material; a KERI-backed service is the future second implementation) and provisioning its store set: the private-metadata directory and the data namespace, with the data-namespace ticket published in the directory ([device-linking](device-linking.md)). It SHALL mint a linking invite for a hosted identity — the one-time secret and the bearer-free linking payload — and SHALL link this runtime into an existing identity from a scanned linking payload, one explicit linking act per identity; the payload names the identity, and a runtime already hosting it refuses before dialing.

#### Scenario: Create on one runtime, link on another
- **WHEN** an identity is created on runtime A and runtime B links from a linking invite minted on A
- **THEN** B hosts the identity: it appears among B's hosted identities, and the identity's directory and data namespace converge on B

#### Scenario: Linking one identity imports nothing of another
- **WHEN** runtime B is linked into identity X while identity Y exists elsewhere
- **THEN** B hosts X only, and operations addressed to Y on B are refused as unknown

### Requirement: Connections service establishes, lists, and carries grants
The connections service SHALL produce connections through the establishment dialogue — minting invites for a hosted identity and establishing from an invite payload ([connection-establishment](connection-establishment.md)) — and SHALL list a hosted identity's current connections, delegating to the connections records of that identity's [directory](../data-layer/private-metadata-store.md). It SHALL carry data grants over the connection's [metadata pair](../data-layer/connection-metadata-store.md): publishing a grant of a hosted issuer's namespace toward a connected peer, and reading the grants a connected peer has published — opening the pair from the directory's tickets on demand, so linked devices reach it too. Manual one-sided recording is not offered: establishment is the producer of connections. Reading a grant yields the ticket it carries; importing that namespace remains an explicit data-service act. (The grant payload is the interim whole-store **write** ticket: the store's capability is swarm membership, not access control, so read and write are `UWill`'s to decide once the ingest gate and the egress filter enforce them. Until they do, a grant is unscoped in both directions — the grantee can write into the granted namespace and nothing rejects what it writes. Capability-scoped grants land with `UWill`, and this requirement changes with them.)

#### Scenario: Hosted identities' connection lists are disjoint
- **WHEN** identity X on a runtime establishes a connection with peer P and identity Y on the same runtime establishes none
- **THEN** listing Y's connections yields nothing

#### Scenario: A grant crosses to the peer with no new pairing
- **WHEN** X publishes a grant of its namespace toward its established peer P, after establishment completed
- **THEN** P's runtime reads the grant from the metadata pair, and importing the carried ticket through the data service lets P read X's entries once synced

#### Scenario: Connections operations on an unhosted identity are refused
- **WHEN** an invite, establishment, listing, or grant operation addresses an identity the runtime neither created nor linked
- **THEN** the operation fails with an unknown-identity error and nothing is minted, established, listed, or published

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
