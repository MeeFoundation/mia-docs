## Why

The platform shares data two ways: a connection between two identities, with grants on the issuer's own data namespace, and a pod, a space its members write into together. Pods carry every case connections carry and the cases they cannot, and a load test on pods has passed, so the team has decided to remove connections. Half of the platform's machinery serves connections alone — the pairing ceremony, the connection metadata stores, grants and their binder, per-claim read and write control, writer-side retraction, the UWill token types — and every reader of the code and the specs pays for it on every visit. This change removes connections and everything that serves only them, from the code, the tests, the specs and the ADRs, and keeps pods working exactly as they do.

**Example:** Alice keeps a diary for herself and lets Bob read her email address.

| | today, by connection | today, by pod | after this change |
|---|---|---|---|
| Alice's diary | `data().write(alice, alice, notes/diary)` into her data namespace | a record in a pod Alice creates and invites nobody into | a record in a pod Alice creates and invites nobody into |
| Bob reads `contact/email` | `connections().invite` on Alice's phone a1, `establish` on Bob's phone b1, `publish_grant` on a1 naming the claim | `pods().invite` on a1, `join` on b1, `put_record` of a claim on a1 | `pods().invite` on a1, `join` on b1, `put_record` of a claim on a1 |
| Bob's laptop b2 catches up while a1 is offline | from b1, which serves Bob's own devices under the grant | from any member device | from any member device |

The pods change recorded two conditions on this removal: connections go once pods prove themselves in practice, the mobile application's integration included, and the defence against a member's device that contradicts its own member's history lands before connections go. This change lifts both. The load test is the practice the team asked for, and the mobile application now lives outside this tree on specifications of its own, so the two mobile proposals here describe nothing that will be built. The defence stays deferred under the criterion that set it — before any pod carries data people depend on — which the removal of connections does not move: a pod carries the same data with connections present or gone.

## What Changes

- **BREAKING — connections go, with everything that serves only them.** The pairing ceremony and its ALPN `/pdn/pairing/0`; the connection metadata stores and the PMS's connections records; grants, the grant binder and the grant surface of the connections service; read capabilities and the per-claim egress filter built on them; write grants, the ingest gate's capability verdict, the rejection a gate echoes back, writer-side retraction and the PMS's retraction markers; the out-of-band ticket handover of the data service; the UWill token types and the `pdn-layer` crate around them, which nothing consumes.
- **BREAKING — an identity's own data namespace goes.** An identity's store set is its private metadata store (PMS) alone, and what an identity keeps for itself is a record in a pod of one: the pod its identity creates and invites nobody into, held whole by the identity's own devices. The data service — write, read and list by issuer and path — goes with the namespace, and the linking reply hands over the PMS write ticket alone, the identity key reaching the new device inside the PMS as it does today.
- **What pods stand on stays, under names of its own.** The dialogue machinery linking and a pod's join share — framing, the pending-invite set, the state slot, the invite lifetime, the unreachable-inviter error — leaves the pairing module for a module of its own. The sweep that today arms connections keeps confirming this device in the PMS and opening the identity's pods, as an armer named for what it arms. pdn-store keeps the per-session egress predicate and ingest verdict the access book supplies — a pod's departure past and a dial's admission of signed entries run on them — and loses the rejection echo and the retraction of a stored entry, so its ingest verdict is accept or drop.
- **The session mechanics are specified once, for the stores that remain.** What subset reconciliation and capability-gated ingest state about every session — the view frozen at setup, the access decided before the snapshot opens and again when what it read moved, the bound in time, the uniform refusal, the content-free gossip topic, a swarm made of the store's device set, the key length bound, the future-timestamp window — moves into one new capability over the PMS and a pod's two stores, and the rest of both capabilities retires with the grants they judge.
- **The HTTP host and the stand.** The debug routes for connections, grants and entries go; the stand's scenarios that ran on connections and the data namespace run on pods; the connections demo, its compose file and its CI step go, and the pods demo stays.
- **Tests keep their coverage.** A test whose subject is a removed mechanism goes with it. A test that reaches a mechanism that stays — linking, restart recovery, the PMS, persistence, co-located sessions, blob collection, session snapshots, identity stacks, the host's surface — through a connection, a grant or the data namespace is rewritten onto a pod or the PMS before what it stood on is removed, and each rewrite is checked to fail with its mechanism broken.
- **ADRs.** ADR-0004, ADR-0007, ADR-0008, ADR-0009, ADR-0010 and ADR-0011 become obsolete stubs. Two new ADRs carry what pods still need from them: pdn-store as a variant of iroh-docs whose every session is judged by the embedder, from ADR-0008 and ADR-0010, and a pod's join over a raw iroh dialogue, from ADR-0011. ADR-0002, ADR-0003, ADR-0012 and ADR-0013 are edited to the platform without connections.
- **The rest of the documentation tree.** Invariant 3 goes and Invariant 2 states acquisition by membership; the threat model, the glossary (`connection` and `capability` go), the north star, the code practices — the access-control ladder and the product-path rule's worked example, both written on grants — the openspec context and every `CLAUDE.md` are rewritten for pods.
- **Other changes.** The active changes `reconcile-trigger`, `retraction-marker-lifetime`, `mobile-host-surface` and `mobile-demo-app` are deleted; every other active change is swept for what it says about connections, grants, the data namespace or pairing; `unclassified-connection-bounds` concerns iroh connections and stays. Archived changes whose subject this change removes are deleted, and the prose of the others is rewritten where it states what this change makes false.
- **Two defects the data namespace masked are fixed.** Readiness reads the blob store as well as the replica store, since a pod's placement on a full disk stops the blob store and leaves the replica store answering; and pdn-store's live actor tries a dial or a payload download again, for up to 2 minutes, toward a gossip neighbor it cannot reach — a member's device restarted on a new port after a kill, which iroh's selected path keeps dialing at its old one. The data namespace's 10 s pass hid both in the stand's scenarios.
- **Nothing else a pod does changes.** No requirement of a pod's stores, its membership, its records or its join changes in behaviour: what changes there is text that names a connection, a grant or the data namespace.

Out of scope, named so their absence reads as considered: a state directory written by a build with connections is not migrated, and the stand and every developer start from fresh directories; a node of this build and a node of an earlier one are not made to work together: the linking reply changes shape under the same ALPN and the same payload version, so an old device linking to a new inviter fails after its secret burns, while a new device linking to an old inviter succeeds and drops the data-namespace ticket unread; the defence against a member's own contradicting history, and a node serving a payload by its hash to any caller, stay as they are.

## Capabilities

### New Capabilities

- `components/mee-pdn/data-layer/reconciliation-sessions`: what every reconciliation session on a PMS or a pod's store is served and admits, and the mechanics every session shares — the per-session egress predicate and ingest verdict, the view frozen at setup, the access decided at setup, the bound in time, the uniform refusal, the content-free topic, the swarm, the key length bound and the future-timestamp window.

### Modified Capabilities

- `components/mee-pdn/data-layer/change-subscription`: the store whose changes the armer consumes is the PMS, without the grant binder or retraction markers.
- `components/mee-pdn/data-layer/identity-scoped-replicas`: replicas are an identity's PMS and its pods' stores; grantee imports and data-namespace imports go.
- `components/mee-pdn/data-layer/in-process-sessions`: co-located sessions cover the PMS and pods; the cases built on a granted namespace go.
- `components/mee-pdn/data-layer/multi-identity`: a node's identities hold a PMS and pods each; no data namespace and no connection.
- `components/mee-pdn/data-layer/node-assembly`: the supplied handlers are linking and a pod's join; dispatch and blob collection cover the stores that remain.
- `components/mee-pdn/data-layer/private-metadata-store`: connections records, retraction markers and the data ticket go; devices, tickets, the identity key and pod records stay.
- `components/mee-pdn/data-layer/pod-store`: the requirement that membership needs no connection retires, and text naming connections, grants or subset reconciliation is rewritten.
- `components/mee-pdn/pdn-node/core`: the connections service, the data service, retraction surfacing and grant binding go; the identity, pods and sync services and the armer stay.
- `components/mee-pdn/pdn-node/device-linking`: an identity's store set is its PMS; the reply hands over the PMS write ticket alone.
- `components/mee-pdn/pdn-node/pods`: text naming pairing or connections is rewritten onto the join dialogue's own terms.
- `components/mee-pdn/pdn-node/restart-recovery`: a restart re-derives pods from the PMS; connections, grants and the data namespace are no longer re-derived.
- `components/mee-pdn/pdn-node-http/host`: the debug surface covers identities, linking and pods.
- `components/mee-pdn/pdn-node-http/container-stand`: the stand's scenarios, restarts, denials and demos run on pods.

### Retired Capabilities

Every requirement of each is removed and its spec is deleted from the main tree by hand at archive, with no delta of its own: openspec refuses to retire a spec whose requirements carry example tables, as every spec of this tree does. The design records where each requirement goes.

- `components/mee-pdn/data-layer/capability-gated-ingest`
- `components/mee-pdn/data-layer/connection-metadata-store`
- `components/mee-pdn/data-layer/data-store`
- `components/mee-pdn/data-layer/read-capabilities`
- `components/mee-pdn/data-layer/subset-reconciliation`
- `components/mee-pdn/data-layer/write-retraction`
- `components/mee-pdn/pdn-node/connection-establishment`
- `components/mee-pdn/pdn-node/namespace-addressing`

## Impact

- **Code removed:** in `crates/pdn-node`, `connections.rs`, `data.rs`, `retraction.rs` and the pairing half of `pairing.rs`; in `crates/data-layer`, `connection_metadata.rs`, `grant.rs`, `retraction.rs`, `layer.rs`, the data-namespace and connection paths of `access.rs`, `node.rs` and `registry.rs`, and the connections and retraction parts of `private_metadata.rs`; in `crates/pdn-store`, the rejection echo, `retract_entry` and the standing validator outside sessions, and a retry of a dial or a download toward a gossip neighbor it cannot reach is added; the whole `crates/pdn-layer`; the `pdn-types` items left without a consumer; in `crates/pdn-node-http`, `connections.rs` and the data routes.
- **Public API:** `ConnectionsService`, `DataService`, `subscribe_retractions`, `RetractionEvent`, `WriteNotGranted`, `GranteeCannotShare`, the pairing payload and errors, and the grant types leave `pdn-node`'s surface; `SyncNode` loses every data-namespace and connection operation.
- **Wire:** the pairing ALPN goes; the linking reply carries no data-namespace ticket; the sync protocol's message loses its rejected-entry part. No ALPN and no version moves, so nodes of this build are made to work only with nodes of this build.
- **Tests:** 12 scenario files go whole — 8 in `crates/pdn-node/tests`, 4 in `crates/data-layer/tests` — and 6 more lose the tests whose subject is gone; 18 files have tests rewritten onto pods or the PMS, the stand's suite among them, as the tasks list one by one.
- **Tooling and CI:** `just demo-connections`, `ops/compose-connections.yml`, `ops/demo-connections.sh` and the CI step running them go.
- **Documents:** the spec tree, the ADRs, the code practices, the openspec context, every crate's `CLAUDE.md` and the workspace `CLAUDE.md`; the gitignored review findings about removed code go with it.
