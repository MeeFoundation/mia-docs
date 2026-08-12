## Context

The HTTP host exists and the scenarios that drive it are green, but every one of them runs inside a single test process: the "hosts" are two or three runtimes in one address space, their endpoints talk over loopback, and a request reaches the router as a function call rather than through a socket. That arrangement proves the surface and the runtime logic; it cannot prove that a node packaged as a binary comes up in a container, publishes an address a peer on another container can dial, and keeps serving a granted namespace when a sibling process is killed.

The material for the stand is largely known. The previous prototype in `mee-v3-single-device` carries a working Dockerfile (cargo-chef planner and builder over a slim runtime stage), a testcontainers harness of about 339 lines, and the recipes `build-image`, `run-image` and `integration-tests`; the shapes transfer, the names and the environment variables do not — the suite's recipe is `test-docker` here, naming the tool the recipe actually invokes, since the workspace's in-process scenarios are integration tests too and are what `just test` and the flaky hunt already select. On this side, the pieces the stand needs from the host are already in place: liveness answers unconditionally, the debug subtree appears only under its flag, the bind address comes from the environment, and the binary answers the stop signal a container runtime sends.

Two properties of the current runtime shape the design more than anything else. Storage is in memory and the node's secret key is fresh per process, so a container that stops and starts again is a different node with an empty state — the stand can stop a device but cannot restart one. And a read nudges a reconciliation before answering from the local replica, so a caller that keeps re-reading converges without waiting out the periodic pass; the pass, every 10 seconds, is the backstop when a nudge's dial is lost.

## Goals / Non-Goals

**Goals:**

- An image of `pdn-node-http` that a container runtime starts, and three recipes that build it, run one of it, and run the suite against it.
- A harness that spawns several containers on one docker network and drives each only through its published HTTP port.
- The scenarios already green in process — the whole stand scenario with its paired denials, and device linking — running across containers without being restated, plus one scenario that only containers can host: a granted peer still converging after the device that published the grant is stopped.
- An inner loop that stays as fast as it is now: the default test run neither builds an image nor waits on containers, and the flaky hunt does not sweep them in.

**Non-Goals:**

- Persistence of any kind, and therefore any scenario that restarts a node.
- The live demo's orchestration (compose, fixed addressing, a script to run in front of an audience).
- Continuous integration for the suite, and the image caching that would make it affordable.
- Network fault injection, relays, hole punching, discovery, and scale.
- Any change to the runtime, the data layer, or the fork. A scenario that cannot be expressed without one is a finding, not a task.

## Decisions

### D1: The request layer is abstracted; the scenarios above it are written once

The existing helpers hand a request to a router. They move onto one small abstraction — a call taking a method, a path, an optional body, and returning a status and bytes — with two implementations: the router in process, and an HTTP client against a container's published port. Everything above that call (create an identity, mint and consume a payload, publish and read a grant, write and read an entry, poll until a value appears) is written against the abstraction, so the whole stand scenario and the linking scenario exist as one body each, invoked by both test binaries.

Alternatives considered. Restating the scenarios in the stand's binary duplicates roughly 400 lines of assertions and lets the two copies drift, which is worse than usual here because the copies are meant to prove the same property under two transports. Deleting the in-process scenarios once the container ones exist loses the fast gate — seconds, no image, and it runs in continuous integration today. Keeping both, written once, costs one indirection.

Scenarios that differ in more than transport stay separate: stopping a container has no in-process counterpart, and the in-process suite keeps its own bounded-surface tests (the debug gate, the readiness budget, the oversized body) where a container adds nothing.

### D2: Convergence is waited for by repeating a read, at the runtime's own cadence

The container scenarios poll a read until it answers, with a budget generously above the 10-second periodic pass. No cadence knob is added to the host binary: the debug surface deliberately offers nothing that forces a reconciliation, and a stand tuned to a cadence no deployment uses would prove convergence that no deployment has. The in-process suite's sub-second cadence comes from the library's own spawn options, which the host does not expose and this change does not add.

The practical cost is bounded. A read nudges its namespace's reconciliation before answering, so the common case converges in the time of one exchange; the periodic pass only matters when a nudge's dial is lost, which is exactly the case a real transport is here to exercise.

### D3: Bind everything inside the container, publish only HTTP

The image leaves the runtime's endpoint bind variable unset, so the endpoint binds every interface and the address it publishes in an invite is the container's address on the docker network — dialable by a sibling container with no relay and no discovery, which is the connectivity the stand is specified to have. The HTTP listener binds all interfaces through the host's own host variable, and the container runtime publishes that port to the test host.

Two consequences the harness must respect. It must not pass the loopback bind value that the workspace recipes export for the in-process suite, since a node that publishes loopback is unreachable from any other container. And the iroh port is never published to the test host: everything between nodes stays inside the docker network, which is also what keeps the "no HTTP between hosts" property honest — the harness knows each container's URL, and no container knows another's.

### D4: The suite is opt-in through an ignore attribute plus a recipe — for cost, not for availability

A container daemon is present on every machine this is developed on, the development container included, where the socket is mounted for exactly this purpose. The suite is opt-in for three other reasons. It needs a built image, so a default run either rebuilds one every time — minutes of release build inside the builder — or silently tests whatever image happens to be lying around, which is worse than testing nothing. It waits on convergence at the runtime's own cadence (D2), so its wall-clock time is in minutes while the in-process suite's is in seconds, and `just test` is the inner loop. And the flaky-hunt recipe selects the integration binaries by default, so a container binary joins every stress run, which is the one run in the workspace measured in hundreds of iterations.

`just test-docker` builds the image and runs the stand's binary with ignored tests enabled; the tests carry `#[ignore]` with a reason naming the image and the daemon. A cargo feature would gate them too, but it hides them from a plain listing and adds a feature to a crate that has none.

The same cost is why continuous integration stays out of this change: the pipeline today is the default test run, and adding an uncached image build to every pull request is the expense the proposal defers, not a property the stand lacks.

### D5: The image build follows whatever the workspace resolves, the local fork checkout included

The workspace can point the store fork at the checkout beside it — through the cargo configuration file, which is kept out of version control — and the build follows that resolution rather than refusing it: rebuilding the image is then the shortest path from a fork edit to that edit running in the stand, which is the loop the stand is supposed to shorten. Two build inputs follow from that: the checkout's source, and the configuration file that points at it, both named in the allowed set of the build context (D10). The dependency-planning stage sees the same two, so the cached dependency layer is built from the same resolution as the final build.

One consequence in the image: the dependency stage receives only the recipe, so a recipe naming a local path would resolve nothing — a small stage ahead of it turns both optional inputs into "present, possibly empty", and the dependency stage then resolves exactly what the final build does.

The cost is two lines of the allowed set, not a different shape of it: the context's bulk — the agent worktrees, the private notes, the earlier prototypes, the docs repository — is excluded either way, and the fork folds into this repository shortly, after which its source is a workspace member that the context must carry regardless.

Nothing is given up by allowing it: a pull-request build starts from a clean checkout with no local configuration file, so what merges is built against the published fork regardless of what any developer's tree resolves to.

Alternative considered: refusing to build while the patch is active, so an image could never carry an engine that exists on one machine. Rejected — that check is already performed where it decides anything, and it costs the one workflow that makes a fork change cheap to try on the stand.

### D6: The stopped-device scenario is also the check on a dormant branch

A contact derived from a device record carries an endpoint id and nothing else; resolving it depends on the endpoint already knowing a path to that id. In process, over loopback, that has never been in doubt. Across containers it is real: if the surviving device cannot be reached by id, this scenario fails, and that failure is the signal to take up the deferred branch that carries addresses in the device record (product-path-gaps design, D4). Addresses are not added pre-emptively — the check exists precisely so the branch stays dormant on evidence rather than on assumption.

### D7: One docker network per scenario, created and removed by the harness

Each scenario creates its own network and removes it when it ends, including on a panic. A shared network is cheaper, but a container left behind by a failed run would be dialable by the next scenario, and an isolation defect would read as a pass. Container lifetimes are managed by the testcontainers client, which removes them when the handle drops.

### D8: A release build, packaged on a slim runtime image

The builder stage uses cargo-chef so a dependency layer survives a source edit, and a compiler cache mount so repeated builds are cheap; the runtime stage carries the binary, the certificate bundle, and a non-root user. The build is release, matching what the demo runs: a debug node under real timing is a different animal from the one the audience sees, and the sync paths are the part of it under test.

### What it costs, measured

Reference figures, on a 16-core machine whose container daemon holds 8: the first image build is about 2 minutes, of which the dependency stage is 48 seconds and installing the recipe tool 25; a rebuild with no source change is 11 seconds. The three scenarios together take 11 seconds, ten stress iterations of them 113. The workspace's in-process suite is 112 seconds — the figure the stand is kept out of.

### D9: The paired denials that run in containers, and those that stay in process

Per the access-control practice, the container scenario's authorized read is paired in the same place with its tightest denials: a third container that has no connection and no grant is refused, and the claims the grant withholds are absent from the grantee's view after a second replication wave is proven to have happened. The rest of the refusal table — a malformed request, an unhosted identity, a burnt invite secret, a write outside the write set — stays in the in-process suite, where it is already green and where a container adds only minutes.

### D12: A stopped node is confirmed by the daemon, not by a probe to its address

Whether a node this scenario stops is really gone is asked of the container daemon. The address it served on says nothing: a stopped container releases its published port, the next container to start can be given it, and a probe then reaches a live node of another scenario — which reads as "the stopped device is still answering" and fails a scenario that is behaving correctly.

### D11: The stand's scenarios are bounded by a test group, not by this machine's core count

The runner schedules one test per core of the machine it runs on, which is the right measure for a test whose node is a task and the wrong one for a test whose node is a container: the daemon holds a fixed share of the machine, and a run wide enough saturates it, at which point a node misses its readiness budget and the failure says nothing about the product. The stand's binary therefore sits in a test group with a small thread ceiling, and every other binary keeps the default.

Raising the readiness budget instead would have been the wrong repair to the same observation — it makes an overloaded run take longer to fail without making it converge, and it hides the one condition the budget exists to report.

### D10: The build context is an allowed set, not a list of things to keep out

The context is declared the other way round from how it is declared today: everything is excluded, and the build's inputs are named — the workspace manifests and lockfile, the crates, the fork's checkout, and the cargo configuration file that may point at it — with build artifacts, repository directories and environment files excluded again at any depth. A list of exclusions has to be extended every time something new appears beside the workspace, and it is silent when it is not; an allowed set is wrong only when the build fails, which is the failure that gets noticed.

The repository root argues for it by itself: a denial list would have to name the agent worktrees (tens of gigabytes of full repository copies), the private notes, three earlier prototype checkouts, the docs repository, the knowledge base and the review directory — and the two patterns it carries today for repository and environment files match at the root only, so every nested repository travels into the context unnoticed. What the build actually needs is a handful of paths.

Checking it is not a matter of reading the file: a throwaway image copies the context and lists every path it received, dotfiles included, and that listing is read against the allowed set. The criterion is presence, not bulk — a leaked private note weighs nothing and matters more than a large directory that was going to be excluded anyway; size only says which leak is expensive. It has a recipe of its own, so the check is a command rather than a remembered incantation.

The list belongs at the repository root, and it collides with nothing there. An ignore file applies to a build context, not to a repository, and the development container's images are built from the `.devcontainer` directory as their context — so the root list has exactly one build under it, the stand's image, and would cover any later build that takes the root as its context. If a second root-context image ever needs a different set, the builder reads an ignore file named after the Dockerfile and sitting beside it, which replaces the root one for that build; the reason to prefer the root file until then is that a list nobody remembers to write is the one an unrelated tree travels through.

### Operating conditions

Walked, with the outcome for each: several identities on one node (the scenario's third container hosts its own identity, and the stand's identities are created per container); one device or several (Alice runs on two containers in the linking and stopped-device scenarios); a device linking after data already exists (the linking scenario reads an entry written before the link); a device that goes away (the stopped-device scenario, which is the property containers exist to prove); capabilities granted and withdrawn (the whole scenario ends by withdrawing the grant and asserting access closes).

Deliberately left out: a device that restarts, since a restarted container is a different node without persistence; an unstable connection, since the stand has no fault injection and adding it is not this change; a disk that fills, which does not apply to memory storage.

## Risks / Trade-offs

- **A container spawned from inside the development container is a sibling, not a child** → its published port lands on the host, and the development container runs in another network namespace, so the address the harness dials must come from the container client's own host resolution rather than from an assumed loopback. That resolution answers loopback from the host, and from inside a container the gateway of the daemon's bridge network, which reaches the published port because the daemon publishes it on every interface. The suite therefore runs in both places with nothing set by hand.
- **The image build dominates the edit loop** → the dependency layer and the compiler cache survive source edits, and the recipe reuses the tag; a scenario-only edit rebuilds one layer.
- **Real timing makes the suite flaky** → the change ends with a bounded stress pass over the stand's suite, and any failure is diagnosed as a defect of this change rather than carried forward. The suite's small size keeps that affordable; the flaky practice's full discipline applies if a failure appears.
- **A published address that no peer can use** (loopback first in the list, or a bind variable leaking in from the environment) → the image sets the HTTP bind explicitly and leaves the endpoint's bind unset; the harness passes an explicit environment rather than inheriting one, and a stalled scenario dumps the containers' logs before failing.
- **A dialable-by-id assumption that does not survive a real network** → D6 turns that from a silent weakness into a failing scenario with a named follow-up.
- **The dependency-planning stage reaches for a fork checkout it was never given** → it does, and the build stops there rather than resolving something else: the dependency stage receives only the recipe, and a recipe naming a local path needs that path. A stage of its own normalises both optional inputs — the checkout and the cargo configuration — into "present, possibly empty", so the dependency stage resolves exactly what the final build does whether or not a workspace resolves the fork locally.
- **The suite grows into a second home for everything** → the scenarios that belong here are those whose subject is the transport, the process boundary, or a device's disappearance; everything else stays in process, where it is faster and already covered.

## Migration Plan

Nothing to migrate: the change adds files, three recipes, and two development dependencies. Rolling it back is deleting them, and nothing in the runtime, the data layer, or the fork changes, so no deployment, spec, or test outside this change depends on it.

## Open Questions

- Whether the suite eventually runs in continuous integration, and what image cache makes that affordable — deferred with the rest of the continuous-integration question.
- Whether the live demo's compose file reuses the harness's environment conventions or defines its own; that change decides, and this one keeps the conventions in one place so it can.
