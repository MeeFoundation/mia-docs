# Restart recovery

## Purpose

What a [runtime](core.md) holds after it starts again on a directory it used before. One durable record names the identities this node hosts, each with the namespace of its private metadata directory, and nothing else: that directory already carries the identity's own state — its device set, its tickets, its connections records (Invariant 1) — so a second record of the same facts could only disagree with it. Recovery re-hosts each named identity through the steps a newly created identity goes through once its stores exist, and lets the rest re-derive along the product path: the data namespace from its published `data` ticket, the connections from the identity's connection records, each connection's metadata pair from that pair's two published tickets, the granted namespaces from the counterparty's grant records through the sweep that imports them anyway. It needs no peer, no network, and no ceremony repeated. The bytes and the key underneath are [durable storage](../data-layer/durable-storage.md)'s; what a restart deliberately does not bring back — invites minted and not consumed, ceremonies in flight — is named here.

## Requirements

### Requirement: The runtime records which identities it hosts
A runtime with durable storage SHALL keep, in its directory, a record of the identities it hosts: each identity's `PdnId` and the namespace of its private metadata directory. It SHALL record nothing else about them — no data namespace, no connections, no metadata pairs, no bound grants — because the directory is already the durable record of an identity's own state, and a second record of the same facts can disagree with it. Every change to the record SHALL replace it whole — written beside, renamed over — so an interrupted change leaves the previous record intact and the operation failed.

#### Scenario: Hosting is recorded when an identity is created
- **WHEN** an identity is created on a runtime with durable storage
- **THEN** the record names that identity and its directory namespace, and names nothing else about it

#### Scenario: Hosting is recorded when a device links
- **WHEN** a device links to an identity and its catch-up completes
- **THEN** the record names that identity and the directory namespace it imported

#### Scenario: A failed record change loses no identity
- **WHEN** recording a second identity fails — the process killed, the disk full — and the runtime restarts
- **THEN** the first identity is hosted from the intact previous record, and the second is either fully hosted or absent, never half-recorded

### Requirement: A restarted runtime recovers each hosted identity along the product path
At spawn, a runtime SHALL host every identity its record names whose directory replica its store holds, by opening that identity's private metadata directory from the replica the node already holds and performing the same registration a newly created identity performs: the directory arms session classification, the identity enters the hosted set, and its connection sweep begins. Everything else SHALL be re-derived from the directory rather than recorded: the identity's data namespace from its published `data` ticket, its connections from its connection records, each connection's metadata pair from that pair's two published tickets, and the granted namespaces from the counterparty's grant records. Recovery SHALL require no peer, no ceremony, and no network.

#### Scenario: An identity comes back hosted
- **WHEN** a runtime restarts on a directory whose record names one identity
- **THEN** that identity is reported as hosted, its own entries are readable, and no ceremony was performed to get there

#### Scenario: A connection and its grant come back
- **WHEN** a runtime that holds an established connection and an imported grant restarts
- **THEN** the connection is listed, the grant is readable from the pair, and the granted namespace's entries are readable again once the pair's first sweep completes

#### Scenario: Several identities on one node each come back
- **WHEN** a runtime hosting two identities, each with a connection of its own, restarts
- **THEN** both are hosted, and each lists its own connections and no other identity's

#### Scenario: A device that linked before the restart is still a device
- **WHEN** a device that joined an identity before a restart is read out of that identity's device set afterwards
- **THEN** it is present, and it is the same node id it registered under

### Requirement: An identity is hosted only when its record is complete
The record SHALL be written after an identity's store set is provisioned, and it SHALL be the last step of that provisioning that can fail — nothing after it may fail, so an identity is either recorded and hosted or neither. A start that finds no record for a replica the node holds SHALL NOT host it: a process that died part-way through creating or linking an identity therefore leaves replicas nothing points at, which are never registered and never served.

A provisioning that fails before the record SHALL take back what it provisioned on the node it ran on, rather than leave replicas the node goes on reconciling for the rest of the process's life. On disk they remain, unnamed by any record and never served, and the next start does not adopt them.

No operation ends an identity's hosting: the record only ever grows, and removing a line is not offered. Two states would use it — an identity a person no longer wants hosted on this device, and a line whose replica the store no longer holds, which recovery skips on every start — and neither is served today.

The record line SHALL become durable only after the replicas it names are durable, so that the halves cannot disagree in the other direction — a line naming a replica the store has never committed.

#### Scenario: An interrupted provisioning hosts nothing
- **WHEN** a runtime restarts after a create or a link that ended before its record was written
- **THEN** no identity is hosted from it, and reads addressed to it are refused as not hosted

#### Scenario: A failed provisioning leaves the running node as it found it
- **WHEN** creating an identity fails at its record write on a runtime that keeps running
- **THEN** the replicas it provisioned are no longer tracked by that runtime, and the identities it hosted before are untouched

#### Scenario: An unreadable record stops the start
- **WHEN** a runtime starts on a directory whose record cannot be read or parsed
- **THEN** the start fails with an error naming that record, rather than starting with nothing hosted

#### Scenario: A first start has no record
- **WHEN** a runtime starts on a directory that holds no record
- **THEN** it starts hosting nothing, and creating an identity writes the first entry of the record

### Requirement: A record line whose replica is missing is skipped, not fatal
A record line naming a directory replica the node's store does not hold SHALL be skipped: that identity is not hosted, the skip is reported, the line is left in the record, and every other line recovers as usual. A line whose replica the store does hold but cannot be opened SHALL stop the start, naming the identity — a runtime that silently hosted less than its record names would look healthy while refusing everything. The two SHALL be told apart by what the replica store holds, never by the wording of a failure.

The asymmetry is the reason: skipping loses one identity's hosting on this device, and the line stays readable by whoever ends the hosting, while stopping the start loses every identity on that disk at once — and a runtime that cannot start cannot be asked to repair itself, leaving erasure of the storage directory as the only way back.

#### Scenario: A line whose replica is absent is skipped and the rest comes back
- **WHEN** a runtime starts on a record naming two identities, one whose directory replica its store holds and one whose it does not
- **THEN** the first is hosted and its entries read back, the second is not hosted and reads addressed to it are refused, the start succeeds, and the record is left as it was

### Requirement: Access does not survive an outage, only bytes do
A granted replica's bytes persist across a restart, but the issuer behind them SHALL NOT be registered until a live grant record is read again, so between the start and the pair's first sweep the replica is not readable and not served. A grant withdrawn while the runtime was off SHALL be honoured on the sweep that reads the withdrawal, exactly as one withdrawn while it was running.

#### Scenario: A withdrawal during an outage closes the replica
- **WHEN** a grant is withdrawn while the audience's runtime is off, and that runtime restarts and reconnects
- **THEN** the granted namespace stops being readable there, and its issuer resolves to nothing

#### Scenario: A re-granted claim comes back
- **WHEN** a grant withdrawn during an outage is published again over the same claim after the audience's runtime restarts
- **THEN** the namespace is imported again and its entries become readable, with no ceremony repeated

#### Scenario: An unexplained replica is never served
- **WHEN** a runtime restarts holding a replica that no live grant record explains
- **THEN** no read of it succeeds and no session serves it, whatever its bytes still hold

### Requirement: Work in flight does not survive a restart
Invites minted and not yet consumed, ceremonies in flight, and the in-memory bookkeeping the runtime rebuilds by sweeping SHALL NOT be recovered. A ceremony interrupted by a restart SHALL fail as it does when interrupted by anything else, leaving nothing hosted on either side.

#### Scenario: A pending invite does not outlive the process
- **WHEN** an invite is minted, the runtime restarts, and the invite's secret is presented
- **THEN** it is refused, as an unknown secret is refused
