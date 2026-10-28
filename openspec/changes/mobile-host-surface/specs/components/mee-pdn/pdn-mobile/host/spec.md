# Mobile host

The mobile host is the second host over the runtime and the first one on the product side of the boundary [http-host](../../pdn-node-http/host/spec.md) draws: a product host embeds the runtime core in-process and reaches other nodes only over the runtime's own protocols, while the runtime carries no host dependency of its own. What this surface exposes, what it refuses to expose, how it reports a refusal, and what it says about the state underneath it are requirements, because an application built on it can only be as honest as the surface it stands on.

Three words are used throughout with the meanings the runtime gives them. An *identity* is what the runtime hosts: a private metadata store (PMS) of its own devices, and the pods it holds. A *pod* is the shared primitive: a membership store and a record store that every current member replicates. A *record* is what a member places in a pod under its own name — a claim or an immutable-document placed once, or a mergeable-document that takes operations.

## ADDED Requirements

### Requirement: The facade covers the runtime's operations and adds none
The facade SHALL make the embedded runtime's service operations reachable from the application: creating an identity and listing the hosted ones; minting a device-linking payload and consuming one; creating a pod, listing the pods an identity holds, listing a pod's members, minting a pod invite and joining a pod by one, and writing a membership act; placing a record, appending an operation to a mergeable-document, reading a record, reading a mergeable-document's operations, and listing a pod's records; and reporting the node id.

Each exported call SHALL delegate to one service call and SHALL add no orchestration of its own. It retries no ceremony, remembers no result, and holds no rule about what a member may read. An application and a facade that each kept a view of the same thing would drift, and the drift would show as a screen contradicting the node it sits on.

#### Scenario: Every act of the demonstration is reachable
- **WHEN** an application drives two nodes through the facade alone — creating an identity on each, creating a pod on one, minting a pod invite there, joining from the other, placing a record, and reading it back through the joiner
- **THEN** every step is an exported call, and no step requires reaching into the runtime around the facade

#### Scenario: A ceremony's outcome is the runtime's
- **WHEN** an exported ceremony call fails
- **THEN** the facade reports the failure and retries nothing, and a retry is the application making a fresh call with a freshly minted payload

### Requirement: The exported surface is exactly this set
The facade SHALL export the operations named above and SHALL NOT export the runtime's remaining public surface. In particular it SHALL NOT export any out-of-band namespace share or import, and SHALL NOT export anything the runtime gates behind its test-only feature. The facade SHALL build with that feature disabled, so a forced write or an observation of a replica is not merely unexported but absent from the binary.

Beside those operations the facade SHALL export exactly 1 value that reaches no service call: the ceiling on one record payload or operation, so a caller can refuse an oversized write before making one. It is stated here rather than left to be discovered, because an export the specification does not admit is indistinguishable from one somebody added on the way past.

On Android the facade SHALL export besides exactly 1 symbol the binding generator does not produce: the JNI entry `Java_uniffi_pdn_1mobile_AndroidContext_install`, which hands the runtime the application's context (the requirement on the Android context below). It reaches no service call and changes nothing a node does except where its DNS resolvers come from.

#### Scenario: The withheld operations are absent, not merely undocumented
- **WHEN** the facade's exported surface is enumerated
- **THEN** it names no share, no import, no forced write, and no observation of a replica

#### Scenario: The test-only feature is off in what ships
- **WHEN** the artifacts a device installs are built
- **THEN** the facade is compiled without the runtime's test-only feature enabled

### Requirement: No namespace ticket crosses the facade
No exported call SHALL hand over or accept a namespace ticket in any form. A pod's store tickets cross only inside the join dialogue, between the runtime on either side.

The sanctioned way a pod's stores arrive is the join: the inviter's runtime hands them over once the dialogue's one-time secret matches, and the membership the joiner then holds is what every member's replica judges its sessions by. An application able to import a ticket would hold a pod's stores the membership never admitted it to, and the substitution would sit in the arrange step, where nothing afterwards reveals it: the value still appears, obtained the wrong way ([product-path-arrangement](../../../../code-practices/product-path-arrangement.md)).

#### Scenario: A pod's records arrive with no ticket above the facade
- **WHEN** a member mints a pod invite, another handle joins with it, and the joiner then reads a record the member placed
- **THEN** the record eventually reads back, and no exported call was available that would have handed over or accepted a namespace ticket

### Requirement: The facade offers no convenience the product lacks
The facade SHALL NOT offer any call whose purpose is to force a reconciliation, reset state, drop a replica, or reach a store other than through a service operation. Repeating the read SHALL be the only wait mechanism available for a value written elsewhere.

The reason is what the demonstration proves. A screen given a synchronize control would keep showing convergence after convergence broke; a screen that reset state between acts would hide an act that only worked from a fresh node. Both substitutions live in the arrange and act steps, and both leave the assertions looking right.

#### Scenario: Repeating the read is the only wait
- **WHEN** the application waits for a record placed on another node
- **THEN** repeating the read is the only mechanism available for the wait, and no exported call exists whose purpose is to force a reconciliation

#### Scenario: No act resets the node
- **WHEN** the exported surface is enumerated
- **THEN** it offers no call that clears an identity, forgets a pod, or returns the node to a fresh state

### Requirement: An identity that never joined a pod obtains nothing of it through the facade
Every positive access the facade offers SHALL be specified beside the tightest denial the facade can express: a handle whose identity never joined a pod obtains nothing of it, neither its listing nor any record, and is refused as no member of that pod.

The second read negative [access-control-tests](../../../../code-practices/access-control-tests.md) names — a party holding the replica's ticket but no capability — cannot be staged through this surface at all, because no ticket crosses it. That is the surface working as specified, not an omission, and the denial stays where it can be staged: the runtime's own scenarios, which hold it against a hand-made ticket. This requirement says so rather than leaving the gap to be read as an oversight.

#### Scenario: An outsider is refused beside the member who reads
- **WHEN** a member places a claim and a joiner reads it, and a third handle whose identity holds no invite lists the pod and reads the same claim
- **THEN** the joiner reads the claim and the third handle obtains nothing, both of its calls refused as addressing a pod it is no member of

### Requirement: One handle owns one node
One facade handle SHALL own exactly one runtime, brought up by an explicit call that names the directory the node keeps its state in and stopped by an explicit call that is safe to repeat. The embedder names the directory because it is the one that knows its own sandbox, and the runtime's spawn requires a storage choice ([durable storage](../data-layer/durable-storage.md)). A handle SHALL NOT offer a set of nodes, and SHALL refuse a second bring-up of its own while its node is up rather than silently replacing it. The constraint is on the handle rather than on the operating-system process, so a test binary holding two handles against two runtimes remains possible while an application holding one cannot grow a node set behind it.

A host that could hold several nodes invites a staging in which several devices are several runtimes inside one phone, and that staging cannot show the act it would exist for: a device that goes away takes every runtime co-located with it, so the sibling that should keep serving dies with the device that was meant to leave.

#### Scenario: Bring-up and stop are explicit
- **WHEN** the application brings the node up and later stops it, calling stop a second time
- **THEN** the first stop closes the endpoint and the protocols, and the second is a no-op rather than a failure

#### Scenario: A second bring-up is refused
- **WHEN** a bring-up is requested while a node is already up
- **THEN** the facade refuses it and the running node is untouched

### Requirement: An Android host hands the runtime its application context
An Android application SHALL call `uniffi.pdn_mobile.AndroidContext.install(context)` with its application context once, after `System.loadLibrary("pdn_mobile")` and before its first bring-up. The runtime's DNS reader asks Android for the active network's resolvers through JNI and needs that context to; without it the reader panics, the panic is caught, and the node falls back to public resolvers, which a network that answers only its own resolvers — a VPN's, a company's — then leaves unable to find its relay. The first call SHALL count and a later one SHALL change nothing. The facade SHALL take the call as a JNI entry and not through the generated bindings, because JNA loads the library without running `JNI_OnLoad`; the Kotlin declaration, `object AndroidContext { @JvmStatic external fun install(context: Any) }` in the package `uniffi.pdn_mobile`, is the application's, since the packaging carries no hand-written Kotlin. A build of the facade for Android SHALL NOT set `panic = "abort"`: a bring-up without the context would then abort the process at its first lookup instead of falling back.

**Example:** an application's `Application.onCreate` calls `System.loadLibrary("pdn_mobile")`, then `AndroidContext.install(this)`, then brings its node up; on the emulator the node reads the resolvers `10.0.2.3` and `10.0.2.4`, reaches `euc1-1.relay.n0.iroh.link`, and logs no `ndk_context` panic.

#### Scenario: An installed context gives the node the network's resolvers
- **WHEN** an Android application installs its context before its first bring-up
- **THEN** the node resolves names through the active network's DNS servers, and no JNI panic is logged

#### Scenario: A bring-up without the context still runs
- **WHEN** an Android application brings its node up without installing its context
- **THEN** the bring-up succeeds, and the node resolves names through public DNS servers

#### Scenario: A second install changes nothing
- **WHEN** an Android application calls `install` again, with the same context or another
- **THEN** the node keeps the context of the first call

### Requirement: Record payloads cross as bytes, unchanged and bounded
A record's payload and a mergeable-document's operation SHALL cross the facade as raw bytes on the way in and on the way out, with no encoding, escaping or transformation between what was written and what is read.

The facade SHALL bound a single payload or operation by a stated ceiling and SHALL refuse one above it before the runtime is called. A write buffers the whole payload across the binding boundary and a phone is killed for memory rather than asked to swap, so an unbounded payload is the one input that ends the process instead of returning an error. The HTTP host bounds its own for the same reason and a smaller one is appropriate here.

The bound is on what this host puts in, and SHALL NOT be applied to what a read hands back. A record another member wrote arrives in the replica whatever its size — a host over the same runtime bounds its own writes at a size a phone would not choose — and refusing to hand such a value over would make the record unreadable rather than making the device safer.

#### Scenario: What was written is what is read
- **WHEN** an arbitrary byte string is placed as a claim and read back
- **THEN** the bytes read equal the bytes written, of the same length, with no framing of the facade's own around them

#### Scenario: An empty payload is refused
- **WHEN** a record is placed with an empty payload
- **THEN** the facade reports malformed input, because the engine keeps no entry for one, and no record is placed

#### Scenario: A payload above the ceiling is refused, not attempted
- **WHEN** a record is placed with a payload larger than the stated ceiling
- **THEN** the facade refuses it before calling the runtime, and the node is still up afterwards

### Requirement: A read that answers nothing is not proof of absence
A read of a record SHALL be able to report that it has no value, and the facade SHALL state, where a caller reads about it, that this covers a record that has not arrived as well as one that does not exist.

Entries and payloads travel independently, so "stored" precedes "readable" for every value that crosses between nodes. A screen that rendered an absent value as a fact would announce that a member placed nothing at the exact moment the member's record was on its way.

#### Scenario: A record on its way reads as no value
- **WHEN** a record's entry has replicated in and its payload has not yet arrived
- **THEN** the read reports no value, indistinguishably from a record that was never placed, and the application keeps reading rather than concluding

### Requirement: A listing reports addresses and fetches no payload
Listing a pod's records SHALL report each record's address — the member it sits under, its kind and its id — and SHALL NOT fetch payloads.

#### Scenario: Listing a pod the identity is no member of is refused
- **WHEN** a listing names a pod the identity never joined
- **THEN** the facade reports the unknown-pod refusal rather than an empty listing

### Requirement: A ceremony payload crosses in the runtime's own encoding, unread and interoperable
A linking payload or a pod invite SHALL cross the facade in the encoding the runtime's own payload type serializes to, and the facade SHALL NOT name the payload's fields, inspect it, or wrap it in a format of its own. It SHALL also offer a textual form a screen can draw as a code and rebuild from a scan.

The encoding is a requirement rather than an implementation choice because a payload's whole purpose is to be consumed by another node, and the other node may be behind a different host over the same runtime. A payload that only this host can parse would make a phone and any other host unable to complete a ceremony together, and "whatever the runtime minted" would have become a second format with the same name.

The facade SHALL state that a payload carries a live one-time secret. Nothing in a payload grants durable access — no ticket, no identity proof — and until the secret is burnt or expires, whoever captures the payload can consume it in the intended recipient's place. Rendering a payload on a screen is therefore an exposure with a lifetime, and the minting call SHALL let the caller choose that lifetime.

#### Scenario: A payload minted here is consumed through another host
- **WHEN** a pod invite is minted through the facade, decoded and re-encoded by another host's rules over the same runtime, and consumed through the facade
- **THEN** the join succeeds without translation, and neither side had to name a field of it

#### Scenario: A code read for the wrong act is the runtime's refusal
- **WHEN** a linking payload is handed to the join and a pod invite to the linking call
- **THEN** each is reported as malformed input, and the consuming identity holds no pod afterwards

#### Scenario: A captured payload is consumable until it burns
- **WHEN** a pod invite is photographed from a screen and consumed by a party other than the intended one, before the secret is burnt or expired
- **THEN** the join succeeds for that party, which is why the surface states the exposure rather than implying a payload is safe to show

#### Scenario: A payload's lifetime is the application's choice
- **WHEN** a payload is minted with a lifetime given
- **THEN** the secret expires after it, and consuming the payload afterwards is refused

### Requirement: A ceremony call ends within a bounded time
An exported ceremony call SHALL either complete or fail within a bounded time, never remaining outstanding indefinitely, so a screen showing progress reaches an outcome. Consuming a linking payload SHALL take the caller's bound for the whole act — the dialogue spends from it first and the catch-up gets what remains — and SHALL report a distinct failure when the catch-up did not finish inside it, having rolled back what it imported. Joining a pod SHALL answer once both of the pod's stores caught up, and a catch-up that runs out of its bound SHALL be reported as that, the pod recorded and its catch-up continuing.

The runtime distinguishes an inviter that was never reached, a dialogue that ended in refusal, and a dialogue that reached the inviter and got no answer. The facade SHALL preserve that distinction, because the three call for different acts from the person: move closer or check the network, mint a fresh code, or try again.

#### Scenario: An unanswering inviter costs a bounded wait
- **WHEN** a payload is consumed against an inviter that accepts the dialogue and never answers
- **THEN** the call fails within the ceremony's own bound with the timeout failure, distinct from a refusal

#### Scenario: A link that could not catch up leaves nothing behind
- **WHEN** consuming a linking payload succeeds in the dialogue and the catch-up does not finish within the caller's bound
- **THEN** the call reports the catch-up failure, and the node hosts no part of that identity afterwards

### Requirement: A refused operation is reported as a refusal
The facade SHALL map failures to the platform's error type through one closed table, distinguishing at least: a ceremony the counterparty refused; an identity this node does not host; a pod the identity is no member of; a membership act the pod's membership refuses, with its reason; a record placed once that takes no operation; a record that reads on no entry here; a record read by the call meant for the other kind; an identity key that has not reached this device; an act of this kind already committed or in flight; a counterparty a ceremony never reached; a ceremony dialogue that ran out of its bound; a catch-up that ran out of its bound; a payload whose format version this runtime does not speak; a storage directory another running node already holds; input the host itself rejected before calling the runtime; a call with no node up, and a bring-up with one up; and an unrecognized failure. It SHALL NOT report a refused operation as success, and SHALL NOT expose the internal cause chain of an unrecognized failure, which the platform log retains instead.

The version refusal earns its own kind by being the one a person meets rather than an engineer: a code minted by an older build scans cleanly and cannot be consumed, and reporting that as an internal failure would tell someone their phone is broken when their counterparty needs an update.

The table SHALL name, for each kind, whether it comes from the runtime or from the host's own check before the runtime is called. The distinction is not one of mechanism but one of place: these checks sit above the service call, so they are the host's to write, to name, and to keep in step with the runtime's own refusals rather than assume.

Where the runtime cannot separate two of these outcomes, the table SHALL follow the runtime rather than promise a distinction that does not exist. A dialogue whose bound expires while the dial is still in flight is reported as the dialogue's own timeout, because that is what the runtime reports.

This table is the facade's own, and it names more kinds than `pdn-node-http`'s does. That host folds an unreachable counterparty and both ceremony timeouts into its unrecognized failure and says so deliberately — for a container test the distinction a denial rested on was a refusal against a defect. A person holding a phone needs three different actions from those three outcomes: move closer or check the network, mint a fresh code, try again. The divergence SHALL be stated where the facade is described, rather than left for a reader comparing the two hosts to discover.

Every paired denial rests on the table's distinctions ([access-control-tests](../../../../code-practices/access-control-tests.md)): a surface answering alike for "the runtime refused you" and "this host is broken" makes each pairing vacuous.

#### Scenario: A refusal is distinguishable from a defect
- **WHEN** a plain member attempts to remove another member, and separately the application meets an unrecognized internal failure
- **THEN** the first is reported as a refused membership act naming that the actor is not an owner, the second as an internal failure with a stable message, and the two are told apart without reading their text

#### Scenario: An unhosted identity is refused, not absent
- **WHEN** an exported call addresses an identity the runtime neither created nor linked
- **THEN** the facade reports the unknown-identity refusal, distinct from a record that has no value

#### Scenario: A ceremony's failures do not collapse into a defect
- **WHEN** a payload is consumed against a counterparty that cannot be reached, against one that refuses, and against one whose dialogue runs out of its bound
- **THEN** each failure carries a kind the runtime distinguishes, told apart without reading its text, and none of them is the unrecognized failure

#### Scenario: A host refusal is distinguishable from a runtime refusal
- **WHEN** the host rejects an empty record payload and, separately, the runtime refuses an operation appended to a claim
- **THEN** both are reported as refusals of their own kinds, and the table names which of the two came from the host

#### Scenario: An unmapped error does not become a refusal
- **WHEN** a runtime error outside the table reaches the facade
- **THEN** it is reported as the unrecognized failure and never as a refusal, so an unexpected defect cannot be read as an access decision

### Requirement: The reconcile cadence is chosen by the host
The host SHALL bring the runtime up with an explicitly configured reconcile interval rather than inheriting the default, and SHALL state the configured value in its own documentation.

The periodic pass drives every replica the node tracks outside a pod, so the interval is what bounds two waits a person feels: a write reaching another device of the same identity, and a linking catch-up, whose re-dial cadence is that pass. A pod's stores run a pass of their own.

The default is 10 seconds. A short interval costs radio wakeups and battery, so the choice belongs to a host that knows what it is running, and the value is written down so the resulting speed is read as this host's configuration and never as a property of the network.

#### Scenario: The interval is configured, not defaulted
- **WHEN** the node is brought up
- **THEN** the reconcile interval it runs at is the one the host configured, and that value appears in the host's own documentation

### Requirement: The facade authorizes nothing
The facade SHALL add no identity, no authentication and no authorization of its own: every operation is the runtime's, refused by the runtime on the runtime's terms. Reaching the facade is reaching the node, and the facade runs inside the application's process, so the application's own screen lock is the whole of the posture in front of it.

#### Scenario: No exported call is gated by the facade
- **WHEN** the exported surface is enumerated
- **THEN** no call carries a credential, a token, or a permission of the facade's own devising

### Requirement: Exported calls are asynchronous and own their execution
Exported calls SHALL be asynchronous across the binding boundary, and the facade SHALL own the asynchronous runtime the operations need. No exported call SHALL require its caller to hold a lock across it.

Every operation that crosses the network — a ceremony, a join waiting on its catch-up, a read of a replicated store — takes time no caller can be held for. Where a caller's continuation resumes is the caller's own affair and no requirement here claims it; what the facade owes is a call that returns to be awaited rather than one that blocks until the network answers.

#### Scenario: A ceremony does not hold its caller
- **WHEN** a ceremony call is outstanding
- **THEN** the caller is free to run and the result arrives when the ceremony ends, with no thread of the caller's blocked on it

### Requirement: The host repeats what the runtime says about its state, and adds nothing
A node keeps its replicas, its payloads and its own key in the directory named at bring-up ([durable storage](../../data-layer/durable-storage/spec.md)), and comes back on that directory as the same node hosting what it hosted ([restart recovery](../../pdn-node/restart-recovery/spec.md)). What a restart does not bring back is work in flight — a pod invite or a linking payload minted and not consumed, a ceremony interrupted. The facade SHALL state that where an embedder reads about it, SHALL NOT present the device's storage as anything but the only copy, and SHALL NOT offer an act whose meaning depends on work in flight outliving the process.

The facts belong to `data-layer` and `pdn-node` and are cited here rather than asserted, so that a change to the runtime's storage does not leave a mobile specification as the only place the old behaviour is written down.

#### Scenario: A restart comes back as the same node
- **WHEN** the application process ends and starts again on the directory it named before
- **THEN** it reports the node id it had before, hosts the identities it hosted, holds the pods it held with their records readable at once, and a pod invite minted and not consumed before the stop is refused

### Requirement: An identity carries no key material, and the host claims none
The runtime mints an identity as a placeholder value with no key material behind it ([core](../../pdn-node/core/spec.md)), so nothing binds an identity to a person or an organization. The facade SHALL NOT present an identity as authenticated, verified or proven, and SHALL NOT expose an operation that would imply it.

A membership gained through a pod's join is evidence that a device ran the join with the same one-time secret, and nothing more. What the person on the other side is called is what they said they were called.

#### Scenario: Nothing on the surface claims to prove who a peer is
- **WHEN** the exported surface and its types are read
- **THEN** no value is named a proof, a verification or a credential of an identity
