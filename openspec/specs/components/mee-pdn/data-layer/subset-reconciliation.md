# Subset reconciliation

## Purpose

Capability-filtered reconciliation — "subset-RBSR" — the read-side counterpart of the ADR-0008 ingest hook, enforcing Invariant 2: a serving node reveals only the claims the receiving peer is read-authorized for. The grant vocabulary the filter consumes is the [read capabilities](read-capabilities.md) mechanism.

## Requirements

### Requirement: Reconciliation reveals only read-authorized claims

During reconciliation with a peer, a serving node SHALL compute range fingerprints, split boundaries, offers, and item transmissions over only the claims the peer is read-authorized for. A claim the peer is not authorized for SHALL NOT be fingerprinted, offered, or sent.

#### Scenario: Only the authorized subset is delivered

- **WHEN** an issuer holds claims c1, c2, c3 and a peer is authorized for c1, c2
- **THEN** the peer receives c1 and c2, and c3 is never transmitted

### Requirement: Withheld claims are hidden, not merely undelivered

The reconciliation transcript a peer observes SHALL depend only on the claims it is authorized for, so the existence of unauthorized claims is not revealed — no fingerprint or split boundary derived from them reaches the peer.

#### Scenario: Existence of an unauthorized claim is hidden

- **WHEN** an unauthorized claim c3 lies between authorized claims c2 and c4 in key order
- **THEN** the peer's session is indistinguishable from one in which c3 does not exist

### Requirement: The filter runs in pdn-store on the read side

Filtering SHALL run at reconciliation time inside `pdn-store`, per peer, distinct from the ingest gate at the `validate_entry` hook. It SHALL consume the caller's effective rights as an opaque per-session predicate over entries, assembled above the fork — `pdn-store` SHALL know neither the grant format nor the identity vocabulary. The ingest gate consumes the same session classification through its own predicate ([capability-gated ingest](capability-gated-ingest.md)): read on egress, write on ingest, independently.

#### Scenario: Read filter is independent of the ingest gate

- **WHEN** the egress filter runs on a node with the ingest validator installed
- **THEN** read filtering applies unchanged, and an entry refused at ingest neither widens nor narrows what egress reveals

### Requirement: Same-identity reconciliation is unfiltered

Reconciliation between devices of the identity a replica belongs to SHALL deliver every claim of that replica — all are read-authorized by Invariant 1 — so the filter does not restrict an identity's own devices. On a multi-identity node this SHALL be judged per replica: a node is an own device for the replicas of the identities it is linked into, and a scoped peer elsewhere.

#### Scenario: Own devices replicate in full

- **WHEN** two devices of one identity reconcile a replica bound to that identity
- **THEN** all claims replicate, with no capability presented

#### Scenario: Being an own device is per replica, not per node

- **WHEN** a node linked into identity A but not identity B reconciles a replica of B under a capability covering one claim
- **THEN** the filter applies — only that claim is delivered — even though the node is fully authorized for A's replicas

### Requirement: Delivery is gated before transfer

A claim SHALL be filtered out before transmission, never retracted after — Invariant 2 governs acquisition, not retention.

#### Scenario: An unauthorized claim never leaves the server

- **WHEN** a peer is not authorized for claim c3
- **THEN** c3 is absent from every message the server sends, at no point transmitted and then recalled

### Requirement: The caller's rights are resolved once, at session setup

A serving node SHALL resolve the caller's read rights when a reconciliation session is set up, and that resolution SHALL govern the session for its whole lifetime. A grant widened, narrowed, or withdrawn while a session is under way SHALL NOT change what that session serves — it governs the sessions set up after it. The ingest gate resolves the same records at the same moment ([capability-gated ingest](capability-gated-ingest.md)), so the read and write halves of one session's decisions rest on one state. The bound this places on revocation is the point rather than a side effect: a withdrawal takes effect from the next session, and what the peer obtained while it was granted stays with it — Invariant 2 governs acquisition, not retention.

#### Scenario: A withdrawn grant refuses the next session and keeps delivered data

- **WHEN** an issuer withdraws a peer's grant and afterwards writes the withdrawn claim again
- **THEN** the peer's later sessions carry nothing of that write, while the value it obtained before the withdrawal stays readable to it

#### Scenario: A rights change does not reach a session already under way

- **WHEN** a grant is narrowed while a session over that replica is still exchanging rounds
- **THEN** that session goes on serving what it was set up to serve, and the narrowing governs the next session

### Requirement: A session serves a view frozen at session setup

A node SHALL serve one reconciliation session from a store snapshot taken at session setup: every fingerprint, split boundary, offer, and item the session derives SHALL reflect the store as of that moment, so a write landing mid-session neither shifts the served view between rounds nor reaches the peer within the session — it travels on the next one. What one view buys is consistency inside a session, not a prerequisite of reconciliation: the engine converges over a drifting store too, because reconciliation is anti-entropy and what one session misses the next one carries — for as long as a session can finish, which the bound below qualifies, and for what the set gains rather than what it loses, which the requirement on removals below states. It buys agreement among the things a single session derives — a fingerprint and the items behind it describe the same claims, and a split boundary still partitions the set it was computed over when a later round returns to it — and it puts the data half of the session's decisions on the footing the rights half already stands on, since the caller's rights are resolved at session setup and hold for the session's lifetime. Opening the snapshot SHALL first commit the store's pending write batch, so every entry inserted before session setup is in the snapshot. Ingest SHALL stay on the live store: an entry the peer sends is judged against current state, so an older remote entry never overwrites a newer local write the snapshot predates. The check behind a rejection — whether the replica would newly store the refused entry — reads the live store for the same reason and a graver one: a rejection makes its sender destroy its own copy, so judged against the frozen view it would name an entry the replica took in after session setup and cost the sender data both sides hold ([capability-gated ingest](capability-gated-ingest.md)). The snapshot SHALL be released when the session ends, on every exit path — completion, refusal, failure, and cancellation alike — and a session that neither completes nor fails is ended by the bound below, so no snapshot outlives its session and no session runs without end.

#### Scenario: A mid-session write travels on the next session

- **WHEN** a node writes a claim after a session's setup, while the session is still exchanging rounds
- **THEN** the session delivers the pre-setup claims only, and the next session delivers the new claim

#### Scenario: An older remote entry loses to a newer mid-session write

- **WHEN** a session's snapshot predates a newer local write to a key, and the peer transmits an older entry for that key
- **THEN** the older entry is not inserted — the ingest comparison reads the live store, not the frozen view

#### Scenario: An entry landing after session setup draws no rejection

- **WHEN** an entry reaches a replica after a session's setup — so the frozen egress hides it and the sender re-offers it — and the gate refuses that sender
- **THEN** the reply carries no rejection for that entry, because the gate reads the live store, where the replica holds it

#### Scenario: A session's snapshot is released on every exit path

- **WHEN** a session ends — completed, refused, failed, or cancelled
- **THEN** its snapshot is released; a refused request opens none on the node that refused it, while the node that asked releases the one it opened before asking

### Requirement: A removal is carried by the artefact it leaves

Reconciliation converges over a drifting store because what one session misses the next one carries, and that holds for what a set gains: a later session offers an entry an earlier one did not have. It does not hold for what a set loses. A session serves rows that a removal took out after its setup, and the next session carries no news of the removal — only the absence of what was removed, which a peer already holding it cannot tell from a set it is ahead on. What carries a removal is therefore the artefact the removal leaves behind, and every removal SHALL leave one whose reach covers every peer the removed rows can reach. A prefix delete leaves an empty entry, which replicates as any entry does. A retraction leaves a marker in the directory of every hosted identity granted by that issuer, which replicates to that identity's devices and arms them to remove the entry and refuse its re-ingest ([write retraction](write-retraction.md)). The reach that marker has to cover is bounded by what serves the replica: a granted replica is served only to devices of the grant's audience identity and to the issuer, so a retracted entry never reaches a grantee of another identity, whose devices the marker does not reach. A removal that would leave no such artefact SHALL instead end the open sessions of its namespace, because nothing else would converge on it. A frozen view therefore delays a removal by at most one session's lifetime and cannot lose it.

#### Scenario: A retraction inside a session is served for the rest of it

- **WHEN** a writer retracts its own refused entry while a session it serves is exchanging rounds
- **THEN** that session goes on serving the retracted entry, and the peer holds it until the retraction's marker reaches it and removes it

#### Scenario: A prefix delete inside a session lands in two parts

- **WHEN** a node deletes a prefix while a session it serves is exchanging rounds
- **THEN** that session serves the deleted entries and not the empty entry that deleted them, and the next session carries that empty entry, which deletes them at the peer

### Requirement: A session is bounded in time

A reconciliation session SHALL be bounded as a whole, and a session reaching that bound SHALL be ended rather than left running. Two things rest on the bound. A node runs one exchange per replica and peer and starts no other while one runs, so a session that never ends stops that pair from reconciling at all. And a session holds a store snapshot, whose read transaction holds back reclamation of every page freed while it lives, so the same bound is what bounds that. Bounding the wait between messages instead would bound neither, since a peer sending one message every few seconds keeps both for as long as it likes. A connection that goes dead rather than quiet is cut by the transport well inside the bound, so the bound is what answers for a peer that stays reachable and stops making progress.

A session cut short at the bound loses what it had not delivered, not what it had: entries already ingested are stored, and later sessions carry the rest. That holds while a session delivers something. It does not hold for a set whose transfer cannot finish inside the bound, because a message is ingested whole or not at all and a node holding nothing of a replica receives the served set as a single message: a cut then delivers nothing, the next session starts over, and reconciliation does not converge at all rather than converging slowly. Raising the bound moves that threshold rather than removing it; removing it wants a limit on the size of a transmitted set, which this layer does not yet impose.

#### Scenario: A stalled session is ended and its pair reconciles again

- **WHEN** a peer holds a session open without carrying it to completion
- **THEN** the session is ended at the bound, its snapshot is released, and that pair reconciles again on a later trigger

#### Scenario: A session cut short keeps what it delivered

- **WHEN** a session ends at the bound after delivering part of what it owed
- **THEN** the delivered entries are stored, and later sessions carry the rest

### Requirement: The gossip topic carries no content

A replica's gossip topic SHALL carry only content-free announcements, never entries. A local insert SHALL broadcast a content-free author-head digest (a sync report) to neighbors; the entry itself SHALL NOT be broadcast, and an entry received over gossip SHALL be dropped, never inserted. Content SHALL flow only over the classified reconciliation an announcement triggers — the receiver, seeing it has news, pulls, and re-announces to its own neighbors after pulling (the cascade). Because the topic id equals the namespace id and topic membership is unauthorized, a subscriber that knows the id therefore obtains only activity metadata (author heads, timing), never keys, hashes, or values — and for a data namespace, the reconciliation the announcement triggers is gated, so an unresolvable subscriber obtains nothing at all. (The content hash a fetch-hint announcement carries, and the blob channel behind it, are a separate, deferred gap.)

#### Scenario: An own device converges through the announcement, not a pushed entry

- **WHEN** an issuer's device writes an entry and another of its devices is a swarm member
- **THEN** the second device converges on the entry — obtained over the reconciliation the announcement triggered, not received as a broadcast entry

#### Scenario: A data-namespace topic subscriber obtains no content

- **WHEN** a party that knows a data namespace's id but holds no grant and no device record subscribes to its topic, and the issuer then writes
- **THEN** the subscriber obtains no key, hash, or value of the write — the topic carries only the content-free announcement, and the reconciliation it would trigger is refused

### Requirement: Grantees stay outside the gossip swarm

A peer whose access arrived through a grant SHALL NOT be a member of the replica's gossip swarm. The swarm SHALL consist of the issuer's own devices; a grantee's only data path is the reconciliation it initiates. This composes with the content-free topic above: membership conveys announcements, so removing a grantee from the swarm (rather than serving it filtered) keeps even activity metadata about unauthorized claims off its wire, and spares the relaying cost a broadcast presumes members share.

Membership SHALL follow the recorded sync strategy in both directions: a grantee import of a replica that had already joined the swarm — a device-replicated import downgraded to a grantee binding — SHALL leave the swarm as part of the import, not merely stop re-joining (the fork's leave-gossip operation: the topic subscription closes in both directions while the replica stays open, syncing, and subscribed to). A data import SHALL refuse a ticket naming a replica that is tracked but not data-bound (a directory, a connection metadata store): repurposing a device-shared replica's tracking — and, with the downgrade now leaving the swarm, cutting its live path — must not be reachable on the word of whoever minted a ticket.

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

- **WHEN** a data import — device or grantee — is handed a ticket naming a replica that this node tracks as a directory or connection metadata store
- **THEN** the import is refused, and the device-shared replica's tracking, swarm membership, and live path are untouched

### Requirement: A granted replica serves the audience identity's devices

A node holding a granted replica SHALL serve a sync session for it to a caller that resolves, by authenticated node id, as a device of the grant's audience identity — resolved through that identity's own directory, never through records a counterparty wrote. The session's rights SHALL come from the serving device's locally replicated grant record for the replica's issuer, read at session setup: the record serves through the same claim-set egress filter the issuer applies, and an absent, withdrawn, undecodable, or wrongly-addressed record refuses. A record whose capability names an audience other than the identity resolved SHALL refuse: position in a directional store never substitutes for the capability's named audience. On a node hosting several identities, only the directory of the identity the grant is addressed to is consulted.

#### Scenario: A sibling catches up while the issuer is offline

- **WHEN** a device of the audience identity opens a granted replica and requests a sync from a sibling device that holds the replica and a live local grant record, with every device of the issuer offline
- **THEN** the sibling serves the session per the local record and the granted claim arrives at the requesting device, payload included

#### Scenario: A scoped sibling session is filtered by the same claim set

- **WHEN** the local grant record is scoped and a sibling device syncs the replica
- **THEN** the sibling receives exactly the entries the claim set covers — the transcript is the one the issuer would have served, and withheld entries stay hidden

#### Scenario: A withdrawn local record refuses the next sibling session

- **WHEN** the withdrawal tombstone has reached the serving device's copy of the pair and a sibling then requests a sync
- **THEN** the request is refused indistinguishably from the replica not being hosted, and what the sibling obtained while granted is retained

#### Scenario: A co-located identity's device is not an audience device

- **WHEN** the serving node hosts a second identity and a caller resolves only in that other identity's directory
- **THEN** the session is refused indistinguishably from the replica not being hosted

### Requirement: A granted replica reconciles with siblings as well as the issuer

A granted replica's tracked contacts SHALL admit devices of the audience identities and of the issuer alike — supplied at import from the ticket, and thereafter set wholesale by the owning runtime as it re-derives the list from the device records. Setting SHALL replace the previous list, so a device absent from the new derivation stops being dialed by the periodic reconcile pass and the before-access nudge; both SHALL dial the tracked list as it stands at each pass. The engine's own record of peers that once served the replica is separate, unions into each dial, and ages out on its own.

#### Scenario: The reconcile pass dials a sibling contact

- **WHEN** a granted replica is tracked with a sibling device among its contacts and the issuer is unreachable
- **THEN** the next reconcile pass reaches the sibling and the replica converges without the issuer

#### Scenario: A replaced list drops the absent contact

- **WHEN** the tracked list is set anew without a device that was in it
- **THEN** the following passes and nudges dial the new list, and the dropped device is not in it

### Requirement: Unauthorized callers are refused uniformly

A sync request for a hosted replica from a caller with no computable rights SHALL be refused indistinguishably from the replica not being hosted on this node; empty effective rights SHALL be refused the same way. A node SHALL serve a replica only in roles it can judge from its own records — for a granted foreign replica that means exactly the devices of the grant's audience identity, judged through the audience's directory and the local grant record; every other caller SHALL be refused.

#### Scenario: A ticket holder without a grant learns nothing

- **WHEN** a caller holding the replica's ticket but no grant requests a sync
- **THEN** the request is refused with the same answer an unhosted replica would produce, and no fingerprint, count, or existence signal is revealed

#### Scenario: A scoped holder does not re-serve to a third party

- **WHEN** a caller that resolves as no device of the grant's audience identity — even one holding a sibling-minted ticket — asks a scoped holder to sync the issuer's replica
- **THEN** the scoped holder refuses as for an unhosted replica, since it cannot compute a third party's rights
