# data-layer: ingest policies

Domain-level admission policies in `data-layer`: how the fork's validator callback (`Fn(&SignedEntry) -> bool`) is bridged into domain terms, and which policy decides. In this change the only policy is the device axiom — it inspects the resolved binding and reads no store. (Having a policy *read* the connections store to gate data is a deferred follow-up.)

## ADDED Requirements

### Requirement: Ingest context carries the resolved binding
The bridge SHALL resolve the entry's iroh namespace through the node's registry into a typed binding — `Data(NamespaceId)` for peer-visible `(about, issued_by)` namespaces, `Connections { owner }` for the device-shared connections store — and SHALL hand policies an ingest context carrying that binding (absent for unbound replicas). Resolution SHALL use only namespace→binding registry state, so it runs within the existing fork seam with no fork change.

#### Scenario: Bound data namespace resolves
- **WHEN** an entry arrives for an iroh namespace bound as a data namespace
- **THEN** the policy sees `Data(NamespaceId)` with the namespace's `(about, issued_by)` pair

#### Scenario: Bound connections store resolves
- **WHEN** an entry arrives for an iroh namespace bound as the connections store
- **THEN** the policy sees `Connections { owner }`

#### Scenario: Unbound replica resolves to no binding
- **WHEN** an entry arrives for an iroh namespace with no registry binding
- **THEN** the policy sees an absent binding

### Requirement: Device axiom admits own bindings without store reads
A policy (`SelfOwned`) SHALL admit entries of bindings owned by the local identity — `Connections { owner == me }`, and `Data(ns)` with `ns.issued_by == me` — without consulting any store, so that an identity's own state (its connections store, its own data namespaces) replicates between its devices and bootstraps against empty local state.

#### Scenario: Own connections store admitted on empty state
- **WHEN** entries of the local identity's connections store arrive while the local connections store holds no live connections
- **THEN** the entries are admitted and persisted

#### Scenario: Foreign binding is not admitted by the axiom
- **WHEN** an entry arrives whose binding is owned by a different identity
- **THEN** the device axiom does not admit it

### Requirement: Policies compose
Policies SHALL be composable such that an entry is admitted when any composed policy admits it (first-accept). The policy set provided in this change (the device axiom alone) SHALL reject entries of unbound replicas and of bindings not owned by the local identity.

#### Scenario: Unknown replica is rejected
- **WHEN** an entry arrives for a replica with no registry binding under the provided policy set
- **THEN** the entry is rejected and is absent from the store
