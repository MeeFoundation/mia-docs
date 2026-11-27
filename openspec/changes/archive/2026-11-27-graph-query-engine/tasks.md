# Tasks: graph-query-engine

> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

Every scenario in this change's deltas is a test of `crates/graph-query-engine`, on pod-tools its tests define, and a test must fail with its mechanism removed.

## 1. Specification

- [x] 1.1 ADR-0019: pods and the assistant read pod data through a graph query engine
- [x] 1.2 Deltas: materialization interface, catch-up, ontology registry, queries, vector index
- [x] 1.3 Glossary: `architecture/language/pod-tool.md`

## 2. Scenarios written as tests of the crate

- [x] 2.1 A pod-tool with no registered materialization contributes nothing to the graph (materialization interface)
- [x] 2.2 A bulk load that fails after its subjects and nodes are written leaves nothing it wrote, and its keys are applied one at a time into the graph key by key gives, subjects' types included (catch-up), tested by failing the load at a named table
- [x] 2.3 A full disk fails a bulk load, and the keys are applied one at a time (design, operating conditions), tested as a load that cannot stage its files
- [x] 2.4 The engine with no materialization registered loads its registry and answers with no nodes (materialization interface, D7)
- [x] 2.5 A zone whose record source offers a version is not read again until the version moves (catch-up)
- [x] 2.6 The types present are counted per pod, within the view (queries)
- [x] 2.7 A subject carries its claim count and its type names, oldest first (queries)
- [x] 2.8 A value is refused for a missing field, a wrong cardinality or a wrong primitive, and a type with no fields takes no value (ontology registry)
- [x] 2.9 A view tells the tool ontologies of its zones and no other (materialization interface)

## 3. The crate

- [x] 3.1 `crates/graph-query-engine` in mee-pdn, named in the workspace's members, with its tests; nothing else in mee-pdn changes but the workspace's build of LadybugDB: the member line and an optimized `lbug` in debug builds (`Cargo.toml`), the source tree the lbug crate builds from (`.cargo/config.toml`, `scripts/lbug-vector-source.sh`, `scripts/lbug_ndk_atomic_ref.py`, `just lbug-vector-source`), that recipe in CI, and the crate's line in `CLAUDE.md`
- [x] 3.2 The crate passes mee-pdn's toolchain, lints and dependency policy (`rust-toolchain.toml`, `clippy.toml`, `deny.toml`): clippy with the workspace's lints, `cargo fmt --check` and `cargo doc` clean on the pinned toolchain; every crate it adds comes from crates.io under a license `deny.toml` allows, and CI's `cargo deny check` checks advisories
- [x] 3.3 The crate pins LadybugDB, `lbug = "=0.22.1"`, chosen for its vector index on Android, and no type of LadybugDB's is in its interface (D8)
- [x] 3.4 A binary built against the crate for Android links the vector extension and searches an index (design, Risks): pdn-agent's Android app, built against the crate in mee-pdn, indexed 584 texts and answered from vector search on a phone (RMX3710)

## 4. Gates

- [x] 4.1 `openspec validate graph-query-engine --strict` and `python3 -I scripts/check-docs.py`
- [x] 4.2 Every scenario of the deltas is a passing test of the crate, run in mee-pdn with no application: `cargo test -p graph-query-engine`, 53 passed
