# mobile-common: host surface

The mobile host is the second host over the runtime and the first one on the product side of the boundary [http-host](../pdn-node/http-host.md) draws: a product host embeds the runtime core in-process and reaches other nodes only over the runtime's own protocols, while the runtime carries no host dependency of its own. What this surface exposes, what it refuses to expose, how it reports a refusal, and what it says about the state underneath it are requirements, because an application built on it can only be as honest as the surface it stands on.

Two words are used throughout with the meanings the runtime gives them, and one of the two needs care. An *identity* is what the runtime hosts: a data namespace, a directory of its own devices, and the connections it has established.

A *granted claim* is what a grant names, one at a time, each with or without the right to write. It is not an entry path: the runtime derives a claim identity from the issuer and the path, and it is that derived identity the grant carries and a grant read reports. The derivation is one-way, so nothing recovers a path from a claim identity — a caller that wants to show a path names the paths it knows or has listed and derives their identities to compare. Neither sense matches the glossary's [claim](../../architecture/language/claim.md), which is an assertion about a subject with proof of its issuance; the word is used here in the data layer's sense because that is the sense the code exports, and the glossary is where the two senses have to be reconciled.

## ADDED Requirements

### Requirement: The facade covers the runtime's operations and adds none
The facade SHALL make the embedded runtime's service operations reachable from the application: creating an identity and listing the hosted ones; minting a device-linking payload and consuming one; minting an invite payload and consuming one; listing an identity's connections; publishing a grant, reading the grants a peer published, reading the grants the identity published itself, and withdrawing a published grant; writing, reading and listing entries of an issuer's data namespace; and reporting the node id.

Each exported call SHALL delegate to one service call and SHALL add no orchestration of its own. It retries no ceremony, caches no grant, remembers no result, and holds no rule about what a peer may read. An application and a facade that each kept a view of the same thing would drift, and the drift would show as a screen contradicting the node it sits on.

#### Scenario: Every act of the demonstration is reachable
- **WHEN** an application drives two nodes through the facade alone — creating an identity on each, minting an invite on one, establishing from the other, publishing a grant, writing an entry, and reading it back through the grantee
- **THEN** every step is an exported call, and no step requires reaching into the runtime around the facade

#### Scenario: A ceremony's outcome is the runtime's
- **WHEN** an exported ceremony call fails
- **THEN** the facade reports the failure and retries nothing, and a retry is the application making a fresh call with a freshly minted payload

### Requirement: The exported surface is exactly this set
The facade SHALL export the operations named above and SHALL NOT export the runtime's remaining public surface. In particular it SHALL NOT export the out-of-band namespace share and import — neither the whole-store nor the scoped form — and SHALL NOT export anything the runtime gates behind its test-only feature. The facade SHALL build with that feature disabled, so a forced write or a contact-set observation is not merely unexported but absent from the binary.

Beside those operations the facade SHALL export exactly 2 values that reach no service call: the claim derivation, which a caller needs to join a grant read against paths it knows, and the ceiling on one entry payload, so a caller can refuse an oversized write before making one. Both are stated here rather than left to be discovered, because an export the specification does not admit is indistinguishable from one somebody added on the way past.

#### Scenario: The withheld operations are absent, not merely undocumented
- **WHEN** the facade's exported surface is enumerated
- **THEN** it names no share, no import, no forced write, and no observation of a replica's contact set

#### Scenario: The test-only feature is off in what ships
- **WHEN** the artifacts a device installs are built
- **THEN** the facade is compiled without the runtime's test-only feature enabled

### Requirement: No namespace ticket crosses the facade
Reading a grant SHALL hand back the capability alone — the issuer, the claims, and for each claim whether it may be written — and SHALL NOT expose the replica ticket the runtime's read of a peer's grant carries beside it. The read of the identity's own published grants carries no ticket to drop: the caller issues the namespace the record addresses, so a ticket to it answers nothing. No exported call SHALL accept a ticket in any form.

The sanctioned way a granted namespace arrives is that the runtime binds what the grant names, by itself, as the grant record replicates in. An application able to import a ticket would keep showing data after that binding broke, and the substitution would sit in the arrange step, where nothing afterwards reveals it: the value still appears, obtained the wrong way ([product-path-arrangement](../../code-practices/product-path-arrangement.md)).

#### Scenario: A granted namespace arrives with no ticket above the facade
- **WHEN** a connected peer publishes a grant toward the hosted identity and the application then reads the granted claim
- **THEN** the claim eventually reads back, and no exported call was available that would have handed over or accepted a namespace ticket

#### Scenario: A grant read carries no ticket
- **WHEN** the application reads what a peer granted it
- **THEN** the value it receives names the issuer, the claims and their write rights, and carries nothing that would address or open the replica

### Requirement: The facade offers no convenience the product lacks
The facade SHALL NOT offer any call whose purpose is to force a reconciliation, reset state, drop a replica, or reach a store other than through a service operation. Repeating the read SHALL be the only wait mechanism available for a value written elsewhere.

The reason is what the demonstration proves. A screen given a synchronize control would keep showing convergence after convergence broke; a screen that reset state between acts would hide an act that only worked from a fresh node. Both substitutions live in the arrange and act steps, and both leave the assertions looking right.

Reading or listing a namespace received under a grant does nudge that namespace's filtered reconciliation, without blocking: the answer comes from the local replica at once and the nudge pulls fresh entries toward the next read. That is why repeating the read is a wait and not a poll of a static value, and it is the runtime's behaviour rather than a means the facade adds.

#### Scenario: Repeating the read is the only wait
- **WHEN** the application waits for a value written on another node
- **THEN** repeating the read is the only mechanism available for the wait, and no exported call exists whose purpose is to force a reconciliation

#### Scenario: No act resets the node
- **WHEN** the exported surface is enumerated
- **THEN** it offers no call that clears an identity, forgets a namespace, or returns the node to a fresh state

### Requirement: A party the issuer never connected to obtains nothing through the facade
Every positive access the facade offers SHALL be specified beside the tightest denial the facade can express: a handle whose identity holds no connection to the granting identity and no grant from it obtains nothing of that identity's data, neither the granted claim nor any other, and is refused as addressing an issuer it holds nothing of.

The second read negative [access-control-tests](../../code-practices/access-control-tests.md) names — a party holding the replica's ticket but no capability — cannot be staged through this surface at all, because no ticket crosses it. That is the surface working as specified, not an omission, and the denial stays where it can be staged: the runtime's own scenarios, which hold it against a hand-made ticket. This requirement says so rather than leaving the gap to be read as an oversight.

#### Scenario: An outsider is refused beside the grantee who reads
- **WHEN** a grant is published toward one handle's identity and read by it, and a third handle whose identity is connected to neither side attempts the same read and listing
- **THEN** the grantee reads the granted claim and the third handle obtains nothing, refused as addressing an issuer it holds nothing of

### Requirement: One handle owns one node
One facade handle SHALL own exactly one runtime, brought up by an explicit call and stopped by an explicit call that is safe to repeat. A handle SHALL NOT offer a set of nodes, and SHALL refuse a second bring-up of its own while its node is up rather than silently replacing it. The constraint is on the handle rather than on the operating-system process, so a test binary holding two handles against two runtimes remains possible while an application holding one cannot grow a node set behind it.

A host that could hold several nodes invites a staging in which several devices are several runtimes inside one phone, and that staging cannot show the act it would exist for: a device that goes away takes every runtime co-located with it, so the sibling that should keep serving dies with the device that was meant to leave.

#### Scenario: Bring-up and stop are explicit
- **WHEN** the application brings the node up and later stops it, calling stop a second time
- **THEN** the first stop closes the endpoint and the protocols, and the second is a no-op rather than a failure

#### Scenario: A second bring-up is refused
- **WHEN** a bring-up is requested while a node is already up
- **THEN** the facade refuses it and the running node is untouched

### Requirement: Entry payloads cross as bytes, unchanged and bounded
An entry's payload SHALL cross the facade as raw bytes on the way in and on the way out, with no encoding, escaping or transformation between what was written and what is read. An entry path SHALL cross as the runtime's own path form, and a path the runtime rejects SHALL be reported as malformed input rather than corrected.

The facade SHALL bound a single entry payload by a stated ceiling and SHALL refuse one above it before the runtime is called. The runtime holds every replica in memory and a phone is killed for memory rather than asked to swap, so an unbounded payload is the one input that ends the process instead of returning an error. The HTTP host bounds its own for the same reason and a smaller one is appropriate here.

The bound is on what this host puts in, and SHALL NOT be applied to what a read hands back. An entry another node wrote arrives in the replica whatever its size — a host over the same runtime bounds its own writes at a size a phone would not choose — and refusing to hand such a value over would make a claim the grant permits unreadable rather than making the device safer. What a caller has instead is the length a listing reports before any payload is fetched, which is why a listing reports it.

#### Scenario: What was written is what is read
- **WHEN** an arbitrary byte string is written at a claim and read back
- **THEN** the bytes read equal the bytes written, of the same length, with no framing of the facade's own around them

#### Scenario: An empty payload is refused
- **WHEN** a write is attempted with an empty payload
- **THEN** the facade reports malformed input, because the engine keeps no entry for one, and the claim's previous value is unchanged

#### Scenario: A payload above the ceiling is refused, not attempted
- **WHEN** a write is attempted with a payload larger than the stated ceiling
- **THEN** the facade refuses it before calling the runtime, and the node is still up afterwards

### Requirement: A read that answers nothing is not proof of absence
A read of a claim SHALL be able to report that it has no value, and the facade SHALL state, where a caller reads about it, that this covers two situations the runtime does not distinguish: no entry exists at that claim, and an entry's record has arrived while its payload has not yet been fetched.

Records and payloads travel independently, so "stored" precedes "readable" for every value that crosses between nodes. A screen that rendered an absent value as a fact would announce that a peer shared nothing at the exact moment the peer's value was on its way.

#### Scenario: A value on its way reads as no value
- **WHEN** a granted claim's record has replicated in and its payload has not yet arrived
- **THEN** the read reports no value, indistinguishably from a claim that was never written, and the application keeps reading rather than concluding

### Requirement: A listing reports metadata and matches whole path components
Listing an issuer's entries SHALL report each entry's issuer, path and payload length, and SHALL NOT fetch payloads. An optional path prefix SHALL restrict the listing, matching whole path components rather than characters.

#### Scenario: A prefix matches components, not characters
- **WHEN** entries exist at `contact/email` and at `contacts/email`, and a listing is taken with the prefix `contact`
- **THEN** the listing reports the first and not the second

#### Scenario: Listing an issuer this node holds nothing of is refused
- **WHEN** a listing names an issuer whose data store this node does not hold
- **THEN** the facade reports the unknown-issuer refusal rather than an empty listing

### Requirement: A grant names claims of the granting identity's own data
Publishing a grant SHALL name the issuer whose data is granted, and the claims, each with or without the right to write. The facade SHALL pass a grant naming an issuer other than the granting identity to the runtime and report its refusal: an identity grants its own data, and delegating another's is not supported.

One grant record exists per granted issuer toward a peer, so publishing again SHALL replace the previous record, and withdrawing SHALL be one act naming the peer and the issuer.

#### Scenario: Republishing replaces rather than accumulates
- **WHEN** a grant toward a peer is published and then published again with a different claim set
- **THEN** the peer reads one grant, carrying the second claim set, and the first claim set is no longer among what it may read

#### Scenario: Granting another identity's data is refused
- **WHEN** a grant publication names an issuer that is not the granting identity
- **THEN** the facade reports the unsupported-delegation refusal and no record is written

### Requirement: Both grant reads are passed through as the observations they are
The runtime's grant reads report what is readable at the moment of the call and never wait ([core](../pdn-node/core.md)). The facade SHALL preserve that: it SHALL NOT wait inside either read for a grant to arrive, and SHALL NOT report a grant record whose payload has not been fetched as anything other than no grant.

A caller waiting for a grant therefore repeats the read, as it does for a claim. A facade that waited inside the call would turn a peer who granted nothing into a call that never returns.

#### Scenario: A grant that has not arrived reads as no grant
- **WHEN** a peer has published a grant whose record has not replicated in
- **THEN** the read reports no grant and returns promptly, and repeating it later reports the grant

### Requirement: A ceremony payload crosses in the runtime's own encoding, unread and interoperable
An invite or linking payload SHALL cross the facade in the encoding the runtime's own payload type serializes to, and the facade SHALL NOT name the payload's fields, inspect it, or wrap it in a format of its own. It SHALL also offer a textual form a screen can draw as a code and rebuild from a scan.

The encoding is a requirement rather than an implementation choice because a payload's whole purpose is to be consumed by another node, and the other node may be behind a different host over the same runtime. A payload that only this host can parse would make a phone and any other host unable to complete a ceremony together, and "whatever the runtime minted" would have become a second format with the same name.

The facade SHALL state that a payload carries a live one-time secret. Nothing in a payload grants durable access — no ticket, no identity proof — and until the secret is burnt or expires, whoever captures the payload can consume the invitation in the intended recipient's place. Rendering a payload on a screen is therefore an exposure with a lifetime, and the minting call SHALL let the caller choose that lifetime.

#### Scenario: A payload minted here is consumed through another host
- **WHEN** a linking payload is minted through the facade and handed to another host over the same runtime, and a payload minted by that host is handed to the facade
- **THEN** each consumes the other's without translation, and neither had to name a field of it

#### Scenario: A payload survives a code and a camera
- **WHEN** a payload is rendered as a code and read back from a scan of it
- **THEN** the value recovered is the value minted, byte for byte

#### Scenario: A captured payload is consumable until it burns
- **WHEN** an invite payload is photographed from a screen and consumed by a party other than the intended one, before the secret is burnt or expired
- **THEN** the establishment succeeds for that party, which is why the surface states the exposure rather than implying a payload is safe to show

#### Scenario: A payload's lifetime is the application's choice
- **WHEN** a payload is minted with a lifetime given
- **THEN** the secret expires after it, and consuming the payload afterwards is refused

### Requirement: A ceremony call ends within a bounded time
An exported ceremony call SHALL either complete or fail within a bounded time, never remaining outstanding indefinitely, so a screen showing progress reaches an outcome. Consuming a linking payload SHALL take the caller's bound for the whole act — the dialogue spends from it first and the catch-up gets what remains — and SHALL report a distinct failure when the catch-up did not finish inside it, having rolled back what it imported.

The runtime distinguishes an inviter that was never reached, a dialogue that ended in refusal, and a dialogue that reached the inviter and got no answer. The facade SHALL preserve that distinction, because the three call for different acts from the person: move closer or check the network, mint a fresh code, or try again.

#### Scenario: An unanswering inviter costs a bounded wait
- **WHEN** a payload is consumed against an inviter that accepts the dialogue and never answers
- **THEN** the call fails within the ceremony's own bound with the timeout failure, distinct from a refusal

#### Scenario: A link that could not catch up leaves nothing behind
- **WHEN** consuming a linking payload succeeds in the dialogue and the catch-up does not finish within the caller's bound
- **THEN** the call reports the catch-up failure, and the node hosts no part of that identity afterwards

### Requirement: A refused operation is reported as a refusal
The facade SHALL map failures to the platform's error type through one closed table, distinguishing at least: a write the local grant record does not permit; a grant naming an issuer the granting identity may not delegate; a ceremony the counterparty refused; an identity or issuer this node does not host; a peer this identity has no connection to; an act of this kind already committed or in flight; a counterparty a ceremony never reached; a ceremony dialogue that ran out of its bound; a catch-up that ran out of its bound; a payload whose format version this runtime does not speak; input the host itself rejected before calling the runtime; and an unrecognized failure. It SHALL NOT report a refused operation as success, and SHALL NOT expose the internal cause chain of an unrecognized failure, which the platform log retains instead.

The version refusal earns its own kind by being the one a person meets rather than an engineer: a code minted by an older build scans cleanly and cannot be consumed, and reporting that as an internal failure would tell someone their phone is broken when their counterparty needs an update.

The table SHALL name, for each kind, whether it comes from the runtime or from the host's own check before the runtime is called. The distinction is not one of mechanism — a malformed path is a typed error of the same shared validation both hosts call — but one of place: these checks sit above the service call, so they are the host's to write, to name, and to keep in step with the runtime's own refusals rather than assume.

Where the runtime cannot separate two of these outcomes, the table SHALL follow the runtime rather than promise a distinction that does not exist. A dialogue whose bound expires while the dial is still in flight is reported as the dialogue's own timeout, because that is what the runtime reports.

This table is the facade's own, and it names more kinds than `pdn-node-http`'s does. That host folds an unreachable counterparty and both ceremony timeouts into its unrecognized failure and says so deliberately — for a container test the distinction a denial rested on was a refusal against a defect. A person holding a phone needs three different actions from those three outcomes: move closer or check the network, mint a fresh code, try again. The divergence SHALL be stated where the facade is described, rather than left for a reader comparing the two hosts to discover.

Every paired denial rests on the table's distinctions ([access-control-tests](../../code-practices/access-control-tests.md)): a surface answering alike for "the runtime refused you" and "this host is broken" makes each pairing vacuous.

#### Scenario: A refusal is distinguishable from a defect
- **WHEN** the application writes a claim the local grant record covers read-only, and separately meets an unrecognized internal failure
- **THEN** the first is reported as a refusal naming the ungranted write, the second as an internal failure with a stable message, and the two are told apart without reading their text

#### Scenario: An unhosted identity is refused, not absent
- **WHEN** an exported call addresses an identity the runtime neither created nor linked
- **THEN** the facade reports the unknown-identity refusal, distinct from a claim that has no value

#### Scenario: A grant toward an unconnected peer is refused
- **WHEN** a grant publication names a peer this identity has no connection to
- **THEN** the facade reports the not-connected refusal, distinct from malformed input

#### Scenario: A ceremony's failures do not collapse into a defect
- **WHEN** a payload is consumed against a counterparty that cannot be reached, against one that refuses, and against one whose dialogue runs out of its bound
- **THEN** each failure carries a kind the runtime distinguishes, told apart without reading its text, and none of them is the unrecognized failure

#### Scenario: A host refusal is distinguishable from a runtime refusal
- **WHEN** the host rejects an empty entry payload and, separately, the runtime refuses an ungranted write
- **THEN** both are reported as refusals of their own kinds, and the table names which of the two came from the host

#### Scenario: An unmapped error does not become a refusal
- **WHEN** a runtime error outside the table reaches the facade
- **THEN** it is reported as the unrecognized failure and never as a refusal, so an unexpected defect cannot be read as an access decision

### Requirement: An ungranted write is reported as its own refusal
The runtime refuses a write at a claim the local grant record covers read-only, at the call and without touching the replica ([core](../pdn-node/core.md)). The facade SHALL report that refusal as a kind of its own, distinct from every other refusal and from a write the node accepted.

The facade SHALL also state what an accepted write does and does not mean: a write into a granted namespace was admitted locally against the grant record this node has read, and the issuer's own gate decides afterwards. A claim the issuer's record does not cover is refused there and the provisional entry is retracted here, and no answer on this surface carries that verdict.

#### Scenario: The read-only claim refuses and the value stands
- **WHEN** a grantee writes at a claim its grant covers read-only
- **THEN** the call is refused, and reading that claim afterwards yields the value that was there before

### Requirement: The reconcile cadence is chosen by the host
The host SHALL bring the runtime up with an explicitly configured reconcile interval rather than inheriting the default, and SHALL state the configured value in its own documentation.

The periodic pass drives every replica the node tracks, whichever synchronization strategy it follows, so the interval is what bounds three waits a person feels: a published grant record reaching the peer's copy of the connection's metadata pair, a write reaching another device of the same identity, and a linking catch-up, whose re-dial cadence is that pass. It is not what bounds the grantee's read of a granted claim — that read nudges its own filtered reconciliation, so repeating it converges largely independently of the interval.

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

Every operation that crosses the network — a ceremony, a read that waits on a payload, a listing of a replicated namespace — takes time no caller can be held for. Where a caller's continuation resumes is the caller's own affair and no requirement here claims it; what the facade owes is a call that returns to be awaited rather than one that blocks until the network answers.

#### Scenario: A ceremony does not hold its caller
- **WHEN** a ceremony call is outstanding
- **THEN** the caller is free to run and the result arrives when the ceremony ends, with no thread of the caller's blocked on it

### Requirement: The host repeats what the runtime says about its state, and adds nothing
The runtime holds replicas, payloads, hosted identities, device records, connections and its own key in memory ([node-assembly](../data-layer/node-assembly.md)), so ending the process loses every one of them. The facade SHALL state that where an embedder reads about it, SHALL NOT present any state as persisted, and SHALL NOT offer an act whose meaning depends on state outliving the process.

The fact belongs to `data-layer` and is cited here rather than asserted, so that a change to the runtime's storage does not leave a mobile specification as the only place the old behaviour is written down.

#### Scenario: A restart is a new node
- **WHEN** the application process ends and starts again
- **THEN** it hosts no identity, holds no connection, and its node id differs from the one it had before

### Requirement: An identity carries no key material, and the host claims none
The runtime mints an identity as a placeholder value with no key material behind it ([core](../pdn-node/core.md)), so nothing binds an identity to a person or an organization. The facade SHALL NOT present an identity as authenticated, verified or proven, and SHALL NOT expose an operation that would imply it.

A connection established through the pairing ceremony is evidence that two devices ran the ceremony with the same one-time secret, and nothing more. What the person on the other side is called is what they said they were called.

#### Scenario: Nothing on the surface claims to prove who a peer is
- **WHEN** the exported surface and its types are read
- **THEN** no value is named a proof, a verification or a credential of an identity
