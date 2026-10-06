# Durable storage

## Purpose

What a node keeps on disk, and where. Storage is named at the spawn — memory, or a directory — and a node given a directory keeps there everything it needs to be itself: a subdirectory per hosted identity holding that identity's replicas ([data store](../data-store/spec.md), [private metadata store](../private-metadata-store/spec.md), [connection metadata store](../connection-metadata-store/spec.md), the stores of its [pods](../pod-store/spec.md)), the one author it writes them with and the record that it is hosted here, the blobs their payloads resolve through, and the endpoint secret key its node id comes from. The key is what makes the rest worth keeping: a node that came back under a fresh id would be a stranger to its own device record and to every ticket it ever handed out. A directory belongs to one running node at a time. What the runtime above rebuilds from such a directory — the identities it hosts, their connections, the namespaces they were granted — is [restart recovery](../../pdn-node/restart-recovery/spec.md)'s.

## Requirements

### Requirement: Storage is configured at spawn, and neither mode is a default
A node's storage SHALL be chosen when it is spawned, by name: memory, or a directory. A spawn that names neither SHALL NOT be expressible — no caller wants a default, because the production consumer embeds the runtime and passes a directory inside its own sandbox, and the test suites want memory and say so. The location SHALL NOT be read from the process environment inside the data layer, because several nodes spawn in one process and a directory belongs to one node.

**Example:** who names a node's storage, and how.

| caller | spawns with |
|---|---|
| the in-process test suites | `SpawnOptions::memory()` |
| pdn-node-http, the container stand | `SpawnOptions::on_directory(dir)`, dir read by the host from `PDN_DATA_DIR` |
| a host shipped to a device | `SpawnOptions::for_product(dir)`, dir inside its own sandbox |
| a `SpawnOptions` naming no storage | does not compile: storage is a field with no default, and `SpawnOptions` has no `Default` |

#### Scenario: A node spawned on memory stores in memory
- **WHEN** a node is spawned with memory named as its storage
- **THEN** it creates no files, and its state ends with the process

#### Scenario: Two nodes in one process store apart
- **WHEN** two nodes are spawned in one process, each configured with a directory of its own
- **THEN** each keeps its own state, and neither reads the other's directory

### Requirement: The directory holds the replicas, the blobs, the author, and the node's key
A configured directory SHALL hold everything a node needs to be itself: a subdirectory per hosted identity carrying that identity's replica store, its author and its hosting record — the namespace of its private metadata directory, written at the commit point of the create or link that hosts it ([restart recovery](../../pdn-node/restart-recovery/spec.md)) — the blob store, and the node's endpoint secret key. The node SHALL create the directory, readable only by its owner, when it is absent, read the key when it is present, and generate and store a key readable only by its owner when it is not — written beside and linked into place exclusively, so no half-written key can exist and two starts racing on one directory read one key rather than minting two. A staging file left by a start that died mid-write SHALL NOT stop the next start. A key file that cannot be parsed SHALL stop the start with an error naming it, and SHALL NOT be replaced with a fresh key. A configuration that persists the stores without the key SHALL NOT be expressible.

**Example:** `/var/lib/pdn` after Alice-work and Alice-leisure are hosted; `<x>` is identity x's `PdnId` in 64 hex digits.

```
/var/lib/pdn/                    mode 0700 when the node creates it
  node.key                       mode 0600: the endpoint's secret key in hex, written as node.key.tmp, then hard-linked into place
  lock                           held by the running node
  blobs/                         the payloads, one store for the node
  identities/<Alice-work>/
    docs.redb                    her replica store
    default-author               the one author her writes carry
    directory                    her hosting record: her directory's namespace, written at the commit point
  identities/<Alice-leisure>/    the same three files
```

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
### Requirement: The node's wire identity is stable across starts
A node spawned on a directory holding a key SHALL bind its endpoint with that key, so its node id is the one it had before. A node's device records, the tickets it minted, and the contacts its peers hold all name that id, so a node that came back under a different id would be unreachable by everything it handed out.

**Example:** what names Alice's device a1 elsewhere; `<a1>` is its node id, the public half of the secret key in `/var/lib/pdn/node.key`.

| record | held by | a1 restarted on `/var/lib/pdn` | a1 back under a fresh key |
|---|---|---|---|
| `devices/<a1>` in Alice's directory | her other devices | names a1 | names an id that never answers |
| a ticket a1 minted, `<a1>` in `DocTicket.nodes` | whoever imported it | dials a1 | dials nobody |
| `devices/<a1>` in the device set she publishes | Bob's node b1 | admits a1's sessions | refuses the new id as not hosted |

#### Scenario: The node id survives a restart
- **WHEN** a node is shut down and spawned again on the same directory
- **THEN** it reports the same node id, and a ticket minted before the shutdown still names a reachable address

#### Scenario: A fresh directory is a different node
- **WHEN** a node is spawned on an empty directory
- **THEN** it reports a node id of its own, holding none of another directory's state

### Requirement: One running node per directory
A directory SHALL be used by one running node at a time. A node spawned on a directory another running node holds SHALL fail to start, naming the directory and the reason, rather than reporting a corrupt store or starting alongside.

**Example:** two spawns on `/var/lib/pdn` in one process.

| t | node A | node B |
|---|---|---|
| t0 | spawns, takes the advisory lock on `/var/lib/pdn/lock` | |
| t1 | | spawns: `try_lock` on the same file answers `WouldBlock`, before any store opens |
| t2 | | fails with `DirectoryHeld`: "storage directory /var/lib/pdn is held by another running node" |
| t3 | serves on, its stores untouched | |

#### Scenario: The second node is refused
- **WHEN** a node is spawned on the directory of a node that is already running
- **THEN** the spawn fails with an error naming that directory, and the running node is unaffected

### Requirement: A storage failure is reported, never swallowed
A write the storage layer refuses — an exhausted disk above all — SHALL surface as a failed operation to the caller that made it. A refused write SHALL NOT be reported as stored, and a replica whose last transaction did not commit SHALL NOT be reported as converged.

**Example:** the stand's node with `/var/lib/pdn` on a 16 MiB tmpfs; `<Alice>` is its one identity; each write a distinct 256 KiB payload.

| request | answer |
|---|---|
| `PUT /debug/data/<Alice>/<Alice>/fill/0000` | 204, while the filesystem has room |
| `PUT …/fill/<n>`, the first write refused | 500, and the host logs "unmapped host error: …" with the storage failure |
| `GET …/fill/<n>` | not the refused payload |
| `POST /debug/identities` | an error: the replica store commits nothing more until a restart |

#### Scenario: A write on a full disk fails loudly
- **WHEN** a node's directory is on a filesystem with no free space and an entry write is attempted
- **THEN** the write fails with an error naming the storage failure, and a subsequent read does not report the entry as stored
### Requirement: A replica store's cache is a share of a node budget, cut as the store opens
A node SHALL be spawned with the memory its replica stores may hold together, and SHALL NOT be spawned with a count of identities to divide it by: the cache one identity's replica store keeps SHALL be bounded at that memory divided by the identities the storage directory records as hosted — each subdirectory holding a hosting record — with the opening identity counted whether or not its record is written yet. A subdirectory with no record, which is what an unfinished create or link leaves, SHALL take no share. The share SHALL be cut as each store opens and SHALL NOT change while that store is open, so a device carrying one identity gives it the whole budget, an identity provisioned while the node runs takes a share cut from the set that now includes it, and no store already open is reopened for it. Every start SHALL therefore cut every share from the whole set the directory records, which is what brings a node that grew while it ran back within its budget. The workspace SHALL state one default in a single place, which the hosts and the test suites take rather than restate: 1 GiB for a node's replica stores. A node whose bounds handed out together pass its budget SHALL report it. A replica store held in memory carries no bound at all. A host running where memory is scarce states the budget once at that application's first start, from the memory that device can spare, and keeps it with its own settings; this spec states the expectation and no mobile host implements it here. The bound caps resident memory rather than reserving it.

**Example:** a node on `/var/lib/pdn` with the default budget, `DEFAULT_REPLICA_CACHE_BUDGET_BYTES` = 1,073,741,824 bytes (1 GiB).

| event | identities the share is cut from | store opens at | bounds exceed the budget |
|---|---|---|---|
| first start, Alice-work created | Alice-work, opening before her record | 1 GiB | no |
| Alice-leisure created while the node runs | Alice-work recorded, Alice-leisure opening | 512 MiB; Alice-work keeps 1 GiB | yes: 1.5 GiB handed out |
| restart; a third subdirectory has no hosting record | Alice-work and Alice-leisure, recorded | 512 MiB each | no |

#### Scenario: The default gives a single identity the whole budget
- **WHEN** a node is spawned without naming a budget
- **THEN** its one identity bounds its store's cache at the stated default budget

#### Scenario: A store in memory carries no bound
- **WHEN** a node spawned on memory provisions an identity
- **THEN** that identity's store carries no cache bound, and the node reports no breach of its budget

#### Scenario: A start cuts every share from the identities the directory records
- **WHEN** a node is spawned on a directory recording two hosted identities and holding the subdirectory of a third that no commit recorded, and provisions the two
- **THEN** each store opens bounded at half the budget, and the node reports no breach of its budget

#### Scenario: An identity added later takes a share of its own
- **WHEN** an identity is provisioned on a running node whose directory recorded one hosted identity before
- **THEN** its store opens bounded at half the budget, the store already open keeps the bound it opened at, and the node reports that the bounds handed out together pass its budget

### Requirement: One author per hosted identity, persisted with that identity's stores
Every store a hosted identity holds SHALL write with that identity's one author, and that author SHALL be persisted with the identity's replicas, so a node that restarts writes each identity's entries as the author it wrote them as before. An author minted per store or per start makes a rewritten key accumulate one live record per author: replacement and deletion are scoped to the writing author and to one key, so every superseded copy stays live in the replica and replicates. A device record written under one author and withdrawn under another likewise stays in the replica; the set still reads the device as absent, because the latest-per-key collapse sees the tombstone before empty entries are excluded — a query behavior the withdrawal scenario pins. Two identities of one node SHALL write with two different authors, so what a counterparty or a pod binds to an identity on this device is that identity's author and not the node's.

**Example:** Alice writes `contact/email`, the node restarts, she writes it again; A1 and A2 are authors.

| | author persisted in `default-author` | author minted per start |
|---|---|---|
| before the restart | `(A1, contact/email) = "before"` | `(A1, contact/email) = "before"` |
| after the rewrite | `(A1, contact/email) = "after"` | `(A1, contact/email) = "before"`, `(A2, contact/email) = "after"` |
| live records at the path | 1 | 2, and the stale one replicates |

#### Scenario: A rewritten key keeps one live record
- **WHEN** a hosted identity writes a path, the node restarts, and it writes the same path again
- **THEN** the replica holds one live record for that path, carrying the newer value

#### Scenario: A withdrawn device does not come back with a restart
- **WHEN** a device is withdrawn from an identity's device set, and a device of that identity restarts
- **THEN** the withdrawn device is absent from the set as read after the restart

#### Scenario: Two identities on one node write as two authors
- **WHEN** two identities hosted on one node each write an entry
- **THEN** the two entries carry two different authors, and each identity's later writes carry the one it wrote with before
