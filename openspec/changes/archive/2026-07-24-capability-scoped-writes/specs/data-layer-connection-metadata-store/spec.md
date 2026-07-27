# Delta: data-layer-connection-metadata-store

## MODIFIED Requirements

### Requirement: Grants are keyed by data-store issuer

A grant SHALL live as one record at `grants/<issuer-hex>` (64 lowercase hex chars of the granted data store's issuer `PdnId`), carrying a capability scoped to an exact claim set — naming, per claim, whether write is granted alongside read — together with the data store's ticket. Every grant is capability-scoped: there is no grant that conveys a whole store without naming its claims. In one directional store at most one grant SHALL exist per issuer at any moment: publishing replaces the record wholesale, and withdrawal SHALL be one tombstone over that one record — so no ordering of separate entries, locally or across replicating devices, can ever expose a grant other than the last one published, and mixed rights can never be observed half-withdrawn. A grant record that is absent, whose payload has not yet replicated, or whose payload a build cannot decode SHALL be treated as no grant — never inferred from absence or from partial state. The reading side SHALL nevertheless be able to tell a decided absence — no record at all, or a record granting someone else — from a record whose content is simply not readable yet, because a caller deciding whether it may *write* needs opposite answers for the two, and one of them is a window a republication opens routinely. The ticket's mode follows the record as a whole: a grant carrying no write on any claim ships a read ticket (no namespace secret, so the grantee cannot write at all), a grant carrying write on any claim ships a write ticket. The capability's own `issuer` and `audience` bind the grant to its subject: a record SHALL be honored only over the data of the issuer and toward the audience its capability names, never on the record's position alone. This binds both sides — the serving side classifying a caller, and the audience side reading what was granted to it. On the reading side position is least sound of all: the counterparty writes this store, so the key a record sits under is the counterparty's word too, and a record read on its key alone would let one counterparty direct this node's handling of a third identity's data. Capability payloads inside the record SHALL otherwise be treated as opaque bytes at this layer.

#### Scenario: A grant round-trips

- **WHEN** the issuer publishes a grant carrying a data-store ticket and the counterparty reads it after sync
- **THEN** the ticket and capability read equal those published, keyed by the data store's issuer

#### Scenario: A grant published later needs no new pairing

- **WHEN** establishment completed earlier and the issuer publishes a new grant into `own`
- **THEN** the counterparty reads it from `peer` without any further pairing dialogue

#### Scenario: Republishing replaces the record wholesale

- **WHEN** a grant for an issuer is followed by another grant for the same issuer, on a different claim set, different per-claim commands, or a different ticket
- **THEN** the counterparty eventually reads exactly the later grant, and the earlier record is gone — no stale capability or ticket survives beside the new record to mask it

#### Scenario: Withdrawal is one act

- **WHEN** the issuer withdraws the grant for an issuer
- **THEN** one tombstone removes it — read and write rights together; the issuer's own book reads it as absent at once, the counterparty eventually reads no grant, and at no intermediate state does either side read a grant other than the last published record

#### Scenario: A record addressed to another identity authorizes no one

- **WHEN** a grant record sits in the directional store toward one counterparty but its capability names a different identity as audience
- **THEN** the serving side treats it as no grant for the counterparty the store is toward — position never substitutes for the capability's named audience

#### Scenario: A record whose capability names another issuer grants nothing to its reader

- **WHEN** a counterparty writes a record at the key of a third identity's data store, with a capability naming that third identity as issuer
- **THEN** the reading side treats it as no grant, and nothing about that third identity's data is acted on

#### Scenario: A record whose content has not arrived is not an absence

- **WHEN** a grant record is present but the payload naming its claims has not replicated yet
- **THEN** the reading side reports it as not yet readable rather than as no grant, so a caller that must not guess can wait instead of concluding
