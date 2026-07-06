# data-layer: device linking (per identity, repeatable)

Linking keeps its single-seed shape and gains multi-identity semantics: the same node links into further identities by further explicit acts, one seed per identity, with no identity discovered through another.

## ADDED Requirements

### Requirement: An identity is provisioned on its first device
`provision_identity` SHALL bring an identity's store set up on its first device: it creates the connections store, publishes that store's ticket in a fresh private metadata store under the same directory key linking discovers it by, and registers the device in the device set. A seed obtained from the provisioned directory SHALL be sufficient for `link_device` on another node. Data namespaces are not provisioned here (their discovery at linking is deferred — ADR-0009).

#### Scenario: Provision, then link from the seed alone
- **WHEN** a node provisions an identity and its directory seed is handed to a second node, which links with it
- **THEN** the second node discovers and imports the connections store through the directory, with no ticket supplied out of band

#### Scenario: The first device is registered
- **WHEN** a node provisions an identity
- **THEN** that node's id is present in the device set of the provisioned directory

### Requirement: Linking into further identities is independent and repeatable
A node SHALL link into any number of identities by running the linking procedure once per identity with that identity's seed. Each linking act SHALL affect only the identity being linked: it SHALL NOT import stores of other identities, and it SHALL NOT expose one identity's seed or tickets through another identity's directory.

#### Scenario: Second identity links onto an already-linked node
- **WHEN** a node already linked into identity A runs the linking procedure with identity B's seed
- **THEN** identity B's private metadata store and connections store are imported and replicate, while identity A's stores continue operating unchanged

#### Scenario: Linking one identity brings nothing of another
- **WHEN** a node links into identity A while identity B's stores exist on the seed-issuing device
- **THEN** no store of identity B appears on the linking node
