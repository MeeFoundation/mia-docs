## REMOVED Requirements

### Requirement: A removal is carried by the artefact it leaves

**Reason**: The store no longer deletes by prefix — an entry affects only its own key — so the requirement's prefix delete and its scenario describe nothing; the requirement returns under a new name, its prose and scenarios speaking of a delete at one key.
**Migration**: Replaced by "A removal travels as the artefact it leaves" in the same capability.

## ADDED Requirements

### Requirement: A removal travels as the artefact it leaves

Reconciliation converges over a drifting store because what one session misses the next one carries, and that holds for what a set gains: a later session offers an entry an earlier one did not have. It does not hold for what a set loses. A session serves rows that a removal took out after its setup, and the next session carries no news of the removal — only the absence of what was removed, which a peer already holding it cannot tell from a set it is ahead on. What carries a removal is therefore the artefact the removal leaves behind, and every removal SHALL leave one whose reach covers every peer the removed rows can reach. A delete leaves an empty entry at the deleted key, which replicates as any entry does; it replaces its author's older entry at that key and SHALL NOT be replaced in turn by an older entry at that key, whichever side of a session offers first, so a replica that still holds the deleted entry converges on the delete instead of handing the entry back. A retraction leaves a marker in the directory of the identity whose author wrote the retracted entry, which replicates to that identity's devices and arms them to remove the entry and refuse its re-ingest ([write retraction](../write-retraction/spec.md)). The reach that marker has to cover is bounded by what serves the replica: a granted replica is served only to devices of the grant's audience identity and to the issuer, so a retracted entry never reaches a grantee of another identity, whose devices the marker does not reach, and a co-located identity granted by the same issuer holds a replica of its own, which the entry never entered. A removal that would leave no such artefact SHALL instead end the open sessions of its namespace, because nothing else would converge on it. A frozen view therefore delays a removal by at most one session's lifetime and cannot lose it.

#### Scenario: A retraction inside a session is served for the rest of it

- **WHEN** a writer retracts its own refused entry while a session it serves is exchanging rounds
- **THEN** that session goes on serving the retracted entry, and the peer holds it until the retraction's marker reaches it and removes it

#### Scenario: A delete inside a session lands in two parts

- **WHEN** a node deletes an entry while a session it serves is exchanging rounds
- **THEN** that session serves the deleted entry and not the empty entry that deleted it, and the next session carries that empty entry, which deletes it at the peer

#### Scenario: A delete converges whichever side opens the session

- **WHEN** a replica deletes its author's entry at a key while another replica still holds that entry, and the deleting replica opens the next session between them
- **THEN** both replicas hold the delete after that session and after every later one, whichever side opens it
