# Delta: data-layer-subset-reconciliation

## MODIFIED Requirements

### Requirement: The filter runs in pdn-store on the read side

Filtering SHALL run at reconciliation time inside `pdn-store`, per peer, distinct from the ingest gate at the `validate_entry` hook. It SHALL consume the caller's effective rights as an opaque per-session predicate over entries, assembled above the fork — `pdn-store` SHALL know neither the grant format nor the identity vocabulary. The ingest gate consumes the same session classification through its own predicate ([capability-gated ingest](../data-layer-capability-gated-ingest/spec.md)): read on egress, write on ingest, independently.

#### Scenario: Read filter is independent of the ingest gate

- **WHEN** the egress filter runs on a node with the ingest validator installed
- **THEN** read filtering applies unchanged, and an entry refused at ingest neither widens nor narrows what egress reveals
