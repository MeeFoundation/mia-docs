# Proposal: mobile-host-surface

## Why

The runtime has one host, and it exists for the container stand and says so: `pdn-node-http` is scaffolding, its routes are unpinned, and its own spec calls the HTTP surface a host over the core rather than the platform API, requiring that product hosts embed the runtime in-process. Nothing in the tree is such a host. A phone cannot reach the runtime at all, so every property the runtime proves is proven to an engineer reading a terminal.

This change builds the host a phone can run, and stops there. The application that will stand on it, its screens, and the demonstration are a separate change: they are a different language, a different repository, and — most importantly — a different kind of verification. What is here has tests and gates. What follows has a run-through with 2 devices in a room, which no test replaces and which nothing here should pretend to cover.

It begins after `own-grant-read`, which gives the runtime the reading of an identity's own published grants. That operation is exported here and added there, because it is a runtime capability with its own tests and its own paired denial, and bundling it into a host's change would hide both.

## What Changes

- **The stack is proven to build for both mobile targets, before anything is built on it.** Nothing below the facade — iroh, quinn, the TLS provider, the docs engine — has been compiled for `aarch64-apple-ios` or `aarch64-linux-android` in this project, and 2 devices have never paired over a real network with no relay configured. The portability spike is the first task and a gate, and its outcomes are sorted rather than lumped: a feature or configuration change is proceeded through, a dependency needing a fork stops the change, and a platform behaviour that contradicts a requirement below amends it before anything is built on it.
- **A uniffi facade over the runtime, in this workspace.** `crates/pdn-mobile` exposes what the runtime's services already offer — create an identity and list the hosted ones, mint and consume a linking payload, mint and consume an invite payload, list connections, publish a grant and read both halves and withdraw, write and read and list entries, report the node id — as one exported call per service call. It is the second host of the same shape as `pdn-node-http`, it lives in the workspace so `just check` and `just test` cover it, and the runtime keeps knowing nothing about either host. What that crate produces is generated, packaged and released from `pdn-sdk`, a repository of its own: an artifact needs Xcode and the Android NDK, and an application needs a released version it can name.
- **And stops in the same places, for the same reasons.** No namespace ticket crosses the facade. Nothing forces a reconciliation, resets state, or reaches a store outside a service operation. An application that imported a ticket would show data arriving with the grant binding broken, and one given a synchronize control would show convergence with convergence broken — and both substitutions sit in the arrange step, where nothing afterwards reveals them.
- **One handle owns one node.** Bring-up and stop are explicit, stop is safe to repeat, and a handle refuses a second bring-up of its own rather than replacing its node. The constraint is on the handle rather than on the process, so a test binary holding 2 handles stays possible while an application cannot grow a node set behind one.
- **A refusal arrives as a refusal, and the facade's table is stated rather than inherited by reference.** The HTTP host's closed table folds an unreachable counterparty and every ceremony timeout into its unrecognized failure, deliberately — for a container test, a refusal against a defect was the only distinction a denial rested on. A person holding a phone needs different actions from those outcomes, and needs a code minted by an older build reported as a version they cannot consume rather than as a broken phone. So the facade names them, and this change writes its table out instead of pointing at another host's.
- **What a grant names is stated, because it is not a path.** A grant carries claim identities derived from the issuer and an entry path, one-way, so publication derives them and a grant read reports them. The surface says so and exports the derivation, since a caller that wants to show a path has to compare derived identities against paths it knows or has listed. Leaving this implicit would make a grant read undisplayable and the derivation invisible.
- **A single entry payload is bounded.** The runtime holds every replica in memory, and on a phone an unbounded payload ends the process and takes every hosted identity with it. Memory pressure is the one operating condition a phone adds that a container never had, so the facade bounds what it controls and says so.
- **The cadence is a host decision, stated as such.** The host brings the runtime up with an explicitly configured reconcile interval. The default is 10 seconds, so a value can appear well after the write, and the number is written down where the host's behaviour is described so nobody reads the resulting speed as a property of the network.
- **The facade repeats what the runtime says about its state and adds nothing.** Replicas, payloads, hosted identities and the node's own key live only as long as the process, and an identity is a placeholder value with no key material behind it. Both facts belong to the runtime and `data-layer`, so the surface cites them and requires only its own duty: never presenting either as something else.

## Out of Scope (deferred)

- **The application, its screens, and the two platform shells** — the `mobile-demo-app` change, which depends on this one. Nothing about React Native, the camera, a foreground service, or a consent declaration is decided here.
- **The demonstration** — likewise. This change makes it possible and asserts nothing about it.
- **On-disk persistence.** Replicas and payloads stay in memory and the node's secret key stays fresh per start. Persistence is larger than a storage flag: the hosted-identity set is assembled only by the acts of creating and linking, so a process that came back up would hold replicas and no idea which identity each belongs to.
- **Identity backed by key material.** An identity is a random 32-byte value; KERI is the live prospect and nothing here anticipates it.
- **Retraction verdicts across the binding boundary.** The runtime offers them as a stream, which needs a streaming shape and a decision about buffering. Without them, a write into a granted namespace that the issuer's gate later refuses is retracted with no answer on this surface carrying the verdict — the statement the HTTP host's docs already carry.
- **A relay or discovery configuration.** Either would widen where a node can be reached and change what the transport does. It is a change to `data-layer`, not to a host.
- **Widening the HTTP host's error table** to match the facade's. Whether the two hosts converge on the ceremony outcomes is a question for `pdn-node-http`'s own change; this one states the divergence instead of reaching into another component.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree.

| Capability (delta)           | Archive destination                                       |
| ---------------------------- | --------------------------------------------------------- |
| `mobile-common-host-surface` | `openspec/specs/components/mobile-common/host-surface.md`  |
| `sdk-artifacts`              | `openspec/specs/components/sdk/artifacts.md`               |

### New Capabilities

- `mobile-common-host-surface`: what the facade exposes and what it withholds, how entry bytes and paths cross it, what a read that answers nothing means, how a refusal is reported, that one handle owns one node, and what it says about volatile state and an identity without keys.
- `sdk-artifacts`: what a release is built from and names, that the packaging adds nothing to the facade's surface and holds no source of its own, that generated bindings are committed nowhere, the configuration and the architectures a release carries, and that an application consumes a release by naming it.

### Modified Capabilities

None. The runtime's own change is `own-grant-read`; this one exports what that adds and alters no capability of another component. One line of `components/pdn-node/http-host.md` becomes false when this lands — it says other hosts embed the same core *later* — and is corrected in the same change without a delta, since it is prose rather than a requirement.

## Impact

- **`crates/pdn-mobile`** (new): the uniffi facade, its exported types, and its error table. Depends on `pdn-node` only — no `data-layer` dependency, matching the HTTP host. Builds as a static library for `aarch64-apple-ios` and `aarch64-linux-android`, and the generated Swift and Kotlin are build artifacts rather than sources, produced by `pdn-sdk` and committed nowhere.
- **`pdn-sdk`** (new repository, nested and gitignored beside `mia-docs` and `pdn-app`, added to the workspace file): the binding generation, the XCFramework, the Android archive, and the releases an application names, each release naming the commit of `mee-pdn` it packages (D10).
- **`crates/pdn-node`**: untouched. The operation this facade exports arrives with `own-grant-read`.
- **Tooling**: the 2 mobile targets added to `just setup-tooling` and a recipe building the crate for each, here; the binding generation and the packaging, in `pdn-sdk` with the toolchains they need. The container stand, its pipeline job and the demo script are unaffected — they exercise the same runtime through the other host.
- **Tests**: the facade's surface driven in-process against 2 handles through exported calls alone, with the paired denial of an unconnected third handle in the same place; the error table asserted directly; a payload minted here parsed by the other host's decoding and the reverse. The absences are stated in the crate's docs rather than asserted, because an absence has no test that could fail.
- **`components/data-layer/node-assembly.md`**: gains the periodic reconcile pass, the interval its spawn names and the 10-second default as a requirement, so a mobile specification is not the only written statement of the number a host configures. What a node keeps and where is `durable-storage.md`'s and needs no move — it states already that storage is named at the spawn and that neither mode is a default.
- **The risk that outranks the rest**: the portability premise. Until one build runs on one phone and two devices pair over a real network, every task after the spike rests on an assumption.
