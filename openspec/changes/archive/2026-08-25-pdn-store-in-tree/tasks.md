# Tasks: pdn-store-in-tree

A move and its wiring. Nothing in the store's code, tests, or docs changes; every task below is a manifest, a recipe, a workflow, a docs line, or a proof that a scenario is not vacuous.

## 1. The crate

- [x] 1.1 Copy the checkout at `721de62` into `crates/pdn-store` without `.git`, `target`, and the release and pipeline tooling (D8); what is kept is byte for byte the checkout's — `diff -rq` reports only the dropped files
- [x] 1.2 `Cargo.toml`: `publish = false`, a description naming the variant, the docs.rs block gone; the README's head names the variant in place of upstream's badges
- [x] 1.3 Workspace: `crates/pdn-store` a member, `pdn-store = { path = "crates/pdn-store", package = "iroh-docs" }`, the checkout gone from `exclude` and from `.gitignore`

## 2. Recipes and pipeline

- [x] 2.1 `just test` ends with `cargo test --workspace --doc` when given no `-p` or `-E` selection (D5)
- [x] 2.2 `just test-store`: nextest under `--all-features` and `--no-default-features`, then the doctests under every feature (D4)
- [x] 2.3 `just check-store`: clippy on both other feature sets with warnings denied, rustdoc with warnings denied, the featureless `wasm32-unknown-unknown` build (D3, D4)
- [x] 2.4 `precommit-check` and `fix` run both recipes
- [x] 2.5 `ci.yml`: a `store` job beside the workspace's — stable toolchain with the wasm32 target, `just check-store`, `just test-store`
- [x] 2.6 `nightly.yml`: a `store-flaky` job and its `store_iterations` input, running the stress recipe narrowed to the store's ignored tests with `--no-fail-fast` (D6)

## 3. Image build and environment

- [x] 3.1 `ops/Dockerfile`: the `local-inputs` stage and its two `COPY --from` lines gone; `.dockerignore`: the allowances for the checkout and the cargo configuration file gone (D7)
- [x] 3.2 `.devcontainer/compose-all.yml`: the checkout's target volume gone; `mee-pdn.code-workspace`: the checkout's folder gone

## 4. Docs, rules, skills

- [x] 4.1 Workspace `CLAUDE.md` (crate list, commands, git, comments, path-scoped rules) and `README.md` (setup section gone, crate list, recipes)
- [x] 4.2 `crates/data-layer/CLAUDE.md` names the crate rather than the repository; `crates/pdn-store/CLAUDE.md` carries the in-tree commands and checklist in place of the repository's
- [x] 4.3 `.claude/rules/pdn-store.md` scoped to `crates/pdn-store/**`, naming the four recipes
- [x] 4.4 The review skill in `.claude` and `.agents` sweeps two repositories; `fact-of-the-day` draws the store's share from `crates/pdn-store`
- [x] 4.5 Sweep: `mobile-demo-app` no longer describes its repository as nested beside `pdn-store`; ADR-0008 left as a record

## 5. Scenarios made real

- [x] 5.1 The lock file's `iroh-docs` entry carries no `source`; `cargo tree -p data-layer` shows `iroh-docs` at `crates/pdn-store`
  - `Cargo.lock`: `name = "iroh-docs"` / `version = "0.101.0"` / `dependencies = [` — the git source line gone; `cargo tree`: `iroh-docs v0.101.0 (/…/crates/pdn-store)`.
- [x] 5.2 A warning only the featureless build sees fails `check-store` and nothing else — a probe function behind `cfg(not(feature = "fs-store"))`: clippy under every feature passes with warnings denied, the featureless clippy line fails
  - Probe in place: `cargo clippy -p iroh-docs --all-features --all-targets -- -Dwarnings` exit 0; `cargo clippy -p iroh-docs --no-default-features --lib --bins --tests -- -Dwarnings` exit 101, `error: function \`featureless_probe\` is never used`. Probe removed, file restored byte for byte.
- [x] 5.3 A break only the wasm32 build sees fails `check-store` and nothing else — `compile_error!` behind `cfg(wasm_browser)`: the native check passes, the wasm build fails
  - Probe in place: `cargo check -p iroh-docs` exit 0; the wasm32 build line exit 101, `error: probe`. Probe removed, file restored byte for byte.
- [x] 5.4 A README example that stops compiling fails the doctests, and `just test -p iroh-docs` passes without running them
  - A bogus import added to the README's example: `cargo test -p iroh-docs --all-features --doc` exit 101, `error[E0432]: unresolved import`; `just test -p iroh-docs -E 'test(test_ticket_base32)'` exit 0 with no `Doc-tests` line in its output. README restored byte for byte.
- [x] 5.5 Ordinary runs report the three tests marked flaky as skipped; the nightly line with two iterations and `--no-fail-fast` runs all three in both iterations, the failing one not stopping the rest
  - `just test`: 3 skipped among the store's; `just test-store`: 3 and 2 skipped. `just stress -p iroh-docs --run-ignored ignored-only --stress-count 2 --no-fail-fast`: 6 results over 42 s — `sync_full_basic` FAIL in both iterations, `sync_restart_node` and `sync_big` PASS in both, the runner's summary counting 2 failed iterations rather than stopping at the first.
- [x] 5.6 The build context carries `crates/pdn-store` and no `.cargo` entry (`just check-context`, needs the daemon)
  - With a `.cargo/config.toml` beside the workspace: the listing carries `crates` with `pdn-store` under it and no `.cargo` entry.
- [x] 5.7 The `store` and `store-flaky` jobs are wired; their first runs are the pull request's and the next night's
  - Both workflows parse; the jobs call the same recipes a local run does, so what they run is what 6.3, 6.4, and 6.5 ran here.

## 6. Gates

- [x] 6.1 `just check` green, no warnings
  - fmt, clippy on product targets, clippy and check on all targets: 0 warnings; stable rustfmt reports nothing on the store's code.
- [x] 6.2 `just test` green, the store's unit tests and its `client`, `gc`, `sync` binaries among the run, the doctest passed
  - 295 of 295 passed, 18 skipped (15 container scenarios, 3 tests marked flaky); the store's 117 unit tests, `client` 5, `gc` 1, `sync` 12 among them; `Doc-tests iroh_docs`: 1 passed.
- [x] 6.3 `just check-store` green, no warnings
  - Both clippy lines with warnings denied, rustdoc with warnings denied, the wasm32 build (2 min 20 s from cold): 0 warnings. The build yields `libiroh_docs.rlib` and no `.wasm`, which is why the upstream `import "env"` assertion is not carried (D8).
- [x] 6.4 `just test-store` green under both feature sets, the doctest passed
  - `--all-features`: 130 passed, 3 skipped; `--no-default-features`: 101 passed, 2 skipped (one test marked flaky sits behind `fs-store`); doctests under every feature: 1 passed.
- [x] 6.5 The tests marked flaky measured: seconds per iteration, and which of them fails and whether it fails from the checkout too (D6)
  - One iteration of the three: 20 s (`sync_big` 19 s, the other two under 4 s). `sync_full_basic` fails 3 of 3 under the workspace and 3 of 3 from a copy of the checkout run against its own lock file and target directory, on the same assertion (`tests/sync.rs:1337`); both lock files pin the same `iroh` 1.0.2, `iroh-blobs` 0.103.0, `iroh-gossip` 0.101.0, `redb` 3.1.3 and 4.1.0, `tokio` 1.52.3. The store's own flaky job never completed a run (queued on self-hosted runners, cancelled after 24 hours).
