# android-app: shell

The Android shell is the thin layer between the generated Kotlin bindings and the shared screens. It forwards calls, translates errors, and owns the three things the platform decides for it: how long the process is allowed to live, what reaching the local network requires at the platform level it targets, and consent to use the camera. What the application does with the runtime belongs to [host-surface](../mobile-common/host-surface.md), and what the screens must do belongs to [screens](../mobile-common/screens.md).

## ADDED Requirements

### Requirement: The node runs in a foreground service with a visible notification
While a node is up, the application SHALL run it inside a foreground service whose notification is visible to the person, and the service SHALL be started as the node comes up and stopped as it goes down.

Every identity, device record, connection and entry lives in the process, and a backgrounded process is terminated at the system's discretion. A node without a foreground service therefore loses its identities at a moment nobody chose, in the middle of whatever the person was doing.

#### Scenario: The node survives the screen going elsewhere
- **WHEN** the person leaves the application for another one and returns
- **THEN** the node is the same node, the hosted identities are the same identities, and the notification was visible throughout

#### Scenario: The notification says what is running
- **WHEN** the service is running
- **THEN** its notification states that the node is up and how many identities it hosts, so the person can tell the running state from the stopped one without opening the application

#### Scenario: Stopping the service is stated as losing the state
- **WHEN** the person stops the service
- **THEN** the application states that the identities it hosted are gone, and does not present them as recoverable

### Requirement: Local-network reachability is declared as the target platform level requires
The application SHALL declare whatever the platform level it targets requires in order to exchange traffic with peers in the local network, and SHALL surface a refusal of that access as itself rather than as an unreachable peer.

Plain sockets to the local subnet need no consent on the platform levels in wide use, and newer levels introduce a gate of their own. The requirement is that the declaration match the target level, established by checking that level rather than assumed in either direction — an application that assumed the permissive case would fail silently on a newer device, which is the same failure the iOS shell's declaration exists to prevent.

#### Scenario: A refused access is reported as refused access
- **WHEN** the platform level in use gates local-network traffic and that access is not granted
- **THEN** the shell reports the missing access, and does not present the failure as a peer that never answered

#### Scenario: The target level's requirement is established, not assumed
- **WHEN** the target platform level is chosen or raised
- **THEN** what it requires for local-network traffic is checked on a device running that level, and the declarations follow from the answer

### Requirement: Camera consent is requested and its refusal is legible
The application SHALL request camera access when the code reader is first opened, and SHALL report a refusal as a refusal on that screen, offering the person the way to grant it.

#### Scenario: A refused camera is reported on the reading screen
- **WHEN** camera access is refused and the person opens the code reader
- **THEN** the screen states that the camera is not available to the application and how to grant it

### Requirement: The shell builds for the device architectures and touches no file
The shell SHALL package the facade's shared library for the architectures of the devices in use, and the node SHALL require no filesystem access: replicas and payloads are held in memory, so nothing is written to the application's storage.

#### Scenario: The installed build runs on a device
- **WHEN** the application is installed on a physical device and opened
- **THEN** the node comes up and reports its node id, having created no store on disk

### Requirement: The shell holds no protocol logic
The shell SHALL forward calls to the facade and translate its errors, and SHALL make no decision the runtime makes: it retries no ceremony, caches no grant, inspects no payload, and holds no rule about what a peer may read.

A decision taken here has no test that would catch it, since the shell sits between a tested surface and screens tested elsewhere. It is kept empty on purpose so that reading it is enough.

#### Scenario: A refusal passes through unchanged
- **WHEN** the facade reports a refusal
- **THEN** the shell delivers it to the screens with its kind intact, adding no retry and no substituted outcome
