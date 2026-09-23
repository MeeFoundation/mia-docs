# data-layer: subset reconciliation — delta for cells

## MODIFIED Requirements

### Requirement: Same-identity reconciliation is unfiltered

Reconciliation between devices of the identity a replica belongs to SHALL deliver every claim of that replica — all are read-authorized by Invariant 1 — so the filter does not restrict an identity's own devices. A cell's two stores extend the same rule to every member: reconciliation between devices of the cell's members SHALL deliver every entry of either store, since a cell has no narrower audience than its members. On a multi-identity node this SHALL be judged per replica: a node is an own device for the replicas of the identities it is linked into, a member device for the stores of the cells those identities are members of, and a scoped peer elsewhere.

#### Scenario: Own devices replicate in full

- **WHEN** two devices of one identity reconcile a replica bound to that identity
- **THEN** all claims replicate, with no capability presented

#### Scenario: Being an own device is per replica, not per node

- **WHEN** a node linked into identity A but not identity B reconciles a replica of B under a capability covering one claim
- **THEN** the filter applies — only that claim is delivered — even though the node is fully authorized for A's replicas

#### Scenario: Member devices of a cell replicate in full

- **WHEN** a device of member A and a device of member B reconcile either store of a cell both are members of
- **THEN** every entry replicates, with no capability presented

### Requirement: Grantees stay outside the gossip swarm

A peer whose access arrived through a grant SHALL NOT be a member of the replica's gossip swarm. The swarm SHALL consist of the replica's device set: the issuer's own devices for a data store or a directory, the counterparty's devices too for a connection metadata store, and the devices of every member for each of a cell's stores — a cell has no grantees, its members are its whole audience, so member devices join the swarm as an identity's own devices do. A grantee's only data path is the reconciliation it initiates. This composes with the content-free topic above: membership conveys announcements, so removing a grantee from the swarm (rather than serving it filtered) keeps even activity metadata about unauthorized claims off its wire, and spares the relaying cost a broadcast presumes members share.

Membership SHALL follow the recorded sync strategy in both directions: a grantee import of a replica that had already joined the swarm — a device-replicated import downgraded to a grantee binding — SHALL leave the swarm as part of the import, not merely stop re-joining (the fork's leave-gossip operation: the topic subscription closes in both directions while the replica stays open, syncing, and subscribed to). A data import SHALL refuse a ticket naming a replica that is tracked but not data-bound (a directory, a connection metadata store, a cell's membership store or record store): repurposing a device-shared replica's tracking — and, with the downgrade now leaving the swarm, cutting its live path — must not be reachable on the word of whoever minted a ticket.

A grantee SHALL NOT mint a ticket on the replica, whether it holds it under a grant or imported it out of band. Minting restarts the replica's sync as a store of the minting identity's own: the replica rejoins the swarm, and every peer the engine recorded is dialed naming that identity instead of the issuer, which the issuer's devices refuse as not hosted.

#### Scenario: A scoped peer receives nothing over gossip

- **WHEN** a claim is written into a replica whose swarm is the issuer's devices, while scoped peers hold capabilities on other claims
- **THEN** no scoped peer receives the claim or any digest of it over gossip, and the issuer's devices receive the claim itself

#### Scenario: A grantee receives entries by reconciliation only

- **WHEN** the issuer writes after a peer imported the replica's ticket, past the window in which a swarm would have formed
- **THEN** a granted peer receives the write, filtered to its granted claims, over its next classified reconciliation, and a bare-ticket holder with no recorded grant receives nothing — the write never arrives over gossip

#### Scenario: A swarm member is served only while authorized

- **WHEN** a peer that is a swarm member of a replica holds a grant, converges on a write, then has the grant withdrawn and the issuer writes again
- **THEN** the post-withdrawal write never reaches it although it is still a swarm member — content follows the access book, not swarm membership, and what was delivered while granted is retained

#### Scenario: A device-shared replica refuses a data import

- **WHEN** a data import — device or grantee — is handed a ticket naming a replica that this node tracks as a directory, a connection metadata store or one of a cell's stores
- **THEN** the import is refused, and the device-shared replica's tracking, swarm membership, and live path are untouched

#### Scenario: Member devices of a cell form its swarm

- **WHEN** a member writes into a cell's record store while devices of the other members are subscribed to its topic
- **THEN** those devices converge on the entry through the content-free announcement and the pull it triggers, none of them holding a grant

## REMOVED Requirements

### Requirement: A removal is carried by the artefact it leaves

**Reason**: The store no longer deletes by prefix — an entry affects only its own key (cells D24) — so the requirement's prefix delete and its scenario describe nothing; the requirement returns under a new name, its prose and scenario speaking of a delete at one key.
**Migration**: Replaced by "A removal travels as the artefact it leaves" in the same capability.

## ADDED Requirements

### Requirement: A removal travels as the artefact it leaves

Reconciliation converges over a drifting store because what one session misses the next one carries, and that holds for what a set gains: a later session offers an entry an earlier one did not have. It does not hold for what a set loses. A session serves rows that a removal took out after its setup, and the next session carries no news of the removal — only the absence of what was removed, which a peer already holding it cannot tell from a set it is ahead on. What carries a removal is therefore the artefact the removal leaves behind, and every removal SHALL leave one whose reach covers every peer the removed rows can reach. A delete leaves an empty entry at the deleted key, which replicates as any entry does; a cell's record store removes the whole record where its tombstone lands. A retraction leaves a marker in the directory of every hosted identity granted by that issuer, which replicates to that identity's devices and arms them to remove the entry and refuse its re-ingest ([write retraction](../write-retraction/spec.md)). The reach that marker has to cover is bounded by what serves the replica: a granted replica is served only to devices of the grant's audience identity and to the issuer, so a retracted entry never reaches a grantee of another identity, whose devices the marker does not reach. A removal that would leave no such artefact SHALL instead end the open sessions of its namespace, because nothing else would converge on it. A frozen view therefore delays a removal by at most one session's lifetime and cannot lose it.

#### Scenario: A retraction inside a session is served for the rest of it

- **WHEN** a writer retracts its own refused entry while a session it serves is exchanging rounds
- **THEN** that session goes on serving the retracted entry, and the peer holds it until the retraction's marker reaches it and removes it

#### Scenario: A delete inside a session lands in two parts

- **WHEN** a node deletes an entry while a session it serves is exchanging rounds
- **THEN** that session serves the deleted entry and not the empty entry that deleted it, and the next session carries that empty entry, which deletes it at the peer
