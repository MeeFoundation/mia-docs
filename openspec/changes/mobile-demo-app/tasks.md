# Tasks: mobile-demo-app

Start after `mobile-host-surface` has landed and its portability spike has passed. Until a build runs on a phone and two devices pair over a real network, nothing here has a foundation. The spike's recorded answers about the async shape of the bindings, iOS local-network consent, and the Android platform level's requirement are inputs to groups 1 and 4.

## 1. The repository and the boundary

- [x] 1.1 `pdn-app` exists as its own git repository, gitignored by `mee-pdn` and present in the workspace file, carrying its README and CLAUDE.md. What remains of it is task 6.1: keeping both true to what actually gets built
- [ ] 1.2 React Native project across both platforms, consuming the facade's XCFramework and archive as artifacts rather than sources
- [ ] 1.3 The native module per platform: forwards calls, translates errors, decides nothing (D1)
- [ ] 1.4 Bring-up and stop wired to explicit acts on both platforms, not to a lifecycle callback (D6)

## 2. Screens

- [ ] 2.1 Identities: create, list hosted, choose the one the other screens act under, and the screen states that what it lists is lost when the application stops
- [ ] 2.2 Own entries: list, read, write under the chosen identity
- [ ] 2.3 Connections: list, show a code, read a code — the person chooses the act before reading, and nothing above the facade parses or wraps a payload (D3)
- [ ] 2.4 One connection: what this peer granted me and what I granted this peer, both read from the node on every device, each claim named by joining derived identities against paths the screen knows or has listed, with publishing and withdrawing a grant
- [ ] 2.5 Waiting is a state with a cause: a screen reading a value that has not arrived says what it waits for and reads again, never concluding from one empty read, and says so when waiting outlasts what the configured cadence explains
- [ ] 2.6 Refusals on screen: what was refused, named; the previous value left in place after an unpermitted write; an unrecognized failure with a stable message and its cause chain only in the platform log. The one exception stated where it is implemented: after a withdrawal the grantee's node refuses the whole issuer, and that renders as the peer no longer sharing rather than as a fault
- [ ] 2.7 A displayed code states that whoever photographs it can use it until it is used or expires, shows itself as spent afterwards, and is dismissable at once (D4)
- [ ] 2.8 The display kept awake while a code is shown and while a value is awaited (D5)
- [ ] 2.9 Identifiers rendered so two people can compare them by eye, a peer's name shown as the person's own note, and nothing labelled verified or proven
- [ ] 2.10 No control anywhere offers a ticket, an import, a share, a forced synchronization or a reset — walked screen by screen, because absence is the requirement
- [ ] 2.11 The camera and the code rendering, the only platform capability the screens need beyond the facade

## 3. iOS shell

- [ ] 3.1 The local-network usage declaration with its reason text
- [ ] 3.2 A legible state when local-network consent is absent or refused, met the way the spike found it can be met
- [ ] 3.3 Camera consent declared, and a refusal reported on the reading screen with the way to grant it
- [ ] 3.4 The node stopped explicitly as the application leaves the foreground, and a termination presented as what it is — no identity hosted, said rather than shown as an empty list
- [ ] 3.5 The facade linked for the device architecture; nothing written to the application's container

## 4. Android shell

- [ ] 4.1 A foreground service started with the node and stopped with it, its notification naming the running node and the number of identities it hosts
- [ ] 4.2 Stopping the service presented as losing the hosted identities, not as something recoverable
- [ ] 4.3 Whatever the target platform level requires for local-subnet traffic, per the spike's finding, with a refusal of that access reported as itself
- [ ] 4.4 Camera consent requested at the reader and a refusal reported there
- [ ] 4.5 The facade's shared library packaged for the device architectures; nothing written to application storage

## 5. The demonstration

- [ ] 5.1 The written run-through: the acts of the demonstration in order, each with the device it happens on, that device's platform, the refusal shown beside it, and the sentence naming what it proves
- [ ] 5.2 The outsider's act: a fourth node, connected to neither side, shown obtaining nothing of the granting identity's data — the tightest denial of the change's own headline claim, and one no audience has seen. It is a node and not a second identity beside the grantee, because the data service answers by issuer rather than by the identity a screen is set to (D7)
- [ ] 5.3 The 2 nodes that are not phones: `pdn-node-http` processes on the presenter's machine in the same network, one joining an identity as its second device and one playing the outsider. Both need `PDN_DEBUG=1`, since the routes the presenter drives are absent without it. What is narrated: that they are not phones, that their payload is carried by hand, and that they run at the default cadence (D7)
- [ ] 5.4 The re-grant act: the same claim granted again after the withdrawal, and the access reopening — the path `operating-conditions` singles out, and the difference between showing a boundary and showing a dead end
- [ ] 5.5 The device-leaves gesture defined as airplane mode with the application in view, never a lock screen, and the reason recorded next to it: on iOS a lock can end the process and take every identity with it (D6)
- [ ] 5.6 The 5 absences written into the narration — volatile state, an identity without keys, a configured cadence, which nodes are not phones, and that a withdrawal closes further delivery without recalling what was already delivered (D9)
- [ ] 5.7 The operating conditions the demonstration covers and the ones it does not, written beside the acts, memory pressure among the uncovered — a phone is killed for it and a container never was
- [ ] 5.8 Staging: the network confirmed to pass traffic between 2 of its clients, and 2 devices mirrored onto one screen with a camera over the table as the fallback (D8)
- [ ] 5.9 A full run-through end to end, twice, on the devices and network the demonstration runs on, with every application restarted between the passes — the only way to find an act that silently depended on the previous run's state

## 6. Docs and spec tree (manual, not deltas)

- [ ] 6.1 `pdn-app`'s README and CLAUDE.md kept true to what was built: the layout as it ended up, the build steps as recipes that exist, and the environment facts unchanged
- [ ] 6.2 CLAUDE.md of `mee-pdn`: `pdn-app` in the directory layout beside `mia-docs` and `pdn-store`
- [ ] 6.3 Sweep the spec tree and the active changes for statements this change invalidates

## 7. Gates

- [ ] 7.1 The run-through of 5.9 passed twice, and every refusal in it observed rather than assumed
- [ ] 7.2 `openspec validate --all --strict` before archiving. The deltas' relative links are written for the archive destination, not for the delta's own directory
