## ADDED Requirements

### Requirement: A durable profile reopens one stable node

A persistent `SyncNode` SHALL be created or reopened from one explicit profile directory. The profile SHALL persist the endpoint secret key, documents, blobs, author secrets, and the local catalog required to interpret and reopen namespaces. Reopening the same profile SHALL preserve its `NodeId`; opening a different empty profile SHALL create an independent node.

#### Scenario: Reopen preserves the node identity

- **WHEN** a node is created in profile A, its `NodeId` is observed, the process shuts down, and a new node assembly opens profile A
- **THEN** the reopened node reports exactly the same `NodeId`

#### Scenario: Separate profiles are separate nodes

- **WHEN** 2 nodes are initialized from distinct empty profile directories
- **THEN** they have distinct endpoint secret keys, distinct `NodeId` values, and no shared local documents or blobs

### Requirement: Documents, blobs, and author authority survive restart

The profile SHALL use persistent document and blob backends and SHALL restore author secret material through a protected secret-bearing backend. After reopen, every cataloged replica and its available payload blobs SHALL be readable, and the restored runtime author SHALL append to replicas it could write before shutdown without minting a replacement author.

#### Scenario: Reopened author reads and writes an existing replica

- **WHEN** a node creates a replica, writes an entry and payload with its runtime author, shuts down, and reopens the same profile
- **THEN** the entry and payload are readable and a second write by the restored author succeeds in the same replica

#### Scenario: Missing payload storage fails visibly

- **WHEN** a cataloged document references a locally available payload but the profile's blob backend cannot be opened
- **THEN** startup fails and the node does not report the document as successfully reopened

### Requirement: Runtime assembly state is reconstructed before admission

The durable catalog SHALL record the exact local meaning needed to rebuild every hosted identity store set, prepared-but-not-yet-bound replica pair and opaque handle, issuer-to-namespace binding, tracked replica role and sync strategy, and grant-owned import. Startup SHALL first validate intent structure and perform catalog/secret-only recovery, then open persistent docs and blobs under closed admission, replay every operation whose deterministic rule touches those backends, and only afterwards reopen the resulting named replicas and rebuild registry and access state. It SHALL NOT infer a replica's role from an unreferenced document or declare a backend intent complete while that backend is closed. A prepared record SHALL carry exact stable backend identifiers and roles without inventing an issuer; binding or rollback SHALL be the only transitions out of that state.

#### Scenario: Several hosted identities reopen without crossing

- **WHEN** one profile hosts identities X and Y with distinct directory and data namespaces, writes one entry for each, shuts down, and reopens
- **THEN** X and Y are both restored, each resolves to its own namespaces and entry, and neither identity resolves to the other's namespace

#### Scenario: An unreferenced replica is not adopted

- **WHEN** the docs backend contains a replica that no committed catalog record or unfinished intent names
- **THEN** startup does not classify it as hosted, tracked, or bound to an issuer

#### Scenario: A prepared pair survives before its issuer exists
- **WHEN** a catalog intent records 2 prepared replicas under one opaque handle and the process stops before an issuer is derived
- **THEN** reopen restores or deterministically rolls back that exact pair without adopting another replica or fabricating an issuer binding

#### Scenario: Admission waits for restoration

- **WHEN** profile recovery has opened the stores but has not finished rebuilding the access state
- **THEN** no document-sync, pairing, linking, or runtime service request is accepted

### Requirement: Successor runtime security records use the durable catalog

The runtime catalog SHALL expose a disjoint `runtime-security/<owner>/<family>/<key>` facility for non-secret, versioned records owned by successor capabilities. The facility SHALL preserve opaque record bytes and schema version across reopen, track a monotonically increasing generation per key, and support a conditional batch that compares all expected generations and atomically writes or deletes all named records or none. It SHALL NOT interpret an owner's payload as data-layer assembly state.

A transition contained entirely in these records SHALL use one conditional batch. A transition that also changes documents, blobs, secret records, or runtime bindings SHALL first persist a versioned owner intent naming exact old/new generations and external targets, perform idempotent side effects, and commit the final record batch while clearing the intent. Startup SHALL replay every platform and owner intent before validating the owner's required records or admitting its service. A missing, malformed, unsupported-version, or generation-inconsistent required record SHALL fail that owner closed and SHALL NOT be reconstructed from process memory or current replicated arrival order.

Replay SHALL respect backend dependencies: catalog-only owner batches MAY replay before backend open, but an owner intent naming documents, blobs, replicas, bindings, or a secret whose deletion follows such work SHALL remain unfinished until the relevant persistent backend is open under the closed admission gate. Any protected secret input needed for that later replay SHALL be validated before the backend phase and retained until the intent reaches the transition that no longer needs it.

An outer forget operation SHALL mark the owner non-admissible and name its security-record prefix before deleting successor records or related secrets/replicas. It SHALL commit only after no surviving record references the removed owner. Diagnostics MAY expose record family, key, version, and generation but SHALL NOT expose secret bytes or opaque payload fields that the owner marks sensitive.

#### Scenario: A local security transition is all or nothing

- **WHEN** a successor conditionally advances several accepted-head records and one ceremony record in one batch
- **THEN** reopen observes either every new generation or every previous generation, never a mixture

#### Scenario: A cross-backend transition replays before admission

- **WHEN** a process stops after an owner intent commits but before its document write and final security-record batch complete
- **THEN** startup deterministically completes or rolls back the named transition before that owner's service or projection is published

#### Scenario: A required successor record is not inferred

- **WHEN** a required runtime-security record is missing, malformed, or has an unsupported owner schema version
- **THEN** the owner fails closed before admission and the runtime does not recreate it from replicated documents or cached process state

### Requirement: Catalog transitions are crash-consistent

Every operation that changes durable assembly state SHALL persist a versioned intent before its first backend side effect, use identifiers fixed in that intent, and commit the final catalog record before reporting success. Startup SHALL complete or roll back each unfinished intent by an operation-specific deterministic rule. A retry SHALL converge without creating a second replica, author, binding, or hosted identity.

#### Scenario: Restart after each namespace transition converges

- **WHEN** a process is stopped in turn after the intent, backend mutation, binding rebuild, and catalog commit of one namespace operation and the same profile is reopened after each stop
- **THEN** every reopen reaches the operation's one specified final or rolled-back state and no duplicate namespace or binding exists

#### Scenario: Disk full does not acknowledge a partial transition

- **WHEN** a catalog or backend write fails because the profile storage has no space
- **THEN** the operation returns an error, its final catalog record is not reported committed, and the next reopen sees an unfinished intent it can retry or roll back

### Requirement: Profile initialization is atomic and fail-closed

The endpoint key, protected runtime-author storage, and profile metadata SHALL be committed durably before an initialized profile is exposed. A missing or invalid required secret, corrupt catalog, unsupported profile version, unreadable backend, partial initialization, or non-empty unrecognized directory SHALL fail startup. Startup SHALL NOT replace a secret, create empty stores over existing state, skip an identity, or fall back to memory.

#### Scenario: A corrupt endpoint key never changes the node identity silently

- **WHEN** an initialized profile's endpoint-key file is malformed or missing
- **THEN** reopen fails with no endpoint bound and no newly generated key written

#### Scenario: Unsupported version is not migrated implicitly

- **WHEN** the profile header names a format version the runtime does not support
- **THEN** startup fails before mutating any profile component

#### Scenario: Interrupted first initialization has one outcome

- **WHEN** the process stops after generating an endpoint key but before the initialized profile header is durably committed
- **THEN** reopen follows the specified initialization recovery path and never exposes 2 different `NodeId` values for that profile

### Requirement: One process owns a profile

The runtime SHALL canonicalize the existing profile parent and require it and the profile root to be trusted owner-only directories: owned by the effective user with no group/other write bit on Unix, or protected by the equivalent current-account-only modification ACL on other supported platforms. A shared or otherwise untrusted writable parent SHALL be refused. It SHALL derive and acquire the operating-system-backed sibling lock before creating or validating the root and hold it until all durable components close. Before and under the lock it SHALL reject a final-component symlink/reparse point and any recognized profile component that is one. It SHALL record the root's stable file identity and, after the path-based docs/blob backends open, recheck that the same root is still at the canonical path before admission; mismatch closes all components and fails startup. Lock acquisition SHALL NOT create an entry inside the root or cause an empty root to be accepted as initialized. After acquisition, only an absent or empty real directory may initialize; a non-empty real directory SHALL carry a valid initialized header. A concurrent cooperative opener SHALL fail without opening backends or binding an endpoint. A process crash SHALL release the lock; a leftover sibling lock file SHALL have no bearing on profile recognition.

The local security boundary excludes a malicious process running as the same OS account, because that principal can already read or replace the owner-only endpoint and KERI secret records. Same-account runtime instances SHALL honor the sibling lock. Other accounts are excluded by the trusted parent/root permissions. This threat boundary is part of persistent profile configuration and SHALL be documented rather than implied to be descriptor-anchored isolation.

#### Scenario: Concurrent open is refused

- **WHEN** process A holds profile P open and process B attempts to open P
- **THEN** B receives a typed profile-in-use failure and does not start a node

#### Scenario: A symbolic-link alias cannot take a second lock

- **WHEN** process A holds a real profile path open and process B attempts to open a symbolic link whose final component resolves to that profile
- **THEN** B is refused before opening any backend because a profile root cannot be a symbolic link

#### Scenario: An untrusted profile parent is refused

- **WHEN** the canonical profile parent or root is writable by another non-administrator account
- **THEN** persistent startup fails before any backend opens or endpoint binds

#### Scenario: A path swap during open is detected

- **WHEN** the stable root identity after path-based backend open differs from the identity validated under the lock
- **THEN** startup closes every opened component and fails before admission

#### Scenario: Crash releases ownership for recovery

- **WHEN** the process holding profile P terminates without clean shutdown
- **THEN** a later process can acquire P and run catalog recovery

#### Scenario: Lock bootstrap does not initialize the profile

- **WHEN** a process acquires the sibling lock for an absent or empty profile root and terminates before writing the profile header
- **THEN** the root remains absent or empty, the next opener follows the ordinary initialization path, and no lock artifact is accepted as a profile header

### Requirement: Shutdown reports durable failures

Shutdown SHALL close one admission gate shared by runtime services and every supplied and built-in protocol, including docs, blobs, gossip, pairing, and linking; stop reconciliation and other producers; and drain all admitted sessions and catalog mutations. After quiescence, retained direct component handles SHALL run fallible `prepare_shutdown/flush` for catalog, docs, blobs, and gossip and mark their protocol handlers inert. `Router::shutdown()` SHALL run only after that prepare succeeds or its failure has been captured; the handlers' infallible shutdown hooks SHALL then perform no durability work and no mutation. The profile lock is released last. A bounded drain failure SHALL return an error and leave unfinished mutations recoverable. No handler may mutate durable state after prepare begins. A drain, prepare, flush, router, or close failure SHALL be returned to the caller rather than only logged. Where upstream APIs cannot return these failures, pinned workspace fork/adapter APIs are mandatory; logging inside an infallible handler is insufficient.

#### Scenario: Clean shutdown reopens all acknowledged writes

- **WHEN** writes and catalog operations have returned success and shutdown returns success
- **THEN** a new process opening the same profile reads every acknowledged write and committed catalog record

#### Scenario: Flush failure reaches the host

- **WHEN** a durable component fails its shutdown flush
- **THEN** shutdown returns a failure and the profile lock is not released before the component close path completes

#### Scenario: A built-in session cannot race the final flush

- **WHEN** a docs, blobs, gossip, pairing, or linking session is active when shutdown begins
- **THEN** the admission gate refuses new work, the admitted session drains or leaves a recoverable intent before fallible prepare, and no durable mutation occurs after prepare starts or during the later router shutdown hook

### Requirement: In-memory storage is explicit

An in-memory node SHALL be available only through an explicitly named test/development storage mode. A production persistent constructor SHALL require a profile path and SHALL NOT select memory because a path is missing, invalid, or unwritable.

#### Scenario: Tests opt into memory

- **WHEN** a unit or scenario test requests the explicit in-memory mode
- **THEN** the node uses memory documents and blobs and makes no restart-persistence guarantee

#### Scenario: An unwritable profile does not become an in-memory node

- **WHEN** production startup receives a profile directory it cannot write
- **THEN** startup fails and no in-memory node is created

### Requirement: All secret-bearing profile material is locally protected

The profile root and every secret-bearing component SHALL use owner-only permissions on platforms that support them. This includes the endpoint secret key, the backend's runtime author secrets, and every versioned opaque secret record used by later capabilities, including KERI root and device keys. Secret records SHALL be stored separately from non-secret catalog metadata and secret bytes SHALL never appear in headers, diagnostics, logs, or error text. A failure to establish or validate required permissions SHALL fail initialization or reopen before any secret is used. Missing, malformed, unreadable, or permission-invalid required secret material SHALL NOT be skipped, regenerated, or replaced with memory state.

#### Scenario: Profile inspection exposes no secrets through metadata

- **WHEN** the profile header and runtime catalog are decoded for diagnostics
- **THEN** neither contains endpoint, runtime-author, KERI, or generic secret-record bytes

#### Scenario: Secret permission setup fails closed

- **WHEN** the platform supports owner-only permissions and initialization cannot apply them to the root or any secret-bearing component
- **THEN** initialization fails before the profile is marked complete

#### Scenario: Reopen validates every required secret
- **WHEN** the endpoint key, runtime author secret, or a registered generic secret record is missing, unreadable, malformed, or permission-invalid
- **THEN** reopen fails before service admission without logging or generating replacement bytes

### Requirement: Generic secret lifecycle is crash-consistent

Every generic secret SHALL have a versioned opaque handle, a secret type, an owner, and cataloged lifecycle state; secret bytes SHALL exist only in the protected secret record. Before the first secret of a multi-secret owner, the catalog SHALL persist an outer owner intent containing every preallocated handle, type, and non-secret recovery input while the owner remains non-admissible. Creation SHALL durably record `CreateSecret(owner, handle, type)` before any secret-file side effect, write through an owner-only same-directory temporary file, sync, atomically rename and sync the parent, and register the handle as required under that outer intent while clearing the inner intent. One catalog transaction SHALL make the owner active and clear the outer intent only after every required handle is registered. Recovery SHALL deterministically complete an owner whose recorded inputs suffice or unregister/delete all its handles; a registered handle not named by a committed owner or unfinished outer intent SHALL be removed and SHALL NOT be adopted. Recovery of any standalone uncommitted create SHALL delete its temporary and final files, sync the parent, and clear the intent; file presence SHALL NOT register or adopt it.

Deletion SHALL durably record `DeleteSecret(handle)` and mark the owning identity or operation non-admissible before unregistering the handle. It SHALL then atomically remove the handle from the required-secret set, delete the record, sync the parent, and clear the intent before reporting success. Every step and its recovery SHALL be idempotent. An outer identity-forget intent SHALL list the affected handles, make the identity non-admissible first, drive their delete transitions, and commit only after no surviving catalog record references them.

Startup SHALL validate header, catalog structure, secret-area permissions, and intent schemas; replay secret-only outer-owner/create/delete work that has no backend dependency; then validate the endpoint, runtime-author, and every protected input required by a remaining cross-backend intent. It SHALL open docs/blobs under closed admission, replay cross-backend and outer-forget work in its recorded order, and only then validate all secrets that remain registered in the final catalog. A secret under an unfinished deletion SHALL not fail the pre-backend phase merely because its bytes are already absent when no later step needs it; a secret under an unfinished outer owner is completed only through that owner or deleted. Conversely, a secret such as a protected verified-ticket pair that a pending import needs SHALL fail closed if missing or invalid before that import replays. No service or router SHALL observe an identity between non-admission and completed recovery.

#### Scenario: Cross-backend replay waits for an open backend

- **WHEN** startup finds an intent whose next idempotent step imports a document replica or mutates a blob, binding, or tracked role
- **THEN** it leaves that intent unfinished through structural recovery, opens the required backend under closed admission, and only then completes or rolls back the recorded step

#### Scenario: A crash at any standalone secret-create boundary leaves no adopted secret

- **WHEN** the process stops after any transition of a secret create that has no committed owner and no unfinished outer-owner intent
- **THEN** reopen rolls the create back, removes all named temporary or final records, and exposes neither the handle nor its owner

#### Scenario: A crash between key registration and owner commit leaves no orphan

- **WHEN** a KERI creation or linking attempt stops after any one of its secret handles is registered and before its active owner record commits
- **THEN** reopen follows the durable outer intent to complete that exact owner or deletes every handle it names, and no registered key survives without a committed owner or unfinished intent

#### Scenario: A crash at any secret-delete boundary completes deletion

- **WHEN** the process stops after delete intent, unregister, or file removal
- **THEN** reopen completes the deletion without treating that handle as a missing required secret and without admitting its owner

#### Scenario: Forget cannot strand an identity behind a deleted key

- **WHEN** identity forget stops after one KERI key record is deleted but before every catalog and replica transition completes
- **THEN** reopen resumes the outer forget before required-secret validation or admission, deletes the remaining named keys, and leaves no committed identity reference to any deleted handle
