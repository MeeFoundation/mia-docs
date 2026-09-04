# Proposal: disk-persistence

## Why

A node keeps everything in memory and mints a fresh wire key on every start: the replicas, the blobs, the identities it hosts, the connections it established and the grants it imported all end with the process, and what comes back up carries a new node id. A stopped container is therefore not a node that went away and returned — it is a node that never existed, and the one that replaces it is a stranger to every device record and every ticket the old one handed out. The stand can stop a device and has nothing to assert about starting one again, the demo re-establishes every connection from nothing on each run, and the scale measurement that wants 1,000,000 claims has only RAM to put them in, where the node runs out of memory before it runs out of reconciliation.

Persistence is what turns "the state survived" into a property that can be asserted at all, and the container stand is what makes it assertable: a restart is a container restart, not something an in-process test can stage.

## What Changes

- **Storage becomes an explicit configuration of the spawn, with no default.** A node is spawned on memory or on a directory, both by name: the runtime's production consumer is a mobile application that embeds it and passes a directory inside its own sandbox, the workspace's suites want memory and say so, and a default in either direction serves nobody. Given a directory, the node keeps its replicas in redb, its blobs on the filesystem, and its author beside them — the fork already offers both shapes, so the sync and egress code is the same code either way.
- **The node's secret key lives in that directory.** Without it the node comes back under a new wire id while its own device record, its tickets and its peers' contacts all name the old one: a node that remembers a device that no longer exists and cannot be reached by anything it ever handed out. That failure looks like a working node, which makes the key not an addition to persistence but a condition of it.
- **One author per node, persisted with the stores.** Each store mints an author of its own at construction today, so a restarted node reads its own past entries as another writer's — the directory's own-entry checks compare `entry.author()` against the author held in memory, and a retraction marker names an author and a path. The persisted default author the fork keeps next to its replicas becomes the node's one author.
- **Hosted identities survive the restart, and everything else re-derives from them.** A small durable file names what this node hosts: each identity and the namespace of its private metadata directory — replaced whole on every change, so a kill cannot half-write it. Nothing else is written down, because nothing else has to be — the directory is already the durable record of an identity's own state (Invariant 1), so the data namespace comes back from its `data` ticket, the connections from the `connections/` records, each connection's metadata pair from its two published tickets, and the granted namespaces from the counterparty's grants through the binder that already sweeps them. Recovery walks the product path the identity's other devices walk, rather than a second bookkeeping of its own.
- **A directory belongs to one running node.** The replica store takes an exclusive lock on its file, so a second process on the same directory refuses to start; the refusal names the directory and the cause rather than arriving as a lock error from three layers down.
- **The host requires `PDN_DATA_DIR`** and stops without it — the host exists for the container stand and offers no in-memory mode. The image sets the variable to its own data directory, so a container needs no per-node configuration, and the demo's compose file gives each node a volume of its own. The demo still starts clean — its teardown removes the volumes with the nodes — and gains one step that stops a node and starts it again, which is the show the persistence is for.
- **The stand tests a restart.** The scenario that today asserts a stopped device is never started again is replaced by one that starts it, after a clean stop and after a kill alike: the same node id, the same identity, the connection and the grant still in force, an entry written before the stop still readable, and no ceremony repeated. Its denial is in the same place — a node started on an empty directory holds none of it.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree.

| Capability (delta)             | Archive destination                                        |
| ------------------------------ | ---------------------------------------------------------- |
| `data-layer-durable-storage`   | `openspec/specs/components/mee-pdn/data-layer/durable-storage.md`  |
| `pdn-node-restart-recovery`    | `openspec/specs/components/mee-pdn/pdn-node/restart-recovery.md`   |
| `pdn-node-http-host`           | `openspec/specs/components/mee-pdn/pdn-node-http/host.md`          |
| `pdn-node-container-stand`     | `openspec/specs/components/mee-pdn/pdn-node-http/container-stand.md`    |

### New Capabilities

- `data-layer-durable-storage`: what a node keeps on disk and where — the explicit storage configuration at spawn (memory or a directory, both by name and neither a default), the directory's contents (replicas, blobs, author, secret key), the wire identity that is stable across starts because that key is, and the single running node per directory.
- `pdn-node-restart-recovery`: what the runtime holds after a restart — the durable record of the identities this node hosts, recovery of each along the product path (directory, then data namespace, connections, metadata pairs, granted namespaces), the order that makes an interrupted create or link fail closed rather than half-host an identity, and what deliberately does not survive (invites in flight, ceremonies in flight).

### Modified Capabilities

- `pdn-node-http-host`: the host reads where its state lives from the environment, beside the two bind variables and the debug flag it already reads, and refuses to start when the variable is unset or the directory unusable — it offers no in-memory mode to fall back to.
- `pdn-node-container-stand`: the scenario stating that a stopped node is never started again is replaced by the restart scenario; the image and the demo's compose file carry a volume per node; the demo's teardown removes the volumes, so a run still never meets the previous run's state.

## Impact

- **`crates/data-layer`**: the spawn options gain a required storage configuration — memory or a directory, by name; `Docs::persistent` and a filesystem blob store replace their in-memory counterparts when a directory is configured; the endpoint binds with a key read from that directory or generated and written on first start; stores take the node's persisted author instead of minting one each; a way to open a store on a namespace the node already holds, which recovery needs and which nothing offers today (`create` and `import` are the two constructors).
- **`crates/pdn-node`**: the runtime writes the hosted-identities file when an identity is created or linked and removes an entry when hosting ends; at spawn it reads that file and re-hosts each identity through the same steps `create` performs after provisioning — register the directory for session classification, insert the hosted entry, start the connection armer — which brings connections, metadata pairs and granted namespaces back by themselves.
- **`crates/pdn-node-http`**: `PDN_DATA_DIR` read beside `PDN_HOST`, `PDN_PORT` and `PDN_DEBUG`, required, and passed into the runtime spawn; unset stops the start.
- **`ops/`**: the image sets `PDN_DATA_DIR` to its data directory and declares no volume of its own; `compose.yml` gives each of the demo's nodes a volume; `demo.sh` gains the restart step; the `demo` recipe removes volumes on teardown.
- **Tests**: a data-layer scenario that reopens a node on the same directory; the stand's restart scenario with its empty-directory denial; the existing suites keep running in memory — naming it at the spawn helpers — so their wall-clock time does not move.
- **Nothing in the `pdn-store` fork.** Persistent replica storage, the persistent author, and the exclusive file lock are all already there — this change configures them.

## Out of Scope (deferred)

- **A write-ahead log across stores.** Recovery does not distinguish a clean stop from a kill: an acknowledged write commits within the stores' bounded settle window (a finding of this change — see the design's D11), the node's own files are replaced whole, and both kinds of stop reopen through the same path. What stays out of scope is completing a transition a kill cut between stores — an interrupted create or link is abandoned fail-closed as orphan replicas, not replayed to completion.
- **Encryption at rest.** The directory holds namespace secrets and the node key in the clear, protected by file permissions and by whatever the host protects it with. What that is worth on a phone or a shared machine is a question for the KERI key material, which arrives with a threat model of its own.
- **On-disk format versioning and migration.** Nothing deployed holds data, so a format change is a directory removed; a stored version marker earns its place when there is something to migrate.
- **Identity key material.** A `PdnId` stays a random placeholder here — what becomes durable is the node's wire key, not an identity's. KERI changes what an identity is made of and is its own change.
- **A disk that fills, and blob retention.** Named in the design as a risk with its failure mode, not solved: no quota, no garbage collection, no store-size bound. The frozen session snapshot's growth (an open session pins pages) becomes visible on a real file here, and bounding it stays with the session work.
- **Recovering a node's peers' addresses.** Contacts are re-derived from tickets exactly as they are today; a restarted node re-dials what those name, and improving that derivation is the metadata-pair reachability question, unchanged by this.
- **The scale runs.** This change is what makes the 1,000,000-claim measurement possible; the measurement itself is separate work.
