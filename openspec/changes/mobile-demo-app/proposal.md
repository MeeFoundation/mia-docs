# Proposal: mobile-demo-app

## Why

`mobile-host-surface` gives the runtime a host a phone can run. This change puts screens on it, so that what the platform does can be watched by someone deciding whether it is worth building — two people in a room, one sharing exactly one field, the other unable to tell what else exists.

The audience fixes the form. Nothing is shown that a person cannot see happening, so no output read aloud from a terminal stands in for a screen. And nothing is claimed that the code does not do, because a demonstration that oversells is discovered later by the same audience. What the platform genuinely lacks — durable state, key-backed identity — is stated rather than avoided.

## What Changes

- **An application repository, `pdn-app`, nested beside `mia-docs` and `pdn-store`.** React Native screens shared by both platforms over a thin native module per platform. Native code appears only where the platform demands it: the generated bindings, the camera, and the lifecycle.
- **5 screens, and no sixth.** The identities this node hosts; the acting identity's own entries; its connections; one connection, showing what this peer granted and what was granted to it; and a code reader. A screen with no act behind it on the host surface has nothing to show.
- **The screens are required to be honest about the node, which the surface cannot enforce from below.** An application over a truthful surface can still cache a grant, swallow a refusal into a spinner, or draw an absent value as a fact. None of those is visible in the facade's tests and none is platform-specific, so they become requirements of their own: waiting is a state with a cause, a refusal is shown as what was refused, an empty read is not a conclusion, both halves of a connection's grants are read from the node, and no control offers a ticket, an import, a forced synchronization or a reset.
- **The person chooses the act before reading a code, and nothing above the facade parses a payload.** A payload is opaque above the host surface; the application asks whether this is an invitation to connect or a device joining an identity, and passes the value to that call. Reading a code for the wrong act produces the runtime's refusal, shown as a refusal.
- **A code on screen is treated as an exposure with a lifetime.** The screen says that whoever photographs it can use it until it is used or expires, shows it as spent afterwards, and is dismissable at once. The display is kept awake while a code is shown or a value awaited, because a screen that dims mid-ceremony ends the ceremony from the person's side.
- **2 shells, each holding the one platform fact that breaks it.** On iOS the local-network consent declaration is mandatory: without it outbound traffic to the subnet is dropped silently, which reads as a peer that never answers. On Android the node runs inside a foreground service with a visible notification, because state is held in memory and a backgrounded process is terminated at the system's discretion, taking the identity with it.
- **The node comes up by an explicit act on both platforms, and the 2 lifetimes are stated.** The shells differ — one keeps a service alive, the other lives while the application is in view — so an act performed by locking a phone means different things on the two, and the demonstration says which phone is which.
- **The demonstration's product-shaped properties become requirements; its logistics do not.** What the acts must show — several identities kept apart, a code that burns, claims absent rather than hidden, a read-only claim refusing the write, a second device standing in for the first, a withdrawal closing what it opened and a re-grant over the same claim reopening it, an outsider obtaining nothing — is specified. How a room is arranged is a run-through document, not a permanent requirement.
- **The staging needs 4 nodes, and the reason is a denial that cannot be faked.** The outsider must hold no connection to the granting identity, and hosting it as a second identity beside the grantee would not work: the data service answers by the issuer whose namespace is read, not by the identity a screen thinks it is acting under. So 2 phones run the application and 2 processes on the presenter's machine fill the other roles, each named in the narration for what it is.
- **And the demonstration states what it does not show:** that state is volatile, that an identity carries no key material, that the reconcile cadence is a configured number, which nodes in the staging are not phones, and that withdrawing a grant closes further delivery without recalling what was already delivered. The last is where a vanishing field would otherwise be read as deletion, which the platform does not promise.

## Out of Scope (deferred)

- **Everything in `mobile-host-surface`** — the facade, its table, the runtime's own-grant read, the portability spike. This change begins after that one has landed and its spike has passed.
- **On-disk persistence and key-backed identity.** Both are named in `mobile-host-surface`'s deferred list. This change is arranged so that no act depends on state outliving a process.
- **Retraction verdicts on screen.** They do not cross the facade, so a write that the issuer's gate later refuses is retracted with no screen showing the verdict.
- **A published application.** Development builds installed on named devices are the whole distribution posture: no store listing, no account, no update channel.
- **Any network client of the application's own.** Nodes reach each other only over the runtime's protocols, and a ceremony payload moves between phones through a person, which here is a code on a screen and a camera.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree.

| Capability (delta)            | Archive destination                                        |
| ----------------------------- | ---------------------------------------------------------- |
| `mobile-common-screens`       | `openspec/specs/components/mobile-common/screens.md`        |
| `mobile-common-demo-scenario` | `openspec/specs/components/mobile-common/demo-scenario.md`  |
| `ios-app-shell`               | `openspec/specs/components/ios-app/shell.md`                |
| `android-app-shell`           | `openspec/specs/components/android-app/shell.md`            |

### New Capabilities

- `mobile-common-screens`: the five screens, the act chosen before a code is read, a code as an exposure with a lifetime, waiting as a state with a cause, a refusal shown as what was refused, both halves of a connection read from the node, and the absence of any control the surface does not offer.
- `mobile-common-demo-scenario`: the acts with their paired denials, the environment they require, the operating conditions covered and uncovered, and what the narration must state as absent.
- `ios-app-shell`: local-network and camera consent, foreground-only operation with an explicit bring-up, and the device build.
- `android-app-shell`: the foreground service and its notification, local-network reachability at the target platform level, camera consent, and the device build.

### Modified Capabilities

None. `mobile-host-surface` states what the facade offers; nothing here changes it.

## Impact

- **`pdn-app`** (new repository, nested and gitignored beside `mia-docs` and `pdn-store`, added to the workspace file): the React Native screens, the two native modules, and the two platform projects.
- **`crates/pdn-mobile`**: consumed, not changed. If a screen turns out to need something the facade does not export, that is a change to `mobile-host-surface`'s capability rather than an addition made here.
- **Tests**: none of the demonstration is covered by an automated test, and this change says so rather than implying otherwise. Two phones are not a test fixture; what stands in for coverage is a written run-through performed twice on the devices that will run it, with the applications restarted between the passes.
- **The risk that outranks the rest**: the demonstration is only as good as its projection. Mirroring two phones onto one screen is the fragile part of the day, rehearsed with the same devices and cables, with a camera over the table as the fallback.
