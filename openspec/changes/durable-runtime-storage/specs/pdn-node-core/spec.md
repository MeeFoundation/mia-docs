## ADDED Requirements

### Requirement: Production runtime startup restores a durable profile

The production runtime constructor SHALL require an explicit durable profile directory and SHALL complete data-layer profile recovery before publishing service handles or accepting host requests. The sync status after startup SHALL report the restored `NodeId` and all identities whose store sets have committed catalog records. The runtime SHALL expose in-memory construction only through an explicitly named test/development path.

#### Scenario: A host sees restored identities before serving

- **WHEN** a runtime hosting 2 identities shuts down and a new runtime process starts from the same profile
- **THEN** its first admitted sync-status call reports the prior `NodeId` and exactly those 2 hosted identities

#### Scenario: Recovery failure prevents host admission

- **WHEN** the data-layer profile cannot restore one committed hosted identity or binding
- **THEN** runtime startup fails and no identity, connection, data, sync, pairing, or linking operation is admitted

#### Scenario: In-process tests request memory by name

- **WHEN** an in-process test embeds several runtimes through the explicit in-memory constructor
- **THEN** each runtime operates independently without a profile directory and none claims restart persistence

### Requirement: Runtime shutdown propagates storage failure

The runtime shutdown operation SHALL wait for the data-layer durable shutdown and SHALL return any catalog, document, blob, or profile-close failure to its caller. A host SHALL be able to distinguish successful durable shutdown from termination with unflushed state without parsing logs.

#### Scenario: Host receives a flush error

- **WHEN** a durable backend reports an error while the runtime shuts down
- **THEN** the runtime shutdown result is an error carrying the storage failure category
