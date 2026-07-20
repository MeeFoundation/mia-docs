# data-layer: subset reconciliation

Capability-filtered reconciliation — "subset-RBSR" — the read-side counterpart of the ADR-0008 ingest hook, enforcing Invariant 2: a serving node reveals only the claims the receiving peer is read-authorized for.

## ADDED Requirements

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

Filtering SHALL run at reconciliation time inside `pdn-store`, per peer, distinct from the ingest-only `validate_entry` hook. It SHALL consume the caller's effective rights as an opaque per-session predicate over entries, assembled above the fork — `pdn-store` SHALL know neither the grant format nor the identity vocabulary.

#### Scenario: Read filter is independent of the ingest hook

- **WHEN** the egress filter runs while the fork's `validate_entry` hook has no validator installed
- **THEN** filtering applies unchanged, and it composes with any future ingest validator (ADR-0008) — read on egress, write on ingest, independently

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

### Requirement: The gossip topic carries no content

A replica's gossip topic SHALL carry only content-free announcements, never entries. A local insert SHALL broadcast a content-free author-head digest (a sync report) to neighbors; the entry itself SHALL NOT be broadcast, and an entry received over gossip SHALL be dropped, never inserted. Content SHALL flow only over the classified reconciliation an announcement triggers — the receiver, seeing it has news, pulls, and re-announces to its own neighbors after pulling (the cascade). Because the topic id equals the namespace id and topic membership is unauthorized, a subscriber that knows the id therefore obtains only activity metadata (author heads, timing), never keys, hashes, or values — and for a data namespace, the reconciliation the announcement triggers is gated, so an unresolvable subscriber obtains nothing at all. (The content hash a fetch-hint announcement carries, and the blob channel behind it, are a separate, deferred gap.)

#### Scenario: An own device converges through the announcement, not a pushed entry

- **WHEN** an issuer's device writes an entry and another of its devices is a swarm member
- **THEN** the second device converges on the entry — obtained over the reconciliation the announcement triggered, not received as a broadcast entry

#### Scenario: A data-namespace topic subscriber obtains no content

- **WHEN** a party that knows a data namespace's id but holds no grant and no device record subscribes to its topic, and the issuer then writes
- **THEN** the subscriber obtains no key, hash, or value of the write — the topic carries only the content-free announcement, and the reconciliation it would trigger is refused

### Requirement: Grantees stay outside the gossip swarm

A peer whose access arrived through a grant — capability-scoped or whole-store — SHALL NOT be a member of the replica's gossip swarm. The swarm SHALL consist of the issuer's own devices; a grantee's only data path is the reconciliation it initiates. This composes with the content-free topic above: membership conveys announcements, so removing a grantee from the swarm (rather than serving it filtered) keeps even activity metadata about unauthorized claims off its wire, and spares the relaying cost a broadcast presumes members share.

Membership SHALL follow the recorded sync strategy in both directions: a grantee import of a replica that had already joined the swarm — a device-replicated import downgraded to a grantee binding — SHALL leave the swarm as part of the import, not merely stop re-joining (the fork's leave-gossip operation: the topic subscription closes in both directions while the replica stays open, syncing, and subscribed to). A data import SHALL refuse a ticket naming a replica that is tracked but not data-bound (a directory, a connection metadata store): repurposing a device-shared replica's tracking — and, with the downgrade now leaving the swarm, cutting its live path — must not be reachable on the word of whoever minted a ticket.

#### Scenario: A scoped peer receives nothing over gossip

- **WHEN** a claim is written into a replica whose swarm is the issuer's devices, while scoped peers hold capabilities on other claims
- **THEN** no scoped peer receives the claim or any digest of it over gossip, and the issuer's devices receive the claim itself

#### Scenario: A whole-store grantee receives entries by reconciliation only

- **WHEN** the issuer writes after a peer imported the replica's whole-store ticket, past the window in which a swarm would have formed
- **THEN** a granted peer receives the write over its next classified reconciliation, and a bare-ticket holder with no recorded grant receives nothing — the write never arrives over gossip

#### Scenario: A swarm member is served only while authorized

- **WHEN** a peer that is a swarm member of a replica holds a grant, converges on a write, then has the grant withdrawn and the issuer writes again
- **THEN** the post-withdrawal write never reaches it although it is still a swarm member — content follows the access book, not swarm membership, and what was delivered while granted is retained

#### Scenario: A device-shared replica refuses a data import

- **WHEN** a data import — device or grantee — is handed a ticket naming a replica that this node tracks as a directory or connection metadata store
- **THEN** the import is refused, and the device-shared replica's tracking, swarm membership, and live path are untouched

### Requirement: Unauthorized callers are refused uniformly

A sync request for a hosted replica from a caller with no computable rights SHALL be refused indistinguishably from the replica not being hosted on this node; empty effective rights SHALL be refused the same way. A node SHALL serve a replica only in roles it can judge — for a foreign replica whose grant book it does not hold, it SHALL refuse.

#### Scenario: A ticket holder without a grant learns nothing

- **WHEN** a caller holding the replica's ticket but no grant requests a sync
- **THEN** the request is refused with the same answer an unhosted replica would produce, and no fingerprint, count, or existence signal is revealed

#### Scenario: A scoped peer does not re-serve its slice

- **WHEN** a third party asks a scoped holder to sync the issuer's replica
- **THEN** the scoped holder refuses as for an unhosted replica, since it cannot compute the third party's rights
