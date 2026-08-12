## 1. The build context

- [x] 1.1 Rewrite `.dockerignore` as an allowed set (D10): exclude everything, then name the build's inputs — the workspace manifests and lockfile, `crates/`, the fork's checkout, and `.cargo/config.toml`, which is where a local fork resolution is declared.
- [x] 1.2 Exclude build artifacts, repository directories and environment files again at any depth. The patterns the current list carries for the last two match at the root only, so every nested repository — the fork's, the docs repository's, each worktree's — travels into the context today.
- [x] 1.3 Verify the context by enumeration rather than by eye: `ops/Dockerfile.context`, a throwaway image that copies the context and lists it. The package install takes its assume-yes flag (`apt-get install -y tree`), or the build stops at a prompt no one is there to answer. And the listing runs as `tree -a --du -h`: `-a` because without it the repository directories, the environment files, the agent worktrees and the cargo configuration — everything the check is for — are hidden; `--du -h` because it accumulates sizes per directory in the same output, so presence and cost are read in one pass; and no forced colour, since the output is read from a log.
- [x] 1.4 Read the listing as a whole against the allowed set: the criterion is that nothing outside it is present at all, not that the context is small. Sizes are the second lens — they say which leak is expensive, not whether there is one. Run the check before and after the rewrite, so what used to travel is on the record, and record the transferred size as a number a later growth can be compared against.
- [x] 1.5 Note in `ops/Dockerfile.context` that it reads the ignore file named after itself and otherwise the root one: if the stand's image ever takes a Dockerfile-specific ignore file, this check silently stops reading the list it is meant to check.

## 2. The image

- [x] 2.1 Write `ops/Dockerfile`: a cargo-chef planner stage, a builder stage with a compiler-cache mount building `-p pdn-node-http --release`, and a slim runtime stage carrying the binary, the certificate bundle, and a non-root user.
- [x] 2.2 Set the image's environment: the HTTP host binds all interfaces on the default port, and the runtime's endpoint bind stays unset so the endpoint publishes the container's address. Expose the HTTP port.
- [x] 2.3 Check that the runtime image carries the binary and its certificates and nothing else — no source, no repository directory, no build artifacts from the builder stage.
- [x] 2.4 Build the image by hand once and check the two properties that make the rest possible: the container answers `GET /live`, and `/debug/` is 404 without the flag.

## 3. The recipes

- [x] 3.1 Add `build-image` to the justfile: build with the image tag defaulted and overridable, following the workspace's own dependency resolution.
- [x] 3.2 Build once with `.cargo/config.toml` pointing the fork at the checkout beside the workspace, and confirm the image carries that fork — the dependency-planning stage included, since it must see the same resolution as the final build.
- [x] 3.3 Add `run-image`: one container, HTTP port published, debug flag on, for a hands-on look.
- [x] 3.4 Add `check-context`: build and run `ops/Dockerfile.context`, so the check is a command rather than a remembered incantation.
- [x] 3.5 Add `test-docker`: build the image, then run the stand's test binary with ignored tests enabled. Keep the suite out of `just test`.
- [x] 3.6 Check that `just test` runs none of the stand's tests and that `just stress` with no selection does not sweep its binary into a flaky hunt.

## 4. The transport abstraction

- [x] 4.1 In `crates/pdn-node-http/tests/common/`, introduce the request-level abstraction (method, path, optional body, into status and bytes) and move the existing helpers onto it, keeping the in-process router implementation behind it.
- [x] 4.2 Move the step helpers (identity creation, payload minting and consumption, grant publication and reading, entry write and read, poll-until-value) onto the abstraction, so they name no transport.
- [x] 4.3 Lift the whole-scenario body and the linking body into shared functions parameterized by the harness, and have the in-process binaries call them. The suite must stay green with no behavior change — this step moves code and nothing else.

## 5. The container harness

- [x] 5.1 Add the dev-dependencies (a testcontainers client and an HTTP client) to `crates/pdn-node-http`.
- [x] 5.2 Write the harness: create and remove a network per scenario including on panic; spawn a container with an explicit environment (never inheriting the workspace's loopback bind value); wait for `/live`; expose the container's URL to the scenario.
- [x] 5.3 Implement the abstraction over a real HTTP client against a container's published port, with a convergence budget above the runtime's periodic reconciliation interval.
- [x] 5.4 Add a stop operation for a container, and make a failed wait dump the containers' logs before failing.

## 6. The scenarios

- [x] 6.1 `tests/stand.rs`: the whole stand scenario across 3 containers, calling the shared body, with its paired denials — the unconnected container refused, and the withheld claims absent after a proven second replication wave.
- [x] 6.2 The linking scenario across 2 containers, calling the shared body: the joined device reports the identity as hosted and reads an entry written before the link.
- [x] 6.3 The stopped-device scenario: an identity on 2 containers, the grant published from the first, that container stopped, and the peer converging on an entry written by the survivor. If the survivor turns out not to be dialable by endpoint id, stop and record it against the deferred device-record addressing branch (design, D6) instead of working around it.
- [x] 6.4 Mark every test in the stand's binary ignored, with a reason naming the daemon and the image.

## 7. Verification

- [x] 7.1 Run `just test-docker` from a clean image and confirm all three scenarios pass.
- [x] 7.2 Run the suite from inside the development container as well, where a spawned container is a sibling on the host's daemon and the development container sits in another network namespace: it works through the container client's host resolution, with nothing set by hand.
- [x] 7.3 Stress the stand's suite (a bounded repeat, tens of runs) and treat any failure as a defect of this change, diagnosed here and not carried forward.
- [x] 7.6 Bound the stand's binary to a test group (D11), so the runner's default width cannot saturate the daemon and leave a node short of its readiness budget.
- [x] 7.4 Run `just precommit-check` — the in-process suite must be green and unchanged in behavior after the move in section 4.
- [x] 7.5 Record the suite's wall-clock time and the image build time from cold and from warm caches, so the next change knows what it costs.

## 8. Documentation

- [x] 8.1 Note the recipes in the workspace's command list, including that the suite needs a daemon and a built image.
- [x] 8.2 Update the crate's docs where the surface's tests are described, so the stand's suite is findable from the crate it drives.
- [x] 8.3 Validate the change (`openspec validate container-stand --strict`) and archive it once the scenarios are green.
