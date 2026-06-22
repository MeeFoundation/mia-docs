# data-layer: device linking

The single-seed bootstrap procedure: a new device of an identity comes up from the private-metadata-store ticket alone, discovers the identity's other stores through that directory, and joins the device set.

## ADDED Requirements

### Requirement: A device links from a single seed
`link_device` SHALL bring a node up as a device of an identity given only the private-metadata-store ticket (the seed): it imports the private metadata store, then discovers the connections-store ticket from that store and imports the connections store. No store other than the private metadata store is provided out of band.

#### Scenario: Connections store discovered from the directory
- **WHEN** a node links with only the private-metadata-store seed of an identity whose directory holds a connections-store ticket
- **THEN** the node imports the connections store and converges on its contents, without that ticket being supplied out of band

### Requirement: A linked device registers itself
On linking, a device SHALL add its own node id to the private metadata store's device set.

#### Scenario: New device joins the set
- **WHEN** a device links to an identity
- **THEN** its node id appears in the identity's device set

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
