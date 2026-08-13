# Proposal: container-stand

## Why

Every node the test suite has ever run is a task inside one test process: one address space, one scheduler, one loopback interface, and an HTTP surface reached by handing a request straight to the router. The stand the demo needs is the opposite of that — separate processes, separate containers, a docker network between them, and requests arriving over a socket. Nothing in the tree builds an image or runs a test across two of them, so "two nodes pair, grant, and replicate" is today proven only under conditions no deployment has, and every property that depends on a real transport — an address that a peer on another host can dial, a device that goes away when its process does — is asserted nowhere.

The HTTP surface that made this possible landed already; the scenarios it drives are green in process. What is missing is the packaging and the harness: an image of the host binary, the recipes that build and run it, and a test that drives several containers through the same scenarios over real HTTP.

## What Changes

- **The host binary ships as an image.** A multi-stage Dockerfile builds `pdn-node-http` and packages it on a slim base, running as a non-root user, listening on all interfaces so a sibling container can reach its surface. The iroh endpoint keeps binding every interface, so the address it publishes in an invite is the container's address on the docker network — which is what makes a direct dial between containers work with no relay and no discovery.
- **Recipes carry it, following the same shape as the previous prototype's.** `build-image` builds the image, `run-image` runs one container for a hands-on look, and `test-docker` builds the image and runs the stand's suite. It sits in the `test` family and names its prerequisite rather than claiming the name integration tests, which the workspace's in-process scenarios already are. The suite stays out of `just test` and out of the flaky hunt's default selection: it needs an image built first, and its wall-clock time belongs to a gate, not to the inner loop.
- **A container harness spawns nodes and speaks to them over HTTP.** Each node is one container on a shared docker network with its HTTP port published to the test host. The harness starts a container, waits for `/live`, and offers the steps a scenario needs — create an identity, mint and consume payloads, publish and read grants, write and read entries, repeat a read until a value arrives — so a scenario names a node and a request, and never a transport.
- **The surface's tests move onto the stand entirely.** The helpers that hand a request straight to a router go, and the in-process scenario binaries built on them go with them: `pdn-node`'s own suite proves establishment, linking, grants and replication without HTTP, so an in-process run of a stand scenario proves that behaviour a third time and the surface not at all. What stays in this process is the one property a container cannot show — liveness answering while readiness reports a held state lock.
- **The scenarios run across containers.** The whole stand scenario with its paired denials (identities created, a connection established, a scoped grant published, an entry written, the grantee reading it, the withheld claims absent, an outsider refused, the grant withdrawn and access closing); a device joining an identity through the linking ceremony; a granted peer still converging after the device that published the grant is stopped, which is the reachability property proven across processes rather than across tasks; a grant that names a claim writable, denied one claim over; two personas on one node, each with an audience of its own; and the refusal table, in a binary beside them.
- **The build context becomes an allowed set.** Everything is excluded and the build's inputs are named — manifests, lockfile, crates, the fork's checkout, and the cargo configuration file that may point at it. The repository root holds tens of gigabytes that have no business in an image (agent worktrees, private notes, three earlier prototypes, the docs repository), and a list of exclusions is silent about whatever appears there next.
- **The pipeline runs the suite on every proposed change.** The expense that would have kept it out — an image rebuilt from nothing on each run — is answered by the container builder's layer cache rather than accepted, so the suite becomes a gate instead of a recipe a person remembers to run. The job selects its parallelism the same way the local recipe does, from what the container daemon reports about itself, so the two cannot drift apart.
- **The live demo runs the same image.** A compose file brings up seven nodes — Alice with two personas on a phone plus a laptop each, Bob and Carol with a phone and a laptop each — on one container network, with every HTTP port published on loopback. A narration script drives them over HTTP alone and tears them down on every exit, the failing one included, so a run never meets the previous run's state.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree.

| Capability (delta)          | Archive destination                                     |
| --------------------------- | ------------------------------------------------------- |
| `pdn-node-container-stand`  | `openspec/specs/components/pdn-node/container-stand.md` |

### New Capabilities

- `pdn-node-container-stand`: the out-of-process stand — what the image contains and how it is configured, that each node is its own process in its own container, that nodes reach each other only over the runtime's protocols while HTTP stays the control plane from the test host, which scenarios the suite runs, that the stand is where the HTTP surface is tested at all, that the suite stays out of the default test run and the flaky hunt while running in the pipeline on every proposed change with a bounded parallelism, and that the live demo runs on the same image.

### Modified Capabilities

None. The HTTP host already serves liveness unconditionally, gates its debug subtree behind a flag, binds where it is told, and answers a container stop signal — the four things the stand needs from it. No requirement of any component changes here.

## Impact

- **`ops/Dockerfile`** (new): a cargo-chef planner and builder stage over the workspace, a slim runtime stage carrying the binary alone, a non-root user, the HTTP port exposed, and container-appropriate defaults for the host's two bind variables.
- **`.dockerignore`**: rewritten as an allowed set, with build artifacts, repository directories and environment files excluded at any depth. Beside it, `ops/Dockerfile.context` lists what the context actually carries, run through a `check-context` recipe.
- **`justfile`**: `build-image`, `run-image`, `check-context`, `test-docker`, `stand-profile`, `demo`.
- **`.config/nextest.toml`** (new): the test groups that bound the stand's parallelism, one rung per daemon size, with the suite's binaries filtered into them.
- **`.github/workflows/ci.yml`**: a `stand` job beside the existing one — the image built through the builder's layer cache, then the suite run through the profile the daemon's own CPU count selects.
- **`ops/compose.yml`** and **`ops/demo.sh`** (new): the demo's seven nodes on one network with loopback-published ports, and the narration that drives them over HTTP.
- **`crates/pdn-node-http`**: the stand's test binaries (the scenarios, the refusal table, the surface's own bounds) and their harness module, plus dev-dependencies on a testcontainers client and an HTTP client. The existing `tests/common/mod.rs` becomes that harness, and the in-process scenario binaries go together with the router implementation behind them; the one property that cannot be reached from outside a node's process keeps a test of its own in this process.
- **Nothing in `crates/pdn-node`, `crates/data-layer`, `crates/pdn-layer` or the `pdn-store` fork.** If a scenario cannot be expressed without changing one of them, that is a finding of this change, not a task in it.

## Out of Scope (deferred)

- **On-disk persistence and the node's secret key** — the runtime is in memory and takes a fresh key per start, so a restarted container is a different node that remembers nothing. The suite therefore stops containers and never restarts them, and "state survived a restart" stays unproven until persistence lands as its own change, which needs this one to be verifiable at all.
- **Authentication on the debug surface** — the demo publishes on loopback and the suite's nodes share a network of their own, so the surface's boundary is where it is published rather than a secret it checks. A control plane that authenticates its caller is its own change, and it needs a decision on whether "HTTP only from the test host" is a security boundary or an arrangement.
- **Relays, hole punching, discovery** — one docker network and direct addresses are the whole of the stand's connectivity, exactly as the in-process suite uses loopback.
- **Scale runs** — a million claims and a thousand connections are measured on this stand later, and neither shapes what it is here.
- **Retraction verdicts** — they do not cross the HTTP surface, so the write-retraction scenarios stay in process.
