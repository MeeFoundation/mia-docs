# Proposal: pdn-store-in-tree

## Why

The store — n0's `iroh-docs`, diverged where the platform's access model needs it — is the one crate of the platform that lives outside the workspace: a repository of its own, consumed as a git dependency pinned by revision, with a checkout nested beside the workspace and kept out of version control, and a `[patch]` recipe that points the workspace at that checkout while a change is in progress. Substantive changes almost always touch it, so every such change is two commits in two repositories landing in a fixed order — push the store, bump the pin, refresh the lock file — reviewed across two trees, with an image build that allows for a checkout that may or may not be beside the workspace and a cargo configuration file that may or may not point at it.

The store's own checks run nowhere. Its pipeline names self-hosted runners this organization does not have, so its test jobs — the three feature sets, the tests marked flaky — have queued for a day and been cancelled, every day; the checks that do run on hosted runners are not the checks a change of ours is held to. One of its three tests marked flaky fails on every run, and nobody could have seen it.

## What Changes

- **The store becomes a crate of the workspace, `crates/pdn-store`.** A copy of the checkout at its current revision — source, tests, examples, property-test regressions, licenses, README — with nothing of its code, its tests, or its docs changed. The package keeps the upstream name `iroh-docs` and the workspace alias `pdn-store` stays, so no `use` line moves anywhere; the manifest gains `publish = false` and a description of what the crate is, and loses the block that addressed docs.rs. The README's head names the variant in place of upstream's badges.
- **The workspace resolves it by path.** The git dependency, the `[patch]` recipe, the nested checkout, the cargo configuration file that pointed at it, and the workspace's exclusion of that checkout all go. The lock file gains the store's development dependencies, which a git dependency's consumer never resolves.
- **The store's own checks move into `just` and the pipeline.** `just check` and `just test` cover it under default features as they cover every crate, and `just test` ends with the workspace doctests — nextest runs none, and the store's README example is one. Two recipes carry what the workspace build never compiles: `just check-store` (clippy under every feature and under none with warnings denied, rustdoc with warnings denied, the featureless build for `wasm32-unknown-unknown`) and `just test-store` (the tests under both other feature sets, then the doctests under every feature). Both run in `precommit-check` and `fix`, and the pipeline runs them in a `store` job beside the workspace's.
- **The tests marked flaky get the nightly.** The three `#[ignore = "flaky"]` tests stay out of every ordinary run and are repeated by a `store-flaky` job of the nightly workflow, selected by package and by the ignore mark alone, with `--no-fail-fast` so one failing iteration does not hide the rest. Ten iterations measure at about 3.5 minutes.
- **The image build loses its local-inputs stage.** The store is a build input like every crate, through the `crates` entry of the build context's allowed set; the allowance for a checkout beside the workspace and for a cargo configuration file goes with the stage that copied them.
- **Nothing of the store's release and pipeline tooling comes along.** Its workflows, the `cargo-release` and `git-cliff` configuration with the changelog they generated, the `cargo-make` format task, `deny.toml`, the code of conduct, and a nextest configuration whose test group matched no test. Not carried either: cross builds, the android build, `cargo-semver-checks`, the MSRV job, `cargo deny`, codespell, and the wasm `import "env"` assertion — the last read a `.wasm` file an rlib-only crate never produces, so it passed on the missing file.
- **The docs and the agent rules follow.** The workspace `CLAUDE.md` and README, the data layer's and the store's own `CLAUDE.md`, the path-scoped rule for the store (now `crates/pdn-store/**`), the review skill that swept three repositories (now two), the fact-of-the-day command, the devcontainer's volume list, and the editor workspace file.

## Out of Scope (deferred)

- **Renaming the package to `pdn-store`.** Every `use iroh_docs::` in the store's tests, examples, and README would move; the alias already makes the upstream name invisible to consumers. A rename is its own small change if wanted.
- **The workspace's lint set.** The store keeps its own `[lints]` table; the workspace's pedantic set would raise hundreds of warnings in upstream code, and a triage of them is not a move.
- **Tracking upstream through git.** The copy carries no history: the store's commits stay in the archived repository, and a change from upstream arrives as a patch. Adding the tree as a subtree instead, which would let `git subtree pull` merge upstream, was offered and declined.
- **The failing test.** `sync_full_basic` fails on every run, under the workspace and from the checkout alike — 3 of 3 each, on the same assertion, with a lock file identical across the iroh stack — so it is a property of the store, not of the move. It stays marked flaky and runs nightly, where it is red until a change of the store's code addresses it; this change makes none.
- **The spec tree's records.** ADR-0008 names the store by its repository address as the place its facts were verified; a record stays as written.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree.

| Capability (delta)         | Archive destination                                     |
| -------------------------- | ------------------------------------------------------- |
| `data-layer-store-crate`   | `openspec/specs/components/data-layer/store-crate.md`   |
| `pdn-node-container-stand` | `openspec/specs/components/pdn-node/container-stand.md` |

### New Capabilities

- `data-layer-store-crate`: where the store lives and how it is named — a member crate at `crates/pdn-store`, resolved by path, package `iroh-docs` behind the alias `pdn-store` — and how the configurations the workspace build never compiles are checked and tested: the other two feature sets, rustdoc, the wasm32 build, the doctests, and the nightly run of the tests marked flaky.

### Modified Capabilities

- `pdn-node-container-stand`: the requirement that the image carries the workspace as it resolves loses its object — a fork pointed at a checkout beside the workspace — and now states that the image is built from the workspace alone, with no input outside version control reaching the build.

## Impact

- **`crates/pdn-store`** (new): 42 files copied from the checkout at revision `721de62`; `src/`, `tests/`, `examples/`, `proptest-regressions/`, `build.rs`, and both licenses byte for byte; `Cargo.toml` metadata and the README's head as described.
- **`Cargo.toml`, `Cargo.lock`**: the member, the path dependency behind the alias, the checkout gone from `exclude`; the lock gains about 60 packages, all development dependencies of the store.
- **`justfile`**: `test` ends with the doctests when not narrowed; `test-store` and `check-store`; `precommit-check` and `fix` run both.
- **`.github/workflows/ci.yml`, `nightly.yml`**: the `store` job; the `store-flaky` job and its iteration input.
- **`ops/Dockerfile`, `.dockerignore`**: the local-inputs stage and the two allowances gone.
- **`.gitignore`, `.devcontainer/compose-all.yml`, `mee-pdn.code-workspace`**: the checkout's entries gone.
- **`CLAUDE.md`, `README.md`, `crates/data-layer/CLAUDE.md`, `crates/pdn-store/CLAUDE.md`, `.claude/rules/pdn-store.md`, the review skill in `.claude` and `.agents`, `.claude/commands/fact-of-the-day.md`**: the in-tree wording.
- **Nothing in `crates/data-layer`, `crates/pdn-node`, `crates/pdn-node-http`, `crates/pdn-layer`, or `crates/pdn-types`** beyond one line of `data-layer`'s `CLAUDE.md`. Every consumer already names the store as `pdn_store`.
- **Outside the tree**: the nested checkout at the root is deleted and the `pdn-store` repository archived, both by hand. The active change `mobile-demo-app` describes an application repository nested beside `mia-docs` and `pdn-store`; the sweep drops the store from that description.
