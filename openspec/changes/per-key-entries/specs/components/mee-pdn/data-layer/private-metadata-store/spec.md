## MODIFIED Requirements

### Requirement: Retraction markers, granted issuer in the key

A write-retraction verdict SHALL be recorded as a directory entry at `retractions/<issuer-hex>/<author-hex>/<path>` — the granted data store's issuer, the retracted entry's author, and the retracted entry's path. The payload SHALL carry the bounding timestamp, the writing device's node id, and the retracted entry's content hash and timestamp; a marker acts once its payload is readable, since the bound lives in it. Markers replicate between the identity's devices like every directory entry, and only the identity's own devices ever write them (Invariant 1). A marker SHALL be pruned when its retention window elapses — each device drops the markers it recorded once their entries age past the window, and reports their addresses so the caller can disarm what they armed — or, when the issuer's namespace binding is forgotten, each device drops every marker it recorded for that issuer; a marker at one path SHALL leave the markers at every other path standing, a longer path beginning with the same bytes included; a bare re-grant of write SHALL NOT prune it, and a newer own write at the marked path is not matched by it. The consuming behaviour — removal, ingest refusal, the event — is [write retraction](../write-retraction/spec.md); this store carries the record.

#### Scenario: A marker round-trips between devices
- **WHEN** one device of the identity writes a retraction marker and a sibling's directory replica syncs
- **THEN** the sibling reads the marker with its bound, node id, content hash, and timestamp once the payload arrives

#### Scenario: Pruning follows the grant binding
- **WHEN** the granted namespace of an issuer with live markers is forgotten
- **THEN** the directory carries no markers for that issuer afterwards

#### Scenario: Aged markers are pruned by the device that recorded them
- **WHEN** a marker this device recorded is older than the retention window and another is younger
- **THEN** the aged one is dropped and its address reported, and the younger one stays

#### Scenario: A marker at a path leaves the markers at longer paths

- **WHEN** a device records a marker for an entry at `contact/email` and then one for an entry at `contact`, under the same issuer and author
- **THEN** both markers list, on that device and on a sibling once its directory replica syncs
