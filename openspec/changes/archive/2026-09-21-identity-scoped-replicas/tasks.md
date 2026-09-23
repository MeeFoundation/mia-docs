# Tasks: identity-scoped-replicas

Scope: a hosted identity owns its own replicas, author and sessions over the node's one endpoint; every session names, as identities, the identity whose replica it addresses and the identity it acts as; rights are never unioned across a node's identities; two identities of one node meet through a path inside the process. Nothing about grants, swarms or reconciliation cadence changes shape.

## 1. Vocabulary and decision record

- [x] 1.1 The vocabulary of the wire value — the 32 opaque bytes pdn-store compares to tell whose replica a session addresses and whom its caller acts for, filled with a hosted identity's `PdnId` — stated where it is used, in the identity-scoped replicas spec. A glossary entry of its own carried a word the code has since dropped and was folded back in
- [x] 1.2 ADR-0013 stands as the decision record for the level of isolation; verified by the proposal, the design and the new capability spec citing it and by no other ADR contradicting it after the sweep in 8.3

## 2. pdn-store: the protocol boundary

- [x] 2.1 The first message of a sync session carries the identity of the replica addressed and the identity the caller acts for, as opaque 32-byte values (D2, D3); verified by a codec test driving a session over an in-memory stream pair and by the message failing to decode when a field is absent
- [x] 2.2 An accepted connection is dispatched by that message before any replica is touched (D6): the handler resolves the identity, hands the streams and the message to that hosted identity's engine, and refuses an unknown identity as not hosted; verified by a node of two hosted identities receiving a session for each and by the refusal being byte-identical to the not-hosted refusal
- [x] 2.3 The session access provider receives the caller's identity beside the namespace, the peer and the role (D3, D5); verified by a test asserting the provider sees the identity the caller named, and by the dispatch test of 2.2 failing if the value is dropped on the way
- [x] 2.4 A session entry point over an in-memory stream pair, running the same codec, the same session setup and the same access provider calls on both sides (D7); verified by two identities of one node converging a namespace both hold, and by the filtered case of 5.3 leaking when the egress filter is disabled
- [x] 2.5 A write announces to the identities of its own node that hold the namespace, content-free, and the announcement carries the identity of the replica that wrote (D9); verified by a co-located identity reading the entry within one reconcile interval and by the withheld claim staying absent from it
- [x] 2.6 The periodic pass reconciles a co-located pair whose replicas differ and leaves a converged pair alone; verified by an identity brought up behind converging on the next pass, and by a metric showing no in-process session opened for a quiet pair over several intervals
- [x] 2.7 The store's own gates stay green across its feature sets and the wasm target: `just check-store`, `just test-store`, and the workspace doctests
- [x] 2.8 The session access provider is a requirement of assembling the store, not an option that defaults to serving whole (D17); verified by the store's own suites naming the provider they take and by the build refusing an assembly that names none

## 3. data-layer: the hosted identity's own stack

- [x] 3.1 A hosted identity owns an engine, a replica store, a registry and an access book; `SyncNode` holds the map from identity to that stack and opens each identity's store from its own subdirectory (D1, D12); verified by two identities on one node holding two replicas of one namespace and by each store's file existing under its own subdirectory
- [x] 3.2 Every create and import names the identity it is held for, the private metadata directory and the connection metadata stores included (D13); verified by the two-audiences case and by an import naming another identity being refused with nothing registered in either
- [x] 3.3 A caller's named identity is admitted only when that identity's records list the caller's node id (D4); verified by a node that is a device of the named identity being served and a node that is not being refused as not hosted — the denial arranged with the fixture of 3.8
- [x] 3.4 Rights, egress filter and write admission follow the named identity alone, with no union across the node's identities (D5); verified by two co-located audiences of one issuer each receiving its own claim, and by the session naming one of them carrying nothing of the other's
- [x] 3.5 One author per hosted identity, persisted with that identity's stores, and the retraction tracker judging an entry by the author of the identity whose replica holds it (D10); verified by two identities on one node writing entries under two authors, by each keeping its author across a restart, and by the rewritten-key and withdrawn-device scenarios holding per identity
- [x] 3.6 The replica store's cache bound is a share of a node budget cut as the store opens, from the identities the storage directory then records as hosted, the opening one included, with one default of 1 GiB declared once and taken by the hosts and the suites (D14); verified by a spawn without a budget bounding its one identity at the whole default, a store in memory carrying no bound, a start on a directory of two recorded identities bounding each at half the budget while the subdirectory an unfinished create left takes no share, and an identity provisioned on a running node taking a share of its own while the store already open keeps its bound and the node reports the overshoot
- [x] 3.7 A dial whose target address carries this node's own wire identity routes to the in-process path, wherever the address came from — a contact list, a ticket, a device record (D7); verified by a node of two identities converging after a restart with no dial failing
- [x] 3.8 `test-util` fixture that names an identity of the caller's choosing in a session, as `write_unguarded` produces an entry the gate refuses; verified by the denial in 3.3 failing when the device-set check is removed
- [x] 3.9 A data replica whose identity holds no records to judge the caller by is refused rather than served whole, while a directory and a connection metadata store keep their ticket bound (D17); verified by a ticket holder obtaining nothing from such a replica and by an identity's devices still replicating its directory
- [x] 3.10 Each identity's subdirectory carries its hosting record — its directory's namespace, written beside and renamed over at the commit point after the identity's replicas are flushed — and a start lists the identities whose subdirectory holds one (D12); verified by a start finding the recorded identity and neither one provisioned and never recorded nor one whose record a read-only subdirectory refused

## 4. pdn-node: the acting identity

- [x] 4.1 The data service takes the identity performing the operation and acts for that identity alone; verified by a co-located identity reading and listing an issuer only the other holds and receiving the unknown-issuer error, and by the same read succeeding for the identity that holds it
- [x] 4.2 A granted replica's contacts are its own identity's devices and the issuer devices its own connection publishes (D5); verified by the three rewritten reachability scenarios of 7.1 and by a co-located audience's devices being absent from the contact set
- [x] 4.3 The pairing dialogue's message exchange becomes generic over its streams, so one implementation serves both transports (D8); verified by the existing establishment suites passing unchanged over the network
- [x] 4.4 Establishment between two identities of one node, run inside the process (D8); verified by both listing the connection and a grant crossing, by the replayed invite being refused, and by a third co-located identity seeing neither the connection nor what they published
- [x] 4.5 Recovery restores each hosted identity with stores of its own, importing its directory and its granted namespaces there (D1, D12); verified by two identities granted different claims of one issuer coming back reading each its own and neither the other's
- [x] 4.6 The ticket a grant record carries is imported for the identity the grant is addressed to (D11); verified by the grant binder's own path and by an import naming another identity refused in the same place
- [x] 4.7 The grant binder decides from the pair it swept: the namespace binds for the identity the grant addresses, a withdrawal forgets that identity's replica, and the check whether another pair still holds the issuer goes (D16); verified by a withdrawal toward one of two co-located audiences leaving the other reading its own replica and receiving a fresh write, and by the withdrawn identity's issuer resolving to nothing for it
- [x] 4.8 A retraction verdict is recorded in the directory of the identity whose author it names, and nowhere else (D10); verified by a retracted write of one identity leaving a co-located identity's directory and replica untouched, and by the sibling removal still running for the writing identity's own devices
- [x] 4.9 A namespace imported out of band is readable to the identity that imported it and re-served to no one (D17); verified by a sibling of that identity and an outsider, both holding the same ticket, obtaining nothing, and by the entries staying readable to the importer
- [x] 4.10 A failed link drops the stores it brought up and nothing else, and the displaced binding an import returns goes with the sharing it existed for; verified by `a_failed_link_leaves_a_granted_namespace_of_the_same_issuer_intact` passing on the separated replicas, its doc restated, and by a start on the directory a failed link left hosting nothing from it
- [x] 4.11 Recovery re-hosts the identities whose subdirectory records their hosting, the node-wide `hosted-identities.json` and its writer gone; a record whose store is gone is skipped before anything is provisioned for it, and a record skipped at a start stays for the next (D12); verified by `a_record_whose_replica_is_absent_is_skipped_and_the_rest_comes_back` — a store gone and a store without the replica, no store opened where one was gone, both records unchanged across a create after the start — and by a create and a link whose record is refused at the commit point hosting nothing afterwards

## 5. pdn-node-http: the surface and the stand

- [x] 5.1 The debug data routes name the acting identity beside the issuer; verified by a read naming a co-located identity that holds no grant answering a client error, beside the read that succeeds
- [x] 5.2 The stand runs two identities on one container, each connected to a peer of its own, asserting that each reads what its own peer granted, that neither reads the other's, and that an outsider reads neither; verified by `just test-docker` and by the assertion failing when the identity is dropped from the session
- [x] 5.3 The stand's existing scenarios keep passing unchanged, including the restart and the storage-failure ones

## 6. Measurement

- [x] 6.1 Profile a catch-up of one identity and record the share of its time spent on that identity's actor thread; it answers both how much a node gains from a store per identity and whether a cached fingerprint tree is the next thing to build
- [x] 6.2 Record the cache one identity's store actually uses at the chosen share — bytes held and evictions — against a store of the size a phone carries; the number decides the budget and the count a mobile host states

## 7. Tests rewritten and swept

- [x] 7.1 The four scenarios in `pdn-node/tests/reachability.rs` that rest on one replica shared by two audiences: three rewritten to the separated expectation, each keeping its paired denial — audiences hosted together keep separate replicas; a withdrawal toward one audience leaves the co-located one alone; an issuer device leaves the contacts of the replica whose connection stopped publishing it — and `a_withdrawal_counts_grants_not_bookkeeping` removed with the count it pins (D16)
- [x] 7.2 The three author scenarios in `data-layer/tests/persistence.rs` restated per identity, keeping their instrument: a record under a second author still accretes, so the count proves something
- [x] 7.3 The arrange steps of the `data-layer` suites host the identity whose replicas they hold and put the syncing device in its device set, the way the product reaches them, and name that identity in their creates and imports; verified by `just test -p data-layer` with no suite losing a scenario
- [x] 7.4 Every scenario this change adds is verified against the mechanism deliberately broken — the device-set check, the identity on the session, the egress filter, the announcement — and the test that would pass either way is rewritten

## 8. Documentation and sweep

- [x] 8.1 The crate `CLAUDE.md` files and the module and item docs that describe one author per node, one replica per namespace, or a node-wide classification restated — `data-layer/src/node.rs` on the node's one author, `pdn-node/src/data.rs` on operations addressing issuers rather than identities, and the `data-store` spec's line on author keys being node-local
- [x] 8.2 `openspec validate --all --strict`, with every `#### Scenario:` heading of the deltas checked by eye
- [x] 8.3 Sweep `openspec/specs/**` and the other active changes for the wording this change invalidates — one author per node, the union of co-hosted audiences, a replica served on its ticket alone, a link rollback restoring a displaced binding — and for what cells, reconcile-trigger and mobile-host-surface assume about a node hosting several identities

## 9. Stress pass

- [x] 9.1 Stress the affected scenario suites under nextest per the flaky-tests practice — the in-process path, linking, establishment, reachability, the store's own suites — with any failure treated as a defect of this change and diagnosed in isolation before anything is built on top
