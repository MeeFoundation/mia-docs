# data-layer: node assembly — delta for cells

## ADDED Requirements

### Requirement: The node removes the payloads no replica it holds references

The node SHALL run blob collection over its one blob store at an interval `SpawnOptions` sets, with a single protect callback that answers with the union of the payloads every hosted identity's replicas reference, so that a payload SHALL stay while any replica of any identity the node hosts references it and SHALL leave the blob store at the first run after none does. A forgotten replica — a [cell](../../../../architecture/language/cell.md)'s record store, a data replica, the replica of a withdrawn grant — SHALL free its payloads with no removal of its own. A run SHALL be skipped while an identity the storage directory records is not hosted, so that a start removes nothing of an identity recovery has yet to reach.

**Example:** Carol leaves "Family" on her phone c1, which hosts Carol alone; the cell's record store held Bob's lease scan and a photo whose bytes Carol also keeps in her own data namespace.

| payload | referenced after the record store is forgotten by | on c1 after the next run |
|---|---|---|
| Bob's lease scan | nothing | removed |
| the photo | Carol's data namespace | kept |

#### Scenario: A payload no replica references is removed

- **WHEN** a node forgets the only replica whose entries reference a payload, and a collection run passes
- **THEN** the blob store no longer holds the payload

#### Scenario: A restart removes nothing before its identities are hosted again

- **WHEN** a node on a storage directory restarts, and collection runs pass before an identity the directory records is hosted again
- **THEN** the blob store still holds every payload that identity's replicas reference

#### Scenario: A payload a co-located identity references stays

- **WHEN** two identities hosted on one node hold replicas referencing one payload, one of them forgets its replica, and a collection run passes
- **THEN** the blob store still holds the payload, and the other identity reads it
