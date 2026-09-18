# data-layer: durable storage — delta for identity-scoped-replicas

## MODIFIED Requirements

### Requirement: The directory holds the replicas, the blobs, the author, and the node's key
A configured directory SHALL hold everything a node needs to be itself: a subdirectory per scope carrying that scope's replica store and author, the blob store, and the node's endpoint secret key. The node SHALL create the directory, readable only by its owner, when it is absent, read the key when it is present, and generate and store a key readable only by its owner when it is not — written beside and linked into place exclusively, so no half-written key can exist and two starts racing on one directory read one key rather than minting two. A staging file left by a start that died mid-write SHALL NOT stop the next start. A key file that cannot be parsed SHALL stop the start with an error naming it, and SHALL NOT be replaced with a fresh key. A configuration that persists the stores without the key SHALL NOT be expressible.

#### Scenario: A fresh directory is provisioned
- **WHEN** a node is spawned on a directory that does not exist
- **THEN** the directory is created with owner-only permissions, a secret key is generated and stored the same way, and the node runs

#### Scenario: The stores come back
- **WHEN** a node writes entries, is shut down, and a node is spawned on the same directory
- **THEN** the entries are readable, with their payloads, without any peer being reachable

#### Scenario: Each scope's stores come back as its own
- **WHEN** a node hosting two identities writes an entry under each, is shut down, and a node is spawned on the same directory
- **THEN** each identity reads back what it wrote, and neither reads the other's entry

#### Scenario: A malformed key stops the start
- **WHEN** a node is spawned on a directory whose key file cannot be parsed
- **THEN** the spawn fails with an error naming that file, and no new key is written

#### Scenario: A leftover staging file does not block the start
- **WHEN** a node is spawned on a directory holding a half-written key staging file and no key
- **THEN** a key is minted, the leftover is gone, and a later start on the directory reads the committed key back

## ADDED Requirements

### Requirement: A scope's replica store cache size is a fixed share, configured at spawn
The size of the cache a scope's replica store keeps SHALL be part of the storage configuration a node is spawned with, and SHALL be the share one scope takes rather than a budget for the whole node: the cache is bounded per store, a node holds one store per scope, and a store's bound is fixed when that store is opened. An identity created while the node runs SHALL open its store at that same share, and no other scope's store SHALL be reopened for it. A host therefore derives the share from the memory it gives the replica stores and the number of identities the device it runs on is provisioned for. The workspace SHALL state one default of 1 GiB per scope in a single place, which the hosts and the test suites take rather than restate. A host running where memory is scarce computes its share from the memory that device can spare, once at that application's first start, and keeps it with its own settings; this spec states the expectation and no mobile host implements it here.

#### Scenario: The default is one value, taken rather than restated
- **WHEN** a node is spawned without naming a cache share
- **THEN** each of its scopes bounds its store's cache at the stated default

#### Scenario: A host passes a share of its own
- **WHEN** a node is spawned with a cache share named
- **THEN** each of its scopes bounds its store's cache at that value

#### Scenario: An identity added later takes the same share
- **WHEN** an identity is created on a running node
- **THEN** its store opens bounded at the configured share, and the stores of the scopes already open are not reopened

### Requirement: One author per scope, persisted with that scope's stores
Every store in a scope SHALL write with that scope's one author, and that author SHALL be persisted with the scope's replicas, so a node that restarts writes each scope's entries as the author it wrote them as before. An author minted per store or per start makes a rewritten key accumulate one live record per author: replacement and prefix deletion are scoped to the writing author, so every superseded copy stays live in the replica and replicates. A device record written under one author and withdrawn under another likewise stays in the replica; the set still reads the device as absent, because the latest-per-key collapse sees the tombstone before empty entries are excluded — a query behavior the withdrawal scenario pins. Two scopes of one node SHALL write with two different authors, so what a counterparty or a cell binds to an identity on this device is that identity's author and not the node's.

#### Scenario: A rewritten key keeps one live record
- **WHEN** a scope writes a path, the node restarts, and the scope writes the same path again
- **THEN** the replica holds one live record for that path, carrying the newer value

#### Scenario: A withdrawn device does not come back with a restart
- **WHEN** a device is withdrawn from an identity's device set, and a device of that identity restarts
- **THEN** the withdrawn device is absent from the set as read after the restart

#### Scenario: Two identities on one node write as two authors
- **WHEN** two identities hosted on one node each write an entry
- **THEN** the two entries carry two different authors, and each identity's later writes carry the one it wrote with before

## REMOVED Requirements

### Requirement: One author per node, persisted with the stores
**Reason**: The author is a property of a scope rather than of a node: one author for every store made two identities of one node indistinguishable as writers, so an entry either could have written passed as either one's.
**Migration**: The same persistence and the same latest-per-key behaviour are stated per scope by "One author per scope, persisted with that scope's stores"; a node that held one author writes each scope's entries under that scope's author instead.
