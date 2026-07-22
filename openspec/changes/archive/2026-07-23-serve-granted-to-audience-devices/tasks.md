# Tasks: serve-granted-to-audience-devices

## 1. Posture

- [x] 1.1 Add the audience-devices serving posture; granted imports (`import_namespace_granted` / `import_namespace_scoped`) record it instead of `Never`, device imports keep `Serve`
- [x] 1.2 Accept path consults the posture and routes audience-device sessions into classification instead of refusing outright; refusal stays `NotFound`-uniform

## 2. Classification

- [x] 2.1 Resolve the caller's node id against the audience identity's directory device set (the hosted identity handle the book already holds); no resolution → refuse
- [x] 2.2 Rights from the local grant record in the pair's peer store, read at session setup: the claim-set egress filter for a present record; absent / withdrawn / undecodable → refuse (whole-store → full existed here until 3b removed the width)
- [x] 2.3 Multi-identity guard: only the audience identity's directory is consulted — a device resolving solely in a co-located identity's directory is refused

## 3. Sibling contacts

- [x] 3.1 Granted tracking accepts contacts beyond the issuer's (import parameter or an add-contacts act on the node), merged into the tracked contact set
- [x] 3.2 Verify the periodic reconcile pass and the before-access nudge dial the merged contacts unchanged
- [x] 3.3 Runtime: sibling contacts are derived from the audience identity's directory device records — endpoint-id-only addresses — and re-derived on every grant-binding sweep, so a device linked after the import is dialed too and an unrelated hosted identity's devices never are

## 3a. Automatic binding

- [x] 3a.1 `ConnectionMetadataStore::changes()`: an observable change stream over a counterparty replica, payload arrivals included — a grant's ticket is a blob, so the entry arriving is not yet a ticket to act on
- [x] 3a.2 Grant binder per open pair, spawned from the connection sweep so pairs filled by establishment are watched too: a grant that becomes readable imports the namespace its ticket names
- [x] 3a.3 Rebinding and idempotence: a grant still naming the held replica is not re-imported; a grant that comes to name a different replica is
- [x] 3a.4 Withdrawal unbinds: what the binder imported it forgets once the record is gone, bounded to its own imports so an out-of-band import is never dropped
- [x] 3a.5 `ConnectionsService::withdraw_grant` — the missing counterpart of the publish pair, and what makes the unbind path reachable at the service level

## 3b. Whole-store grant removed

- [x] 3b.1 `GrantRecord` loses its `WholeStore` variant; every grant is capability-scoped — no grant conveys a store without naming its claims. The tagged enum stays so an unknown future kind still decodes as no grant
- [x] 3b.2 `GrantWidth` collapses to `Claims | None`; the `whole_store → Full` branch leaves both classification loops, so a granted session is always a filtered one
- [x] 3b.3 `grant_width_in` checks `cap.issuer == issuer && cap.audience == audience` — with whole-store gone the capability always names its subject, so position no longer authorizes on its own; a test isolates the check (mutation-verified: dropping it serves a misaddressed grant)
- [x] 3b.4 Grant surface collapses to one width: `ConnectionMetadataStore::{publish,read}_grant` are the scoped forms renamed; pdn-node's `publish_grant`/`read_grants`/`PeerGrant` are the scoped surface, the whole-store methods gone; the grant binder imports scoped only
- [x] 3b.5 Delta `data-layer-connection-metadata-store` records the format; the main-tree sweep covers `connection-metadata-store.md`, `core.md`, `subset-reconciliation.md`, and the swarm glossary

## 4. Tests

- [x] 4.1 Flip the pinned deny in `a_peer_store_catches_up_from_a_sibling_device_while_the_issuer_is_offline`: the sibling claim catch-up becomes the allowed path; paired denial — an outsider with a sibling-minted ticket obtains nothing after a proven serving wave
- [x] 4.2 Scoped parity: a sibling session over a scoped grant delivers exactly the claim set, withheld entries hidden
- [x] 4.3 Withdrawal: once the tombstone reaches the serving device, its next sibling session refuses; data delivered while granted is retained
- [x] 4.4 Co-located identity: a device hosted for a different identity on the serving node is refused
- [x] 4.5 `just check`, full data-layer suite, stress pass on the touched scenarios (20 iterations now; the full flaky-tests.md series before anything builds on top)
- [x] 4.6 Ceremony-level scenario in pdn-node (`tests/sibling_serving.rs`): create → link → establish → scoped grant; the issuer goes offline, the linked device catches up on the pair, the grant, and the claim from its sibling; existence hidden; a sibling-minted ticket without audience membership delivers nothing (supersedes the store-level offline scenario, removed from `data-layer/tests/connection_metadata.rs` — the store-level suite keeps what services cannot express: withdrawal at the sibling, unarmed-issuer scope parity, the co-located directory intruder)
- [x] 4.7 No import act appears in either pdn-node scenario — the binding path is what makes them pass, and a second scenario pins the unbind direction: a withdrawn grant takes the namespace back out and the issuer becomes unknown again
- [x] 4.8 Both pdn-node scenarios verified non-vacuous by mutation: suppressing the binder spawn fails both, suppressing the withdrawal sweep fails the unbind one

## 5. Docs sweep

- [x] 5.1 `pdn-node/core.md` covered by its own delta (`specs/pdn-node-core/`): the blanket "never re-serves to third parties" is replaced by the audience-device stance, and "importing remains an explicit data-service act" by the grant-binding behaviour, in both the connections and the data requirement
- [x] 5.2 In-code rustdoc carrying the same removed promise: `import_namespace_granted` / `import_namespace_scoped` in data-layer, the data service trait in pdn-node, and the data-layer crate-level module doc
- [x] 5.3 Swept the spec tree and `reconcile-trigger` at archive time: no stale "never re-serves" / whole-store / "grant book it does not hold" phrasing survives (remaining "whole store" mentions are the metadata replica, not a grant width); the three delta requirements are hand-applied to the main tree (subset-reconciliation, core, connection-metadata-store); swarm glossary truthful, "audience" predates this change and needs no new entry
