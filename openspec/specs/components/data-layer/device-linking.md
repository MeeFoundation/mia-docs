# Device linking

## Purpose

The single-seed bootstrap procedure and its first-device counterpart. The private metadata store this procedure reads — the directory — is specified as a store in [private-metadata-store.md](private-metadata-store.md); this spec covers the procedure. `provision_identity` brings an identity up from nothing on its first device: it creates the connections store, publishes its ticket into a fresh private-metadata directory, and registers the device. `link_device` brings a new device of an identity up from one ticket — the private-metadata-store seed (as carried in a QR): it imports that store (the directory), discovers and imports the identity's other stores (the connections store, later data) through tickets found in the directory, then registers the new device in the device set and stays in contact until the registration has demonstrably reached one of the identity's existing devices. The device set is bidirectional — the existing device sees the newcomer. Linking is per identity and repeatable: a node hosting several identities runs it once per identity. The seed is a bearer ticket; identity-bound, revocable linking arrives with UWill.

## Requirements
### Requirement: An identity is provisioned on its first device
`provision_identity` SHALL bring an identity's store set up on its first device: it creates the connections store, publishes that store's ticket in a fresh private metadata store under the same directory key linking discovers it by, and registers the device in the device set. A seed obtained from the provisioned directory SHALL be sufficient for `link_device` on another node. Data stores are not provisioned here (their discovery at linking is deferred — ADR-0009).

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

### Requirement: A device links from a single seed
`link_device` SHALL bring a node up as a device of an identity given only the private-metadata-store ticket (the seed): it imports the private metadata store, then discovers the connections-store ticket from that store and imports the connections store. No store other than the private metadata store is provided out of band.

#### Scenario: Connections store discovered from the directory
- **WHEN** a node links with only the private-metadata-store seed of an identity whose directory holds a connections-store ticket
- **THEN** the node imports the connections store and replicates its contents, without that ticket being supplied out of band

### Requirement: A linked device registers itself
On linking, a device SHALL add its own node id to the private metadata store's device set, after the directory catch-up (so the local write does not race the import's first sync). `link_device` SHALL NOT report success until the registration has reached at least one of the identity's existing devices: delivery counts as confirmed when a sync exchange of the directory that started after the registration write completes successfully — reconciliation exchanges both directions, so such an exchange necessarily carried the registration out. A registration that cannot be delivered within the linking timeout SHALL surface as an error, not a hang. Without this confirmation the registration rides on its one-shot gossip broadcast, which is lost when the gossip neighborhood is not yet up, and nothing else retriggers the exchange.

#### Scenario: New device joins the set
- **WHEN** a device links to an identity
- **THEN** its node id appears in the identity's device set

#### Scenario: Success implies the registration reached an existing device
- **WHEN** `link_device` returns success
- **THEN** a directory sync exchange that started after the registration write has completed successfully, and the identity's existing device observes the newcomer in its device set

### Requirement: The device set is bidirectional
A device added on one device of an identity SHALL become visible on the identity's other devices, since the private metadata store replicates between them.

#### Scenario: Existing device sees the newcomer
- **WHEN** a new device links and registers itself
- **THEN** the existing device's view of the device set eventually contains the new device, and the new device's view contains the existing device

### Requirement: Bootstrap is directory-first
A store other than the private metadata store SHALL be imported during linking only after its ticket has synced into the directory; the private metadata store is therefore brought up before any store discovered through it.

#### Scenario: Order is enforced by discovery
- **WHEN** linking imports a store discovered through the directory
- **THEN** that store's ticket was already present in the (synced) private metadata store
