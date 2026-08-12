## 1. Profile foundation

- [ ] 1.1 Add a versioned layout with header, protected secret area, endpoint secret record, blob/docs stores, runtime catalog, and sibling lock. Define a versioned opaque secret-record API for successor capabilities.
- [ ] 1.2 Implement atomic initialization with file and parent sync and owner-only permissions, where supported, on the root and every secret-bearing path; validate them again at reopen.
- [ ] 1.3 Load the canonical endpoint key into iroh and refuse missing, malformed, unreadable, or permission-invalid endpoint/runtime-author/registered secret records without replacement or memory fallback.
- [ ] 1.4 Implement the selected trusted-parent model for path-based backends: canonical parent/root owned by the current account and not modifiable by other non-administrator accounts; final root and recognized components are not symlinks/reparse points; stable root identity is rechecked after backend open; shared/untrusted writable parents fail before backend open. Document that malicious same-account processes are outside the boundary and cooperative runtimes must honor the sibling lock.
- [ ] 1.5 Reject unsupported versions, partial or corrupt metadata, and non-empty unrecognized directories before mutating any profile component.
- [ ] 1.6 Implement crash-consistent generic secret CRUD: preallocated handles under a durable outer owner intent, owner-linked create/delete intents, same-directory atomic writes and sync, required-secret registration, atomic owner activation only after all handles exist, deterministic complete-or-delete recovery, non-admissible owner state, and structural replay before validation of remaining required secrets.

## 2. Persistent backends

- [ ] 2.1 Enable the filesystem-store features required by the pinned `pdn-store` and `iroh-blobs` versions.
- [ ] 2.2 Assemble persistent nodes with `Docs::persistent` and `FsStore`, while preserving the existing access provider, capability validator, rejection observer, gossip, blob, document, and supplied-protocol wiring.
- [ ] 2.3 Restore the runtime author from persistent author storage and prove it can append to a replica created before restart.
- [ ] 2.4 Add retained component handles and a split-phase fallible `prepare_shutdown/flush` API for catalog, docs, blobs, and gossip. Extend and pin the workspace `pdn-store` fork and, where upstream `iroh-blobs`/gossip APIs are infallible, add a pinned workspace adapter/fork recorded in `Cargo.lock`. After prepare, every `ProtocolHandler::shutdown() -> ()` hook is idempotent transport teardown and performs no write/flush; no durability error is only logged.

## 3. Durable runtime catalog

- [ ] 3.1 Define versioned catalog records for the runtime author, hosted store sets, prepared-but-unbound replica pairs and opaque handles, issuer bindings, tracked roles, grant imports, and disjoint successor-owned `runtime-security/<owner>/<family>/<key>` records with generations.
- [ ] 3.2 Implement atomic conditional multi-record batches and versioned write-ahead intents with expected generations, exact external targets, and deterministic complete-or-rollback recovery for platform and successor-owned operations.
- [ ] 3.3 Route identity provisioning, prepared-pair create/bind/rollback, namespace create/import/undo/forget, host registration, tracking changes, and grant ownership through intent-before-side-effect and commit-before-success transitions.
- [ ] 3.4 Implement phased startup under one closed admission gate: validate structure and intent schemas; mark affected owners non-admissible; replay catalog/secret-only work; validate endpoint/runtime-author and every secret needed by pending backend work; open docs/blobs; replay namespace/replica/binding/bootstrap-import/outer-forget/successor cross-backend intents; then reopen exactly the final cataloged replicas and leave unreferenced replicas unclassified.
- [ ] 3.5 After every backend intent is resolved, validate final required secrets and every registered owner's required security-record schema, and rebuild registry, hosted identity, access-book, tracked-replica, grant-binder, and successor security projections before endpoint, services, or router are admitted. Never mark a cross-backend intent complete while its backend is closed.
- [ ] 3.6 Ensure catalog keys preserve separation for several identities hosted on one node and never infer identity ownership from node-level co-location.
- [ ] 3.7 Make identity forget an outer intent that records all secret handles, marks the identity non-admissible before the first unregister/delete, completes every generic delete, and removes the last reference before commit.

## 4. Runtime and host integration

- [ ] 4.1 Add explicit `Persistent { root }` and named `Memory` storage modes to `SyncNode`, with no fallback from a failed persistent open to memory.
- [ ] 4.2 Change the production `Runtime` constructor to require a profile directory and expose a clearly named in-memory constructor for tests and development.
- [ ] 4.3 Delay protocol-router publication, handler state publication, and all runtime service handles until profile recovery and access reconstruction succeed.
- [ ] 4.4 Update HTTP hosts and binaries to supply a configured profile directory and to stop startup when profile recovery fails.
- [ ] 4.5 Give runtime services and all supplied/built-in docs, blobs, gossip, pairing, and linking handlers one admission gate. Shutdown closes that gate, stops producers, drains all admitted sessions/catalog mutations, invokes retained-handle fallible `prepare_shutdown/flush`, and only then calls `Router::shutdown()` whose handler hooks are inert. Release the profile lock last; propagate every drain/prepare/router/storage failure and permit no mutation after prepare begins.
- [ ] 4.6 Move non-restart tests to the explicit in-memory constructor and give each durable test its own temporary profile directory.

## 5. Deterministic storage tests

- [ ] 5.1 Add a process-level reopen test proving one profile preserves `NodeId`, one distinct profile gets a different `NodeId`, and neither profile sees the other's local stores.
- [ ] 5.2 Add a reopen test proving an existing entry and payload remain readable and the restored author can write a second entry to the same replica.
- [ ] 5.3 Add a restart test with 2 co-hosted identities proving both appear in the first admitted status response and each resolves only its own directory and data namespace.
- [ ] 5.4 Add an admission barrier test proving built-in protocols, supplied protocols, and runtime services cannot run against a partially rebuilt access book.
- [ ] 5.5 Inject a process stop after every intent transition for prepared-pair create/bind/rollback and namespace create/import/bind/forget; prove reopen reaches one state with no duplicate replica, handle, or binding.
- [ ] 5.6 Add a fixture with an unreferenced backend replica and prove recovery does not adopt, bind, host, or track it.
- [ ] 5.7 Add concurrent-open, symbolic-link/reparse alias, untrusted-parent permission, root-identity swap-during-open, crash-release, and lock-bootstrap tests. Prove another-account-writable parents are refused, a swapped root is detected before admission, a cooperative second process is locked out, and a crash after lock creation but before header creation leaves an absent/empty root that initializes normally.
- [ ] 5.8 Inject a process stop after every outer-owner, create-secret, owner-activation, delete-secret, and outer-forget transition; prove reopen completes the exact recorded owner or deletes all of its handles, never leaves a registered orphan, completes deletes before required-secret validation, never admits a forgetting identity, and leaves no catalog reference to deleted bytes.
- [ ] 5.9 Inject a stop before and after a successor conditional batch, owner-intent commit, protected replay-input creation, backend open, external document/blob side effect, final batch, and replay-input deletion. Prove structural recovery leaves backend-dependent intents unfinished, protected inputs remain until no longer needed, cross-backend work runs only after backend open and before owner admission, reopen exposes all old or all new local security generations, and no missing required record is inferred from replicated state.

## 6. Failure and security tests

- [ ] 6.1 Inject missing and malformed endpoint-key files and prove startup fails before binding and never writes a replacement key.
- [ ] 6.2 Inject unsupported header version, corrupt catalog, unreadable docs/blob stores, partial initialization, and a non-empty unrecognized directory; prove each fails before service admission or profile mutation.
- [ ] 6.3 Inject disk-full failures at catalog intent, backend mutation, catalog commit, and shutdown flush; prove no partial operation is acknowledged and the remaining intent is recoverable.
- [ ] 6.4 Verify header/catalog/diagnostics never expose endpoint, runtime-author, or generic secret bytes; test owner-only root and secret paths plus fail-closed reopen for missing, malformed, unreadable, and permission-invalid registered secrets.
- [ ] 6.5 Prove an unwritable persistent path returns an error and does not instantiate the explicit memory mode.
- [ ] 6.6 Prove successful shutdown makes every acknowledged write visible after reopen and an injected flush failure reaches the host as a typed shutdown error.
- [ ] 6.7 Prove a missing secret under an unfinished delete is replayed rather than rejected early, while a missing secret still registered after replay fails closed before admission.
- [ ] 6.8 Hold each built-in docs/blobs/gossip/pairing/linking handler open across shutdown; prove the shared gate refuses new streams, admitted work drains or leaves a recoverable intent before fallible prepare, retained handles surface injected catalog/docs/blob/gossip failures, later router hooks are inert, no post-prepare mutation occurs, and every drain/prepare failure reaches the host.

## 7. Verification and documentation

- [ ] 7.1 Update API and host documentation with profile ownership, storage layout, explicit in-memory mode, failure behavior, and the absence of encryption or backup guarantees.
- [ ] 7.2 Run `cargo fmt --all --check`, targeted data-layer and runtime tests, `cargo nextest run --workspace`, and `cargo clippy --workspace --all-targets --all-features -- -D warnings`.
- [ ] 7.3 Run the affected data-layer and runtime restart scenarios under the repository stress guidance and record the exact harness pool and result.
- [ ] 7.4 Run `openspec validate durable-runtime-storage --strict` and keep `keri-backed-device-linking` blocked until this checklist is complete.
