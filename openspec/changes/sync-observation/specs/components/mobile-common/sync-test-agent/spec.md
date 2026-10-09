# Sync test agent

## Purpose

The application's test build, and the agent inside it that lets the sync tests (`pdn-app/sync-test/`: the load tests and the reliability test) drive a phone's node in a [pod](../../../architecture/language/pod.md) and read what it observes and what it costs. The agent performs acts through the same facade the screens call, adds the facade's observation calls ([mobile host](../../mee-pdn/pdn-mobile/host/spec.md)), samples the CPU of the node's threads and of the whole application and the thermal state, keeps the device awake, and reports to the tests' coordinator over HTTP. The test build is built in the release configuration, since the tests measure only what a device runs. It exists for iOS alone: the mechanisms this spec names — `task_threads` and `thread_info`, `ProcessInfo`, `UIDevice`, the idle timer, `xcrun devicectl` — are Apple's, and the Android application has no test build until a change specifies one for it. None of it is in the build the application ships, which stays what the [screens](../screens/spec.md) specify.

## ADDED Requirements

### Requirement: The agent exists only in the test build, built in the release configuration
The application SHALL have a test build, chosen when the application is built and built in the release configuration, that links a test build of the facade and contains the agent. The release build SHALL contain no agent code, no control channel and no exception for plain HTTP, and SHALL link a release of the facade. In the test build the agent SHALL be the one screen shown, naming the run, the coordinator's address and its own state, and SHALL draw nothing that changes while a run goes on but that state.

**Example:**

| build | configuration | facade | agent | plain HTTP to the local network |
|---|---|---|---|---|
| release | release | a release of `pdn-sdk` | absent | not declared |
| test | release | a test build of `pdn-sdk` | the only screen | declared |

#### Scenario: The release build carries nothing of the agent
- **WHEN** the release build is produced
- **THEN** it contains no agent screen, no control channel and no observation call, and declares no plain-HTTP exception

#### Scenario: The test build reports a release profile
- **WHEN** the test build is launched for a run and the coordinator asks for a reset
- **THEN** the agent's report names the build profile the facade states, and it is `release`

### Requirement: The agent takes its run from the launch environment and its commands from the coordinator
The agent SHALL read the coordinator's address and the run id from the environment the application was launched with, through a native module, and SHALL refuse to act on a launch without them. It SHALL connect to the coordinator as an HTTP client, ask it for commands, perform each through the facade, and report each result, a refusal reported as the refusal the facade returned. A reset SHALL stop the node, delete the node's directory through the native module, and bring a node up on a fresh directory at a reconcile interval of 10 seconds and the pod interval the command names.

**Example:** the commands the coordinator sends.

| command | the agent |
|---|---|
| `reset` | stops the node, deletes its directory, brings a node up at the pod interval given, creates one identity, reports the identity, the node id and the build profile |
| `join_pod` | joins a pod on the invite code given, through the facade's observed join, reports the pod id, and journals and forwards the records of the subscription the join answers |
| `put_record` | places a record of the given kind and payload, for the warm-up |
| `leave` | leaves the pod given, through the facade's membership act, and reports the outcome; the coordinator sends it before a `reset` that precedes a catch-up, so no identity whose node is gone stays a member |
| `observe` | subscribes to one pod and forwards its records |
| `listing` | reports the record listing of one pod |
| `ping` | reports its clock at once |

#### Scenario: A launch without a run does nothing
- **WHEN** the test build is launched without the coordinator's address
- **THEN** the agent shows that it has no run, contacts no address, and brings no node up

#### Scenario: A refused act is reported as refused
- **WHEN** the coordinator sends `join_pod` with an invite code already consumed
- **THEN** the agent reports the facade's refusal, and does not report the pod joined

#### Scenario: A leave before a reset leaves no departed identity a member
- **WHEN** the coordinator sends `leave` for a pod the node's identity is a member of, then `reset`, then `join_pod` on a fresh invite
- **THEN** the other members fold the old identity as departed and the new one as a member, so the pod's member count is the one it had before the leave

#### Scenario: A reset starts from an empty directory
- **WHEN** the coordinator sends `reset` after a run in which the node joined a pod
- **THEN** the node brought up reports a node id and an identity it did not report before, and holds no pod

### Requirement: Every record is journaled before it is forwarded
The agent SHALL append each record a subscription yields to a journal file in the application's own container before forwarding it to the coordinator, unchanged and in the order it arrived. A record that fails to reach the coordinator SHALL stay in the journal. A journal append that fails SHALL be reported to the coordinator as a failure of the journal, and the agent SHALL keep forwarding. The journal SHALL survive the agent's reset, which deletes the node's directory only. The agent SHALL read the subscription in a loop of its own, so a slow report to the coordinator does not slow the reading.

**Example:** the coordinator's copy misses 2 records its HTTP report lost.

```
journal:      seq 8210, 8211, 8212, 8213
coordinator:  seq 8210, 8213
```

The journal pulled from the phone over the cable fills the gap.

#### Scenario: A lost report is in the journal
- **WHEN** the agent's report of a record fails to reach the coordinator
- **THEN** the journal holds that record, in its place in the sequence

#### Scenario: A full disk is reported, not hidden
- **WHEN** an append to the journal fails because the device's storage is full
- **THEN** the coordinator receives a report that the journal failed, and the records the agent still forwards carry their own sequence numbers

### Requirement: The agent reports what the node and the application cost, and the application's state
The agent SHALL report, once a second, unasked, a sample taken through its native module: the user and system CPU time of the whole application process since it started (`getrusage` with `RUSAGE_SELF`); the user and system CPU time of the node's threads, those whose name starts with the facade's prefix `pdn-node` and the store's `sync-actor` threads (`task_threads`, then `thread_info` and the name of each thread); the device's thermal state (`ProcessInfo.thermalState`); whether Low Power Mode is on (`ProcessInfo.isLowPowerModeEnabled`), which lowers CPU clocks and defers network work; the battery's state and level (`UIDevice.batteryState`, `batteryLevel`); and the application's state; each sample with the time it was taken on the device's clock. The node's CPU time SHALL be accumulated by the agent from each thread's change since the previous sample, so it never falls when a thread exits, and a thread that exits between 2 samples loses at most its CPU since the earlier one. The process total less the node's share is the agent's own work and every thread no one named, and is reported as such, not as the node's. The agent SHALL also report every change of the application's state — `active`, `inactive`, `background` — as it happens.

**Example:** two samples a second apart during a catch-up.

```
{"kind":"cpu","t":1790000044051000,"cpu_user_us":81234000,"cpu_sys_us":10422000,"node_cpu_user_us":70110000,"node_cpu_sys_us":9802000,"thermal":"nominal","low_power":false,"battery":"charging","battery_level":0.81,"app_state":"active"}
{"kind":"cpu","t":1790000045051000,"cpu_user_us":82011000,"cpu_sys_us":10530000,"node_cpu_user_us":70792000,"node_cpu_sys_us":9890000,"thermal":"fair","low_power":false,"battery":"charging","battery_level":0.81,"app_state":"active"}
```

The coordinator reads 0.885 seconds of CPU for the process over that second, 0.770 of them on the node's threads and 0.115 the observation's and the application's, at a thermal state that has left nominal.

#### Scenario: A sample arrives every second
- **WHEN** the agent runs a 60-second idle workload
- **THEN** the coordinator receives at least 55 samples, each process CPU time and each node CPU time no lower than the one before, and each node CPU time no higher than the process CPU time of the same sample

#### Scenario: The node's share is reported apart from the agent's work
- **WHEN** the agent forwards the records of a 1,000-record catch-up
- **THEN** its samples over the catch-up show node CPU time below the process CPU time, the difference being the CPU of the threads the facade and the store do not name

#### Scenario: Leaving the foreground is reported
- **WHEN** the application leaves the foreground during a run
- **THEN** the coordinator receives that change of state, at the latest with the agent's first report after the application returns

### Requirement: The agent keeps the device awake, and a window outside the active state is invalid
The agent SHALL disable the application's idle timer (`isIdleTimerDisabled`) while a session with the coordinator is open, from the run's first command until the coordinator ends the run, and again from the first command after a relaunch, and SHALL enable it again when the run ends. A sample window in which the application was not `active` throughout — a sample whose application state is not `active`, or a change of state reported inside the window — SHALL be invalid for measurement, and the coordinator marks the cell it falls in; the agent's reports SHALL let the coordinator tell every such window, by the state on every sample and the time of every change.

**Example:** a cell from 100 to 160 seconds of the run.

| what the agent reports | the cell |
|---|---|
| every sample `active`, no change of state | valid |
| a change to `inactive` at 131 seconds (a notification drawn over the application) and back to `active` at 133 seconds | invalid: the coordinator marks it `inactive` |
| a change to `background` at 140 seconds, then nothing until a relaunch | invalid, and the relaunch is reported |

#### Scenario: The device stays awake through a run
- **WHEN** a run lasts longer than the device's auto-lock delay with no one touching the device
- **THEN** the screen stays on, the application stays `active`, and every sample over the run says `active`; once the run ends, the idle timer is enabled again

#### Scenario: A window outside the active state is told apart
- **WHEN** the application becomes `inactive` for 2 seconds inside a cell and returns to `active`
- **THEN** the coordinator receives both changes of state with their times, and the samples taken while it was `inactive` say so, so the cell can be marked invalid

### Requirement: A relaunch starts new subscriptions
A subscription SHALL NOT be taken to survive the application's process. After a relaunch the agent SHALL subscribe again, each new subscription carrying a new identifier, and SHALL report the relaunch to the coordinator.

**Example:** the coordinator relaunches the application at 40 seconds. The records before the kill carry subscription `c41e…`, the ones after it `07b2…` counting from 0, and the records the node produced in between are reported by neither.

#### Scenario: A relaunched agent subscribes anew
- **WHEN** the application is killed and launched again during a run
- **THEN** the agent reports the relaunch and its new subscriptions carry identifiers it has not used before
