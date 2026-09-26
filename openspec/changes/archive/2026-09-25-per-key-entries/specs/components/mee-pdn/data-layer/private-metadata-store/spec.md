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

### Requirement: The replica reports its namespace and waits for a sync session
The directory SHALL expose the namespace of its replica, so a caller that imported it can name it to forget it, and SHALL offer a bounded wait for the first successful sync session of that replica which started after a given instant. The property waited on is "this replica has caught up with a peer" — a session that started and succeeded — not "some content arrived": polling contents cannot distinguish a replica that synced and found nothing new from one that never synced at all. A wait that elapses SHALL surface as a timeout, never as a hang. Importing a replica enrols it in the node's periodic reconcile pass with the ticket's contacts, and hosting the identity on it starts its first session ([identity-scoped replicas](../identity-scoped-replicas/spec.md)), so the wait needs no trigger of its own and a first exchange that fails is re-dialed within the wait's own budget. The wait watches the replica's events, and a watch left unread past its buffer drops them ([change subscription](../change-subscription/spec.md)): a session whose event it dropped goes unseen, and the wait then returns on the next session, one reconcile interval later at most.

#### Scenario: The wait returns on a successful session, not on content
- **WHEN** a directory replica is imported and a sync session with a peer holding it starts after the given instant and completes successfully
- **THEN** the wait returns; it would not have returned for a session that started before that instant, nor for one that failed

#### Scenario: A replica that cannot reach a peer times out
- **WHEN** no successful sync session of the replica starts after the given instant within the bound
- **THEN** the wait fails with a timeout, and the caller can tell it apart from a successful catch-up
