# Tasks: mobile-demo-app

Start after `mobile-host-surface` has landed and its portability spike has passed. Until a build runs on a phone and 2 nodes pair over a real network, nothing here has a foundation. The spike's recorded answers about the async shape of the bindings, iOS local-network consent, and the Android platform level's requirement are inputs to groups 1 and 4.

## 1. The repository and the boundary

- [x] 1.1 `pdn-app` exists as its own git repository, gitignored by `mee-pdn` and present in the workspace file, carrying its README and CLAUDE.md. What remains of it is task 6.1: keeping both true to what actually gets built
- [~] 1.2 React Native project across both platforms, consuming a named release of `pdn-sdk` — its XCFramework and archive as artifacts rather than sources, and the release named in this repository, so what a phone was built against is readable without opening a build log
- [~] 1.3 The native module per platform: forwards calls, translates errors, decides nothing (D1)
  - iOS, done and run on an iPhone 15 Pro Max: `modules/pdn` is a local Expo module whose podspec vendors the `PdnMobile.xcframework` of `pdn-sdk` and compiles the generated Swift beside it. It forwards each exported call and maps `PdnError` to the 16 kinds of the screens' closed table; a refusal crosses as one code with the kind as its message, and the cause chain goes to `NSLog` and nowhere else.
  - The module also resolves the storage directory inside the application's own container and excludes it from the platform's backup, which is what makes the screens' claim that this device holds the only copy true of the device.
  - Autolinking did not pick the module up on this SDK: `expo-modules-autolinking resolve` reports it, and `pod install` installs 273 pods without it while `expo.inlineModules.watchedDirectories` stays empty. The pod is therefore named by a config plugin, `plugins/with-pdn-module.js`, which writes it into the Podfile at generation — where the shells are generated from, rather than into a generated file the next generation replaces.
  - Android: not started.
  - What the run proves is that the bridge is built, registered and reached. Every scenario of group 2 and group 5 is still unexercised against a real peer.
- [~] 1.4 Bring-up and stop wired to explicit acts on both platforms, not to a lifecycle callback (D6)
  - iOS: both are acts on the identities screen and nothing else offers them. Android waits on its shell.

## 2. Screens

- [ ] 2.1 Identities: create, list hosted, choose the one the other screens act under, and the screen states that what it lists lives on this device, which holds the only copy
- [~] 2.2 Own entries: list, read, write under the chosen identity
  - Run on the device: an entry written under the chosen identity, listed with its payload length, read back, and then granted to a connected peer which read it from its own node. This is the first time the phone was the issuer rather than the grantee, and the join that names a shared claim was exercised from the issuer's side, where the screen knows its own paths, rather than from the listing of a received namespace.
- [~] 2.3 Connections: list, show a code, read a code — the person chooses the act before reading, and nothing above the facade parses or wraps a payload (D3)
  - Both directions run on the device: the phone read a code minted by a `pdn-node-http` peer, and the phone minted one that the same peer consumed. Reading asks for the act first and passes the value straight through; nothing above the facade looked inside a payload in either direction.
- [ ] 2.4 One connection: what this peer granted me and what I granted this peer, both read from the node on every device, each claim named by joining derived identities against paths the screen knows or has listed, with publishing and withdrawing a grant
- [ ] 2.5 Waiting is a state with a cause: a screen reading a value that has not arrived says what it waits for and reads again, never concluding from one empty read, and says so when waiting outlasts what the configured cadence explains
- [~] 2.6 Refusals on screen: what was refused, named; the previous value left in place after an unpermitted write; an unrecognized failure with a stable message and its cause chain only in the platform log. The one exception stated where it is implemented: after a withdrawal the grantee's node refuses the whole issuer, and that renders as the peer no longer sharing rather than as a fault
  - The closed table did not reach a screen at all until this was found on the device, and it is worth writing down because nothing below the device could have caught it. Every refusal the facade made arrived as the unrecognized failure, so a person was told the node had broken whatever had actually happened.
  - The bridge carries a refusal as one code with the kind in the message, and the platform's module layer does not pass that message through: it wraps the call it came from around it and joins a cause chain on with a separator of its own. Taking the whole text for a kind found nothing in the table, and reading a message off the missing entry threw — a second failure on top of the first, which is what reached the screen. The kind is now read out of the message rather than taken to be it, and the error type no longer throws on a kind it does not know, so a mistake there can never again hide the refusal underneath.
  - What made it visible was the log disagreeing with the screen: the facade's own line named `CounterpartyUnreachable` while the screen said the node had failed. The logging sits in Swift, before the bridge, which is why it was right where the screen was wrong.
  - Confirmed on the device afterwards: with local-network access revoked the same ceremony now reads `counterparty-unreachable` rather than the unrecognized failure. The withdrawal exception and the unpermitted write are exercised elsewhere; what is still unexercised on a screen is a refused camera.
- [x] 2.7 A displayed code states that whoever photographs it can use it until it is used or expires, shows itself as spent afterwards, and is dismissable at once (D4)
  - Run on the device: the code was drawn, the lifetime counted down, and at its end the screen stopped drawing the code and said the lifetime had run out.
  - The run happens to prove why the requirement says that rather than "spent": the code had in fact been consumed by the peer before the countdown ended, and the screen said only that the lifetime was out. It cannot know the difference — the facade exports no way to ask whether a minted payload was used — and saying otherwise would have been an invention.
- [ ] 2.8 The display kept awake while a code is shown and while a value is awaited (D5)
- [ ] 2.9 Identifiers rendered so two people can compare them by eye, a peer's name shown as the person's own note, and nothing labelled verified or proven
- [ ] 2.10 No control anywhere offers a ticket, an import, a share, a forced synchronization or a reset — walked screen by screen, because absence is the requirement
- [ ] 2.12 The connections screen's sentence about reaching a peer matches what the endpoint does: addresses published under a node id and a relay behind the session that finds no direct path, rather than one local network
- [~] 2.11 The camera and the code rendering, the only platform capability the screens need beyond the facade
  - Both exercised on the device: the camera read a peer's code, and a code this phone minted was rendered well enough for another party to read it off the screen. A refused camera is still unexercised.

## 3. iOS shell

- [ ] 3.1 The local-network usage declaration with its reason text
- [ ] 3.2 A legible state when local-network consent is absent or refused, met the way the spike found it can be met
- [ ] 3.3 Camera consent declared, and a refusal reported on the reading screen with the way to grant it
- [x] 3.4 Bring-up and stop as acts of the person, a suspension left alone, and a termination presented as what it is — the node down and its directory intact, said rather than shown as an empty list
  - Rewritten against what the suspension measurement found, per 1.1's rule that a platform behaviour contradicting a requirement amends it. The task as first written asked for 2 things the runtime turned out not to want: a stop as the application leaves the foreground, and a termination reported as hosting no identity.
  - The endpoint survives a suspension and resumes with no act of the person, so stopping on the way out would trade a node that comes back for one raised again by hand, and would end a ceremony somebody had merely switched away from. And a termination is not an emptying: the node comes back on its directory as itself.
  - The shell already behaves this way; what changed is the requirement, in `ios-app-shell`.
- [x] 3.5 The facade linked for the device architecture; the node's directory named inside the application's own container and excluded from the platform's backup, so this device holds the only copy
  - Confirmed on the device by reading the flag back rather than trusting the call that set it, since the screens' claim about the only copy rests on that one flag: the node's directory is `Library/Application Support/pdn` inside the application's container and reports `excludedFromBackup=true`.

## 4. Android shell

- [ ] 4.1 A foreground service started with the node and stopped with it, its notification naming the running node and the number of identities it hosts
- [ ] 4.2 Stopping the service presented as losing the hosted identities, not as something recoverable
- [ ] 4.3 Whatever the target platform level requires for local-subnet traffic, per the spike's finding, with a refusal of that access reported as itself
- [ ] 4.4 Camera consent requested at the reader and a refusal reported there
- [ ] 4.5 The facade's shared library packaged for the device architectures; the node's directory named inside the application's own storage, and the backup declaration the target platform level requires written where the shells are generated from, not in a generated manifest

## 5. The demonstration

- [~] 5.1 The written run-through: the acts in order — Alice's identity created and written to on her laptop node, her phone joining it through the linking ceremony, Bob's node connecting afterwards — each with the node it happens on, the platform where that is a phone, the refusal shown beside it, and the sentence naming what it proves
- [ ] 5.2 The outsider's act: a fourth node, holding no connection to Alice, whose script's attempt to obtain her data is watched failing on the browser screen driving it — the tightest denial of the change's own headline claim, and one no audience has seen as a refusal on a screen rather than read off a terminal. It is a node and not a second identity beside the grantee, because the data service answers by issuer rather than by the identity a screen is set to (D7)
- [ ] 5.3 The 3 nodes that are not phones: `pdn-node-http` processes on the presenter's machine — Alice's first device, where her identity is created and the linking payload is minted; Bob's, whose script mints the invite, holds the grants, and whose granting acts are watched on his own browser screen; and the outsider's, whose denial is watched the same way. All 3 need `PDN_DEBUG=1`, since the routes the run-through's script drives and the browser screens shown to the audience are both absent without it. What is narrated: that they are not phones, that a browser page pointed at each node's debug surface runs the same screens as the phone and shows what the script did there, that a code it mints is rendered there for the phone to read, and that they run at the default cadence (D7)
- [ ] 5.4 The re-grant act: the same claim granted again after the withdrawal, and the access reopening — the path `operating-conditions` singles out, and the difference between showing a boundary and showing a dead end
- [ ] 5.5 The device-leaves gesture defined as airplane mode with the application in view, never a lock screen, and the reason recorded next to it: on iOS a lock can end the process and take every identity with it (D6). The device that leaves is the phone, which established the connection and published the grant, and Alice's laptop node carries the fresh value to Bob in its absence
- [ ] 5.6 The 5 absences written into the narration — this device holding the only copy, an identity without keys, a configured cadence, which nodes are not phones and that their side of every act runs through the run-through's script rather than a person's tap, watched on a browser's screen rather than the mobile application's, and that a withdrawal closes further delivery without recalling what was already delivered (D9)
- [ ] 5.7 The operating conditions the demonstration covers and the ones it does not, written beside the acts, memory pressure among the uncovered — a phone is killed for it and a container never was. Uncovered too, and named: a withdrawal performed on a device other than the one that published the grant, and every counterparty act as the mobile application would show it, since Bob and the outsider run `pdn-node-http` processes rather than that application
- [ ] 5.8 Staging: the network confirmed to pass traffic between 2 of its clients, and the phone mirrored onto the screen that also carries the terminal, with a camera over the table as the fallback (D8)
  - No node is restarted once the run-through has begun. A node keeps its id across a restart but not its address — the endpoint binds an ephemeral port and nothing configures one — so with no relay and no discovery a restarted node is unreachable to every peer it had, and the screens cannot say so: a replica holds the last value that arrived and no read reports its age. A stale screen looks exactly like a current one.
- [ ] 5.9 A full run-through end to end, twice, on the devices and network the demonstration runs on, with the application restarted between the passes — the only way to find an act that silently depended on the previous run's state
- [ ] 5.10 The linking act placed before any connection exists: the phone joins an identity that already holds entries and comes up carrying them, and the laptop node holds a second identity of Alice's at that moment so that what the phone does not receive is real
- [ ] 5.11 The connection reaching Alice's laptop node with no act performed there, shown after Bob's ceremony completes on the phone — the wait is the periodic pass, so it is narrated as waiting
- [ ] 5.12 Both directions of granting over the one connection, each watched on the screen of its issuer: Alice granting Bob, so the issuer's acts are tapped through on her phone and what Bob obtains as grantee is read on the browser screen driving his node; Bob granting Alice, so the same issuer's acts, run by the script, are watched on that browser screen and a claim arriving, a writable claim accepting an edit, a read-only claim refusing one, and a withdrawn claim reading as no longer shared are on Alice's phone (D7a)
- [ ] 5.13 The grant-reaches-every-device act: Bob's grant to Alice, read first on her phone, is read again from her laptop node with no act performed there, and a later change Bob makes to one of the granted claims arrives on the laptop too — the identity holds the grant, not the device that first read it (D7b)

## 6. Docs and spec tree (manual, not deltas)

- [ ] 6.1 `pdn-app`'s README and CLAUDE.md kept true to what was built: the layout as it ended up, the build steps as recipes that exist, the facade's artifacts named as a release of `pdn-sdk` rather than as something built out of `mee-pdn`, and the environment facts unchanged
- [ ] 6.2 CLAUDE.md of `mee-pdn`: `pdn-app` in the directory layout beside `mia-docs` and `pdn-sdk`
- [ ] 6.3 Sweep the spec tree and the active changes for statements this change invalidates
- [~] 6.4 The run-sheet artifacts in `mee-pdn` that stage the superseded cast — `demo-script.md`, `demo-script-en.md`, `demo-commands.md`, the scripts under `demo/`, and `status.md` — rewritten onto this staging or marked superseded where they live. `demo/09-restart.sh` is the sharpest case: it restarts a node mid-run, which 5.8 forbids
  - Rewritten: `demo/` now stages 3 `pdn-node-http` nodes (Alice's laptop on 3011, Bob on 3012, Carol on 3013) and one script per act, and both run-sheets follow them. `demo-commands.md` is gone — it duplicated the scripts in prose, which is the copy that drifts. `09-restart.sh` is gone with it, and the QR decoder the pre-flight needs is vendored beside the scripts instead of living in an ignored directory.
  - Moved: `demo/` and `demo-script-en.md` (the Russian run-sheet is dropped along with it, see below) now live in `pdn-app` rather than at the `mee-pdn` workspace root, so what the acts drive sits beside the application they demonstrate. `lib.sh` resolves the workspace root 2 levels up instead of 1, since `demo/` now nests one level deeper; the node binary and the demo's own state under `tmp/` still come from `mee-pdn`, which is the one thing this move could not carry with it.
  - `demo-script.md`, the Russian run-sheet, is removed rather than moved: it duplicated `demo-script-en.md` and had drifted, and one run-sheet in the repository the scripts now live in is enough.
  - Rehearsed on the laptop half only: acts 1 and 3 to 8 were run end to end with Alice's laptop standing in for the phone, including the 409 after a withdrawal and the outsider's denial. What no rehearsal has touched is every act that needs the phone — the linking ceremony above all, which the phone has never performed.
  - The gap this opened is closed: `lib.sh` grew `pdnbrowser`, which switches the browser to a node's screen and no-ops when it is already the one showing, and `01`, `03`, `04`, `05`, `06`, `07`, `08`, `09` each call it for the node their act puts on screen. Base data for Alice and Bob moved into `00-start.sh` too, so `01` and `05` only display and grant rather than also typing entries live.
  - `07-grant-follows-identity.sh` is new (task 5.13): it shows Alice's laptop reading a grant of Bob's it never accepted, and a later change to it arriving with no act performed there. What was `07-stand-in.sh` and `08-outsider.sh` moved to `08` and `09` to make room for it.

## 7. Gates

- [ ] 7.1 The run-through of 5.9 passed twice, and every refusal in it observed rather than assumed
- [ ] 7.2 `openspec validate --all --strict` before archiving. The deltas' relative links are written for the archive destination, not for the delta's own directory
