## Why

`SyncNode` currently uses `MemStore` and `Docs::memory()`, and binds an endpoint without restoring its secret key. A process restart therefore loses documents, blobs, authors, runtime bookkeeping, and the transport identity; any feature that promises restart recovery or stable `NodeId`-addressed records needs a durable runtime foundation first.

## What Changes

- **BREAKING** Production runtime spawn requires an explicit storage directory and reopens one durable node profile from it; the existing in-memory assembly remains available only through an explicitly named test/development constructor.
- The storage directory persists the blob store, document engine state, runtime author secrets, and versioned secret records needed by later profiles. The profile root and every secret-bearing component use owner-only permissions where the platform supports them; diagnostics never contain secret bytes and reopen fails closed on missing, unreadable, malformed, or permission-invalid secrets.
- The iroh endpoint secret key is created once, committed before the endpoint is exposed, and restored on every reopen so the same directory has the same `NodeId`.
- A small versioned runtime catalog records the storage format, the namespaces that must be reopened, durable opaque handles for prepared but not yet issuer-bound replica pairs, and versioned successor-owned runtime security records. Atomic conditional batches and write-ahead intents let a successor couple local security records and recover cross-backend transitions before admission.
- Opening the same profile concurrently is refused. Missing, corrupt, unsupported, partially committed, or unreadable identity/storage metadata fails startup loudly and never falls back to a fresh node or empty stores.
- Shutdown flushes durable components and returns write/flush failures. Restart tests stop the first process cleanly and reopen the same directory in a new process-level assembly.

## Capabilities

### New Capabilities

- `data-layer-durable-runtime-storage`: durable node profile layout, protected endpoint/runtime-author/generic secret material, documents, blobs, authors, prepared replica handles, manifest versioning, exclusive open, reopen behavior, and failure semantics.

### Modified Capabilities

- `pdn-node-core`: runtime construction takes a storage profile, restores the data-layer node before accepting service calls, and exposes in-memory mode only through an explicit non-production path.

## Impact

- `crates/data-layer/src/node.rs`: persistent blob and docs backends, endpoint-key restore, author restore, durable tracked-namespace metadata, the opaque runtime-security-state catalog facility, exclusive profile ownership, flush and reopen paths.
- `crates/pdn-node/src/runtime.rs`: storage-root configuration, startup ordering, restoration of runtime-derived registries, and shutdown error propagation.
- `crates/pdn-node-http` and host binaries: pass an explicit profile directory into runtime startup.
- Scenario tests that call the default spawn helpers move to the explicitly in-memory test constructor or temporary durable profiles.
- This change is the hard prerequisite of `keri-backed-device-linking`; it contains no KERI events or identity-specific recovery policy. It provides generic protected secret records, prepared-replica records, and versioned successor-owned runtime-security records with atomic batch/intent recovery. The successor assigns KERI meaning to those opaque records.
