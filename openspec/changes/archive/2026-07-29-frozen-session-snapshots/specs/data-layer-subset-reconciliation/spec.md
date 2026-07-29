# Delta: data-layer-subset-reconciliation

## ADDED Requirements

### Requirement: The caller's rights are resolved once, at session setup

A serving node SHALL resolve the caller's read rights when a reconciliation session is set up, and that resolution SHALL govern the session for its whole lifetime. A grant widened, narrowed, or withdrawn while a session is under way SHALL NOT change what that session serves — it governs the sessions set up after it. The ingest gate resolves the same records at the same moment ([capability-gated ingest](capability-gated-ingest.md)), so the read and write halves of one session's decisions rest on one state. The bound this places on revocation is the point rather than a side effect: a withdrawal takes effect from the next session, and what the peer obtained while it was granted stays with it — Invariant 2 governs acquisition, not retention.

#### Scenario: A withdrawn grant refuses the next session and keeps delivered data

- **WHEN** an issuer withdraws a peer's grant and afterwards writes the withdrawn claim again
- **THEN** the peer's later sessions carry nothing of that write, while the value it obtained before the withdrawal stays readable to it

#### Scenario: A rights change does not reach a session already under way

- **WHEN** a grant is narrowed while a session over that replica is still exchanging rounds
- **THEN** that session goes on serving what it was set up to serve, and the narrowing governs the next session

### Requirement: A session serves a view frozen at session setup

A node SHALL serve one reconciliation session from a store snapshot taken at session setup: every fingerprint, split boundary, offer, and item the session derives SHALL reflect the store as of that moment, so a write landing mid-session neither shifts the served view between rounds nor reaches the peer within the session — it travels on the next one. What one view buys is consistency inside a session, not a prerequisite of reconciliation: the engine converges over a drifting store too, because reconciliation is anti-entropy and what one session misses the next one carries. It buys agreement among the things a single session derives — a fingerprint and the items behind it describe the same claims, and a split boundary still partitions the set it was computed over when a later round returns to it — and it puts the data half of the session's decisions on the footing the rights half already stands on, since the caller's rights are resolved at session setup and hold for the session's lifetime. Opening the snapshot SHALL first commit the store's pending write batch, so every entry inserted before session setup is in the snapshot. Ingest SHALL stay on the live store: an entry the peer sends is judged against current state, so an older remote entry never overwrites a newer local write the snapshot predates. The check behind a rejection — whether the replica would newly store the refused entry — reads the live store for the same reason and a graver one: a rejection makes its sender destroy its own copy, so judged against the frozen view it would name an entry the replica took in after session setup and cost the sender data both sides hold ([capability-gated ingest](capability-gated-ingest.md)). The snapshot SHALL be released when the session ends, on every exit path — completion, refusal, failure, and cancellation alike — so no snapshot outlives its session.

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
- **THEN** its snapshot is released, and a rejected sync request never opens one
