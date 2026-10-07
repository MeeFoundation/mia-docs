# Restart recovery

## Purpose

What a [runtime](../core/spec.md) holds after it starts again on a directory it used before. Each identity this node hosts carries one durable record in its own subdirectory, beside its replica store — the namespace of its private metadata store (PMS) — and nothing else: that PMS already carries the identity's own state — its device set, its tickets, its connections records (Invariant 1) — so a second record of the same facts could only disagree with it. Recovery re-hosts each recorded identity through the steps a newly created identity goes through once its stores exist, and lets the rest re-derive along the product path: the data namespace from its published `data` ticket, the connections from the identity's connection records, each connection's metadata pair from that pair's two published tickets, the granted namespaces from the counterparty's grant records through the sweep that imports them anyway. It needs no peer, no network, and no ceremony repeated. The bytes and the key underneath are [durable storage](../../data-layer/durable-storage/spec.md)'s; what a restart deliberately does not bring back — invites minted and not consumed, ceremonies in flight — is named here.

## Requirements

### Requirement: The runtime records which identities it hosts
A runtime with durable storage SHALL keep, for each identity it hosts, a hosting record in that identity's own subdirectory of its storage directory, beside the identity's replica store: the namespace of the identity's PMS, the identity being the name of the subdirectory. It SHALL record nothing else about it — no data namespace, no connections, no metadata pairs, no bound grants — because the PMS is already the durable record of an identity's own state, and a second record of the same facts can disagree with it. A record SHALL be written beside, synced to disk, and renamed over, so no start ever reads a half-written record: a process killed before the rename leaves no record, from a create or link that never reported success, and a process killed after it leaves the whole record. Nothing syncs the directory holding the record after the rename, so an operating-system crash or a power loss can take a record back after its create or link reported success, and the next start then finds that subdirectory without a record and hosts nothing from it. A record belongs to its own identity alone: recording one identity never rewrites another's.

**Example:** Alice-work and Alice-leisure, two identities on one node; recording Alice-leisure touches her own subdirectory alone.

```
identities/<alice-work-hex>/pms          Alice-work's record, untouched: her PMS's NamespaceId, 64 hex characters
identities/<alice-leisure-hex>/pms.tmp   written and synced to disk first; a kill here leaves Alice-leisure no record
identities/<alice-leisure-hex>/pms       renamed over from pms.tmp: her PMS's NamespaceId and nothing else
identities/<alice-leisure-hex>/          not synced after the rename: a power loss after create() returned can leave no record
in neither record: a data namespace, a connection, a metadata pair, a bound grant; her PMS holds those
```

#### Scenario: Hosting is recorded when an identity is created
- **WHEN** an identity is created on a runtime with durable storage
- **THEN** that identity's subdirectory holds a record naming its PMS namespace, and nothing else about it

#### Scenario: Hosting is recorded when a device links
- **WHEN** a device links to an identity and its catch-up completes
- **THEN** that identity's subdirectory holds a record naming the PMS namespace it imported

#### Scenario: A failed record change loses no identity
- **WHEN** recording a second identity fails — the process killed, the disk full — and the runtime restarts
- **THEN** the first identity is hosted from its own record, untouched by the attempt, and the second is either fully hosted or absent, never half-recorded

### Requirement: A restarted runtime recovers each hosted identity along the product path
At spawn, a runtime SHALL host every identity whose subdirectory holds a hosting record and whose store holds the PMS replica that record names, each with stores of its own, by opening that identity's PMS from the replica that identity already holds and performing the same registration a newly created identity performs: the PMS arms session classification, the identity enters the hosted set, and its connection sweep begins. Everything else SHALL be re-derived from the PMS rather than recorded: the identity's data namespace from its published `data` ticket, its connections from its connection records, each connection's metadata pair from that pair's two published tickets, and the granted namespaces from the counterparty's grant records, all imported for that identity. A contact re-derived this way that names this node's own address SHALL be reached inside the process. Recovery SHALL require no peer, no ceremony, and no network.

**Example:** Alice's runtime restarts on its storage directory; she holds a connection to Bob, who granted her read on his `contact/email`.

| comes back | read from | when |
|---|---|---|
| Alice, hosted | `identities/<alice-hex>/pms`, naming her PMS | before spawn returns |
| the connection to Bob | `connections/<bob-hex>` in her PMS | before spawn returns |
| her data namespace | `tickets/data` in her PMS | the armer's first sweep |
| the metadata pair | `tickets/connection-metadata/<bob-hex>/own` and `…/peer` there | the armer's first sweep |
| Bob's namespace | `grants/<bob-hex>` in Bob's half of the pair | the grant binder's first sweep |
| every record above is on Alice's own disk, so no peer has to answer | | |

#### Scenario: An identity comes back hosted
- **WHEN** a runtime restarts on a directory recording one hosted identity
- **THEN** that identity is reported as hosted, its own entries are readable, and no ceremony was performed to get there

#### Scenario: A connection and its grant come back
- **WHEN** a runtime that holds an established connection and an imported grant restarts
- **THEN** the connection is listed, the grant is readable from the pair, and the granted namespace's entries are readable again once the pair's first sweep completes

#### Scenario: Several identities on one node each come back
- **WHEN** a runtime hosting two identities, each with a connection of its own, restarts
- **THEN** both are hosted, and each lists its own connections and no other identity's

#### Scenario: Two identities granted by one issuer come back apart
- **WHEN** a runtime hosting two identities granted different claims of one issuer restarts
- **THEN** each identity reads the claim its own grant names and neither reads the other's

#### Scenario: A device that linked before the restart is still a device
- **WHEN** a device that joined an identity before a restart is read out of that identity's device set afterwards
- **THEN** it is present, and it is the same node id it registered under
### Requirement: An identity is hosted only when its record is complete
The record SHALL be written after an identity's store set is provisioned and armed for session classification, and before the identity enters the runtime's hosted set. A link SHALL take every step that can fail it before the record: what follows the record, the device's own confirmation, does not fail the link ([device linking](../device-linking/spec.md)). A create SHALL read its identity's author after the record; that read fails only when the identity's half of the node is missing or the lock over the node's hosted identities is poisoned, and such a failure SHALL fail the create and drop the identity's half of the running node while the record stays on disk, so the next start hosts the identity the failed create recorded. A start that finds no record for a replica the node holds SHALL NOT host it: a process that died part-way through creating or linking an identity therefore leaves replicas nothing points at, which are never registered and never served.

A provisioning that fails before the record SHALL take back what it provisioned on the node it ran on, rather than leave replicas the node goes on reconciling for the rest of the process's life. On disk they remain, unnamed by any record and never served, and the next start does not adopt them.

No operation ends an identity's hosting: a record, once written, is never removed. Two states would use such an operation — an identity a person no longer wants hosted on this device, and a record whose replica the store no longer holds, which recovery skips on every start — and neither is served today.

A record SHALL become durable only after its identity's replicas are durable, so that the halves cannot disagree in the other direction — a record naming a replica the store has never committed.

**Example:** `create()` on a1 (Alice's first device), killed after one of its steps; what the next start finds in `identities/<alice-hex>/`.

| killed after | on disk | the next start |
|---|---|---|
| `provision_identity` | `docs.redb`, `default-author` | hosts nothing from it |
| any step up to `host_identity`: the PMS with `devices/<a1-node-id>`, the data namespace, `tickets/data` | the same, holding the replicas as far as the store committed them | hosts nothing from it, serves neither |
| `commit_hosting`: replicas flushed, record renamed in | + `pms`, the replicas committed | hosts Alice |
| a failure rather than a kill before the commit: `CreateRollback` drops Alice's half of the running node; the files stay | | |
| a failure of `default_author` after the commit: `create()` fails, `CreateRollback` drops Alice's half of the running node, the record stays, and the next start hosts Alice | | |

#### Scenario: An interrupted provisioning hosts nothing
- **WHEN** a runtime restarts after a create or a link that ended before its record was written
- **THEN** no identity is hosted from it, and reads addressed to it are refused as not hosted

#### Scenario: A failed provisioning leaves the running node as it found it
- **WHEN** creating an identity fails at its record write on a runtime that keeps running
- **THEN** the replicas it provisioned are no longer tracked by that runtime, and the identities it hosted before are untouched

#### Scenario: An unreadable record stops the start
- **WHEN** a runtime starts on a directory holding a hosting record that cannot be read or parsed
- **THEN** the start fails with an error naming that record's file, rather than starting with less hosted than the directory records

#### Scenario: A first start has no record
- **WHEN** a runtime starts on a directory that holds no hosting record
- **THEN** it starts hosting nothing, and creating an identity writes that identity's record

### Requirement: A record whose replica is missing is skipped, not fatal
A hosting record naming a PMS replica its identity's store does not hold — the store gone from the subdirectory, or holding no such replica — SHALL be skipped: that identity is not hosted, the skip is reported, the record is left as it is, and every other identity recovers as usual. Where the store is gone, the skip SHALL open none in its place. A record whose store is present but does not open, or whose store holds the named replica but cannot open it, SHALL stop the start — a runtime that silently hosted less than its records name would look healthy while refusing everything. A replica that does not open SHALL fail the start with an error naming the identity; a store that does not open fails it first, with the error every failed store open gives, which names the node's storage directory and not the identity. A skip and a stop SHALL be told apart by whether the store is on disk and what it holds, never by the wording of a failure.

The asymmetry is the reason: skipping loses one identity's hosting on this device, and the record stays readable by whoever ends the hosting, while stopping the start loses every identity on that disk at once — and a runtime that cannot start cannot be asked to repair itself, leaving erasure of the storage directory as the only way back.

**Example:** a start meets a hosting record in `identities/<x-hex>/`, x an identity; the case is read off the store, never off error text.

| the store beside the record | told by | the start |
|---|---|---|
| holds the named replica, which opens | `PrivateMetadataStore::open → Ok(Some(_))` | hosts x |
| `docs.redb` absent | `RecordedHosting { store_present: false }` | skips x with a warning, opens no store |
| `docs.redb` present, does not open | `provision_identity → Err(_)` | fails: `"cannot open the node's stores in <storage-dir>"`, naming no identity |
| holds no such replica | `PrivateMetadataStore::open → Ok(None)` | skips x with a warning |
| holds the named replica, which does not open | `PrivateMetadataStore::open → Err(_)` | fails: `"cannot recover hosted identity <x-hex>: its PMS replica did not open"` |
| both skips leave the record as it is, so the skip repeats on every start | | |

#### Scenario: A record whose replica is absent is skipped and the rest comes back
- **WHEN** a runtime starts on a directory recording three identities — one whose store holds its PMS replica, one whose store is gone, and one whose store holds no such replica — and creates a fourth identity afterwards
- **THEN** the first is hosted and its entries read back, the other two are not hosted and reads addressed to them are refused, no store is opened where one was gone, the start succeeds, and both skipped records are left as they were

### Requirement: A runtime dropped without a shutdown releases its directory
A runtime dropped without a shutdown while its process goes on SHALL release its stores and its directory once its own tasks wind down, so a runtime spawned on the same directory in the same process starts and hosts what the first one hosted. Nothing an identity's engine holds SHALL keep the runtime's node alive: an embedding host that brings runtimes up and drops them, or a handle released without a stop, would otherwise hold a socket, the replica stores and their memory for the rest of the process.

#### Scenario: A dropped runtime's directory is spawned on again
- **WHEN** a runtime hosting an identity is dropped without a shutdown, and a runtime is spawned on the same directory in the same process
- **THEN** the spawn succeeds within a bounded time and the new runtime hosts that identity

### Requirement: Access after a restart comes from the grant record on disk, not from the bytes
A granted replica's bytes persist across a restart, but the issuer behind them SHALL NOT be registered until the grant binder reads a live grant record again, so between the start and the pair's first sweep the replica is not readable and not served. That sweep SHALL read the grant record from this node's own replica of the counterparty's half of the pair, and bind the namespace again whenever the record is live there. A grant withdrawn while the runtime was off is therefore bound again by the first sweep if the withdrawal's tombstone has not yet reached that replica: until it does, the audience reads what its replica already holds, and the audience's own devices are served the claims the stale record names. The sweep that reads the tombstone SHALL unbind the namespace, exactly as for a grant withdrawn while the runtime was running.

**Example:** Alice (issuer) granted Bob read on `contact/email`; Bob's runtime stops, and Alice's node is offline when Bob's comes back.

| t | what happens | Bob's side |
|---|---|---|
| t0 | Alice withdraws: `grants/<alice-hex>` tombstoned in her half of the pair | Bob's runtime is off |
| t1 | Bob's runtime spawns; her namespace's bytes are in his `docs.redb` | Bob's read: `UnknownIssuer` |
| t2 | the grant binder's first sweep reads `grants/<alice-hex>` from Bob's disk, still live, since the tombstone has not arrived | Bob's read: the entry he already held |
| t3 | Alice's node is back; the pair syncs the tombstone, and the sweep that reads it unbinds her namespace | Bob's read: `UnknownIssuer` |

#### Scenario: A withdrawal during an outage closes the replica
- **WHEN** a grant is withdrawn while the audience's runtime is off, and that runtime restarts and reconnects
- **THEN** the granted namespace stops being readable there once the withdrawal has reached the audience's replica of the pair, and its issuer resolves to nothing

#### Scenario: A re-granted claim comes back
- **WHEN** a grant withdrawn during an outage is published again over the same claim after the audience's runtime restarts
- **THEN** the namespace is imported again and its entries become readable, with no ceremony repeated

#### Scenario: An unexplained replica is never served
- **WHEN** a runtime restarts holding a replica that no live grant record explains
- **THEN** no read of it succeeds and no session serves it, whatever its bytes still hold

### Requirement: Work in flight does not survive a restart
Invites minted and not yet consumed, ceremonies in flight, and the in-memory bookkeeping the runtime rebuilds by sweeping SHALL NOT be recovered. A ceremony interrupted by a restart SHALL fail as it does when interrupted by anything else, leaving nothing hosted on either side.

**Example:** a1 (Alice's first device) restarts on its storage directory 30 s after minting a linking invite for a2 (her second).

| held before the stop | kept in | after the restart |
|---|---|---|
| the invite's secret | `pending_linking_invites`, in memory | gone: a2 presenting it gets `LinkingRefused` |
| the pending record of an earlier link whose reply was lost | `pending-devices/<a2-node-id>` in Alice's PMS | still there, conferring nothing, and expiring 24 h after it was written |
| the metadata pairs and the grants bound | `metadata_pairs`, `bound_grants`, in memory | rebuilt by the armer's sweeps |

#### Scenario: A pending invite does not outlive the process
- **WHEN** an invite is minted, the runtime restarts, and the invite's secret is presented
- **THEN** it is refused, as an unknown secret is refused
