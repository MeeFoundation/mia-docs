# data-layer: subset reconciliation — delta for identity-scoped-replicas

## MODIFIED Requirements

### Requirement: The caller's rights are resolved once, at session setup

A serving node SHALL resolve the caller's read rights when a reconciliation session is set up, for the identity the caller names in that session and for no other identity its node id resolves to, and that resolution SHALL govern the session for its whole lifetime. A grant widened, narrowed, or withdrawn while a session is under way SHALL NOT change what that session serves — it governs the sessions set up after it. The ingest gate resolves the same records at the same moment ([capability-gated ingest](../capability-gated-ingest/spec.md)), so the read and write halves of one session's decisions rest on one state. The bound this places on revocation is the point rather than a side effect: a withdrawal takes effect from the next session, and what the peer obtained while it was granted stays with it — Invariant 2 governs acquisition, not retention.

#### Scenario: A withdrawn grant refuses the next session and keeps delivered data

- **WHEN** an issuer withdraws a peer's grant and afterwards writes the withdrawn claim again
- **THEN** the peer's later sessions carry nothing of that write, while the value it obtained before the withdrawal stays readable to it

#### Scenario: A rights change does not reach a session already under way

- **WHEN** a grant is narrowed while a session over that replica is still exchanging rounds
- **THEN** that session goes on serving what it was set up to serve, and the narrowing governs the next session

#### Scenario: A node holding two grants is served each on its own

- **WHEN** an issuer grants one claim to one identity and another claim to a co-located identity, and that node reconciles once for each
- **THEN** each session serves the claim granted to the identity it names, and neither serves the other's

### Requirement: A granted replica serves the audience identity's devices

A node holding a granted replica SHALL serve a sync session for it to a caller that resolves, by authenticated node id, as a device of the grant's audience identity — resolved through that identity's own directory, never through records a counterparty wrote. The session's rights SHALL come from the serving device's locally replicated grant record for the replica's issuer, read at session setup: the record serves through the same claim-set egress filter the issuer applies, and an absent, withdrawn, undecodable, or wrongly-addressed record refuses. A record whose capability names an audience other than the identity resolved SHALL refuse: position in a directional store never substitutes for the capability's named audience. The replica belongs to one scope, and the session names it; the caller's named identity is resolved in that identity's own directory, so no other identity hosted on either node takes part in the decision.

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

A granted replica's tracked contacts SHALL admit devices of the audience identity and of the issuer alike, each paired with the identity it is dialed as — supplied at import from the ticket, and thereafter set wholesale by the owning runtime as it re-derives the list from the device records. Setting SHALL replace the previous list, so a device absent from the new derivation stops being dialed by the periodic reconcile pass and the before-access nudge; both SHALL dial the tracked list as it stands at each pass. The engine's own record of peers that once served the replica is separate, unions into each dial, and ages out on its own.

#### Scenario: The reconcile pass dials a sibling contact

- **WHEN** a granted replica is tracked with a sibling device among its contacts and the issuer is unreachable
- **THEN** the next reconcile pass reaches the sibling and the replica converges without the issuer

#### Scenario: A replaced list drops the absent contact

- **WHEN** the tracked list is set anew without a device that was in it
- **THEN** the following passes and nudges dial the new list, and the dropped device is not in it

#### Scenario: A contact is dialed as the identity it belongs to

- **WHEN** a granted replica held for one identity dials a contact derived from that identity's device records
- **THEN** the session names that identity as the caller, and a device of a co-located identity is not among the contacts of this replica
