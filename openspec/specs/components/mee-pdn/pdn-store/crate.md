# Store crate

## Purpose

The document sync engine under the data layer — n0's `iroh-docs`, diverged where the platform's access model needs it ([ADR-0008](../../../architecture/adr/0008-iroh-without-willow.md)) — as a crate of the workspace: where it lives, how the workspace names it, and how the configurations the workspace build never compiles are checked and tested. The engine's behaviour is specified where it is consumed — the data layer's stores, reconciliation, and ingest gate — and nothing here changes it.

## Requirements

### Requirement: The store is a crate of the workspace
The store SHALL be a member crate of the workspace at `crates/pdn-store`, resolved by path and never published. The package SHALL keep the upstream name `iroh-docs`, so that a patch taken from upstream applies without renaming and the crate's own tests, examples, and README read as upstream's do; consumers SHALL name it through the workspace alias `pdn-store`, and cargo selects it by its own name (`-p iroh-docs`).

#### Scenario: The lock file names no remote source for the store
- **WHEN** the workspace's lock file is read
- **THEN** the store's entry carries no source — no git revision, no registry — and a build of the workspace consults no network for it

#### Scenario: A consumer names the alias and gets the package
- **WHEN** a crate of the workspace depends on `pdn-store`
- **THEN** it resolves to the package `iroh-docs` at `crates/pdn-store`, and its code names the crate as `pdn_store`

### Requirement: The store's other configurations are checked
The workspace build compiles the store under its default features alone. Its other configurations — every feature, no feature, rustdoc, and the featureless build for `wasm32-unknown-unknown` — SHALL be checked by a recipe of their own with warnings denied, under the store's own `[lints]` table rather than the workspace's, and the pipeline SHALL run that recipe on every proposed change in a job beside the workspace's rather than after it.

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

#### Scenario: The store's tests are part of the default run
- **WHEN** `just test` runs with no selection
- **THEN** the store's unit tests and its `client`, `gc`, and `sync` binaries run under default features, its tests marked flaky are reported skipped, and the run ends with the doctests

#### Scenario: A README example that stops compiling fails the run
- **WHEN** the README's example no longer compiles
- **THEN** `just test` with no selection fails at the doctests, and `just test -p iroh-docs` passes without running them

### Requirement: The tests marked flaky run nightly
The store's tests marked `#[ignore = "flaky"]` SHALL stay out of every ordinary run and SHALL be repeated by the nightly workflow, selected by package and by the ignore mark alone, a failing iteration not cancelling the remaining ones.

#### Scenario: An ordinary run skips them
- **WHEN** `just test` or `just test-store` runs
- **THEN** the tests marked flaky are reported skipped and none of them runs

#### Scenario: The nightly hunt runs them to the end
- **WHEN** the nightly workflow's store job runs
- **THEN** the tests marked flaky run the requested number of times, and a failing iteration does not stop the ones after it
