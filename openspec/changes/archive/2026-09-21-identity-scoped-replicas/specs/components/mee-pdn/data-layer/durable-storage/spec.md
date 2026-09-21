# data-layer: durable storage — delta for identity-scoped-replicas

## MODIFIED Requirements

### Requirement: The directory holds the replicas, the blobs, the author, and the node's key
A configured directory SHALL hold everything a node needs to be itself: a subdirectory per hosted identity carrying that identity's replica store and author, the blob store, and the node's endpoint secret key. The node SHALL create the directory, readable only by its owner, when it is absent, read the key when it is present, and generate and store a key readable only by its owner when it is not — written beside and linked into place exclusively, so no half-written key can exist and two starts racing on one directory read one key rather than minting two. A staging file left by a start that died mid-write SHALL NOT stop the next start. A key file that cannot be parsed SHALL stop the start with an error naming it, and SHALL NOT be replaced with a fresh key. A configuration that persists the stores without the key SHALL NOT be expressible.

#### Scenario: A fresh directory is provisioned
- **WHEN** a node is spawned on a directory that does not exist
- **THEN** the directory is created with owner-only permissions, a secret key is generated and stored the same way, and the node runs

#### Scenario: The stores come back
- **WHEN** a node writes entries, is shut down, and a node is spawned on the same directory
- **THEN** the entries are readable, with their payloads, without any peer being reachable

#### Scenario: Each hosted identity's stores come back as its own
- **WHEN** a node hosting two identities writes an entry under each, is shut down, and a node is spawned on the same directory
- **THEN** each identity reads back what it wrote, and neither reads the other's entry

#### Scenario: A malformed key stops the start
- **WHEN** a node is spawned on a directory whose key file cannot be parsed
- **THEN** the spawn fails with an error naming that file, and no new key is written

#### Scenario: A leftover staging file does not block the start
- **WHEN** a node is spawned on a directory holding a half-written key staging file and no key
- **THEN** a key is minted, the leftover is gone, and a later start on the directory reads the committed key back

## ADDED Requirements

### Requirement: A replica store's cache is a share of a node budget, cut at spawn
A node SHALL be spawned with the memory its replica stores may hold together and the number of identities the device is provisioned for, and the cache one identity's replica store keeps SHALL be bounded at that memory divided by that number. The share SHALL be computed at spawn and SHALL bound every store the node opens, so an identity created while the node runs opens its store at that same share and no other identity's store is reopened for it. The workspace SHALL state one default in a single place, which the hosts and the test suites take rather than restate: 1 GiB for a node's replica stores and one identity. A node holding more identities than the number its share was cut from SHALL report that its replica store caches may together exceed the budget, and SHALL NOT change the bound of a store already open. A host running where memory is scarce states both values once at that application's first start, from the memory that device can spare and the identities it offers to carry, and keeps them with its own settings; this spec states the expectation and no mobile host implements it here. The bound caps resident memory rather than reserving it.

#### Scenario: The default gives a single identity the whole budget
- **WHEN** a node is spawned without naming a budget or a count
- **THEN** its one identity bounds its store's cache at the stated default budget

#### Scenario: A host names its budget and its count
- **WHEN** a node is spawned with a budget and a count of the identities the device is provisioned for
- **THEN** each of its identities bounds its store's cache at the budget divided by that count

#### Scenario: An identity added later takes the same share
- **WHEN** an identity is created on a running node
- **THEN** its store opens bounded at the share cut at spawn, and the stores already open are not reopened

#### Scenario: More identities than the count the share was cut for
- **WHEN** a node provisioned for two identities comes to hold three
- **THEN** the third store opens at the same share, no open store's bound changes, and the node reports that its caches may together exceed the budget

### Requirement: One author per hosted identity, persisted with that identity's stores
Every store a hosted identity holds SHALL write with that identity's one author, and that author SHALL be persisted with the identity's replicas, so a node that restarts writes each identity's entries as the author it wrote them as before. An author minted per store or per start makes a rewritten key accumulate one live record per author: replacement and prefix deletion are scoped to the writing author, so every superseded copy stays live in the replica and replicates. A device record written under one author and withdrawn under another likewise stays in the replica; the set still reads the device as absent, because the latest-per-key collapse sees the tombstone before empty entries are excluded — a query behavior the withdrawal scenario pins. Two identities of one node SHALL write with two different authors, so what a counterparty or a cell binds to an identity on this device is that identity's author and not the node's.

#### Scenario: A rewritten key keeps one live record
- **WHEN** a hosted identity writes a path, the node restarts, and it writes the same path again
- **THEN** the replica holds one live record for that path, carrying the newer value

#### Scenario: A withdrawn device does not come back with a restart
- **WHEN** a device is withdrawn from an identity's device set, and a device of that identity restarts
- **THEN** the withdrawn device is absent from the set as read after the restart

#### Scenario: Two identities on one node write as two authors
- **WHEN** two identities hosted on one node each write an entry
- **THEN** the two entries carry two different authors, and each identity's later writes carry the one it wrote with before

## REMOVED Requirements

### Requirement: One author per node, persisted with the stores
**Reason**: The author is a property of a hosted identity rather than of a node: one author for every store made two identities of one node indistinguishable as writers, so an entry either could have written passed as either one's.
**Migration**: The same persistence and the same latest-per-key behaviour are stated per hosted identity by "One author per hosted identity, persisted with that identity's stores"; a node that held one author writes each identity's entries under that identity's author instead.
