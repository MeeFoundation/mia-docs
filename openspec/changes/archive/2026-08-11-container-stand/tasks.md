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

## 4. Where the surface's tests live

- [x] 4.1 In `crates/pdn-node-http/tests/common/`, introduce the request-level helper (method, path, optional body, into status and bytes) and move the step helpers onto it — identity creation, payload minting and consumption, grant publication and reading, entry write and read, poll-until-value.
- [x] 4.2 Point that helper at a container's published port and drop the in-process router implementation together with the scenario binaries that used it (D1): `pdn-node`'s own suite proves the runtime's behaviour without HTTP, so an in-process copy of a stand scenario is a third proof of one property and no proof of the surface.
- [x] 4.3 Keep in this process only what a container cannot show — liveness answering while readiness reports a held state lock — in a test that builds its runtime and its router itself.
- [x] 4.4 Check the tree against that rule: the crate's tests are the stand's binaries plus that one, so "every test of the HTTP surface runs on the stand" is a property of the tree rather than an intention.

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
- [x] 6.5 Move the surface's own bounds onto the stand, in a binary of their own: the debug gate route by route, the same routes present with the flag on, and the body ceiling — each asserted against a node started from the image, so the gate's answer is also the image's own default. Keep in this process only the property that cannot be reached from outside it, the one holding the runtime's state lock, and have it build its runtime itself.
- [x] 6.6 Add the remaining scenarios and the refusal table beside them (D9): a write grant with its denial one claim over, two personas on one node with an audience each, and the refusals — a malformed request, an unhosted identity, a burnt invite secret — all across containers.

## 7. Verification

- [x] 7.1 Run `just test-docker` from a clean image and confirm the whole suite passes.
- [x] 7.2 Run the suite from inside the development container as well, where a spawned container is a sibling on the host's daemon and the development container sits in another network namespace: it works through the container client's host resolution, with nothing set by hand.
- [x] 7.3 Stress the stand's suite (a bounded repeat, tens of runs) and treat any failure as a defect of this change, diagnosed here and not carried forward.
- [x] 7.6 Bound the stand's binary to a test group (D11), so the runner's default width cannot saturate the daemon and leave a node short of its readiness budget.
- [x] 7.4 Run `just precommit-check` — the workspace's own suites stay green after the move in section 4, and the recipe covers the container suite too, since a pass without it says nothing about this crate.
- [x] 7.5 Record the suite's wall-clock time and the image build time from cold and from warm caches, so the next change knows what it costs.

## 8. Documentation

- [x] 8.1 Note the recipes in the workspace's command list, including that the suite needs a daemon and a built image.
- [x] 8.2 Update the crate's docs where the surface's tests are described, so the stand's suite is findable from the crate it drives.
- [x] 8.3 Validate the change (`openspec validate container-stand --strict`) and archive it once the scenarios are green.

## 9. The pipeline

- [x] 9.1 Add a `stand` job to the workflow beside the existing one: the checkout, the toolchain, the test runner, and the container builder.
- [x] 9.2 Build the image in that job through the builder's layer cache, loaded under the tag the scenarios look for, so a run pays for the dependency stage once instead of rebuilding from nothing.
- [x] 9.3 Run the suite through the same profile-selecting recipe the local run uses (D11), so the parallelism of a pipeline run and of a development machine cannot drift apart.
- [x] 9.4 Bound the job's wall clock: past a point the job is stuck rather than slow, and the runner's own ceiling is hours away.
- [x] 9.5 Confirm on a proposed change that the job builds the image and the suite passes inside it.

## 10. The live demo

- [x] 10.1 Write `ops/compose.yml` (D13): seven nodes on one network, the debug flag on, each node's HTTP port published on loopback of the demo host at a fixed port of its own.
- [x] 10.2 Write `ops/demo.sh`: the narration, driving the nodes over HTTP alone, reading its base URLs from the environment, and waiting for every node's liveness before the first step so a slow start is not mistaken for a broken one later.
- [x] 10.3 Add the `demo` recipe: build the image, bring the nodes up and wait for them, run the narration, and remove the nodes on every exit including a failing one. Take the node count from the compose file rather than writing it in the recipe.
- [x] 10.4 Run the demo end to end and confirm both halves of the show: every read converges by repeating the read, and a second run starts from nothing.
