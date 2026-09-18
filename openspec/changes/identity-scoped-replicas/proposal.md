# Identity-scoped replicas

## Why

A node hosts the store sets of any number of identities, and co-location is not a trust boundary: two identities of one person are as separate as two strangers ([operating-conditions](../../specs/code-practices/operating-conditions.md)). The node does not hold them apart. One replica per namespace, one author per node and one classification keyed by node id mean that what belongs to two identities is stored together, written under one name, and told apart only by a check at each point that reads it.

Three consequences are recorded across the tree. A node hosting two audiences of one issuer binds one replica and receives the union of both grants into it, and a local read of that replica answers from the union, because it is addressed by issuer and carries no acting identity. Every store on the node writes with the node's one author, so on a shared node two members of one cell publish the same author key, an entry passes as either member's, and a membership act resolves to two actors at once — the open question F2 of the cells change. And a grant withdrawn toward one audience leaves the other's replica holding what the first one received, because the bytes were never separate.

This change makes the separation structural, at the level ADR-0013 states. A hosted identity becomes a scope that owns its replica store, its author and its sessions, so isolation follows from where the bytes live rather than from a filter applied on every read. The same step settles what subset-rbsr deferred as the per-identity consumer view.

## What Changes

- **A hosted identity is a scope, and a scope owns its replicas.** One replica store, one persisted author and one set of registered replicas per hosted identity, over the node's shared endpoint, gossip and blob store. Two identities granted by one issuer hold two replicas of that issuer's namespace, each with its own contacts and its own rights.
- **A sync session names the scope on both ends.** **BREAKING** The docs protocol carries the scope of the replica being addressed and the scope the caller acts as. A node may name only an identity whose device set lists its node id; naming any other is refused as not hosted. Rights come from the named scope alone and are never unioned across the identities a node hosts.
- **Ingest and egress are judged per scope.** Write admission is recorded per scope, namespace and caller, and the egress filter serves what the named scope's grant covers.
- **Every replica is created and imported into a named scope.** **BREAKING** A create and an import name the identity the replica is held for — the private metadata directory and the connection metadata stores included — and a ticket landing in a scope other than the one whose grant record carried it is refused.
- **Writes name the identity performing them.** **BREAKING** The data service takes the acting identity, and each hosted identity writes with its own author, stable across restarts. What a device is, as a cell or a counterparty sees it, becomes the pair of the device and the identity.
- **Two identities of one node talk inside the process.** iroh refuses a connection to the node's own endpoint, so co-located identities cannot reach each other over the network at all. Sync sessions and the pairing dialogue between two scopes of one node run the full protocol over in-process streams, with both sides classifying, gating and filtering exactly as over the network, and with a write announcing to co-located scopes directly, since a node's own gossip broadcast never reaches its other subscribers.
- **The replica store's cache size becomes configuration, as a share per scope.** The cache is bounded per store and the bound is fixed when the store opens, so a node is spawned with the share one scope takes, derived from the memory a host gives the replica stores and the identities the device is provisioned for; one stated default of 1 GiB per scope serves the hosts and the suites. A host on a phone is expected to compute its own share at that application's first start, which this change states and does not implement.
- **The node's storage directory holds one subdirectory per scope.** **BREAKING** Nothing reads a directory written under the previous layout, and no migration carries one over.

## Capabilities

### New Capabilities

- `components/mee-pdn/data-layer/identity-scoped-replicas`: the scope model — a hosted identity owns its replica store, author and registered replicas; the scope named on each session and how a caller's claim to act as an identity is checked; rights per scope with no union; the import rule; what a node that hosts several identities can and cannot obtain.
- `components/mee-pdn/data-layer/in-process-sessions`: the path between two scopes of one node — when it is chosen, that it runs the same protocol with the same gates, the announcement that reaches co-located scopes, and the reconcile pass that does not open a session per interval with nothing to carry.

### Modified Capabilities

- `components/mee-pdn/data-layer/multi-identity`: isolation between identities on one node becomes structural rather than classified per session, and the scope replaces the node as what a session resolves to.
- `components/mee-pdn/data-layer/subset-reconciliation`: the caller's rights are resolved for the scope it names instead of every identity its node id resolves to, and a granted replica's contacts are addresses paired with the scope they are dialed as.
- `components/mee-pdn/data-layer/capability-gated-ingest`: the write set a session freezes is recorded per scope as well as per replica and caller.
- `components/mee-pdn/data-layer/durable-storage`: the author becomes one per hosted identity rather than one per node, and the directory holds a subdirectory per scope.
- `components/mee-pdn/data-layer/node-assembly`: the docs protocol dispatches an accepted connection to the scope its first message names, while the endpoint still carries all protocols.
- `components/mee-pdn/pdn-node/namespace-addressing`: one namespace per issuer stands, and a node holds one replica of it per scope that acquired it.
- `components/mee-pdn/pdn-node/core`: the data service takes the acting identity; a granted replica's contact set follows the one connection that bound it, so the requirement that unions every co-hosted audience's siblings and issuer devices is replaced.
- `components/mee-pdn/pdn-node/connection-establishment`: two identities of one node establish a connection through the same dialogue, run inside the process.
- `components/mee-pdn/pdn-node/restart-recovery`: recovery restores each hosted identity's scope with its own stores and author.
- `components/mee-pdn/pdn-node-http/host`: a data operation addresses the acting identity as well as the issuer.
- `components/mee-pdn/pdn-node-http/container-stand`: read isolation between two identities on one node becomes assertable, and the stand asserts it.

## Impact

- **`crates/pdn-store`**: the scope fields on the protocol's first message, dispatch of an accepted connection before the engine is chosen, the scope handed to the session access provider, contacts carrying their scope, the announcement carrying the scope of the replica that wrote, and an entry point for a session over in-process streams. The replica store, the sync actor and the range reconciler are untouched, so the divergence from upstream stays at the protocol boundary.
- **`crates/data-layer`**: a scope owning an engine, a registry and an access book; the check that a caller's node id appears in the device set of the identity it names; the import rule; the author per hosted identity; the routing rule that sends a dial to this node's own address through the in-process path; the scope named at every create and import, the private metadata directory and the connection metadata stores included.
- **`crates/pdn-node`**: the acting identity on the data service; the pairing dialogue generic over its streams so it runs in-process; contacts derived per scope; recovery per scope.
- **`crates/pdn-node-http`**: the debug data routes carrying the acting identity.
- **Tests**: the data service's callers updated for the acting identity; three scenarios in `pdn-node/tests/reachability.rs` that assert one replica shared by two audiences rewritten to the separated expectation, each keeping its paired denial; the author scenario in `data-layer/tests/persistence.rs` restated per identity; new scenarios for two identities of one node establishing a connection and converging a shared namespace without the network, and for a node that names an identity it is not a device of, which needs a fixture that names a scope of its own choosing, behind `test-util` as `write_unguarded` is.
- **Other changes**: cells gains a device that is the pair of device and identity and loses the co-hosting half of its open question F2; reconcile-trigger carries the scope in whatever transport it settles on; mobile-host-surface exports the acting identity with the data operations and takes the cache share its application computes.

## Out of Scope

- **Blob egress.** A provider still serves any hash to any caller that asks, so payload bytes are not scoped to an identity. The gate arrives with the identity-bound authorization work.
- **Unlinkability of identities on one node.** One endpoint means one node id in the device sets of every identity the node hosts, so a counterparty of two of them sees the same node id in both. This change isolates what is stored and who wrote it, not who is observed together, and separating the node ids is what an endpoint per identity would take.
- **Identity-level authentication of a session.** The claim to act as an identity is checked against that identity's device set, which is what the node id already carried. A cryptographic proof needs identities to hold key material.
- **Cells.** Nothing here decides membership, roles or the cell stores; it decides the scope they will sit in.
