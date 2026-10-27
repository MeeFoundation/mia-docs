# Sync test agent

## Purpose

The application's test build, and the agent inside it that lets the sync tests (`mee-pdn/sync-test/`: the load tests and the reliability test, with the phone's build and checks in `pdn-app/sync-test/`) drive a phone's node in a [pod](../../../architecture/language/pod.md) and read what it observes and what it costs. The agent starts the facade's test surface ([mobile host](../../mee-pdn/pdn-mobile/host/spec.md)) — the laptop host's routes on the phone's loopback, reached by the tests' coordinator over the device's cable — samples the CPU of the node's threads and of the whole application, its resident memory and the device's state, and keeps the device awake. The test build is built in the release configuration, since the tests measure only what a device runs. It exists for iOS alone: the mechanisms this spec names — `task_threads` and `thread_info`, `task_info`, `ProcessInfo`, `UIDevice`, the idle timer, `xcrun devicectl`, usbmux — are Apple's, and the Android application has no test build until a change specifies one for it. None of it is in the build the application ships, which stays what the [screens](../screens/spec.md) specify.

## ADDED Requirements

### Requirement: The agent exists only in the test build, built in the release configuration
The application SHALL have a test build, chosen when the application is built and built in the release configuration, that links a test build of the facade and contains the agent. The release build SHALL contain no agent code and no test surface, and SHALL link a release of the facade. In the test build the agent SHALL be the one screen shown, naming the run, the surface's port and its own state, and SHALL draw nothing that changes while a run goes on but that state.

**Example:**

| build | configuration | facade | agent and test surface |
|---|---|---|---|
| release | release | a release of `pdn-sdk` | absent |
| test | release | a test build of `pdn-sdk` | the only screen, the surface on the phone's loopback |

#### Scenario: The release build carries nothing of the agent
- **WHEN** the release build is produced
- **THEN** it contains no agent screen, no test surface and no observation call

#### Scenario: The test build reports a release profile
- **WHEN** the test build is launched for a run and the coordinator asks the surface for a reset
- **THEN** the reset's answer names the build profile, and it is `release`

### Requirement: The agent takes its run from the launch environment and serves the surface on the phone's loopback
The agent SHALL read the run id and the surface's port from the environment the application was launched with, through a native module, and with both present SHALL start the facade's test surface on the application's node directory and that port; a launch without them SHALL start no surface and bring no node up. The surface SHALL be reachable at the phone's loopback address alone. The coordinator reaches it over the device's cable through a usbmux tunnel, so the records and the samples cross no network the measured sync uses, and drives the node through the surface's routes: the laptop host's routes for the acts and the observation, and the surface's own reset, samples and clock.

**Example:** the requests of one catch-up cell, through `iproxy -u <udid> 3311:3011` on the laptop.

| request | what the phone does |
|---|---|
| the act route, `leave` | leaves the pod, so no identity whose node is reset stays a member |
| reset, pod interval 300, `direct` | stops the node, deletes its directory, brings a node up, creates one identity, answers the identity, the node id and the build profile |
| the observed join route, on a writer's invite | joins through the observed join and streams the records from `seq` 0 |
| the record route | places the warm-up record of the reliability test |
| the listing route | answers the record listing |
| the samples route | answers the samples taken since the last one read |
| the clock route | answers the device's clock at once |

#### Scenario: A launch without a run does nothing
- **WHEN** the test build is launched without the run id and the port
- **THEN** the agent shows that it has no run, starts no surface, and brings no node up

#### Scenario: The surface is not on the local network
- **WHEN** the test build runs with its surface started, and a device on the phone's local network connects to the surface's port at the phone's local network address
- **THEN** the connection is refused, while the coordinator's requests through the tunnel are answered

#### Scenario: A refused act is reported as refused
- **WHEN** the coordinator asks the surface for an observed join on an invite code already consumed
- **THEN** the surface answers the laptop host's refusal, no stream opens, and the node holds no pod

#### Scenario: A leave before a reset leaves no departed identity a member
- **WHEN** the coordinator asks the surface to leave a pod the node's identity is a member of, then for a reset, then for an observed join on a fresh invite
- **THEN** the other members fold the old identity as departed and the new one as a member, so the pod's member count is the one it had before the leave

### Requirement: The agent reports what the node and the application cost, and the application's state
The agent SHALL take, once a second, through its native module, a sample and hand it to the surface: the user and system CPU time of the whole application process since it started (`getrusage` with `RUSAGE_SELF`); the user and system CPU time of the node's threads — those whose name starts with the facade's prefix `pdn-node`, the store's `sync-actor` threads, and the blob store's own runtime, whose threads are named `iroh-blob-store-` followed by a number and carry the node's payload imports, writes, metadata and collection (`task_threads`, then `thread_info` and the name of each thread); the process's resident memory (`phys_footprint` from `task_info`); the device's thermal state (`ProcessInfo.thermalState`); whether Low Power Mode is on (`ProcessInfo.isLowPowerModeEnabled`), which lowers CPU clocks and defers network work; the battery's state and level (`UIDevice.batteryState`, `batteryLevel`); and the application's state; each sample with the time it was taken on the device's clock and a sequence number. The node's CPU time SHALL be accumulated from each thread's change since the previous sample, so it never falls when a thread exits, and a thread that exits between 2 samples loses at most its CPU since the earlier one. The process total less the node's share is the application's own work and every thread no one named, and is reported as such, not as the node's. The agent SHALL also hand over every change of the application's state — `active`, `inactive`, `background` — as it happens, as a sample of its own.

**Example:** two samples a second apart during a catch-up, as the samples route answers them: the sequence number is the surface's, the sample the native module's.

```
{"seq":42,"sample":{"kind":"cpu","t":1790000044051000,"cpu_user_us":81234000,"cpu_sys_us":10422000,"node_cpu_user_us":70110000,"node_cpu_sys_us":9802000,"resident_bytes":182452224,"thermal":"nominal","low_power":false,"battery":"charging","battery_level":0.81,"app_state":"active"}}
{"seq":43,"sample":{"kind":"cpu","t":1790000045051000,"cpu_user_us":82011000,"cpu_sys_us":10530000,"node_cpu_user_us":70792000,"node_cpu_sys_us":9890000,"resident_bytes":184549376,"thermal":"fair","low_power":false,"battery":"charging","battery_level":0.81,"app_state":"active"}}
```

The coordinator reads 0.885 seconds of CPU for the process over that second, 0.770 of them on the node's threads — the test surface's server among them — and 0.115 the application's, at a thermal state that has left nominal.

#### Scenario: A sample arrives every second
- **WHEN** the agent runs through a 60-second idle workload
- **THEN** the surface's samples route answers at least 55 samples over it, each process CPU time and each node CPU time no lower than the one before, and each node CPU time no higher than the process CPU time of the same sample

#### Scenario: The node's share is reported apart from the application's work
- **WHEN** the coordinator streams the records of a 1,000-record catch-up through the surface
- **THEN** the samples over the catch-up show node CPU time below the process CPU time, the difference being the CPU of the threads neither the facade, the store nor the blob store names

#### Scenario: Leaving the foreground is reported
- **WHEN** the application leaves the foreground during a run
- **THEN** the samples route answers that change of state, at the latest with the first samples the coordinator reads after the application returns

### Requirement: The agent keeps the device awake, and a window outside the active state is invalid
The agent SHALL disable the application's idle timer (`isIdleTimerDisabled`) from the start of a launch with a run until the process ends. A sample window in which the application was not `active` throughout — a sample whose application state is not `active`, or a change of state handed over inside the window — SHALL be invalid for measurement, and the coordinator marks the cell it falls in; the samples SHALL let the coordinator tell every such window, by the state on every sample and the time of every change.

**Example:** a cell from 100 to 160 seconds of the run.

| what the samples say | the cell |
|---|---|
| every sample `active`, no change of state | valid |
| a change to `inactive` at 131 seconds (a notification drawn over the application) and back to `active` at 133 seconds | invalid: the coordinator marks it `inactive` |
| a change to `background` at 140 seconds, then nothing until a relaunch | invalid, and the relaunch is told by a new surface |

#### Scenario: The device stays awake through a run
- **WHEN** a run lasts longer than the device's auto-lock delay with no one touching the device
- **THEN** the screen stays on, the application stays `active`, and every sample over the run says `active`

#### Scenario: A window outside the active state is told apart
- **WHEN** the application becomes `inactive` for 2 seconds inside a cell and returns to `active`
- **THEN** the samples route answers both changes of state with their times, and the samples taken while it was `inactive` say so, so the cell can be marked invalid

### Requirement: A relaunch starts new subscriptions
A subscription SHALL NOT be taken to survive the application's process. After the application is relaunched over the cable, the relaunched surface SHALL bring no node up by itself: the coordinator asks it for a reset and joins the pod again, as the load test does, and every subscription through the surface after that SHALL be a new one, carrying a new identifier and counting from `seq` 0, and the new launch's samples start over. A node brought up again on the directory the previous launch left, under the run's settings, is no path of the surface.

**Example:** the coordinator relaunches the application at 40 seconds. The records before the kill carry subscription `c41e…`; the relaunched surface answers that no node is up until the coordinator's reset, whose node joins on a fresh invite; the records after that carry `07b2…` counting from 0, and the records the previous node produced between the kill and the reset are reported by neither.

#### Scenario: A relaunched surface subscribes anew
- **WHEN** the application is killed and launched again during a run, the coordinator asks the relaunched surface for a reset and an observed join, and opens the event route
- **THEN** the subscription carries an identifier not used before, and its records count from `seq` 0
