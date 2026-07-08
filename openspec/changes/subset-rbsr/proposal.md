# Proposal: subset-rbsr

## Why

Invariant 2 requires that a node receive a data record only if it holds a read capability for it — but today reconciliation delivers every record to any peer that syncs, with no per-record read control. This change adds capability-filtered reconciliation ("subset-RBSR"): a serving node reveals only the records the receiving peer is authorized to read, enforcing Invariant 2 during reconciliation (the read-side counterpart of the ADR-0008 ingest seam — the fork's `validate_entry` hook).

## What Changes

- **Egress capability filter in reconciliation.** The serving node computes range fingerprints, split boundaries, offers, and item transmissions over the _filtered_ view — the records the peer holds read capabilities for. A record the peer cannot present a capability for is never fingerprinted, offered, or sent, so its existence is not revealed. This runs at reconciliation-time in `pdn-store` (the `ranger` path), distinct from the existing ingest-only `validate_entry` hook — this change **modifies `pdn-store`**.
- **Scoped peers live outside the swarm; live updates are directed notifications.** Gossip broadcasts full records (`Op::Put(SignedEntry)`) and relays them through swarm members the serving node does not control, so a broadcast cannot be filtered per recipient (see the worked examples below; design D5 has the full argument). Peers with capability-scoped access therefore never join the replica's gossip swarm. Instead, when a write lands, the serving node — which already maintains the capability index the reconciliation filter consumes — notifies exactly the scoped peers whose capabilities cover the written record, over their direct connections. A notification carries no record content; the notified peer fetches through a capability-filtered reconciliation session. Notifications are a latency optimization, not a correctness carrier: a missed one is healed by the next reconciliation on contact. Swarms whose members are all fully authorized (an identity's own devices, D4) keep full-record gossip unchanged.
- **A minimal read-capability mechanism.** Issuance (an issuer grants an audience read on a set of records), presentation (a peer presents its capabilities at session start), and per-record evaluation (does a presented capability cover this record?). This is the **single-link, degenerate precursor to UWill** — no delegation chains, no revocation cryptography, no token encoding yet; the real format and chain validation supersede it later (ADR-0007).
- **Own-identity sync is unaffected.** An identity's own devices are authorized for all of that identity's data (composes with Invariant 1), so reconciliation between them stays full — the filter admits everything for a same-identity peer.
- **Tests use the mechanism.** A new read-restriction scenario, written fresh (the cross-identity `sync_two_nodes` test was removed together with the ingest gate by multi-identity-node): an issuer grants a peer read on a subset of records, and the test asserts the peer receives exactly that subset while the withheld records never arrive (existence hidden). The same-identity suites (`sync_two_devices`, `device_linking`, `multi_identity`, `three_devices`) must keep replicating in full under the filter.

## Worked examples

Two load profiles make the live-path design concrete. Both start from the same store shape: one issuer, one replica, 10,000,000 records, 1,000 scoped peers. They differ in how sharing is distributed — sparse (each peer sees 1 record) versus dense (every peer sees the same 10,000).

### Example 1: personal store, sparse sharing

Alice's data store holds 10,000,000 records. 1,000 scoped peers — Bob among them — each hold a read capability on **1 distinct record**. Alice's own devices form the replica's swarm; the 1,000 scoped peers are not in it.

- **Alice edits a record shared with nobody.** Her devices receive the record itself over the swarm's full gossip, exactly as without this change. No scoped peer receives anything — not the record, not a digest, not a tick. 0 notifications sent.
- **Alice edits the record shared with Bob.** Her devices receive it over gossip; Bob receives 1 directed notification and runs 1 filtered reconciliation, which delivers exactly that record. The other 999 receive nothing and learn nothing. Cost: O(peers whose capability covers the record) — here, 1.
- **What the rejected alternative — a broadcast tick in a swarm of all 1,001 — would do**: every write, shared or not, would wake all 1,000 peers into reconciliation against Alice's node (a thundering herd, almost all of it empty), and every scoped peer would observe the full rate of Alice's writes across the 10,000,000 records — a side channel far wider than the 1 record each was granted.

### Example 2: organization, dense sharing

The issuer's store holds the same 10,000,000 records; **10,000 of them** are the organization's working documents, shared with **all 1,000 members** — every member's read capability covers the same 10,000-record set. The members work in these documents: 1,000 members × tens of edits each over a working day ≈ 20,000–50,000 covered writes daily.

Consequences for the notification trigger, in order:

- **Every covered write notifies everyone.** Any edit of a working document is covered by all 1,000 capabilities, so the directed notification degenerates into a hand-rolled broadcast: the serving node owes each member a notification per covered write. Directedness stops buying selectivity here — the audience genuinely is everyone.
- **Coalescing turns the flood into a tick.** A member holds at most 1 pending notification until they reconcile; under 20,000–50,000 writes a day every member is effectively always in the "pending" state, so what they actually receive is "there is more — reconcile when ready", at their own cadence. Per-member notification frequency equals that member's reconciliation frequency, not the organization's write rate.
- **No side channel opens.** Every member is authorized for all 10,000 working documents, so the notification leaks only the timing of activity they are entitled to read anyway — dense sharing removes the very asymmetry that made the sparse case privacy-sensitive.
- **The load moves to reconciliation.** Notifications become cheap and boring; the real cost of this profile is 1,000 peers repeatedly running filtered reconciliation against a 10,000,000-record replica, each session authorized for the same 10,000 records. How the filter plugs into `pdn-store` (per-entry predicate against a pre-filtered view — see Open Questions in the design) is decided by this case, and the central fact for that discussion is that all 1,000 sessions share one and the same authorized subset.

### Why the broadcast itself cannot be filtered

A gossip sender controls only its few direct neighbors (HyParView active view), every further delivery is relayed by swarm members outside its control; a relaying member must hold what it forwards, so a scoped relay would either obtain records it is not authorized for — the very transfer Invariant 2 forbids — or tear a hole in the delivery tree; and filtering at every hop would require distributing the access matrix itself to every member. A broadcast presumes members are interchangeable with respect to the topic's content; per-record authorization breaks exactly that premise. Point-to-point sessions — reconciliation — are the only place a per-peer filter is enforceable, so all filtering stays there.

## Out of Scope (deferred)

- **Full UWill** (ADR-0007): delegation chains, chain validation, revocation, token encoding. This change carries only the degenerate single-link read capability the filter consumes; the real format and issuance migrate to the `uwill` module later.
- **The metadata a filtered session still reveals to an authorized peer** (count / opaque keys / timestamps of the records it _is_ authorized for) — accepted; addressed on the linkability axis by non-correlatable ids (KERI), not here.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree, following the `components/pdn-node/uwill.md` convention.

| Capability (delta)                 | Archive destination                                             |
| ---------------------------------- | --------------------------------------------------------------- |
| `data-layer-read-capabilities`     | `openspec/specs/components/data-layer/read-capabilities.md`     |
| `data-layer-subset-reconciliation` | `openspec/specs/components/data-layer/subset-reconciliation.md` |

### New Capabilities

- `data-layer-read-capabilities`: the minimal read-capability — issuance, presentation, and per-record evaluation; the single-link precursor to UWill.
- `data-layer-subset-reconciliation`: capability-filtered reconciliation enforcing Invariant 2 — the serving node reveals only authorized records, hiding the rest (content and existence); the read-side counterpart of the ingest seam.

## Impact

- **`pdn-store`**: a new reconciliation-time egress filter (a per-session predicate over which records participate in fingerprints and item transmissions). Deeper than the ingest hook; touches the reconciliation engine (`ranger`).
- **`crates/data-layer`**: the read-capability type + issuance/evaluation; presentation of capabilities at session setup; wiring the per-peer filter into `SyncNode` reconciliation.
- **`crates/data-layer/tests`**: a new read-restriction scenario test, plus the directed-notification scenario from the worked example; the same-identity suites (`sync_two_devices`, `device_linking`, `multi_identity`, `three_devices`) verified to still replicate in full.
- **Unaffected**: `pdn-types` addressing (issuer / `ClaimId`), `pdn-layer` domain model, and the fork's ingest seam (`validate_entry`, ADR-0008), which stays available and uninstalled. The old ingest gate was removed by multi-identity-node, so this filter is the first enforcement to land on the ungated, ticket-possession baseline — it composes with nothing and replaces nothing.
