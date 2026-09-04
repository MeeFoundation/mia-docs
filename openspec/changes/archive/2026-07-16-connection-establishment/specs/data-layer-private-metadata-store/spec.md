# Private metadata store: the metadata pair's tickets; routing kept apart from grants

The directory gains the per-connection kinds establishment publishes — how a connection made on one device reaches the identity's other devices — and a boundary: tickets to another identity's data stores never live here, only inside [connection metadata stores](connection-metadata-store.md), so a withdrawn grant is never outlived by a stale copy.

## MODIFIED Requirements

### Requirement: Typed tickets, kind in the key
The ticket for a store of kind `k` SHALL be stored at path `tickets/<k>`, with the serialized ticket as the payload. Kinds are an open set of names; `connections` is the kind device linking discovers (see [device-linking.md](../pdn-node/device-linking.md)). A connection's metadata pair is published under per-connection kinds keyed by the counterparty's `PdnId` (64 lowercase hex chars): the write ticket to the identity's own store toward peer `P` at kind `connection-metadata/<P-hex>/own`, and the received read ticket to the counterpart's store at kind `connection-metadata/<P-hex>/peer` — this is how establishment performed on one device reaches the identity's other devices, which open the pair from these tickets on demand.

#### Scenario: A published ticket round-trips
- **WHEN** a ticket is published under a kind on one device and read on another after replication
- **THEN** the ticket read equals the ticket published

#### Scenario: The pair's tickets are discoverable on a linked device
- **WHEN** establishment publishes the `own` and `peer` kinds for a counterparty on the phone, and a laptop is linked into the identity
- **THEN** the laptop reads both tickets from its directory replica after replication, keyed by that counterparty

## ADDED Requirements

### Requirement: The directory routes; grants live in connection metadata stores
The directory carries the identity's own infrastructure — its device set and the tickets to its own stores and to its connections' metadata pairs. It SHALL NOT hold tickets to another identity's data stores: those travel only inside connection metadata stores, where the granting side can withdraw them, so no copy in a directory outlives the grant.

#### Scenario: No counterparty data ticket in the directory
- **WHEN** establishment and a data-grant exchange with a peer complete
- **THEN** the receiving identity's directory contains the metadata-pair kinds for that peer and no ticket to the peer's data namespace — the data-store ticket is read from the metadata store
