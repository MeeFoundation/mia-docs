# Tasks: graph-query-engine

> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

Every scenario in this change's deltas is a test of `crates/graph-query-engine`, on pod-tools its tests define, and a test must fail with its mechanism removed.

## 1. Specification

- [x] 1.1 ADR-0019: pods and the assistant read pod data through a graph query engine
- [x] 1.2 Deltas: materialization interface, catch-up, ontology registry, queries, vector index
- [x] 1.3 Glossary: `architecture/language/pod-tool.md`

## 2. Scenarios with no test yet

- [ ] 2.1 A pod-tool with no registered materialization contributes nothing to the graph (materialization interface)
- [ ] 2.2 A bulk load that fails leaves nothing of its zones, whose keys are then applied one at a time (catch-up)
- [ ] 2.3 A full disk fails a bulk load, and the keys are applied one at a time (design, operating conditions)
- [ ] 2.4 A handle made before its reader's removal (Open Question 1)
- [ ] 2.5 The engine with no materialization registered loads its registry and answers with no nodes (materialization interface, D7)
- [ ] 2.6 A zone whose record source offers a version is not read again until the version moves (catch-up)
- [ ] 2.7 The types present are counted per pod, within the view (queries)
- [ ] 2.8 A subject carries its claim count and its type names, oldest first (queries)
- [ ] 2.9 A value is refused for a missing field, a wrong cardinality or a wrong primitive, and a type with no fields takes no value (ontology registry)

## 3. The crate

- [ ] 3.1 `crates/graph-query-engine` in mee-pdn, named in the workspace's members, with its tests; nothing else in mee-pdn changes
- [ ] 3.2 The crate passes mee-pdn's toolchain, lints and dependency policy (`rust-toolchain.toml`, `clippy.toml`, `deny.toml`)
- [ ] 3.3 The crate pins LadybugDB, `lbug = "=0.22.1"`, chosen for its vector index on Android, and no type of LadybugDB's is in its interface (D8)
- [ ] 3.4 A binary built against the crate for Android links the vector extension and searches an index (design, Risks)

## 4. Gates

- [ ] 4.1 `openspec validate graph-query-engine --strict` and `python3 -I scripts/check-docs.py`
- [ ] 4.2 Every scenario of the deltas is a passing test of the crate, run in mee-pdn with no application
