## Context

`SyncNode` is assembled in `crates/data-layer/src/node.rs` with `MemStore::default()`, `Docs::memory()`, and a freshly generated endpoint key. `Runtime` then creates a new author and fills identity, namespace-binding, access, tracking, and grant-binder maps only in memory. The `pdn-store` fork already exposes `Docs::persistent(path)`, including persistent replica and author storage, and `iroh-blobs` exposes `FsStore`; iroh accepts an explicit `SecretKey`. The missing work is one coherent profile lifecycle around those pieces and durable reconstruction of the runtime state that gives stored replicas meaning.

The storage directory is a security boundary. Replacing a missing endpoint key changes `NodeId`; treating an unreadable catalog as empty drops authorization and hosting state; opening one profile twice permits two processes to write the same databases. Startup therefore fails closed instead of regenerating or adopting state heuristically.

## Goals / Non-Goals

**Goals:**

- Reopen the same endpoint identity, documents, blobs, author identities, namespace bindings, hosted identities, and tracked-replica roles from one explicit profile directory.
- Make initialization and catalog-changing runtime operations crash-consistent and idempotently recoverable.
- Rebuild derived access and reconciliation state before any protocol or service call is accepted.
- Return initialization, write, flush, corruption, version, permission, and concurrent-open failures to the caller.
- Keep a fast explicitly selected in-memory assembly for unit and scenario tests that do not exercise restart behavior.

**Non-Goals:**

- KERI event semantics, the contents of creation/linking records, accepted-head policy, or ceremony recovery decisions; `keri-backed-device-linking` assigns those meanings. This change owns the generic protected-secret, prepared-replica, and opaque runtime-security-record facilities, including atomic local batches and intent replay, so the successor does not invent another durability mechanism.
- Encryption at rest, user-exportable backups, cloud backup, profile synchronization, or secret recovery.
- Live relocation of an open profile, concurrent multi-process access, or automatic repair of corrupt databases.
- Changing reconciliation, capability, or revocation semantics. This change only makes their durable source records and local bindings reopenable.

## Decisions

### D1. Production construction takes an explicit durable profile

`Runtime` and `SyncNode` receive a storage mode. The production entry point requires `Persistent { root }`; `Memory` is exposed through an explicitly named test/development constructor and is never an implicit fallback. The current zero-argument production spawn is removed or changed to require the profile, so a host cannot accidentally promise persistence while running in memory.

An empty directory initializes profile format version 1. A non-empty directory without a valid profile header is refused. The final profile-path component must be a real directory or absent, never a symbolic link; symbolic links in its parent path are resolved by canonicalizing the existing parent. This is stricter than probing individual backend files: silent partial adoption cannot distinguish an interrupted initialization from unrelated files, and refusing a final symlink prevents 2 lexical paths to one backend from taking different sibling locks.

### D2. One versioned profile owns every durable component

The root contains a versioned profile header, protected secret area, blob-store directory, docs-store directory, and runtime catalog database. The endpoint key is one versioned secret record; later components may add named opaque secret records without changing the catalog format. The root, secret area, endpoint record, runtime-author secret storage, and every later secret-bearing record are restricted to the current user where supported. Secret bytes never enter logs, errors, tickets, headers, or general catalog. Initial creation writes through same-directory temporary files, syncs, atomically renames, and syncs the parent before marking initialization complete.

Generic secret records have cataloged lifecycle state, not merely files. A multi-secret owner first persists an outer intent/record containing every preallocated handle, secret type, and non-secret recovery input. Each `CreateSecret` intent names that owner; it writes and syncs an owner-only same-directory temporary record, atomically renames and syncs the secret directory, then registers the handle as required under that still-non-admissible owner and clears the inner intent. Only after all required handles exist may one catalog transaction commit the active owner record and clear the outer intent. Recovery deterministically completes the owner when its recorded inputs suffice, otherwise unregisters and deletes every handle named by the outer intent. Thus a registered handle is always reachable from a committed owner or unfinished outer intent and is never an orphan between key registration and KERI creation/attempt state. Recovery of a standalone uncommitted create removes any temporary or final record, syncs the directory, and clears the intent; it never guesses that a file is registered. Delete first persists a `DeleteSecret` intent and marks the owning operation/identity non-admissible, then atomically unregisters the handle from the required-secret set, deletes its record and syncs the directory, and finally clears the intent. Recovery repeats those steps idempotently. Success is reported only after the final intent transition is durable.

`Docs::persistent` remains the owner of replica and author persistence, and `FsStore` remains the owner of blob persistence. The runtime catalog stores assembly meaning those backends do not know: the stable runtime author identifier, hosted identity store sets, issuer bindings, tracked roles, grant ownership, and prepared-but-unbound replica pairs under versioned opaque handles. It also exposes a disjoint `runtime-security/<owner>/<family>/<key>` namespace for successor-owned, non-secret, versioned security records whose bytes and interpretation remain the successor's responsibility. A prepared record names exact backend identifiers and roles but no issuer; only its explicit bind transition may turn it into a hosted set. Contact sets, access projections, in-flight nudges, live sessions, and subscribers remain derived or ephemeral; a successor's expressly registered security records do not.

Within the catalog, a conditional batch compares the expected generation of every touched key and atomically writes/deletes all of them or none. A successor uses that batch for transitions contained entirely in local security state. A transition that also mutates docs, blobs, secrets, or another backend first persists a versioned successor-owned intent naming exact old/new record generations and exact external targets; recovery deterministically completes or rolls it back before the owning service is admitted. Opaque payloads never exempt the owner from schema-version validation: an unsupported or malformed required successor record fails that owner closed rather than being treated as absent.

### D3. The catalog is write-ahead and recovery is deterministic

Every operation that changes durable assembly or registered runtime security state records a versioned intent in the catalog before mutating docs, secrets, or runtime bindings, performs idempotent backend steps, commits the final catalog batch, and only then reports success. Startup replays unfinished platform and successor-owned intents before exposing the node. Each intent names exact identifiers and expected generations fixed before its first side effect; recovery reuses those values and never adopts an unreferenced replica, secret, or security record merely because it exists. A cross-component forget intent is the outer transaction: it first makes the identity non-admissible and records every secret handle, replica, and successor-security prefix to delete, then drives each transition and commits last. No committed admissible identity may reference an unregistered secret or incomplete required security record.

This is preferred over periodically serializing the in-memory maps: a snapshot can acknowledge a namespace operation before the snapshot reaches disk, and cross-store transactions are unavailable. It is also preferred over scanning all documents and guessing their roles: the docs backend cannot infer whether a replica is an identity directory, owned data, an out-of-band import, or a grant-bound import.

### D4. Startup restores authority before opening the router

Startup takes the exclusive lock, closes admission, and validates the profile header, root and secret-area permissions, catalog structure, and every intent schema without opening a network service. Recovery is deliberately phased because an intent that names a docs/blob mutation cannot be replayed against a backend that is still closed:

1. Mark every owner named by an unfinished operation non-admissible. Replay catalog-only and secret-only transitions whose complete-or-rollback rule needs no docs/blob access, and structurally classify the remaining cross-backend intents. An unfinished create is completed only through its recorded outer owner or rolled back, never promoted by file presence.
2. Validate the endpoint and runtime-author secrets plus every generic secret required to open a backend or replay a remaining intent. A handle under a structurally valid unfinished delete is not treated as a missing required secret when no later replay step needs its bytes; a protected bootstrap-ticket pair required by an unfinished import is validated here and cannot be skipped.
3. Open blobs and docs, restore the runtime author, and keep all protocol/runtime admission closed. Replay every namespace, replica, binding, outer-forget, bootstrap-import, and successor cross-backend intent against those open backends. Only now may recovery complete document/blob side effects and the secret deletions ordered after them.
4. Validate the resulting catalog, every remaining required secret, and every required successor record through its registered owner; reopen exactly the committed replicas, rebuild derived state, and only then publish the endpoint, router, and services.

No phase may classify an unfinished cross-backend intent as complete merely because its backend was closed. Missing, unreadable, malformed, unsupported, or permission-invalid material needed by the current phase fails closed; no replacement is generated and no reduced security state is exposed.

The catalog is local authoritative state for assembly, while replicated documents remain authoritative for grants, device membership, and other domain facts. Rebuild reads current durable document state when deriving access. It does not preserve a stale cached authorization decision merely because that decision existed before shutdown.

### D5. One operating-system lock owns one profile

The selected containment model matches the path-based `Docs::persistent(PathBuf)` and `FsStore` APIs: the canonical existing profile parent and profile root are trusted owner-only directories. On Unix each is owned by the effective user and has no group/other write bit; on ACL platforms the equivalent policy denies modification to principals other than the current account and administrators. Startup validates that policy before and again under the sibling lock, rejects final-component symlinks/reparse points and every recognized component that is one, records the root's stable file identity, and rechecks identity immediately after opening all backends and before admission. A mismatch fails closed and closes every opened component. Persistent profiles in shared or untrusted writable parents are unsupported.

This deliberately excludes a malicious process running as the same OS account from the isolation boundary: that process can already read or replace owner-only KERI and endpoint secrets. Same-account runtime instances are required to honor the sibling advisory lock; different accounts are stopped by the trusted-parent permissions. Under the acquired lock startup inspects the checked root: an absent or empty real directory follows initialization; a non-empty real directory must carry the valid initialized header; every other state is refused. A second cooperative opener fails with a typed profile-in-use error. The lock is released by the operating system after a crash, unlike a persistent boolean that can strand the profile; a sibling lock file left behind is never profile content and does not mark initialization complete, and the durable journal repairs any interrupted profile operation.

### D6. Shutdown is fallible and ordered

Shutdown is split-phase because `iroh::Router::shutdown()` combines transport shutdown with infallible handler hooks. First, one shared admission gate used by runtime services, supplied protocols, and every built-in docs, blobs, gossip, pairing, and linking handler closes. Reconciliation and all producers stop, and every admitted session/catalog mutation drains. The runtime retains direct component handles and calls a workspace-owned fallible `prepare_shutdown/flush` seam for catalog, docs, blobs, and gossip while handlers are idle; that seam marks them quiescent, returns durability failures, and makes their later `ProtocolHandler::shutdown() -> ()` hooks idempotent transport teardown with no write or flush responsibility. Only then does `Router::shutdown()` stop the endpoint and invoke those inert hooks. The profile lock is released last. If pinned upstream APIs cannot provide the seam, the workspace SHALL extend its `pdn-store` fork and add a pinned local adapter/fork for `iroh-blobs`/gossip rather than log or discard an error. No handler may append after prepare begins. Any drain, prepare, flush, router, or close error is returned. A later reopen still runs recovery because a successful shutdown marker is an optimization, not proof that no lower layer needs recovery.

The existing docs protocol logs shutdown failures instead of returning them, so implementation either exposes a fallible engine flush/close path in the fork or retains a component handle that can be flushed explicitly before router shutdown. Logging alone does not meet the contract.

### D7. Operating conditions

Several identities on one node changes the outcome: the catalog keys hosted store sets and bindings by identity and restart tests restore at least 2 co-hosted identities without crossing their namespaces. One device or several does not change the local profile format; replicated device membership is document state and is re-read during access rebuild. Linking before, during, or after matters only through catalog intents: any local binding operation interrupted by restart is replayed before service admission. An unstable connection does not alter durability; reopened tracked replicas resume the ordinary reconcile mechanisms. A full disk changes every write and shutdown outcome and is reported loudly without committing the catalog transition. Restart is the primary condition and has process-level reopen scenarios. Capability movement does not add a new durable cache: current grant and tombstone records are read from reopened documents, so grant, withdrawal, and re-grant behavior remains in the neighboring capabilities.

## Risks / Trade-offs

- [Risk] A catalog intent and a backend step can be separated by a crash. → Each intent carries stable identifiers and every recovery step is idempotent; tests inject a stop after each transition.
- [Risk] Secret-key file permissions vary across platforms. → Enforce owner-only permissions where supported, document the platform limitation, and never broaden permissions as a fallback.
- [Risk] Reopening many replicas delays startup. → Restore correctness before availability; measure and later add checkpoints or bounded parallelism without admitting requests against a partial access book.
- [Risk] The persistent backends can migrate independently of the profile header. → Pin compatible backend versions in one profile-format version and reject an unsupported combination before mutation.
- [Risk] A disk-full error can occur during error recovery or shutdown. → Preserve the unfinished intent, return the failure, and let the next reopen retry; never mark the transition complete merely to unblock shutdown.
- [Risk] Explicit persistent construction touches most tests. → Provide one clearly named in-memory helper for tests and use temporary durable profiles only for restart and storage-failure scenarios.

## Migration Plan

There is no durable runtime state to migrate from the current in-memory assembly. Hosts choose a new empty profile directory on first deployment. Initialization is atomic: if it does not complete, the next launch resumes or refuses the incomplete profile according to the header state, without generating a second endpoint key.

Rollout first lands the data-layer profile and process-level reopen tests, then changes runtime and host constructors, then moves existing non-restart tests to the explicit in-memory helper. `keri-backed-device-linking` implementation begins only after this change validates and its reopen suite passes.

Rollback to a binary that lacks durable profiles cannot open the new directory and therefore cannot preserve its state; rollback means retaining the directory untouched and running the earlier binary only against a separate disposable in-memory instance. No downgrade writer is provided.
