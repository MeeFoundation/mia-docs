## Context

The runtime's services are complete and proven in-process, and the container stand proved they run across separate processes over a real transport. Both proofs are read by an engineer in a terminal, because the only host in the tree exists for the stand. Its own spec says the HTTP surface is a host over the core rather than the platform API, and that other hosts embed the same core ([http-host](../../specs/components/pdn-node/http-host.md)); its requirement is generic — product hosts embed the runtime in-process, and the runtime declares no HTTP of its own. This change builds the first host on the product side of that requirement, and nothing above it.

Three properties of the runtime bound everything below, and none is a choice made here. The iroh endpoint binds with no relay and no discovery configured, so a peer is reached only at an address the endpoint publishes about itself. Replicas and payloads are held in memory, so the process is the lifetime of every identity it hosts. An identity is a placeholder value with no key material behind it.

## Goals / Non-Goals

**Goals**

- A host a phone can run, exposing the runtime's operations and nothing beyond them.
- A surface that cites what the runtime says about the state underneath it, so no host built on it can present either the volatility or the keyless identity as something else.
- Certainty about the portability premise before anything is built on it.

**Non-Goals**

- The application, the screens, the shells, and the demonstration. All of that is `mobile-demo-app`, which depends on this change.
- The own-grant read itself, which is `own-grant-read` and lands first. This change exports it.
- Persistence, key-backed identity, retraction verdicts across the boundary, a relay. Each is in the proposal's deferred list with its reason.
- A platform API. This surface is a host for one application, on the same footing as the debug surface's unpinned routes.

## Decisions

### D1. The facade is a crate in this workspace, not in the application repository

`crates/pdn-mobile` sits beside `crates/pdn-node-http` and depends on `pdn-node` alone. Two reasons, and the second decides it: the facade is a host over the runtime and belongs where the runtime's other host lives, and it is Rust that must not drift from the runtime it wraps — inside the workspace `just check` and `just test` cover it on every change to the runtime, and outside it nothing would.

### D2. One handle owns one node

A facade handle owns exactly one runtime, brought up by an explicit call and stopped by an explicit one. A handle offering a set of nodes keyed by a label would make it easy to stage a demonstration in which 3 devices are 3 runtimes inside one phone, and that arrangement cannot show the act it would exist for: a device that goes away takes every runtime co-located with it, so the sibling that should keep serving dies with the device meant to leave.

The constraint is on the handle, not on the operating-system process. A test binary holding 2 handles against 2 runtimes is how the facade's own scenarios reach two nodes, exactly as the runtime's scenarios already do.

This is the one decision the spike can overturn. If a platform suspension kills a bound endpoint irrecoverably, a host needs an act that brings the node back up, which this decision currently refuses — so 1.4 is a question about the specification and not only about the schedule.

### D3. Both grant reads hand back the capability alone

The runtime's read of a peer's grant returns the capability next to the replica's ticket; the read of an identity's own published grants returns the capability alone, because the caller issues the namespace the record addresses. The facade drops the one ticket there is and exports capabilities, as the HTTP host does. Nothing above the facade holds a ticket, and no exported call accepts one: the sanctioned way a granted namespace arrives is that the runtime binds what the grant names.

### D4. The facade's error table is written out, not inherited by reference

The HTTP host's closed table folds an unreachable counterparty and every ceremony timeout into its unrecognized failure, and says so deliberately: for a container test the distinction a denial rested on was a refusal against a defect, and nothing needed more. A person holding a phone needs different actions from those outcomes — move closer or check the network, mint a fresh code, try again — and needs to be told that a scanned code came from an older build rather than that the phone is broken. So the facade names them.

The table is this change's own, stated in its spec, and its divergence from the HTTP host's is written down rather than discovered later. Whether the two converge is a question for `pdn-node-http`'s own change; reaching into another component's spec from here would be the wrong place to settle it.

Two limits the table respects. Where the runtime does not separate two outcomes — a linking dialogue whose bound expires while the dial is still in flight reports the dialogue's timeout, not an unreachable counterparty — the table follows the runtime instead of promising a distinction that does not exist. And the checks that are not in the runtime's error surface at all (an empty entry payload, a malformed path, a grant naming no claim) sit above the service call, so they are the host's to write and to name as the host's; the mechanism is often the same shared validation both hosts call, and what differs is only where the call sits.

### D5. The reconcile cadence is a host decision, stated as such

The host brings the runtime up with an explicitly configured reconcile interval rather than accepting the default of 10 seconds. A short interval costs radio wakeups and battery, so the number belongs to a host that knows what it is running, and it is written down so nobody reads the resulting speed as a property of the network.

What the interval actually governs: the periodic pass drives every replica the node tracks, under either synchronization strategy, so it bounds a published grant record reaching the peer's copy of the pair, a write reaching another device of the same identity, and a linking catch-up, whose re-dial cadence is that pass. It does not bound the grantee's read of a granted claim, which nudges its own filtered reconciliation, so repeating that read converges largely independently of the interval. Gossip is what a swarm-strategy replica gets in addition, not instead.

The container stand requires that no route, environment variable, or harness call shorten the runtime's cadence ([container-stand](../../specs/components/pdn-node/container-stand.md)). That is about a test making convergence look faster than it is; a host configuring its own spawn is neither a route nor a harness, and its reason is the opposite one — a person watching, in a host that says what number it chose.

### D6. A ceremony payload crosses in the runtime's own encoding

The payload crosses opaquely in the sense that the facade never names its fields, inspects it, or wraps it. It does not cross in an encoding of the facade's choosing: it uses the runtime type's own, because the whole purpose of a payload is to be consumed by another node, and that node may sit behind a different host over the same runtime. A payload only this host could parse would leave a phone unable to complete a ceremony with anything else, while still being called "whatever the runtime minted".

The facade also owes a textual form a screen can draw as a code and rebuild from a scan, since that is the channel the ceremony specs describe — a payload moving between devices through a person.

The payload carries a live one-time secret: nothing in it grants durable access, and until the secret is burnt or expires whoever captures it can consume the invitation in the intended recipient's place. The surface states that exposure rather than implying a payload is safe to leave lying about.

### D7. The environment is physical devices in one local network

Without a relay, an endpoint publishes only the addresses it observes about itself. Every Android emulator holds `10.0.2.15` on its own virtual router, so a payload minted in one emulator points the other at itself and 2 emulators cannot pair. What failure that produces is a question for the spike rather than for this document: dialing that address reaches the dialer's own endpoint, which serves the pairing protocol, so whether it surfaces as an unreachable counterparty or as a refusal depends on the transport's identity check, and a permanent specification should not guess.

An iOS simulator is a different case and the same sentence would be false about it: it runs as a process on the host machine's own network stack, so 2 of them reach each other and pairing works.

### D8. The claim derivation is stated on the surface, in both directions

A grant names claim identities derived from the issuer and an entry path, and the derivation is one-way. So publication takes paths and derives, a grant read reports derived identities, and a caller that wants to display a path derives the identities of paths it knows or has listed and compares. The facade exports the derivation for exactly that join.

This is the one place the surface breaks its own "one exported call, one service call" rule, and it is stated rather than hidden: publication derives before it delegates. The alternative — exporting paths and pretending the grant carries them — would put the derivation somewhere invisible and make a grant read undisplayable.

### D9. A single entry payload is bounded, because a phone is killed for memory

The runtime holds every replica in memory. On a container an unbounded entry payload is a large allocation; on a phone it is the end of the process, and with it every identity the node hosts. The facade therefore bounds one payload by a stated ceiling and refuses above it before calling the runtime, as the HTTP host bounds its own. Memory pressure is the one operating condition a phone adds that a container never had.

### D10. The binding artifacts are packaged and released from a repository of their own

The crate stays in this workspace, as D1 decides, and the packaging of what it produces does not. `pdn-sdk` is a repository of its own, cloned in place beside `mia-docs` and `pdn-app`, holding the binding generation, the XCFramework, the Android archive, and the versioned releases an application consumes. An artifact is not a source: producing one needs Xcode and the Android NDK, which the workspace's inner loop neither has nor should acquire, and an application needs a released version it can name rather than a build tree it reaches into. The recipe reads the crate from the `mee-pdn` checkout it is cloned inside, so what it packages is that tree at that commit.

What the split can break is stated here rather than met on a phone. A release names the commit of `mee-pdn` it was built from, because an application built against a facade older than the runtime whose behaviour its screens describe fails as a refusal arriving from the runtime — and a refusal is exactly what the screens are required to show faithfully, so the one failure they cannot explain is the one where the mismatch is the cause.

## Operating conditions

Walked per [operating-conditions](../../specs/code-practices/operating-conditions.md), for the facade rather than for the demonstration.

- **Several identities on one node** — unchanged by this surface: every call names the identity it acts for, and the runtime keeps them disjoint.
- **One device or several** — the facade exports the own-grant read, whose observation contract exists because a sibling device reads a grant only after it replicates.
- **A device restarts** — the process is the lifetime of everything, so a restart is a new node. Stated as a requirement rather than mitigated.
- **A platform suspension** — the condition a phone adds to the restart case, and the one that can amend D2. The spike answers it.
- **Memory pressure** — the second condition a phone adds; D9 bounds the input the host controls. What an unbounded inbound replica does is not bounded here and is named as out of scope.
- **An unstable connection** — the ceremony bounds and the repeated read are the whole answer; nothing here retries on a caller's behalf.
- **A disk that fills** — does not apply: nothing is written to one.
- **Capabilities granted, narrowed, revoked, granted again** — the facade passes them through and holds no state of its own about them, so a re-grant after a withdrawal needs nothing from it. Verified at the runtime level, not here.

## Risks / Trade-offs

**The stack has never been built for either mobile target.** The whole change rests on it working, which is why the spike is first and is a gate rather than a warm-up, and why 1.1 sorts its outcomes: a feature change is proceeded through, a needed fork stops the change, and a platform behaviour that contradicts a requirement amends the requirement before anything is built. `ring` is the crypto provider in the lockfile, the friendlier of the two for both targets; the address-watching and port-mapping dependencies are the likelier trouble.

**The facade's table diverges from the HTTP host's.** Two hosts over one runtime describe the same failures differently. The divergence is deliberate and stated, and the cost is that a reader comparing them has to read both — which is why each spec says what it does and why.

**Two nodes in the facade's tests are two handles, not two processes.** Weaker than the container stand and stronger than nothing: the runtime's suites prove the inter-node path across tasks and the stand proves it across processes, so what these tests add is the surface, which is what they exist for.

**The payload interop is only as good as its test.** A divergence between the two hosts' encodings would be discovered by a person in a room unless a test parses each host's payload with the other's decoding, which is why that test is named rather than left implied.

## Migration Plan

Nothing to migrate. The facade is a new crate. The container stand, its pipeline job and the demo script keep working unchanged — they exercise the same runtime through the other host. One line of the spec tree becomes false when this lands and is corrected in the same change: `http-host.md` says other hosts embed the same core *later*.

## Open Questions

- Whether the facade's async calls cross the boundary as generated futures or as callbacks, and whether an opaque type crosses at all. The spike records what the generated bindings actually offer.
- Whether `pdn-node-http`'s error table is later widened to name the outcomes this table names, which would be its own change, or whether the two hosts stay divergent on purpose.
- What the target Android platform level requires for local-subnet traffic. It changes nothing here, and the application's shells depend on the answer, so the spike records it.
