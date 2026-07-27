# Delta: data-layer-private-metadata-store

## ADDED Requirements

### Requirement: Retraction markers, granted issuer in the key

A write-retraction verdict SHALL be recorded as a directory entry at `retractions/<issuer-hex>/<author-hex>/<path>` — the granted data store's issuer, the retracted entry's author, and the retracted entry's path. The payload SHALL carry the bounding timestamp, the writing device's node id, and the retracted entry's content hash and timestamp; a marker acts once its payload is readable, since the bound lives in it. Markers replicate between the identity's devices like every directory entry, and only the identity's own devices ever write them (Invariant 1). A marker SHALL be pruned when the entry it addresses can no longer win — superseded by a newer own entry at that author and path, or aged out by a retention window — or in bulk when the issuer's namespace binding is forgotten; a bare re-grant of write SHALL NOT prune it. The consuming behaviour — removal, ingest refusal, the event — is [write retraction](../data-layer-write-retraction/spec.md); this store carries the record.

#### Scenario: A marker round-trips between devices

- **WHEN** one device of the identity writes a retraction marker and a sibling's directory replica syncs
- **THEN** the sibling reads the marker with its bound, node id, content hash, and timestamp once the payload arrives

#### Scenario: Pruning follows the grant binding

- **WHEN** the granted namespace of an issuer with live markers is forgotten
- **THEN** the directory carries no markers for that issuer afterwards
