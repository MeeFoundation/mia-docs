# Delta: data-layer-subset-reconciliation

## ADDED Requirements

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

A granted replica's tracked contacts SHALL admit devices of the audience identity in addition to the issuer's devices — supplied at import or added later — and the periodic reconcile pass and the before-access nudge SHALL dial them exactly as they dial the issuer's.

#### Scenario: The reconcile pass dials a sibling contact

- **WHEN** a granted replica is tracked with a sibling device among its contacts and the issuer is unreachable
- **THEN** the next reconcile pass reaches the sibling and the replica converges without the issuer

## MODIFIED Requirements

### Requirement: Unauthorized callers are refused uniformly

A sync request for a hosted replica from a caller with no computable rights SHALL be refused indistinguishably from the replica not being hosted on this node; empty effective rights SHALL be refused the same way. A node SHALL serve a replica only in roles it can judge from its own records — for a granted foreign replica that means exactly the devices of the grant's audience identity, judged through the audience's directory and the local grant record; every other caller SHALL be refused.

#### Scenario: A ticket holder without a grant learns nothing

- **WHEN** a caller holding the replica's ticket but no grant requests a sync
- **THEN** the request is refused with the same answer an unhosted replica would produce, and no fingerprint, count, or existence signal is revealed

#### Scenario: A scoped holder does not re-serve to a third party

- **WHEN** a caller that resolves as no device of the grant's audience identity — even one holding a sibling-minted ticket — asks a scoped holder to sync the issuer's replica
- **THEN** the scoped holder refuses as for an unhosted replica, since it cannot compute a third party's rights
