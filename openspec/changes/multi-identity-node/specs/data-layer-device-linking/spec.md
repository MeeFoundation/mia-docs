# data-layer: device linking (per identity, repeatable)

Linking keeps its single-seed shape and gains multi-identity semantics: the same node links into further identities by further explicit acts, one seed per identity, with no identity discovered through another.

## ADDED Requirements

### Requirement: Linking into further identities is independent and repeatable
A node SHALL link into any number of identities by running the linking procedure once per identity with that identity's seed. Each linking act SHALL affect only the identity being linked: it SHALL NOT import stores of other identities, and it SHALL NOT expose one identity's seed or tickets through another identity's directory.

#### Scenario: Second identity links onto an already-linked node
- **WHEN** a node already linked into identity A runs the linking procedure with identity B's seed
- **THEN** identity B's private metadata store and connections store are imported and replicate, while identity A's stores continue operating unchanged

#### Scenario: Linking one identity brings nothing of another
- **WHEN** a node links into identity A while identity B's stores exist on the seed-issuing device
- **THEN** no store of identity B appears on the linking node
