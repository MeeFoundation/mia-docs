## Context

`mobile-host-surface` gives the runtime a host a phone can run: a uniffi facade exposing the runtime's operations and nothing beyond them, including the own-grant read that `own-grant-read` adds, so a host is not forced to answer "what am I sharing" from memory. This change puts screens on that host and stages a demonstration for someone deciding whether the platform is worth building.

Everything the facade states about the state underneath it holds here without restatement: the node's directory holds the only copy of its replicas, its payloads and its key, and a node brought up on that directory again is the same node; an identity is a placeholder value with no key material; a peer is reached by publishing its addresses under its node id to n0's name servers, with n0's relay carrying a session that finds no direct path; and the reconcile cadence is a number the host configures. The application is arranged around those four as they stand, not around a later version of them.

## Goals / Non-Goals

**Goals**

- One set of screens over both platforms, honest about the node they show.
- A demonstration in which every act is the product's own act, each shown beside the refusal that gives it meaning.
- The absences stated in the narration, so a viewer does not carry away their opposites.

**Non-Goals**

- Anything in the facade or the runtime. If a screen needs a capability that is not exported, the answer is a change to `mobile-host-surface`, not a workaround here.
- Automated coverage of the demonstration. A phone in a hand is not a test fixture, and pretending otherwise would be exactly the substitution this repository's practices exist to prevent.
- A reusable application. This is one application for one purpose, and its screens are not a product's information architecture.

## Decisions

### D1. React Native for the screens, native only where the platform demands it

5 screens on 2 platforms, with native code confined to what cannot be anything else: the generated bindings, the camera, and the lifecycle. The alternative was 2 native screen sets over the same facade, which removes a layer at the price of writing every screen twice; at this screen count the layer is cheaper than the duplication, and the camera and the lifecycle are native either way.

The consequence to keep in view: the facade's outputs are Swift and Kotlin, packaged by `pdn-sdk` and consumed here as a release, so each platform has a thin module between the bindings and the shared screens. That module lives in this repository rather than in `pdn-sdk`, which packages artifacts and decides nothing about screens. It forwards calls and translates errors. It makes no decisions, and a decision appearing in it is a decision in the wrong place — with no test that would catch it, which is why the shells' specs say it is kept empty on purpose.

### D2. The screens are their own capability, not an appendix to the surface

An application over an honest surface can still be dishonest: it can cache a grant, swallow a refusal into a spinner, or draw an absent value as a fact. None of those is visible in the facade's tests, and none is platform-specific. They are therefore requirements shared by both platforms, with the platform shells left holding only what a platform decides — consent, lifecycle, and the build.

### D3. The person chooses the act before a code is read, and nothing above the facade parses a payload

A code can carry an invitation to connect or a device joining an identity, and the application does not tell them apart: it asks which act the person is performing and passes the value to that call. The alternatives were parsing the payload — which the surface deliberately keeps opaque, and which would need changing whenever the runtime's payload changes — or wrapping it in an envelope of the application's own, a second format to keep in step for nothing gained. Asking is one tap, and the person already knows which act they came for.

Reading a code for the wrong act therefore produces a refusal from the runtime rather than a correction in the application, and the screen shows that refusal.

### D4. A code on screen is an exposure with a lifetime, and the screen says so

The payload carries a live one-time secret: nothing in it grants durable access, which is exactly why it is safe to show to a camera and unsafe to leave on a table. The screen states that, shows the code as spent once consumed, and is dismissable at once. The runtime's default lifetime is 2 minutes and every minting call accepts an override, so how long a code stays up is a decision the screen makes rather than a capability to add.

### D5. The display is kept awake while a code is shown or a value awaited

A screen that dims mid-ceremony ends the ceremony from the person's side, and a demonstration interrupted by a lock screen is an interruption the audience attributes to the product. This is a screens requirement rather than a shell one, because both platforms need it for the same reason.

### D6. The node comes up by an explicit act on both platforms, and the 2 lifetimes are stated

On Android the node runs inside a foreground service with a visible notification, and it keeps answering peers while the person looks at something else. On iOS the node runs while the application is in view, and a termination stops it — what it held comes back on its directory, what does not come back is work in flight. The asymmetry is real and cannot be designed away: only one of the two platforms offers a way to keep a process alive for this.

Bring-up is an explicit act on both, rather than a side effect of the application becoming active, so that the surface's explicit bring-up stays explicit and so the demonstration's own script is the same sequence on either device.

The consequence for the staging: locking the phone is not a neutral gesture. Where an act calls for a device to leave, the gesture is airplane mode with the application still in view, and the narration says which platform the phone runs.

### D7. The staging is Alice on 2 devices, Bob, and an outsider — one phone and 3 processes

4 roles cannot be collapsed. Alice's laptop node is where her identity is created and her first entries are written. Her phone joins that identity and is needed twice over: as the device that comes up caught up, and as a device of an identity whose other device goes away. Bob's node holds an identity of his own and is the party a grant names. A fourth is needed because the outsider must hold no connection to Alice, and the other 3 all do.

The fourth cannot be a second identity on Bob's node. The data service is keyed by the issuer whose namespace is read, not by the identity a screen believes it is acting under, so once that node has bound Alice's replica it answers the read whichever identity is selected. Hosting an outsider beside a grantee would stage a denial that cannot fail.

So: one phone running the application, and 3 `pdn-node-http` processes on the presenter's machine. All 3 are real nodes with real addresses, reached by the phone over the runtime's own protocols.

The order of the acts follows from the cast rather than from convenience. The phone joins an identity that already holds entries, so the catch-up is visible as arrival rather than as a screen that was always full. Bob connects afterwards, so the connection record is seen reaching Alice's laptop with no act performed there. `sibling_serving.rs` holds the neighbouring properties for that order — a device linked before the establishment receives the pair and the grant record and serves by them — and the connection list reads the same replicated directory; the arrival of the connection record itself is inferred from that rather than asserted by a test, which is why the run-through checks this act first.

Two things about the processes are stated in the narration rather than hidden. A machine does not read a code off a screen, so its payload is carried by hand. And the HTTP host spawns the runtime with the default cadence and offers no way to change it, so the acts running through it are the slow ones; making that host's interval configurable is a change of its own if rehearsal shows the slowness is intolerable.

### D7a. One phone means both directions of granting

With one screen in the staging, a single granting direction would show either the issuer's acts or the grantee's and hide the other behind a terminal. So both are shown over the one connection: Alice grants Bob, which puts choosing a claim, publishing, withdrawing and granting again on her phone; Bob grants Alice, which puts a claim arriving, a writable claim accepting an edit, a read-only claim refusing one, and a withdrawn claim reading as no longer shared on the same phone.

The alternative was to narrate a terminal as though it were a grantee's screen, which is the substitution the demonstration's own form rules out. What a counterparty node does is read from a terminal as the counterparty's behaviour, and never as what a person would see.

### D8. The demonstration's logistics live in a run-through document, not in the spec tree

The product-shaped properties are requirements: identities kept apart, a code that burns, claims absent rather than hidden, a read-only claim refusing a write, a second device standing in, a withdrawal closing access and a re-grant reopening it, an outsider obtaining nothing. How the room is arranged is not. A requirement reading "rehearsed twice, with a camera over the table as the fallback" would archive into the permanent component tree, be stale the following week, and be indistinguishable there from product behaviour.

### D9. The withdrawal act is narrated as closing delivery, not as deletion

A field vanishing from a phone reads as deletion, and the platform does not promise that: a revoked capability blocks further delivery, and nothing compels a node that already received data to forget it ([invariants](../../specs/components/mee-pdn/invariants.md), Invariant 2). This is the one act where the demonstration would otherwise oversell, so it is the fifth thing the narration states.

The screen has a matching obligation in the other direction. Withdrawal unbinds the namespace, so the grantee's node stops knowing that issuer and every later read is refused rather than answered empty — and a screen that showed a fault banner at the moment a person exercised their own control would misdescribe the product exactly where it works best.

### D10. The only copy is stated, not papered over

No act depends on a restart, and the narration states that this device's storage holds the only copy of what the screens show. The alternative — a demonstration that avoids the subject and lets a viewer assume a service keeping a copy behind the phone — sells something that does not exist, and the assumption is what the audience would carry away.

## Risks / Trade-offs

**The phone on the presenter's screen.** Mirroring the phone onto the machine that also shows the terminal is the fragile part of the day, rehearsed with the same device and cable, with a camera over the table as the fallback.

**A network in a room may isolate its clients.** Many guest networks forbid client-to-client traffic and report nothing worth reading. A personal hotspot or a dedicated router is part of the staging, and traffic between two clients is confirmed to pass before the day.

**The two shells give the same screens different node lifetimes.** Android keeps a foreground service and answers peers while the person looks elsewhere; iOS runs while the application is in view. The asymmetry cannot be designed away — only one platform offers a way to hold a process for this — so the run-through names the platform the phone runs and the script's "device leaves" gesture is airplane mode rather than a lock.

**The iOS lifetime is a live hazard during the demonstration.** A notification pulled down, a lock screen, fiddling with the mirroring — any of them can end the process, and a node that stopped mid-act answers nothing its peers are waiting for. The mitigation is a rehearsal that includes the mirroring, and a script whose "device leaves" gesture is airplane mode rather than a lock.

**Local-network consent on iOS may not be observable.** The declaration is required, but the platform raises the prompt from the traffic rather than from the declaration, and a refusal presents as silence. What the shell can actually detect is settled by `mobile-host-surface`'s spike; the requirement is phrased around detecting it, and if it cannot be detected the shell's answer is to tell the person what to check.

**Nothing here is covered by a test.** The verification is a run-through performed twice, and that is weaker than a test suite. It is stated in the proposal's Impact rather than papered over with in-process tests that would prove the facade again and the demonstration not at all.

## Migration Plan

Nothing to migrate. The application is a new repository, and the facade is consumed unchanged, as a named release of `pdn-sdk`.

## Open Questions

- Whether the acts running through the laptop node are tolerable at the runtime's default cadence, or whether making that host's interval configurable becomes its own change. Rehearsal answers it.
- Whether a refused local-network consent is observable on iOS, which `mobile-host-surface`'s spike records and which decides how that shell's requirement is met.
