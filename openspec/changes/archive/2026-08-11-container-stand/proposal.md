# Proposal: container-stand

## Why

Every node the test suite has ever run is a task inside one test process: one address space, one scheduler, one loopback interface, and an HTTP surface reached by handing a request straight to the router. The stand the demo needs is the opposite of that — separate processes, separate containers, a docker network between them, and requests arriving over a socket. Nothing in the tree builds an image or runs a test across two of them, so "two nodes pair, grant, and replicate" is today proven only under conditions no deployment has, and every property that depends on a real transport — an address that a peer on another host can dial, a device that goes away when its process does — is asserted nowhere.

The HTTP surface that made this possible landed already; the scenarios it drives are green in process. What is missing is the packaging and the harness: an image of the host binary, the recipes that build and run it, and a test that drives several containers through the same scenarios over real HTTP.

## What Changes

- **The host binary ships as an image.** A multi-stage Dockerfile builds `pdn-node-http` and packages it on a slim base, running as a non-root user, listening on all interfaces so a sibling container can reach its surface. The iroh endpoint keeps binding every interface, so the address it publishes in an invite is the container's address on the docker network — which is what makes a direct dial between containers work with no relay and no discovery.
- **Three recipes carry it, following the same shape as the previous prototype's.** `build-image` builds the image, `run-image` runs one container for a hands-on look, and `test-docker` builds the image and runs the stand's suite. It sits in the `test` family and names its prerequisite rather than claiming the name integration tests, which the workspace's in-process scenarios already are. The suite stays out of `just test` and out of the flaky hunt's default selection: it needs an image built first, and its wall-clock time belongs to a gate, not to the inner loop.
- **A container harness spawns nodes and speaks to them over HTTP.** Each node is one container on a shared docker network with its HTTP port published to the test host. The harness starts a container, waits for `/live`, and offers the same steps the in-process scenarios use — create an identity, mint and consume payloads, publish and read grants, write and read entries — so a scenario reads the same in both places and the transport is the only difference.
- **The scenario steps stop being tied to the in-process transport.** The existing helpers reach a router directly; they move onto a request-level abstraction with two implementations — the router in process, and a real HTTP client against a container — so the container suite reuses the scenarios rather than restating them.
- **Three scenarios run across containers.** The whole stand scenario with its paired denials (identities created, a connection established, a scoped grant published, an entry written, the grantee reading it, the withheld claims absent, an outsider refused, the grant withdrawn and access closing); a device joining an identity through the linking ceremony; and a granted peer still converging after the device that published the grant is stopped, which is the reachability property proven across processes rather than across tasks.
- **The build context becomes an allowed set.** Everything is excluded and the build's inputs are named — manifests, lockfile, crates, the fork's checkout, and the cargo configuration file that may point at it. The repository root holds tens of gigabytes that have no business in an image (agent worktrees, private notes, three earlier prototypes, the docs repository), and a list of exclusions is silent about whatever appears there next.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree.

| Capability (delta)          | Archive destination                                     |
| --------------------------- | ------------------------------------------------------- |
| `pdn-node-container-stand`  | `openspec/specs/components/pdn-node/container-stand.md` |

### New Capabilities

- `pdn-node-container-stand`: the out-of-process stand — what the image contains and how it is configured, that each node is its own process in its own container, that nodes reach each other only over the runtime's protocols while HTTP stays the control plane from the test host, which scenarios the suite runs, and that the suite stays out of the default test run and the flaky hunt, reachable through a recipe that builds the image first.

### Modified Capabilities

None. The HTTP host already serves liveness unconditionally, gates its debug subtree behind a flag, binds where it is told, and answers a container stop signal — the four things the stand needs from it. No requirement of any component changes here.

## Impact

- **`ops/Dockerfile`** (new): a cargo-chef planner and builder stage over the workspace, a slim runtime stage carrying the binary alone, a non-root user, the HTTP port exposed, and container-appropriate defaults for the host's two bind variables.
- **`.dockerignore`**: rewritten as an allowed set, with build artifacts, repository directories and environment files excluded at any depth. Beside it, `ops/Dockerfile.context` lists what the context actually carries, run through a `check-context` recipe.
- **`justfile`**: `build-image`, `run-image`, `check-context`, `test-docker`.
- **`crates/pdn-node-http`**: `tests/stand.rs` and its harness module, plus dev-dependencies on a testcontainers client and an HTTP client. The existing `tests/common/mod.rs` gains the transport abstraction and keeps its in-process implementation; the scenario steps move behind it.
- **Nothing in `crates/pdn-node`, `crates/data-layer`, `crates/pdn-layer` or the `pdn-store` fork.** If a scenario cannot be expressed without changing one of them, that is a finding of this change, not a task in it.

## Out of Scope (deferred)

- **On-disk persistence and the node's secret key** — the runtime is in memory and takes a fresh key per start, so a restarted container is a different node that remembers nothing. The suite therefore stops containers and never restarts them, and "state survived a restart" stays unproven until persistence lands as its own change, which needs this one to be verifiable at all.
- **`just demo` and docker-compose** — the live show runs the same image, but its orchestration, its fixed addressing, and its script are their own change.
- **Continuous integration** — the suite is a local gate through its recipe. Running it on every pull request needs an image cache in the build, which is its own argument to make.
- **Relays, hole punching, discovery** — one docker network and direct addresses are the whole of the stand's connectivity, exactly as the in-process suite uses loopback.
- **Scale runs** — a million claims and a thousand connections are measured on this stand later, and neither shapes what it is here.
- **Retraction verdicts** — they do not cross the HTTP surface, so the write-retraction scenarios stay in process.
