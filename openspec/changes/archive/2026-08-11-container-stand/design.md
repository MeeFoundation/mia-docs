## Context

The HTTP host exists and the scenarios that drive it are green, but every one of them runs inside a single test process: the "hosts" are two or three runtimes in one address space, their endpoints talk over loopback, and a request reaches the router as a function call rather than through a socket. That arrangement proves the surface and the runtime logic; it cannot prove that a node packaged as a binary comes up in a container, publishes an address a peer on another container can dial, and keeps serving a granted namespace when a sibling process is killed.

The material for the stand is largely known. The previous prototype in `mee-v3-single-device` carries a working Dockerfile (cargo-chef planner and builder over a slim runtime stage), a testcontainers harness of about 339 lines, and the recipes `build-image`, `run-image` and `integration-tests`; the shapes transfer, the names and the environment variables do not — the suite's recipe is `test-docker` here, naming the tool the recipe actually invokes, since the workspace's in-process scenarios are integration tests too and are what `just test` and the flaky hunt already select. On this side, the pieces the stand needs from the host are already in place: liveness answers unconditionally, the debug subtree appears only under its flag, the bind address comes from the environment, and the binary answers the stop signal a container runtime sends.

Two properties of the current runtime shape the design more than anything else. Storage is in memory and the node's secret key is fresh per process, so a container that stops and starts again is a different node with an empty state — the stand can stop a device but cannot restart one. And a read nudges a reconciliation before answering from the local replica, so a caller that keeps re-reading converges without waiting out the periodic pass; the pass, every 10 seconds, is the backstop when a nudge's dial is lost.

## Goals / Non-Goals

**Goals:**

- An image of `pdn-node-http` that a container runtime starts, and the recipes that build it, run one of it, and run the suite against it.
- A harness that spawns several containers on one docker network and drives each only through its published HTTP port.
- The scenarios already green in process — the whole stand scenario with its paired denials, and device linking — running across containers instead of in one, plus what only containers can host: a granted peer still converging after the device that published the grant is stopped, and the surface's own bounds asserted against the image.
- An inner loop that stays as fast as it is now: the default test run neither builds an image nor waits on containers, and the flaky hunt does not sweep them in.
- The suite as a gate the pipeline runs on every proposed change, paid for by a layer cache rather than by a rebuild from nothing.
- The live show on the same image: several nodes on one network, fixed loopback addresses, and a narration that drives them over HTTP alone.

**Non-Goals:**

- Persistence of any kind, and therefore any scenario that restarts a node.
- Authentication on the debug surface; where the surface is published is the boundary this change works with.
- Network fault injection, relays, hole punching, discovery, and scale.
- Any change to the runtime, the data layer, or the fork. A scenario that cannot be expressed without one is a finding, not a task.

## Decisions

### D1: Every test of the surface runs on the stand, and one property keeps its own process

The tests that drive the HTTP surface run against nodes on the stand and nowhere else. One helper names a node and a request — a method, a path, an optional body, into a status and bytes — and the node it names is a container; everything above it (create an identity, mint and consume a payload, publish and read a grant, write and read an entry, poll until a value appears) is written once against that helper. The surface's own bounds go there too: the debug gate route by route, the routes it gates, and the body ceiling, each asserted against a node started from the image, where the gate's answer is also the image's own default.

One test keeps its own process, and the reason is a property rather than a preference. The readiness split holds the runtime's coarse state lock from inside the process, and nothing on the surface can be made to hold it — every call that budget guards is, by design, never held across I/O. That test therefore builds its runtime and its router itself and does not come through the harness.

Alternatives considered. A request-level abstraction with two implementations — the router in process, an HTTP client against a container — is where this change starts: it keeps a fast gate that needs no image, at the cost of one indirection. It is not what the change ends with. The two copies prove one property twice and every scenario edit touches both, while the fast gate they buy already exists a layer down, where `pdn-node`'s own suite proves establishment, linking, grants and replication in seconds and without HTTP at all. An in-process copy of a stand scenario is then a third proof of the same property, and the one thing it does not prove is the surface. Restating the scenarios in a second binary instead is worse again, since two hand-written copies drift.

### D2: Convergence is waited for by repeating a read, at the runtime's own cadence

The container scenarios poll a read until it answers, with a budget generously above the 10-second periodic pass. No cadence knob is added to the host binary: the debug surface deliberately offers nothing that forces a reconciliation, and a stand tuned to a cadence no deployment uses would prove convergence that no deployment has. The in-process suite's sub-second cadence comes from the library's own spawn options, which the host does not expose and this change does not add.

The practical cost is bounded. A read nudges its namespace's reconciliation before answering, so the common case converges in the time of one exchange; the periodic pass only matters when a nudge's dial is lost, which is exactly the case a real transport is here to exercise.

### D3: Bind everything inside the container, publish only HTTP

The image leaves the runtime's endpoint bind variable unset, so the endpoint binds every interface and the address it publishes in an invite is the container's address on the docker network — dialable by a sibling container with no relay and no discovery, which is the connectivity the stand is specified to have. The HTTP listener binds all interfaces through the host's own host variable, and the container runtime publishes that port to the test host.

Two consequences the harness must respect. It must not pass the loopback bind value that the workspace recipes export for the in-process suite, since a node that publishes loopback is unreachable from any other container. And the iroh port is never published to the test host: everything between nodes stays inside the docker network, which is also what keeps the "no HTTP between hosts" property honest — the harness knows each container's URL, and no container knows another's.

### D4: The suite is opt-in through an ignore attribute plus a recipe — for cost, not for availability

A container daemon is present on every machine this is developed on, the development container included, where the socket is mounted for exactly this purpose. The suite is opt-in for two other reasons, and neither is its running time: the scenarios themselves cost seconds, as the figures below record. It needs a built image, so a default run either rebuilds one every time — minutes of release build inside the builder — or silently tests whatever image happens to be lying around, which is worse than testing nothing. And the flaky-hunt recipe selects the integration binaries by default, so a container binary joins every stress run, which is the one run in the workspace measured in hundreds of iterations.

`just test-docker` builds the image and runs the stand's binary with ignored tests enabled; the tests carry `#[ignore]` with a reason naming the image and the daemon. A cargo feature would gate them too, but it hides them from a plain listing and adds a feature to a crate that has none.

The pipeline runs the suite in a job of its own, and the expense that would have kept it out — an image rebuilt from nothing on every pull request — is answered by a layer cache rather than accepted: the job builds through the container builder's cache, so a run pays for the dependency stage once.

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

Those scenario figures cover the three scenarios the change starts with. By the end the suite is twelve tests across three binaries, measured again on a daemon holding 8 CPUs and one rung at a time: 1 test slot takes 28 seconds, 2 takes 14, 4 takes 11.5, and 8 takes 11.6. The floor is the suite's longest single test, which 4 slots already reach, so the rungs above it neither cost nor buy anything at this size — and no container misses its readiness budget at any rung, five stress iterations at the widest one included.

### D9: The paired denials that run in containers, and those that stay in process

Per the access-control practice, the container scenario's authorized read is paired in the same place with its tightest denials: a third container that has no connection and no grant is refused, and the claims the grant withholds are absent from the grantee's view after a second replication wave is proven to have happened. The rest of the refusal table — a malformed request, an unhosted identity, a burnt invite secret, a write outside the write set — is asserted across containers too, in a binary of its own beside the scenarios.

One half of the write denial stays out of the stand, and not for convenience. What a refused write here proves is the courtesy check on the grantee's own side: the write never leaves that node. The enforcement is the issuer's ingest gate, which derives its write set independently, and the only way to reach it is to get past the courtesy — which needs a runtime feature this surface does not expose and should not. That half is therefore proven where the bypass lives, in `pdn-node`'s own write-retraction scenario, which forces the write and asserts it never reaches the issuer.

### D12: A stopped node is confirmed by the daemon, not by a probe to its address

Whether a node this scenario stops is really gone is asked of the container daemon. The address it served on says nothing: a stopped container releases its published port, the next container to start can be given it, and a probe then reaches a live node of another scenario — which reads as "the stopped device is still answering" and fails a scenario that is behaving correctly.

### D11: The stand's scenarios are bounded by a test group, not by this machine's core count

The runner schedules one test per core of the machine it runs on, which is the right measure for a test whose node is a task and the wrong one for a test whose node is a container: the daemon holds a fixed share of the machine, and a run wide enough saturates it, at which point a node misses its readiness budget and the failure says nothing about the product. The stand's binaries therefore sit in a test group with a small thread ceiling, and every other binary keeps the default.

The ceiling comes from what the container daemon reports about itself rather than from the cores of the machine running the suite: the two differ whenever the daemon runs on a virtual machine or the suite runs inside a development container. A recipe reads that number and names the matching profile, and both the local run and the pipeline job go through that same recipe, so the bound cannot drift between them. The number of rungs and where each sits is a measurement, revisited when the suite grows — the decision here is only that the bound is the daemon's size and not the test host's.

Raising the readiness budget instead would have been the wrong repair to the same observation — it makes an overloaded run take longer to fail without making it converge, and it hides the one condition the budget exists to report.

### D10: The build context is an allowed set, not a list of things to keep out

The context is declared the other way round from how it is declared today: everything is excluded, and the build's inputs are named — the workspace manifests and lockfile, the crates, the fork's checkout, and the cargo configuration file that may point at it — with build artifacts, repository directories and environment files excluded again at any depth. A list of exclusions has to be extended every time something new appears beside the workspace, and it is silent when it is not; an allowed set is wrong only when the build fails, which is the failure that gets noticed.

The repository root argues for it by itself: a denial list would have to name the agent worktrees (tens of gigabytes of full repository copies), the private notes, three earlier prototype checkouts, the docs repository, the knowledge base and the review directory — and the two patterns it carries today for repository and environment files match at the root only, so every nested repository travels into the context unnoticed. What the build actually needs is a handful of paths.

Checking it is not a matter of reading the file: a throwaway image copies the context and lists every path it received, dotfiles included, and that listing is read against the allowed set. The criterion is presence, not bulk — a leaked private note weighs nothing and matters more than a large directory that was going to be excluded anyway; size only says which leak is expensive. It has a recipe of its own, so the check is a command rather than a remembered incantation.

The list belongs at the repository root, and it collides with nothing there. An ignore file applies to a build context, not to a repository, and the development container's images are built from the `.devcontainer` directory as their context — so the root list has exactly one build under it, the stand's image, and would cover any later build that takes the root as its context. If a second root-context image ever needs a different set, the builder reads an ignore file named after the Dockerfile and sitting beside it, which replaces the root one for that build; the reason to prefer the root file until then is that a list nobody remembers to write is the one an unrelated tree travels through.

### D13: The live demo runs the stand's image, on fixed loopback addresses

The show and the gate share one artifact: the demo brings up the same image the suite runs, so what an audience watches is what the pipeline proved that morning, and a demo that works while the suite is red is a contradiction rather than a possibility. What the demo adds over the suite is orchestration and a narration — a compose file for the nodes and a script that drives them.

Addresses are fixed and published on loopback, which is two decisions rather than one. Fixed, because the narration names devices — Alice's phone, Bob's laptop — and a daemon-assigned port would make each step's address an accident that has to be discovered before it can be spoken about; the suite has the opposite need, since its scenarios run side by side and must not collide. Loopback, because the debug surface is unauthenticated and mints live ceremony secrets, so publishing it further is asked for explicitly rather than inherited from a default.

The nodes are torn down on every exit, the failing one included. A demo that leaves containers behind has the next run meeting the last run's state, which is the one thing a demo must never do — and with storage in memory, tearing down is also what makes every run start clean.

Two smaller shapes follow from the same idea. The count of nodes the recipe reports comes from the compose file rather than from a number written in the recipe, because a number written there goes stale the first time a node is added. And the narration reads its base URLs from the environment, so it names no transport of its own and can be pointed at containers, at processes, or at anything else serving the surface.

The device set is one device per identity, not per person: Alice keeps a laptop for work and another for leisure. That is what makes a device's belonging visible in the room — the leisure laptop hosts the leisure persona and knows nothing of the work one, which is the property the two-personas scenario asserts and the demo shows.

### Operating conditions

Walked, with the outcome for each: several identities on one node (one container hosts two personas of Alice, each with an audience of its own, and the stand asserts that sharing a process is not sharing an audience — connections and grants are keyed by the hosting identity; what the stand cannot assert is read isolation between the two personas, and the reason is structural rather than a gap in the scenarios — see below); one device or several (Alice runs on two containers in the linking and stopped-device scenarios); a device linking after data already exists (the linking scenario reads an entry written before the link); a device that goes away (the stopped-device scenario, which is the property containers exist to prove); capabilities granted and withdrawn (the whole scenario ends by withdrawing the grant and asserting access closes).

Why read isolation between two personas on one node is not among the scenarios: there is nothing to assert. The principal every enforcement point names is the device, not the identity. A serving node computes a caller's rights from its transport-authenticated node id resolved through the published device sets, and a device hosting two identities publishes one node id in both sets — so the resolution is one-to-many and the rights come out as the union, which `data-layer`'s classifier says in as many words. The ingest gate keys its write admission by namespace and node id for the same reason, and a namespace secret is a bearer ticket that no mechanism scopes to "while acting as this identity". Nor is the union a leak worth closing on its own: a device holding both identities' tickets can read either by opening a second session as the other, so refusing the union would cost a round trip and change no outcome.

The boundary becomes assertable only when a session can authenticate *as an identity* rather than as a device — which needs identities to carry key material (KERI) and the reconciliation protocol to carry an identity-level authentication, with the ingest gate rekeyed from node id to identity. The first is planned; the second and third are not yet anywhere, and the KERI plan does not mention namespaces at all. Until all three exist, a scenario asserting that one persona cannot read the other's data would assert a property the system does not have, in a place that could not enforce it.

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

Nothing to migrate: the change adds files, recipes, a pipeline job, and two development dependencies. Rolling it back is deleting them, and nothing in the runtime, the data layer, or the fork changes, so no deployment, spec, or test outside this change depends on it. One thing rolling back does take with it: the surface's tests live on the stand and nowhere else, so removing the stand removes them rather than returning them to this process.

## Open Questions

- Whether "HTTP only from the test host" is a security boundary or an arrangement. Where the surface is published is the whole of its boundary today: the demo publishes on loopback, and the suite's nodes share a network of their own, on which any of them reaches any other's surface. A control plane that authenticates its caller answers the question the other way, and it is its own change.
