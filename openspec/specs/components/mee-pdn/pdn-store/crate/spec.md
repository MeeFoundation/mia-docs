# Store crate

## Purpose

The document sync engine under the data layer — n0's `iroh-docs`, diverged where the platform's access model needs it ([ADR-0008](../../../../architecture/adr/0008-iroh-without-willow.md)) — as a crate of the workspace: where it lives, how the workspace names it, and how the configurations the workspace build never compiles are checked and tested. The engine's behaviour is specified where it is consumed — the data layer's stores, reconciliation, and ingest gate — and nothing here changes it.

The package took the name `pdn-store` after the change that brought the crate into the workspace. That change's archived artifacts describe the arrangement it landed — the package under the upstream name `iroh-docs`, reached through a workspace alias — and are left standing as the record of it.

## Requirements

### Requirement: The store is a crate of the workspace
The store SHALL be a member crate of the workspace at `crates/pdn-store`, resolved by path and never published. The package and the directory SHALL both be named `pdn-store`, with no workspace alias between them, so that one name serves the manifest, cargo's package selection (`-p pdn-store`), and — normalized to `pdn_store` — every `use` line. The crate SHALL carry upstream's version number, so that the release a change is taken from stays readable; a patch taken from upstream applies to the sources unchanged and needs its `iroh_docs::` paths rewritten in the tests, examples, and README.

#### Scenario: The lock file names no remote source for the store
- **WHEN** the workspace's lock file is read
- **THEN** the store's entry carries no source — no git revision, no registry — and a build of the workspace consults no network for it

#### Scenario: A consumer names the store and gets the crate in the tree
- **WHEN** a crate of the workspace depends on `pdn-store`
- **THEN** it resolves by path to `crates/pdn-store`, and its code names the crate as `pdn_store`

### Requirement: The store's other configurations are checked
The workspace build compiles the store under its default features alone. Its other configurations — every feature, no feature, rustdoc, and the featureless build for `wasm32-unknown-unknown` — SHALL be checked by a recipe of their own with warnings denied, under the store's own `[lints]` table rather than the workspace's, and the pipeline SHALL run that recipe on every proposed change in a job beside the workspace's rather than after it.

**Example:** each configuration of the store against the recipe that compiles it.

| configuration | `just check` | `just check-store` |
|---|---|---|
| default features | clippy | — |
| `--all-features`, every target | — | clippy, `-Dwarnings` |
| `--no-default-features`: lib, bins, tests | — | clippy, `-Dwarnings` |
| rustdoc, `--all-features` | — | `cargo doc`, `RUSTDOCFLAGS=-Dwarnings` |
| `wasm32-unknown-unknown`, `--no-default-features` | — | `cargo build`, `getrandom_backend="wasm_js"` |
| pipeline job | `lint-test-wasm` | `store`, running beside `lint-test-wasm` |

#### Scenario: A warning only the featureless build sees fails the store's check
- **WHEN** code warns under `--no-default-features` and not under the default features
- **THEN** `just check` passes and `just check-store` fails

#### Scenario: A break only the wasm32 build sees fails the store's check
- **WHEN** the featureless build for `wasm32-unknown-unknown` fails
- **THEN** `just check-store` fails while `just check` passes

#### Scenario: The pipeline runs the store's checks
- **WHEN** a change is proposed
- **THEN** a `store` job runs the store's checks and its other feature sets' tests, beside the workspace's job

### Requirement: The store's tests run with the workspace's, doctests included
`just test` SHALL run the store's unit and integration tests under default features as it runs every crate's, and, given no selection, SHALL end with the workspace's doctests — nextest runs none, and the store's README example is one. A run narrowed by package or by filter is nextest's alone and skips the doctests. `just test-store` SHALL run the store's tests under the other two feature sets, then the doctests under every feature.

**Example:** which run ends with the doctests, the store's README example among them.

| command | nextest runs | then |
|---|---|---|
| `just test` | every crate's tests, the store's under default features | `cargo test --workspace --doc` |
| `just test -p pdn-store` | the store's tests under default features | no doctests |
| `just test -E 'test(sync_simple)'` | the tests the filter matches | no doctests |
| `just test-store` | the store's tests, `--all-features` then `--no-default-features` | `cargo test -p pdn-store --all-features --doc` |

#### Scenario: The store's tests are part of the default run
- **WHEN** `just test` runs with no selection
- **THEN** the store's unit tests and the tests of its `client`, `dispatch`, `gc`, and `sync` binaries run under default features — `util`, the module three of them share, builds as a fifth binary holding no test — its tests marked flaky are reported skipped, and the run ends with the doctests

#### Scenario: A README example that stops compiling fails the run
- **WHEN** the README's example no longer compiles
- **THEN** `just test` with no selection fails at the doctests, and `just test -p pdn-store` passes without running them

### Requirement: The tests marked flaky run nightly
The store's tests marked `#[ignore = "flaky"]` SHALL stay out of every ordinary run and SHALL be repeated by the nightly workflow, selected by package and by the ignore mark alone, a failing iteration not cancelling the remaining ones.

**Example:** `sync_restart_node` and `sync_big`, in `tests/sync.rs`, are the store's tests marked `#[ignore = "flaky"]`; `sync_restart_node` needs `fs-store`.

| run | outcome |
|---|---|
| `just test` | both reported skipped |
| `just test-store`, `--all-features` | both reported skipped |
| `just test-store`, `--no-default-features` | `sync_big` reported skipped; `sync_restart_node` is not compiled |
| nightly job `store-flaky` | `just stress -p pdn-store --run-ignored ignored-only --stress-count 10 --no-fail-fast`: 10 iterations of both; an iteration that fails leaves the rest running |

#### Scenario: An ordinary run skips them
- **WHEN** `just test` or `just test-store` runs
- **THEN** none of the tests marked flaky runs, and each one the pass's feature set compiles is reported skipped: both under the default features and under every feature, `sync_big` alone under no feature, since `sync_restart_node` needs `fs-store`

#### Scenario: The nightly hunt runs them to the end
- **WHEN** the nightly workflow's store job runs
- **THEN** the tests marked flaky run the requested number of times, and a failing iteration does not stop the ones after it
