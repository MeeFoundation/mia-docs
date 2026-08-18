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

### Requirement: The node is brought up by an act and lives while the application is in view
The shell SHALL bring the node up on an explicit act of the person, not as a side effect of the application becoming active, and SHALL stop it explicitly as the application leaves the foreground. It SHALL treat the loss of the process as the loss of every identity the node hosted: nothing is presented as retained across a termination, and no act is offered whose meaning depends on it.

Bring-up is an act because the surface's own bring-up is one, and because the same sequence then reads identically on either platform — the Android shell starts a service on that act, and a script that says "bring the node up" means the same tap on both.

The runtime holds replicas, payloads and its own key in memory, so a terminated process is a node that never existed. The shell does not fight the platform for background time it cannot use — a node that came back with no identities would be worse than a node the person knows they must keep in view.

#### Scenario: Returning to a terminated application starts fresh
- **WHEN** the system terminates the application and the person opens it again
- **THEN** the application hosts no identity and says so, rather than showing an empty list in place of the identities the previous process held

#### Scenario: Leaving stops the node deliberately
- **WHEN** the application is leaving the foreground
- **THEN** the shell stops the node through the surface's own stop, rather than letting the endpoint be torn down by termination

#### Scenario: Becoming active does not bring a node up by itself
- **WHEN** the application becomes active with no node running
- **THEN** no node is brought up until the person performs the act, and the screen says the node is down

### Requirement: The shell builds for the device target and touches no file
The shell SHALL link the facade built for the physical device architecture, and the node SHALL require no filesystem access: replicas and payloads are held in memory, so nothing is written to the application's container.

#### Scenario: The installed build runs on a device
- **WHEN** the application is installed on a physical device and opened
- **THEN** the node comes up and reports its node id, having created no store on disk

### Requirement: The shell holds no protocol logic
The shell SHALL forward calls to the facade and translate its errors, and SHALL make no decision the runtime makes: it retries no ceremony, caches no grant, inspects no payload, and holds no rule about what a peer may read.

A decision taken here has no test that would catch it, since the shell sits between a tested surface and screens tested elsewhere. It is kept empty on purpose so that reading it is enough.

#### Scenario: A refusal passes through unchanged
- **WHEN** the facade reports a refusal
- **THEN** the shell delivers it to the screens with its kind intact, adding no retry and no substituted outcome
