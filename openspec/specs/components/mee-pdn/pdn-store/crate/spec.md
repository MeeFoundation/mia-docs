# Store crate

## Purpose

The document sync engine under the data layer: the platform's own variant of n0's `iroh-docs` ([ADR-0016](../../../../architecture/adr/0016-pdn-store-is-the-platforms-own.md)), holding what a crate of the workspace reaches, whose every session the embedder judges ([ADR-0014](../../../../architecture/adr/0014-store-sessions-judged-by-the-embedder.md)). This spec covers it as a crate of the workspace: where it lives and how the workspace names it, its one configuration, which the workspace's own check and tests compile, and its public surface, which is what is named outside its sources. The engine's behaviour is specified where it is consumed — the data layer's stores and its reconciliation sessions — and nothing here changes it.

The package took the name `pdn-store` after the change that brought the crate into the workspace. That change's archived artifacts describe the arrangement it landed — the package under the upstream name `iroh-docs`, reached through a workspace alias — and are left standing as the record of it.

## Requirements

### Requirement: The store is a crate of the workspace
The store SHALL be a member crate of the workspace at `crates/pdn-store`, resolved by path and never published. The package and the directory SHALL both be named `pdn-store`, with no workspace alias between them, so that one name serves the manifest, cargo's package selection (`-p pdn-store`), and — normalized to `pdn_store` — every `use` line. The crate SHALL carry the version number the workspace's own crates carry, as `pdn-node` does: it is the platform's crate, and what it took from n0's `iroh-docs` is recorded beside it, in `UPSTREAM.md`, rather than in its version.

**Example:** the version each manifest declares.

| manifest | before this change | after it |
|---|---|---|
| `crates/pdn-node/Cargo.toml` | `0.1.0` | `0.1.0` |
| `crates/pdn-store/Cargo.toml` | `0.101.0`, upstream's release | `0.1.0` |

#### Scenario: The lock file names no remote source for the store
- **WHEN** the workspace's lock file is read
- **THEN** the store's entry carries no source — no git revision, no registry — and a build of the workspace consults no network for it

#### Scenario: A consumer names the store and gets the crate in the tree
- **WHEN** a crate of the workspace depends on `pdn-store`
- **THEN** it resolves by path to `crates/pdn-store`, and its code names the crate as `pdn_store`

#### Scenario: The store carries the workspace's version
- **WHEN** the lock file is read
- **THEN** the store's entry and `pdn-node`'s carry the same version

### Requirement: Every test of the store runs, the nightly hunt included
No test of the store SHALL carry an ignore mark: each SHALL run in every ordinary run. The nightly hunt of the in-process scenarios SHALL repeat the store's integration tests with every other crate's, a failing iteration not cancelling the remaining ones, and SHALL fail when any iteration fails, whether it is the last one or an earlier one.

**Example:** where `sync_big` and `sync_restart_node`, in `tests/sync.rs`, run — the store's slowest test and one that reopens a store file.

| run | `sync_big` | `sync_restart_node` |
|---|---|---|
| `just test` | runs | runs |
| `just test -p pdn-store` | runs | runs |
| nightly job `in-process-scenarios` | 15 iterations, selected by `-E 'kind(test)'` | 15 iterations |

#### Scenario: An ordinary run skips none of the store's tests
- **WHEN** `just test` runs
- **THEN** no test of the store is reported skipped

#### Scenario: A failure before the last iteration fails the nightly hunt
- **WHEN** an iteration of the nightly in-process hunt fails and every iteration after it passes
- **THEN** the iterations after it still run, and the job fails

### Requirement: The store builds in one configuration
The store SHALL declare no feature and SHALL be built for the targets the workspace builds for, so that the workspace's build, its check and its tests compile the same store the product runs. What a feature used to switch off — the file-backed store, the counters a test reads — SHALL always be built.

**Example:** the configurations of the store each recipe compiles.

| recipe | before this change | after it |
|---|---|---|
| `just check` | default features | the one configuration |
| `just test` | default features | the one configuration |
| `just check-store` | `--all-features`, `--no-default-features`, rustdoc, `wasm32-unknown-unknown` | no such recipe |
| `just test-store` | `--all-features`, `--no-default-features`, doctests | no such recipe |

#### Scenario: The store's manifest declares no feature
- **WHEN** `crates/pdn-store/Cargo.toml` is read
- **THEN** it has no `[features]` table and no optional dependency

#### Scenario: The pipeline runs no job for the store alone
- **WHEN** a change is proposed
- **THEN** the store is linted and tested by the workspace's job, and the pipeline has no `store` job

### Requirement: The workspace check denies the store's warnings
`just check` SHALL lint the store, every target of it, with warnings denied, under the store's own `[lints]` table rather than the workspace's, and SHALL build the store's documentation with rustdoc's warnings denied.

**Example:** a store function that nothing calls, and a doc comment linking to a private item.

| defect | `just check` before this change | `just check` after it |
|---|---|---|
| `fn unused() {}` in `src/net.rs` | passes; `just check-store` fails | fails |
| an intra-doc link from a public item to a private one | passes; `just check-store` fails | fails |

#### Scenario: A warning in the store fails the workspace check
- **WHEN** code of the store raises a compiler or clippy warning
- **THEN** `just check` fails

#### Scenario: A broken doc link in the store fails the workspace check
- **WHEN** a doc comment of the store links to an item rustdoc cannot resolve or one that is private
- **THEN** `just check` fails

### Requirement: The store's public surface is what is named outside its sources
An item of the store SHALL be public only when something outside the store's sources names it — another crate of the workspace, its tests included, or one of the store's own integration tests — or when the signature of a public item carries it, since the compiler refuses a crate-private type in a public interface. Every other item SHALL be crate-private, so that one nothing calls is a dead-code warning, which `just check` denies.

**Example:** six items of the store.

| item | named outside the store's sources by | visibility |
|---|---|---|
| `Doc::set_bytes` | the data layer's PMS and pod writes | public |
| `DocsApi::flush` | the data layer's `flush_stores`, which a commit point calls | public |
| `filter::serve_whole` | the store's own integration tests, through `tests/util/mod.rs` | public |
| `QueryBuilder` | nothing; `Query::all`, which the data layer calls, returns it | public |
| `Engine::start_sync_keeping_default` | nothing; `Doc::share` calls it | crate-private |
| `DownloadPolicy` | nothing | removed |

#### Scenario: A crate-private item nothing calls fails the workspace check
- **WHEN** the last caller of a crate-private function of the store is removed
- **THEN** `just check` fails on the dead-code warning, naming the function

### Requirement: The store's tests run with the workspace's
`just test` SHALL run the store's unit and integration tests as it runs every crate's, in the store's one configuration. A module the integration tests share SHALL build no test binary of its own.

**Example:** the store's test binaries after this change.

| binary | holds |
|---|---|
| the library's unit tests | the tests in `src/` |
| `client` | the default author's tests |
| `dispatch` | the dispatch of a session to the identity it names, and the dial retries |
| `sync` | the scenarios of two or more engines syncing |

#### Scenario: The store's tests are part of the default run
- **WHEN** `just test` runs with no selection
- **THEN** the store's unit tests and the tests of its `client`, `dispatch` and `sync` binaries run, and every test binary the store builds holds at least one test
