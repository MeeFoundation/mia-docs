## Context

`mobile-host-surface` gives the runtime a host a phone can run: a uniffi facade exposing the runtime's operations and nothing beyond them, including the own-grant read that `own-grant-read` adds, so a host is not forced to answer "what am I sharing" from memory. This change puts screens on that host and stages a demonstration for someone deciding whether the platform is worth building.

Everything the facade states about the state underneath it holds here without restatement: replicas and payloads live only as long as the process, an identity is a placeholder value with no key material, a peer is reached only in one local network because no relay or discovery is configured, and the reconcile cadence is a number the host configures. The application is arranged around those four as they stand, not around a later version of them.

## Goals / Non-Goals

**Goals**

- One set of screens over both platforms, honest about the node they show.
- A demonstration in which every act is the product's own act, each shown beside the refusal that gives it meaning.
- The absences stated in the narration, so a viewer does not carry away their opposites.

**Non-Goals**

- Anything in the facade or the runtime. If a screen needs a capability that is not exported, the answer is a change to `mobile-host-surface`, not a workaround here.
- Automated coverage of the demonstration. 2 phones are not a test fixture, and pretending otherwise would be exactly the substitution this repository's practices exist to prevent.
- A reusable application. This is one application for one purpose, and its screens are not a product's information architecture.

## Decisions

### D1. React Native for the screens, native only where the platform demands it

5 screens on 2 platforms, with native code confined to what cannot be anything else: the generated bindings, the camera, and the lifecycle. The alternative was 2 native screen sets over the same facade, which removes a layer at the price of writing every screen twice; at this screen count the layer is cheaper than the duplication, and the camera and the lifecycle are native either way.

The consequence to keep in view: the facade's outputs are Swift and Kotlin, so each platform has a thin module between the bindings and the shared screens. That module forwards calls and translates errors. It makes no decisions, and a decision appearing in it is a decision in the wrong place — with no test that would catch it, which is why the shells' specs say it is kept empty on purpose.

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

On Android the node runs inside a foreground service with a visible notification, and it survives the person looking at something else. On iOS the node lives while the application is in view, and a termination loses every identity it hosted. The asymmetry is real and cannot be designed away: state is in memory, and only one of the two platforms offers a way to keep a process alive for this.

Bring-up is an explicit act on both, rather than a side effect of the application becoming active, so that the surface's explicit bring-up stays explicit and so the demonstration's own script is the same sequence on either device.

The consequence for the staging: locking a phone is not a neutral gesture. Where an act calls for a device to leave, the gesture is airplane mode with the application still in view, and the narration says which phone is which platform.

### D7. The staging needs 4 nodes, and 2 of them are processes on the presenter's machine

4 roles cannot be collapsed. The granting identity's first device and the grantee are 2. A third is needed because 2 acts require a node that stays up while another goes away — the granting identity's second device joining, and that device serving the grantee once the first is gone. A fourth is needed because the outsider must hold no connection to the granting identity, and the other 3 all do.

The fourth cannot be a second identity on the grantee's phone. The data service is keyed by the issuer whose namespace is read, not by the identity a screen believes it is acting under, so once that phone has bound the granting identity's replica it answers the read whichever identity is selected. Hosting an outsider beside a grantee would stage a denial that cannot fail.

So: 2 phones running the application, and 2 `pdn-node-http` processes on the presenter's machine in the same local network. Both processes are real nodes with real addresses, reached by the phones over the runtime's own protocols.

Two things about them are stated in the narration rather than hidden. A machine does not read a code off a screen, so its payload is carried by hand. And the HTTP host spawns the runtime with the default cadence and offers no way to change it, so the acts running through it are the slow ones; making that host's interval configurable is a change of its own if rehearsal shows the slowness is intolerable.

### D8. The demonstration's logistics live in a run-through document, not in the spec tree

The product-shaped properties are requirements: identities kept apart, a code that burns, claims absent rather than hidden, a read-only claim refusing a write, a second device standing in, a withdrawal closing access and a re-grant reopening it, an outsider obtaining nothing. How the room is arranged is not. A requirement reading "rehearsed twice, with a camera over the table as the fallback" would archive into the permanent component tree, be stale the following week, and be indistinguishable there from product behaviour.

### D9. The withdrawal act is narrated as closing delivery, not as deletion

A field vanishing from a phone reads as deletion, and the platform does not promise that: a revoked capability blocks further delivery, and nothing compels a node that already received data to forget it ([invariants](../../specs/components/mee-pdn/invariants.md), Invariant 2). This is the one act where the demonstration would otherwise oversell, so it is the fifth thing the narration states.

The screen has a matching obligation in the other direction. Withdrawal unbinds the namespace, so the grantee's node stops knowing that issuer and every later read is refused rather than answered empty — and a screen that showed a fault banner at the moment a person exercised their own control would misdescribe the product exactly where it works best.

### D10. Volatility is designed around, not papered over

No act depends on state outliving a process, and the narration states that state is volatile. The alternative — a demonstration that avoids the subject and lets a viewer assume a disk — sells something that does not exist, and the assumption is what the audience would carry away.

## Risks / Trade-offs

**Two phones on one screen.** Mirroring two devices onto one machine is the fragile part of the day, rehearsed with the same devices and cables, with a camera over the table as the fallback.

**A network in a room may isolate its clients.** Many guest networks forbid client-to-client traffic and report nothing worth reading. A personal hotspot or a dedicated router is part of the staging, and traffic between two clients is confirmed to pass before the day.

**The two shells give the same screens different node lifetimes.** Android keeps a foreground service and survives the person looking elsewhere; iOS lives while the application is in view. The asymmetry cannot be designed away — state is in memory and only one platform offers a way to hold a process for this — so the run-through names each phone's platform and the script's "device leaves" gesture is airplane mode rather than a lock.

**The iOS lifetime is a live hazard during the demonstration.** A notification pulled down, a lock screen, fiddling with the mirroring — any of them can end the process and take the identities with it. The mitigation is a rehearsal that includes the mirroring, and a script whose "device leaves" gesture is airplane mode rather than a lock.

**Local-network consent on iOS may not be observable.** The declaration is required, but the platform raises the prompt from the traffic rather than from the declaration, and a refusal presents as silence. What the shell can actually detect is settled by `mobile-host-surface`'s spike; the requirement is phrased around detecting it, and if it cannot be detected the shell's answer is to tell the person what to check.

**Nothing here is covered by a test.** The verification is a run-through performed twice, and that is weaker than a test suite. It is stated in the proposal's Impact rather than papered over with in-process tests that would prove the facade again and the demonstration not at all.

## Migration Plan

Nothing to migrate. The application is a new repository, and the facade is consumed unchanged.

## Open Questions

- Whether the acts running through the laptop node are tolerable at the runtime's default cadence, or whether making that host's interval configurable becomes its own change. Rehearsal answers it.
- Whether a refused local-network consent is observable on iOS, which `mobile-host-surface`'s spike records and which decides how that shell's requirement is met.
