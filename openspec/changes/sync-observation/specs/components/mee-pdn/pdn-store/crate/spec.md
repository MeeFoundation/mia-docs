# Store crate

## REMOVED Requirements

### Requirement: The store builds in one configuration
**Reason**: The store declares a feature, `observation`, which a test build alone enables, so it builds in the product configuration and in that one.
**Migration**: "The store's one feature, observation, is built by tests alone" holds the targets, the file-backed store and counters built always, and the pipeline's lack of a store job.

## ADDED Requirements

### Requirement: The store's one feature, observation, is built by tests alone
The store SHALL declare exactly one feature, `observation` — the ordered subscription and the session id the sync tests observe a pod's sync by — and no optional dependency, and SHALL be built for the targets the workspace builds for. Only a test build SHALL enable the feature: the data layer's `test-util` feature turns it on, and the product's dependency graph SHALL never include it, which `scripts/check-product-graph.sh` asserts in `just check`. `just check` SHALL lint the store in both configurations, and `just test-product` SHALL run the store's suite in the product configuration, so the store the product runs is compiled, linted and tested as such. What a feature used to switch off — the file-backed store, the counters a test reads — SHALL always be built.

**Example:** the configurations of the store each recipe compiles.

| recipe | the store's configuration |
|---|---|
| `just check` | both: `cargo clippy -p pdn-store --all-targets` without and with `--features observation`, then the product graph checked for the feature |
| `just test` | `observation`, through `data-layer/test-util` |
| `just test-product` | the product configuration: `cargo nextest run -p pdn-mobile -p pdn-store`, no feature |
| a build a device installs | the product configuration |

#### Scenario: The store's manifest declares the observation feature alone
- **WHEN** `crates/pdn-store/Cargo.toml` is read
- **THEN** its `[features]` table holds `observation` and nothing else, it has no optional dependency, and the feature is enabled by `data-layer`'s `test-util` feature and by no product dependency

#### Scenario: The product graph never includes the feature
- **WHEN** `just check` runs
- **THEN** the store is linted without the feature and with it, and the check fails if the product's dependency graph enables `observation` on the store

#### Scenario: The pipeline runs no job for the store alone
- **WHEN** a change is proposed
- **THEN** the store is linted and tested by the workspace's jobs, and the pipeline has no `store` job
