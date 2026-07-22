# Delta: data-layer-connection-metadata-store

## MODIFIED Requirements

### Requirement: Grants are keyed by data-store issuer
A grant SHALL live as one record at `grants/<issuer-hex>` (64 lowercase hex chars of the granted data store's issuer `PdnId`), carrying a capability scoped to an exact claim set together with the data store's ticket. Every grant is capability-scoped: there is no grant that conveys a whole store without naming its claims. In one directional store at most one grant SHALL exist per issuer at any moment: publishing replaces the record wholesale, and withdrawal SHALL be one tombstone over that one record — so no ordering of separate entries, locally or across replicating devices, can ever expose a grant other than the last one published. A grant record that is absent, whose payload has not yet replicated, or whose payload a build cannot decode SHALL be treated as no grant — never inferred from absence or from partial state. The ticket's mode follows the grant's commands: a read-only grant ships a read ticket (no namespace secret, so the grantee cannot write at all), a grant carrying write ships a write ticket. The capability's own `issuer` and `audience` bind the grant to its subject: the serving side SHALL honor a record only for the identity its capability names as audience, never on the record's position alone. Capability payloads inside the record SHALL otherwise be treated as opaque bytes at this layer.

#### Scenario: A grant round-trips
- **WHEN** the issuer publishes a grant carrying a data-store ticket and the counterparty reads it after sync
- **THEN** the ticket and capability read equal those published, keyed by the data store's issuer

#### Scenario: A grant published later needs no new pairing
- **WHEN** establishment completed earlier and the issuer publishes a new grant into `own`
- **THEN** the counterparty reads it from `peer` without any further pairing dialogue

#### Scenario: Republishing replaces the record wholesale
- **WHEN** a grant for an issuer is followed by another grant for the same issuer, on a different claim set or ticket
- **THEN** the counterparty eventually reads exactly the later grant, and the earlier record is gone — no stale capability or ticket survives beside the new record to mask it

#### Scenario: Withdrawal is one act
- **WHEN** the issuer withdraws the grant for an issuer
- **THEN** one tombstone removes it; the issuer's own book reads it as absent at once, the counterparty eventually reads no grant, and at no intermediate state does either side read a grant other than the last published record

#### Scenario: A record addressed to another identity authorizes no one
- **WHEN** a grant record sits in the directional store toward one counterparty but its capability names a different identity as audience
- **THEN** the serving side treats it as no grant for the counterparty the store is toward — position never substitutes for the capability's named audience
