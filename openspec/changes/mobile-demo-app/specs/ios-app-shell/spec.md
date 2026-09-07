# ios-app: shell

The iOS shell is the thin layer between the generated Swift bindings and the shared screens. It forwards calls, translates errors, and owns the three things the platform decides for it: consent to reach the local network, consent to use the camera, and how long the process is allowed to live. What the application does with the runtime belongs to [host-surface](../mobile-common/host-surface.md), and what the screens must do belongs to [screens](../mobile-common/screens.md).

## ADDED Requirements

### Requirement: Local-network consent is declared and its refusal is legible
The application SHALL declare its use of the local network, so the system asks the person for consent before traffic to the subnet is attempted. When consent is absent or refused, the shell SHALL surface that state as itself.

Without the declaration the platform drops outbound traffic to the local subnet silently. The symptom is an establishment that times out and a read that never converges, which points at the network, at the peer, or at the runtime — anywhere except at the missing declaration. This is written down because the symptom and the cause are nowhere near each other.

#### Scenario: A refused consent is reported as a refused consent
- **WHEN** the person declines local-network access and then tries to establish a connection
- **THEN** the shell reports that local-network access is not granted, and does not present the failure as an unreachable peer

#### Scenario: The declaration is present in what ships
- **WHEN** the installed application's declarations are inspected
- **THEN** the local-network usage declaration is among them, with text saying why the application needs it

### Requirement: Camera consent is declared and its refusal is legible
The application SHALL declare its use of the camera, and SHALL report a refusal as a refusal on the screen that needs it, offering the person the way to grant it.

The camera is the ceremony's channel between two devices. Without it there is no act to perform on the reading side, so the screen says that rather than showing a reader that never sees anything.

#### Scenario: A refused camera is reported on the reading screen
- **WHEN** camera access is refused and the person opens the code reader
- **THEN** the screen states that the camera is not available to the application and how to grant it

### Requirement: The node is brought up and stopped by acts of the person, and a suspension is neither
The shell SHALL bring the node up on an explicit act of the person, not as a side effect of the application becoming active, and SHALL stop it on an explicit act of the person. It SHALL NOT stop the node because the application is leaving the foreground. It SHALL present a termination as the node stopping rather than as the identities going away, and SHALL offer no act whose meaning depends on work in flight outliving the process.

Bring-up is an act because the surface's own bring-up is one, and because the same sequence then reads identically on either platform — the Android shell starts a service on that act, and a script that says "bring the node up" means the same tap on both.

A suspension does not destroy the endpoint. Nothing of a suspended process runs, so the node serves no peer while the application is away; what it does not need on the way back is a bring-up. This is observed rather than assumed: the application was suspended for 20 minutes while a peer wrote a new value to a granted claim, and on the return the node answered and the value was there, with no act of the person in between. Stopping the node as the application left the foreground would therefore trade a node that resumes for one that has to be raised again by hand, and would end a ceremony that a person had merely switched away from.

What the return does need is a read, and that belongs to the screens: a suspension stops the timer the periodic read runs on and the platform does not start it again ([screens](../mobile-common/screens.md)).

A terminated process is a node that stopped, not a node that never existed: what it held is in the directory it named at bring-up ([durable storage](../data-layer/durable-storage.md)), and it comes back on that directory as the same node ([restart recovery](../pdn-node/restart-recovery.md)). The shell does not fight the platform for background time it cannot use, and asks for none.

#### Scenario: Returning to a terminated application finds the node stopped, not emptied
- **WHEN** the system terminates the application and the person opens it again
- **THEN** the screen says the node is down and offers bringing it up, and a bring-up on the same directory reports the node id it had and the identities it hosted

#### Scenario: A suspension is survived without an act of the person
- **WHEN** the application is suspended while its node is up, a peer writes to a granted claim meanwhile, and the person returns
- **THEN** the node answers, the value the peer wrote is readable, and no bring-up was needed for either

#### Scenario: Leaving the foreground stops nothing
- **WHEN** the application leaves the foreground with its node up
- **THEN** the shell performs no stop, and the node is the same node on the return

#### Scenario: Becoming active does not bring a node up by itself
- **WHEN** the application becomes active with no node running
- **THEN** no node is brought up until the person performs the act, and the screen says the node is down

### Requirement: The shell builds for the device target and keeps the node's directory the only copy
The shell SHALL link the facade built for the physical device architecture, and SHALL name at bring-up a directory inside the application's own container, which the node writes its replicas, its payloads and its key into.

The shell SHALL exclude that directory from the platform's backup, so that what the screens state — that this device holds the only copy — is a fact of the device rather than a sentence in the interface. The container is carried into the person's cloud account by default, so a node's directory leaves the device unless the shell says otherwise, and an application about data staying where its owner put it would be the one moving it.

#### Scenario: The installed build runs on a device
- **WHEN** the application is installed on a physical device and opened
- **THEN** the node comes up on a directory inside its own container and reports its node id

#### Scenario: The node's directory is not carried into a backup
- **WHEN** the node's directory exists and the device is backed up
- **THEN** the directory is marked as excluded from backup, and no replica, payload or key of the node appears in the backup

### Requirement: The shell holds no protocol logic
The shell SHALL forward calls to the facade and translate its errors, and SHALL make no decision the runtime makes: it retries no ceremony, caches no grant, inspects no payload, and holds no rule about what a peer may read.

A decision taken here has no test that would catch it, since the shell sits between a tested surface and screens tested elsewhere. It is kept empty on purpose so that reading it is enough.

#### Scenario: A refusal passes through unchanged
- **WHEN** the facade reports a refusal
- **THEN** the shell delivers it to the screens with its kind intact, adding no retry and no substituted outcome
