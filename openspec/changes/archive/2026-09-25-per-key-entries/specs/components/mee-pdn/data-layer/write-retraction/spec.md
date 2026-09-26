## MODIFIED Requirements

### Requirement: The verdict replicates to sibling devices as a directory marker

The rejection reaches only the writer device that was in the session, so a sibling that holds the entry but has not itself reached the issuer would not learn of it; the verdict SHALL therefore also be recorded at `retractions/<issuer-hex>/<author-hex>/<path>`, with a bounding timestamp inside, in the private metadata store of the identity that holds the replica the entry was written into — the identity the verdict's author names, one author per identity. The replica belongs to that identity alone, so no device of another identity holds the entry, and a marker in a co-located identity's directory would address what that identity obtained under its own grant. Every device of the identity, on reading the marker, SHALL remove matching entries — that author, that path, timestamp at or below the bound — from its copy of the granted replica and SHALL refuse their re-ingest, so a retraction cannot flap back from a sibling that still holds the entry. That refusal SHALL be silent: the marker states what this identity already retracted, and the peer offering the entry is often the issuer itself, which kept it and is entitled to hold it. One live entry per author and path exists in a replica at a time, so the bound also covers a value rewritten while the marker travelled, and a newer own write dated above the bound is never matched. The marker is an accelerator and a durability aid, not the enforcement — a device that reaches the issuer with an entry of its own authorship earns its own rejection regardless. It is not backed up that way for a copy authored elsewhere: a rejection names one author, and a device honors only rejections naming an author it writes with, so the retention window has to outlast replication of the marker to the identity's own devices, and a session open across the retraction, which can hand the entry to a sibling after the marker was recorded. Markers SHALL carry the writing device's node id, the content hash, and the timestamp of what was retracted, as provenance for the event and a future recovery surface. A marker SHALL be dropped when its retention window (14 days) elapses — each device ages out the markers it recorded, judged by the marker entry's own timestamp — and when the granted namespace is forgotten, each device drops every marker it recorded for that issuer. A newer own write at that author and path is not matched by the marker, since the bound is the retracted entry's timestamp: writing again after a retraction is the way back, and the marker stays until it ages out. Dropping a marker SHALL take down the ingest refusal it armed: arming only ever widens, so a refusal that outlived its marker would go on answering for as long as the node runs, past the window that is supposed to bound it. Restoring write on the claim SHALL NOT drop the marker: a re-grant does not validate the old refused entry, and it removes the issuer-gate backstop, so the marker holds until it ages out.

#### Scenario: A sibling converges on the retraction

- **WHEN** one device retracts an entry and the marker replicates to a sibling still holding it
- **THEN** the sibling removes the entry too, and it reappears on neither device

#### Scenario: A marker never suppresses the issuer's entries

- **WHEN** a retraction marker exists for an own author at a path
- **THEN** the issuer's entries at that path — other authors — replicate unaffected

#### Scenario: The issuer's later write at a marked path is read

- **WHEN** the issuer narrows a claim to read-only, a racing own write is retracted and marked, and the issuer later writes that path itself
- **THEN** the issuer's newer value — its own author — reaches the audience and is read, unaffected by the live marker

#### Scenario: Restoring write does not drop the marker

- **WHEN** the issuer restores write on a claim that has a live retraction marker
- **THEN** the marker stands until the retention window elapses or the binding is forgotten — the re-grant alone drops nothing, and a newer own write at the path is admitted past it

#### Scenario: Markers age out and leave with the grant binding

- **WHEN** a marker's retention window elapses, or the granted namespace is forgotten
- **THEN** the marker is pruned from the directory, and the ingest refusal it armed stops refusing

#### Scenario: A co-located identity's directory carries no marker

- **WHEN** one hosted identity's write into a granted namespace is retracted while a co-located identity holds a grant of the same issuer
- **THEN** the marker is recorded in the writing identity's directory alone, and the co-located identity's directory and replica are unchanged
