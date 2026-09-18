# Tasks: identity-scoped-replicas

Scope: a hosted identity owns a scope — its own replicas, author and sessions — over the node's one endpoint; every session names the scope it addresses and the scope it acts as; rights are never unioned across a node's identities; two identities of one node meet through a path inside the process. Nothing about grants, swarms or reconciliation cadence changes shape.

## 1. Vocabulary and decision record

- [ ] 1.1 Glossary entry `architecture/language/scope.md` — what a scope is, that it is one hosted identity, and what belongs to it — linked from the first use in the identity-scoped replicas and multi-identity specs; verified by the link resolving from both
- [ ] 1.2 ADR-0013 stands as the decision record for the level of isolation; verified by the proposal, the design and the new capability spec citing it and by no other ADR contradicting it after the sweep in 8.3

## 2. pdn-store: the protocol boundary

- [ ] 2.1 The first message of a sync session carries the addressed scope and the caller's scope as opaque 32-byte values (D2, D3); verified by a codec test driving a session over an in-memory stream pair and by the message failing to decode when a field is absent
- [ ] 2.2 An accepted connection is dispatched by that message before any replica is touched (D6): the handler resolves the scope, hands the streams and the message to that scope's engine, and refuses an unknown scope as not hosted; verified by a two-scope node receiving a session for each and by the refusal being byte-identical to the not-hosted refusal
- [ ] 2.3 The session access provider receives the caller's scope beside the namespace, the peer and the role (D3, D5); verified by a test asserting the provider sees the scope the caller named, and by the dispatch test of 2.2 failing if the value is dropped on the way
- [ ] 2.4 A session entry point over an in-memory stream pair, running the same codec, the same session setup and the same access provider calls on both sides (D7); verified by two scopes of one node converging a namespace both hold, and by the filtered case of 5.3 leaking when the egress filter is disabled
- [ ] 2.5 A write announces to the scopes of its own node that hold the namespace, content-free, and the announcement carries the scope of the replica that wrote (D9); verified by a co-located scope reading the entry within one reconcile interval and by the withheld claim staying absent from it
- [ ] 2.6 The periodic pass reconciles a co-located pair whose replicas differ and leaves a converged pair alone; verified by a scope brought up behind converging on the next pass, and by a metric showing no in-process session opened for a quiet pair over several intervals
- [ ] 2.7 The store's own gates stay green across its feature sets and the wasm target: `just check-store`, `just test-store`, and the workspace doctests

## 3. data-layer: the scope

- [ ] 3.1 A scope owns an engine, a replica store, a registry and an access book; `SyncNode` holds the map from scope to that stack and opens each scope's store from its own subdirectory (D1, D12); verified by two scopes on one node holding two replicas of one namespace and by each store's file existing under its own subdirectory
- [ ] 3.2 Every create and import names its scope, the private metadata directory and the connection metadata stores included (D13); verified by the two-audiences case and by an import naming another scope being refused with nothing registered in either
- [ ] 3.3 A caller's named scope is admitted only when that identity's records list the caller's node id (D4); verified by a node that is a device of the named identity being served and a node that is not being refused as not hosted — the denial arranged with the fixture of 3.8
- [ ] 3.4 Rights, egress filter and write admission follow the named scope alone, with no union across the node's identities (D5); verified by two co-located audiences of one issuer each receiving its own claim, and by the session naming one of them carrying nothing of the other's
- [ ] 3.5 One author per scope, persisted with that scope's stores, and the retraction tracker recognising the set of this node's scope authors (D10); verified by two identities on one node writing entries under two authors, by each keeping its author across a restart, and by the rewritten-key and withdrawn-device scenarios holding per scope
- [ ] 3.6 The replica store's cache bound is configuration, as a share per scope, with one default of 1 GiB declared once and taken by the hosts and the suites (D14); verified by a spawn without a share bounding each scope at the default, a spawn with a share bounding at it, and an identity created on a running node opening at the same share with no other store reopened
- [ ] 3.7 A dial whose target address carries this node's own wire identity routes to the in-process path, wherever the address came from — a contact list, a ticket, a device record (D7); verified by a two-scope node converging after a restart with no dial failing
- [ ] 3.8 `test-util` fixture that names a scope of the caller's choosing in a session, as `write_unguarded` produces an entry the gate refuses; verified by the denial in 3.3 failing when the device-set check is removed

## 4. pdn-node: the acting identity

- [ ] 4.1 The data service takes the identity performing the operation and acts in its scope alone; verified by a co-located identity reading and listing an issuer only the other holds and receiving the unknown-issuer error, and by the same read succeeding for the identity that holds it
- [ ] 4.2 A granted replica's contacts are its own identity's devices and the issuer devices its own connection publishes (D5); verified by the three reachability scenarios of 7.1 and by a co-located audience's devices being absent from the contact set
- [ ] 4.3 The pairing dialogue's message exchange becomes generic over its streams, so one implementation serves both transports (D8); verified by the existing establishment suites passing unchanged over the network
- [ ] 4.4 Establishment between two identities of one node, run inside the process (D8); verified by both listing the connection and a grant crossing, by the replayed invite being refused, and by a third co-located identity seeing neither the connection nor what they published
- [ ] 4.5 Recovery restores each hosted identity in its own scope, importing its stores and its granted namespaces there (D1, D12); verified by two identities granted different claims of one issuer coming back reading each its own and neither the other's
- [ ] 4.6 The ticket a grant record carries is imported into the scope of the identity the grant is addressed to (D11); verified by the grant binder's own path and by a cross-scope import refused in the same place

## 5. pdn-node-http: the surface and the stand

- [ ] 5.1 The debug data routes name the acting identity beside the issuer; verified by a read naming a co-located identity that holds no grant answering a client error, beside the read that succeeds
- [ ] 5.2 The stand runs two identities on one container, each connected to a peer of its own, asserting that each reads what its own peer granted, that neither reads the other's, and that an outsider reads neither; verified by `just test-docker` and by the assertion failing when the scope is dropped from the session
- [ ] 5.3 The stand's existing scenarios keep passing unchanged, including the restart and the storage-failure ones

## 6. Measurement

- [ ] 6.1 Profile a catch-up of one identity and record the share of its time spent on that scope's actor thread; it answers both how much a node gains from a store per scope and whether a cached fingerprint tree is the next thing to build
- [ ] 6.2 Record the cache a scope actually uses at the chosen share — bytes held and evictions — against a store of the size a phone carries; the number decides the share a mobile host computes

## 7. Tests rewritten and swept

- [ ] 7.1 The three scenarios in `pdn-node/tests/reachability.rs` that assert one replica shared by two audiences rewritten to the separated expectation, each keeping its paired denial: audiences hosted together keep separate replicas; a withdrawal toward one audience leaves the co-located one alone; an issuer device leaves the contacts of the replica whose connection stopped publishing it
- [ ] 7.2 The author scenario in `data-layer/tests/persistence.rs` restated per scope, keeping its instrument: a record under a second author still accretes, so the count proves something
- [ ] 7.3 The arrange steps of the `data-layer` suites name their scope; verified by `just test -p data-layer` with no suite losing a scenario
- [ ] 7.4 Every scenario this change adds is verified against the mechanism deliberately broken — the device-set check, the scope on the session, the egress filter, the announcement — and the test that would pass either way is rewritten

## 8. Documentation and sweep

- [ ] 8.1 The crate `CLAUDE.md` files that describe one author per node, one replica per namespace, or a node-wide classification updated to the scope
- [ ] 8.2 `openspec validate --all --strict`, with every `#### Scenario:` heading of the deltas checked by eye
- [ ] 8.3 Sweep `openspec/specs/**` and the other active changes for the wording this change invalidates — one author per node, the union of co-hosted audiences, an unregistered replica as a property of a node — and for what cells, reconcile-trigger and mobile-host-surface assume about a node hosting several identities

## 9. Stress pass

- [ ] 9.1 Stress the affected scenario suites under nextest per the flaky-tests practice — the in-process path, linking, establishment, reachability, the store's own suites — with any failure treated as a defect of this change and diagnosed in isolation before anything is built on top
