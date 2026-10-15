## REMOVED Requirements

### Requirement: A restarted runtime recovers each hosted identity along the product path

**Reason**: Two of its cases — a connection with its grant, and two identities granted by one issuer — rest on connections and grants, removed by this change, and it re-derives a data namespace this change removes; the requirement returns as "A restarted runtime re-derives each hosted identity from its PMS".

**Migration**: None: a restarted runtime re-derives the identity's pods from its PMS, as the [pods](../pods/spec.md) spec states.

### Requirement: Access after a restart comes from the grant record on disk, not from the bytes

**Reason**: Grants are removed by this change.

**Migration**: None: a pod's store is served after a restart by the membership view its replica holds.

## MODIFIED Requirements

### Requirement: The runtime records which identities it hosts
A runtime with durable storage SHALL keep, for each identity it hosts, a hosting record in that identity's own subdirectory of its storage directory, beside the identity's replica store: the namespace of the identity's PMS, the identity being the name of the subdirectory. It SHALL record nothing else about it — no pod, no device, no ticket — because the PMS is already the durable record of an identity's own state, and a second record of the same facts can disagree with it. A record SHALL be written beside, synced to disk, and renamed over, so no start ever reads a half-written record: a process killed before the rename leaves no record, from a create or link that never reported success, and a process killed after it leaves the whole record. Nothing syncs the directory holding the record after the rename, so an operating-system crash or a power loss can take a record back after its create or link reported success, and the next start then finds that subdirectory without a record and hosts nothing from it. A record belongs to its own identity alone: recording one identity never rewrites another's.

**Example:** Alice-work and Alice-leisure, two identities on one node; recording Alice-leisure touches her own subdirectory alone.

```
identities/<alice-work-hex>/pms          Alice-work's record, untouched: her PMS's NamespaceId, 64 hex characters
identities/<alice-leisure-hex>/pms.tmp   written and synced to disk first; a kill here leaves Alice-leisure no record
identities/<alice-leisure-hex>/pms       renamed over from pms.tmp: her PMS's NamespaceId and nothing else
identities/<alice-leisure-hex>/          not synced after the rename: a power loss after create() returned can leave no record
in neither record: a pod, a device, a ticket; her PMS holds those
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

### Requirement: An identity is hosted only when its record is complete
The record SHALL be written after an identity's store set is provisioned and armed for session classification, and before the identity enters the runtime's hosted set. A link SHALL take every step that can fail it before the record: what follows the record, the device's own confirmation, does not fail the link ([device linking](../device-linking/spec.md)). A create SHALL read its identity's author after the record; that read fails only when the identity's half of the node is missing or the lock over the node's hosted identities is poisoned, and such a failure SHALL fail the create and drop the identity's half of the running node while the record stays on disk, so the next start hosts the identity the failed create recorded. A start that finds no record for a replica the node holds SHALL NOT host it: a process that died part-way through creating or linking an identity therefore leaves replicas nothing points at, which are never registered and never served.

A provisioning that fails before the record SHALL take back what it provisioned on the node it ran on, rather than leave replicas the node goes on reconciling for the rest of the process's life. On disk they remain, unnamed by any record and never served, and the next start does not adopt them.

No operation ends an identity's hosting: a record, once written, is never removed. Two states would use such an operation — an identity a person no longer wants hosted on this device, and a record whose replica the store no longer holds, which recovery skips on every start — and neither is served today.

A record SHALL become durable only after its identity's replicas are durable, so that the halves cannot disagree in the other direction — a record naming a replica the store has never committed.

**Example:** `create()` on a1 (Alice's first device), killed after one of its steps; what the next start finds in `identities/<alice-hex>/`.

| killed after | on disk | the next start |
|---|---|---|
| `provision_identity` | `docs.redb`, `default-author` | hosts nothing from it |
| any step up to `host_identity`: the PMS with `devices/<a1-node-id>` and `identity-key` | the same, holding the replicas as far as the store committed them | hosts nothing from it, serves nothing |
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

### Requirement: Work in flight does not survive a restart
Invites minted and not yet consumed, ceremonies in flight, and the in-memory bookkeeping the runtime rebuilds by sweeping SHALL NOT be recovered. A ceremony interrupted by a restart SHALL fail as it does when interrupted by anything else, leaving nothing hosted on either side.

**Example:** a1 (Alice's first device) restarts on its storage directory 30 s after minting a linking invite for a2 (her second).

| held before the stop | kept in | after the restart |
|---|---|---|
| the invite's secret | `pending_linking_invites`, in memory | gone: a2 presenting it gets `LinkingRefused` |
| the pending record of an earlier link whose reply was lost | `pending-devices/<a2-node-id>` in Alice's PMS | still there, conferring nothing, and expiring 24 h after it was written |
| a join of "Family" past its dialogue, its tickets and PMS entry recorded | `joining_in_flight`, in memory | gone; the armer's first sweep opens the pod from what the join recorded |

#### Scenario: A pending invite does not outlive the process
- **WHEN** an invite is minted, the runtime restarts, and the invite's secret is presented
- **THEN** it is refused, as an unknown secret is refused

## ADDED Requirements

### Requirement: A restarted runtime re-derives each hosted identity from its PMS
At spawn, a runtime SHALL host every identity whose subdirectory holds a hosting record and whose store holds the PMS replica that record names, each with stores of its own, by opening that identity's PMS from the replica that identity already holds and performing the same registration a newly created identity performs: the PMS arms session classification, the identity enters the hosted set, and its armer begins. Everything else SHALL be re-derived from the PMS rather than recorded: the identity's pods from its pod records and the tickets beside them, opened by the armer's first sweep, as the [pods](../pods/spec.md) spec states. A contact re-derived this way that names this node's own address SHALL be reached inside the process. Recovery SHALL require no peer, no ceremony, and no network.

**Example:** Alice's runtime restarts on its storage directory; she is a member of "Family", whose pod id is `ad58a3faa04cdc5576c8dc5823a347c6`.

| comes back | read from | when |
|---|---|---|
| Alice, hosted | `identities/<alice-hex>/pms`, naming her PMS | before spawn returns |
| her device set and identity key | `devices/` and `identity-key` in her PMS | before spawn returns |
| "Family" | `pods/ad58a3faa04cdc5576c8dc5823a347c6/1` and the pod's tickets in her PMS | the armer's first sweep |
| every record above is on Alice's own disk, so no peer has to answer | | |

#### Scenario: An identity comes back hosted
- **WHEN** a runtime restarts on a directory recording one hosted identity
- **THEN** that identity is reported as hosted, its PMS reads as before the restart, and no ceremony was performed to get there

#### Scenario: Several identities on one node each come back
- **WHEN** a runtime hosting two identities, each a member of a pod of its own, restarts
- **THEN** both are hosted, and each lists its own pod and not the other's

#### Scenario: A device that linked before the restart is still a device
- **WHEN** a device that joined an identity before a restart is read out of that identity's device set afterwards
- **THEN** it is present, and it is the same node id it registered under
