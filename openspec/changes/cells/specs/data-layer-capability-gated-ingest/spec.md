# data-layer: capability-gated ingest — delta for cells

## MODIFIED Requirements

### Requirement: Own devices and unarmed replicas are not narrowed

A session peer resolving as a device of the issuer SHALL be admitted in full. The gate SHALL arm on replicas data-bound to a hosted identity and on cell stores. On a hosted issuer's data replica it judges by the session peer's deposit, as above. On a cell store it judges by the entry's author key, resolved to a member through the cell's member device records, never by the session peer — a member device relays other members' entries, so the peer that sends an entry is not its author — admitting a claim from a device of its issuer and a document per its mode, and dropping every other entry silently, as the [cell store](../data-layer-cell-store/spec.md) states. One area is the exception: a device-list statement in the cell's membership device area is judged by the signature embedded in it, against the member's announcement key, with the entry's author ignored — the cell store states this verdict too. Directories and connection metadata stores keep ticket-bounded admission (Invariants 1 and 3), a grantee-held replica of a foreign namespace admits what the serving side's egress delivers, and an unregistered replica admits as it serves — whole, bounded by ticket possession. Retraction markers SHALL be consulted on data replicas only, the only replicas whose entries a marker can name, so no state of the marker set can reach the stores that carry device records and grants, nor a cell store.

#### Scenario: Device replication is unaffected

- **WHEN** two devices of the issuer's identity reconcile its data namespace
- **THEN** every entry replicates between them, exactly as without the gate

#### Scenario: A sibling relay of the read slice is not write-gated

- **WHEN** a device of the audience identity catches up a granted replica from a sibling device holding read-only claims
- **THEN** the read-slice entries arrive, although the relaying sibling holds no write on them

#### Scenario: A relayed cell-store entry is judged by its author

- **WHEN** a device of cell member C receives from a device of member B two entries under A's claims — one authored by a device of A, one authored by B's device
- **THEN** the first is admitted and the second is dropped silently, the session peer being B for both
