## Context

The workspace consumes the store as a git dependency, `pdn-store = { git = "https://github.com/MeeFoundation/pdn-store.git", package = "iroh-docs" }`, pinned in the lock file at revision `721de62`. A change that touches the store is developed against a checkout nested at the repository root, kept out of version control, with a `[patch]` entry — in the workspace manifest or in a local cargo configuration file — pointing the git source at that path; landing it means pushing the store, bumping the pin, refreshing the lock, and reviewing across two trees. The image build has a stage of its own that turns "a checkout and a configuration file may be beside the workspace" into "both are present, possibly empty", so the dependency stage plans from the same resolution the final build uses.

The store's own checks are its repository's pipeline: a format check under a nightly rustfmt configuration, clippy on three feature sets with warnings denied, rustdoc through `cargo docs-rs` on nightly, `cargo deny`, tests on the three feature sets across three operating systems, doctests, a wasm32 build, codespell, semver checks, an MSRV job, cross and android builds. The test jobs name self-hosted runners; in this organization they queue for a day and are cancelled, so the feature matrix and the daily run of the tests marked flaky have never completed. The store's `CLAUDE.md` asks a contributor to run all of it locally, with nightly and three extra tools installed.

The checkout is clean and at the pinned revision, so a copy of it is exactly what the workspace already builds. Stable rustfmt under the workspace's `rustfmt.toml` reports nothing on the store's code: the import grouping upstream enforces with nightly options is one stable rustfmt preserves rather than rewrites.

## Goals / Non-Goals

**Goals:**

- The store as a member crate, with nothing of its code, tests, examples, or docs changed by the move.
- One tree, one commit, one review for a change that touches the store and its consumer.
- Every check the store's pipeline was meant to run and could be run here — the three feature sets, rustdoc, the wasm32 build, the doctests, the tests marked flaky — carried by `just` recipes and by the pipeline, with the same command doing the same thing locally and in the pipeline.
- An image build with no input outside version control.

**Non-Goals:**

- Renaming the package, adopting the workspace's lint set, or reformatting the store: each is a change of the store's tree, and this change makes none.
- Carrying the store's history into this repository, or keeping a git-level path to upstream.
- Fixing the test that fails on every run.
- Reproducing the store's pipeline in full: cross and android builds, semver checks, an MSRV job, `cargo deny`, codespell.

## Decisions

### D1: A copy of the checkout, not a subtree

The tree at `crates/pdn-store` is a plain copy of the checkout at `721de62`, without `.git`, `target`, and the store's release and pipeline tooling. The store's history stays in its repository, which is archived; a change taken from upstream from here on arrives as a patch applied by hand.

Alternative considered: `git subtree add` of the store's repository, without squashing. It keeps `git blame` over the store's 16 own commits and lets `git subtree pull` merge upstream releases, at the price of about 205 upstream commits in this repository's log. Offered as the recommendation; the copy was chosen.

### D2: The upstream package name behind the workspace alias, the directory named after the alias

The package stays `iroh-docs`; the workspace dependency stays `pdn-store = { package = "iroh-docs" }`, now with `path = "crates/pdn-store"`. Nothing that names the crate moves: consumers write `pdn_store::`, the store's own tests and examples and README write `iroh_docs::`, and a patch taken from upstream applies to the same paths. Cargo selects the package by its own name, so the recipes and the pipeline say `-p iroh-docs`, and the `just` recipes' feature helper drops the `pdn-node/test-util` flag for that selection as it does for any package but `pdn-node`.

Alternative considered: renaming the package to `pdn-store`. It would make `-p pdn-store` work and remove the one-name-two-spellings wart, at the price of touching every `use iroh_docs::` in the store's tests, examples, and README — a change of the store's tree, deferred.

### D3: The store's own lints and the workspace's formatter

The store keeps its `[lints]` table — `missing_debug_implementations`, the `iroh_docsrs` cfg — and does not opt into the workspace's, whose pedantic set would raise hundreds of warnings in upstream code. Warnings are denied where the store's pipeline denied them, through clippy's own `-Dwarnings` in `check-store` rather than through `RUSTFLAGS`: a `RUSTFLAGS` value changes every artifact's fingerprint, so a run with it would rebuild the iroh stack beside the workspace's build instead of sharing it.

Formatting is the workspace's: `cargo fmt --all` under `rustfmt.toml`, verified by `just check`. Upstream formats with nightly options that group imports std / external / crate and merge them per crate; stable rustfmt's defaults preserve whatever grouping it finds, so the store's code passes the check unchanged and a new import is placed in its group by hand. No `rustfmt.toml` is added for the store: stable rustfmt warns on every nightly option it finds there, on every run.

### D4: Two recipes for what the workspace build never compiles

`just check` lints the workspace under default features, which is the store's default feature set too; `just test` runs its tests under those features as it runs every crate's. What neither compiles — every feature, no feature, the wasm32 target — is the store's own concern and gets its own recipes: `check-store` (clippy on the two other sets with warnings denied, rustdoc with warnings denied, the featureless build for `wasm32-unknown-unknown` with `getrandom_backend="wasm_js"` named through `RUSTFLAGS`, where it is unavoidable), and `test-store` (nextest on the two other sets, then the doctests under every feature). Both join `precommit-check` and `fix`, and the pipeline runs them in a `store` job beside the workspace's job rather than inside it, so the two extra builds of the iroh stack run in parallel with the workspace's instead of after it.

Alternative considered: folding both into `just check` and `just test`. It would keep two recipes fewer at the price of three more builds of the iroh stack on every inner-loop run, for configurations only the store has.

`cargo docs-rs` on nightly is not carried. The crate denies `missing_docs` and `rustdoc::broken_intra_doc_links` at its root, and `cargo doc` on stable with `RUSTDOCFLAGS=-Dwarnings` catches the rest of what the nightly run caught — an intra-doc link to a private item among them.

### D5: Doctests at the end of `just test`, and under every feature in `test-store`

Nextest runs no doctests, and the store brings one: its README, included into the crate's documentation with `include_str!`, holds the setup example. `just test` with no selection ends with `cargo test --workspace --doc`, under the same `pdn-node/test-util` feature the nextest run enables so the two share artifacts; a run narrowed by `-p` or `-E` is nextest's alone, since a selection cannot name a doctest. `test-store` runs the doctests under every feature as the store's pipeline did.

### D6: The tests marked flaky run nightly, ten times

The three `#[ignore = "flaky"]` tests stay marked and stay out of every ordinary run. The nightly workflow gains a `store-flaky` job that runs `just stress -p iroh-docs --run-ignored ignored-only --stress-count N --no-fail-fast`: the package selection narrows the recipe's default filter to the store, `ignored-only` keeps just the marked tests, and `--no-fail-fast` keeps a failing iteration from cancelling the rest — the stress recipe's own selection would otherwise sweep every integration binary of the workspace in. One iteration of the three measures at about 20 seconds, `sync_big` accounting for 19 of them, so the default of 10 iterations costs about 3.5 minutes.

`sync_full_basic` fails on every run: 3 of 3 under the workspace, and 3 of 3 from a copy of the checkout with its own lock file and target directory, on the same assertion (`tests/sync.rs:1337`, an ordered event assertion met by a `SyncFinished` where another event is expected). The lock files agree on every crate of the iroh stack, so the failure is the store's, not the move's, and the job is red from its first night until a change of the store's code addresses it. Marking the test as anything other than flaky, or filtering it out of the job, would be a change of the store's tree or a hunt that hides its one known catch.

### D7: The image is built from the workspace alone

The store reaches the build context through the `crates` entry of the allowed set, like every crate. The `local-inputs` stage and the two allowances it existed for — the checkout beside the workspace and the cargo configuration file that pointed at it — go, so the context carries nothing outside version control and the dependency-planning stage plans from the same manifests the final build uses, with nothing left to make the two differ. The store's `build.rs` and its `include_str!` of the README hold under the planner's skeleton: the planner replaces sources and build scripts with stubs and cooks external dependencies only, and the final build compiles the crate from its real files.

### D8: What is dropped, and what is not carried

Dropped from the copy: the store's workflows and dependabot configuration, `cliff.toml`, `release.toml` and `CHANGELOG.md` (releases were cut with `cargo-release` and `git-cliff` from conventional commits; nothing here is released), `Makefile.toml` (the nightly format task, superseded by D3), `deny.toml`, the code of conduct, the local agent instruction file, the store's lock file, and `.config/nextest.toml`, whose `run-in-isolation` group matched no test. Kept: both licenses, the README (a build input), the example, and the property-test regression seeds, which proptest resolves from the crate's own `src` sibling directory in a workspace too.

Not carried from the pipeline: cross and android builds, semver checks and the MSRV job (concerns of a published crate), `cargo deny` (a workspace-wide policy this workspace has not adopted), codespell, and the wasm `import "env"` assertion, which read a `.wasm` file an rlib-only crate never produces and therefore passed on the missing file.

### Operating conditions

None of the conditions in [operating-conditions](../../specs/code-practices/operating-conditions.md) change the outcome of this change: no behaviour of the runtime, the data layer, or the store moves. Several identities, several devices, linking, an unstable connection, a full disk, a restart, capabilities granted and revoked — each is handled by code this change copies byte for byte and builds from a different path. The tests that back them are the same tests, run by the same runner under the same feature set, plus the configurations the store's pipeline was meant to run.

## Risks / Trade-offs

- [The nightly store job is red from its first night, on `sync_full_basic`] → Named here and in the proposal, with the failure characterized; the job's summary shows which test, and `--no-fail-fast` keeps the other two tests' figures visible beside it. The fix is a change of the store's code, tracked as such.
- [The lock file grows by about 60 packages, the store's development dependencies among them `iroh`'s test utilities] → Development profile only: the image's dependency stage cooks normal dependencies, and a product build resolves none of them.
- [The store's tests bind every interface, where the workspace's bind loopback through `PDN_BIND_ADDR`] → The store's tests are kept as they are; the variable is the data layer's. On a development machine the per-process startup cost the workspace's tests avoid applies to the store's, which the measured figures include.
- [Upstream tracking becomes a manual patch] → Accepted with D1; the alternative was offered.
- [Records and notes that name the store's repository] → ADR-0008 stays as written, a record of where its facts were verified. The active change `mobile-demo-app` is swept. Private notes are outside the tree.

## Migration Plan

By hand, after the change lands: delete the checkout at the repository root, archive the `pdn-store` repository on GitHub, and delete any local `.cargo/config.toml` that carried the `[patch]`. Rollback is a revert of the commit: the git dependency and its pin resolve again from the archived repository.
