# data-layer: connection metadata store (delta)

Device-set publication in the directional stores — the resolution material for classifying a sync caller (subset-rbsr D9) — and the grant layout consolidated to one width-tagged record per issuer. The store's shape otherwise (one replica per direction, grants keyed by data-store issuer, Invariant 3 audience) is unchanged.

## MODIFIED Requirements

### Requirement: Grants are keyed by data-store issuer
A grant SHALL live as one record at `grants/<issuer-hex>` (64 lowercase hex chars of the granted data store's issuer `PdnId`), whose payload names its own width explicitly: the interim whole-store grant — the data store's ticket alone — or a capability-scoped grant carrying the capability and its ticket together. In one directional store at most one grant of one width SHALL exist per issuer at any moment: publishing either width replaces the record wholesale, and withdrawal SHALL be one tombstone over that one record — so no ordering of separate entries, locally or across replicating devices, can ever expose a wider grant than the last one published. A grant record that is absent, whose payload has not yet replicated, or whose payload a build cannot decode SHALL be treated as no grant — width is never inferred from absence or from partial state. The whole-store grant's ticket is a write ticket (the store's capability bounds swarm membership, not access — read and write are the capability mechanism's to state); a scoped grant's ticket mode follows its commands. Capability payloads inside the record SHALL be treated as opaque bytes at this layer.

#### Scenario: A grant round-trips
- **WHEN** the issuer publishes a grant carrying a data-store ticket and the counterparty reads it after sync
- **THEN** the ticket read equals the ticket published, keyed by the data store's issuer

#### Scenario: A grant published later needs no new pairing
- **WHEN** establishment completed earlier and the issuer publishes a new grant into `own`
- **THEN** the counterparty reads it from `peer` without any further pairing dialogue

#### Scenario: Publishing the other width replaces the record wholesale
- **WHEN** a scoped grant for an issuer is followed by a whole-store grant for the same issuer, or the reverse
- **THEN** the counterparty eventually reads exactly the later grant's width, and the earlier record is gone — no stale capability or ticket survives beside the new record to mask it

#### Scenario: Withdrawal is one act whatever the width
- **WHEN** the issuer withdraws the grant for an issuer
- **THEN** one tombstone removes it; the issuer's own book reads it as absent at once, the counterparty eventually reads no grant of either width, and at no intermediate state does either side read a grant wider than the last published record

## ADDED Requirements

### Requirement: Each side publishes its device set into its directional store

An identity SHALL publish the node ids of its devices as `devices/<node-id-hex>` records in every connection-metadata store it issues, with the directory's device-record semantics (marker payload, LWW, tombstone on revocation), and SHALL keep them current as devices are linked and revoked — so the counterparty can resolve a transport-authenticated node id to this identity. The identity is authoritative over its own device set; the records widen no access beyond what the connection already grants.

Publication on opening the pair SHALL be assert-once: a device asserts its record only when the set carries no record of it at all — a live record is left untouched, and a *withdrawn* record (tombstone) is never re-asserted as a side effect of opening. Re-asserting a withdrawn device is a deliberate publication act, distinct from opening. Without this, every pair opening would re-sign the record with a fresh wall-clock timestamp, and a revoked-but-still-running device would out-bid any tombstone the moment it next touched the connection. Revoking the *ability to write* is deferred, recorded in the design (subset-rbsr D9).

#### Scenario: Devices published at establishment

- **WHEN** a connection is established
- **THEN** each side's own store carries a `devices/<node-id-hex>` record for each of that identity's devices

#### Scenario: Linking propagates to every connection

- **WHEN** an identity links a new device
- **THEN** a `devices/<node-id-hex>` record for it appears in the own store of every connection of that identity, and the counterparty can then classify calls from that device

#### Scenario: A foreign device is not resolvable

- **WHEN** a node id appears in no connection's published device set and no directory of the serving node's identities
- **THEN** the serving node resolves it to no identity, and the caller is treated as a stranger

#### Scenario: Opening a pair does not resurrect a withdrawn device

- **WHEN** a device's record is withdrawn and that device — or any machinery on its node — opens the pair again
- **THEN** the record stays withdrawn; only a deliberate publication act re-asserts it
