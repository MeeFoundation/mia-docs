# Proposal: subset-rbsr

## Why

Invariant 2 requires that a node receive a data record only if it holds a read capability for it — but today reconciliation delivers every record to any peer that syncs, with no per-record read control. This change adds capability-filtered reconciliation ("subset-RBSR"): a serving node reveals only the records the receiving peer is authorized to read, enforcing Invariant 2 during reconciliation (the read-side counterpart of the ADR-0008 ingest hook — the fork's `validate_entry`).

## What Changes

- **Egress capability filter in reconciliation.** The serving node computes range fingerprints, split boundaries, offers, and item transmissions over the _filtered_ view — the records the peer holds read capabilities for. A record the peer cannot present a capability for is never fingerprinted, offered, or sent, so its existence is not revealed. This runs at reconciliation-time in `pdn-store` (the `ranger` path), distinct from the existing ingest-only `validate_entry` hook — this change **modifies `pdn-store`**.
- **Scoped peers live outside the swarm.** Gossip broadcasts full records (`Op::Put(SignedEntry)`) and relays them through swarm members the serving node does not control, so a broadcast cannot be filtered per recipient (see the worked examples below; design D5 has the full argument). Peers with capability-scoped access therefore never join the replica's gossip swarm; their only data path is the capability-filtered reconciliation, which they initiate, and which is the sole carrier of correctness — a scoped peer that never reconciles simply never sees updates. Making that path prompt — a directed, content-free trigger to exactly the covered peers on a covered write — is the separate `reconcile-trigger` change; subset-rbsr does not require it (reconciliation-on-contact suffices). Swarms whose members are all fully authorized (an identity's own devices, D4) keep full-record gossip unchanged.
- **The filter plugs in as a session-scoped filtered store.** A filtering adapter implements the reconciliation engine's store interface (`ranger::Store`), assembled per session from a record source and the peer's rights frozen at session setup — the engine itself is untouched and structurally cannot read past the filter, and range fingerprints come out filtered for free (pdn-store computes them by iterating exactly the ranges the adapter filters). On the fs backend the record source is a redb read-transaction snapshot (`snapshot_owned`), pinning each session to a stable view at zero copy cost; the memory backend keeps the live store and today's tolerance to mid-session drift. Where a load profile warrants it, a materialized **per-audience** view replaces rescanning: sessions sharing the same rights reuse one view (Example 2 has two audiences regardless of member count; Example 1 punishes full-store scans), and the audience index the reconcile trigger reuses doubles as the view's invalidation signal.
- **A minimal read-capability mechanism.** Issuance (an issuer grants an audience read on a set of records), presentation (a peer presents its capabilities at session start), and per-record evaluation (does a presented capability cover this record?). This is the **single-link, degenerate precursor to UWill** — no delegation chains, no revocation cryptography, no token encoding yet; the real format and chain validation supersede it later (ADR-0007).
- **Own-identity sync is unaffected.** An identity's own devices are authorized for all of that identity's data (composes with Invariant 1), so reconciliation between them stays full — the filter admits everything for a same-identity peer.
- **Tests use the mechanism.** A new read-restriction scenario, written fresh (the cross-identity `sync_two_nodes` test was removed together with the ingest gate by multi-identity-node): an issuer grants a peer read on a subset of records, and the test asserts the peer receives exactly that subset while the withheld records never arrive (existence hidden). The same-identity suites (`sync_two_devices`, `device_linking`, `multi_identity`, `three_devices`) must keep replicating in full under the filter.

## Load profiles

Two load profiles make the design concrete: how the capability filter behaves under realistic, bidirectional sharing, and what the per-issuer model (ADR-0009) costs a well-connected node at scale. The live path — a covered write prompting its covered peers — is the separate `reconcile-trigger` change; it appears here only to size the load.

### Example 1: personal store, sparse sharing

Alice's data store holds 1,000,000 records. 1,000 scoped peers — Bob among them — each hold a read capability on **1 distinct record** of hers. Alice's own devices form the replica's swarm; the 1,000 scoped peers are not in it. It runs the other way too: each of those 1,000 contacts has shared about **1,000 of their own records** with Alice, so Alice is herself a scoped peer of 1,000 other replicas, holding a filtered slice of each.

- **Alice edits a record shared with nobody.** Her devices receive the record itself over the swarm's full gossip, exactly as without this change. No scoped peer receives anything — not the record, not a digest, not a tick. 0 triggers sent.
- **Alice edits the record shared with Bob.** Her devices receive it over gossip; Bob receives 1 trigger and runs 1 filtered reconciliation, which delivers exactly that record. The other 999 receive nothing and learn nothing. Cost: O(peers whose capability covers the record) — here, 1.
- **What the rejected alternative — a broadcast tick in a swarm holding all 1,000 scoped peers alongside Alice's devices — would do**: every write, shared or not, would wake all 1,000 peers into reconciliation against Alice's node (a thundering herd, almost all of it empty), and every scoped peer would observe the full rate of Alice's writes across the 1,000,000 records — a side channel far wider than the 1 record each was granted.

**Delegation widens the author set.** Each of those 1,000 inbound replicas triggers Alice on a covered write, symmetric to her own outbound side. And once capabilities can be delegated (a contact re-shares a third party's record with her), the issuers Alice holds records from outgrow her contact count: 1,000 contacts, but an estimated 2,000–5,000 distinct issuers over a few years of use. By ADR-0009 that is 2,000–5,000 `pdn-store` replicas — each its own set-reconciliation unit and gossip topic — on Alice's one node: her own (1,000,000 records, full) plus thousands of others', about **1,000 records each**. So Alice sits on both sides of the filter at once — serving her own replica filtered to her consumers, and a filtered consumer of thousands of others' replicas — and the per-node replica-and-topic count tracks the transitive reach of delegation, not the contact count. That count is a scale question for the per-issuer model (ADR-0009), surfaced here, not for the filter itself.

### Example 2: SMB Coordination

The organization — a small-or-medium business — is an identity of its own, and its data store holds **10,000 records** — the working documents — shared with **all 100 members**, but not uniformly: most of the store is readable and writable by everyone, while a small restricted subset is readable by 10 members (10% of the organization) and writable by 5 (5%). (Write authority is the ingest side's concern — ADR-0008, then UWill — not this change; what the read filter and the triggers see are the read audiences.) The members work in these documents: about **100 of the 10,000** are edited on a working day.

Consequences for the trigger, in order:

- **A covered write triggers its record's read audience.** For the common bulk that audience is the whole organization, so the directed trigger degenerates into a hand-rolled broadcast: 100 edited documents × 100 members ≈ 10,000 triggers a day before coalescing (edits in the restricted subset, with their audience of 10, only trim this). On the restricted subset directedness earns its keep again — the 90 non-readers get nothing.
- **Coalescing turns the flood into a tick.** A member holds at most 1 pending trigger until they reconcile, so what a member receives is bounded by both the write rate and their own reconciliation cadence: with about 100 covered writes spread over a working day, a member who reconciles a few times a day sees a few ticks — not 100, and never 10,000.
- **No side channel opens — on either slice.** A member is triggered only about activity on records they can read: the common bulk leaks nothing beyond what everyone may read anyway, and activity in the restricted subset stays invisible to its 90 non-readers — no record, no digest, no tick, no timing.
- **The load moves to reconciliation.** Triggers become cheap and boring; the real cost of this profile is 100 peers repeatedly reconciling the 10,000-record replica, most sessions authorized for almost all of it. Each scan is small here — the pressure is the session count (bounded above by 100 ticks × 100 members a day, pulled down by coalescing and each member's cadence). The central fact for the filter plumbing is that members' sessions fall into just two audiences — the common bulk for 90 members, bulk-plus-restricted for the other 10 — so the view the filter consumes is built once per audience: two views, not one per member. The profile that punishes scanning a large store per fingerprint is the sparse one (Example 1).

### Why the broadcast itself cannot be filtered

A gossip sender controls only its few direct neighbors (HyParView active view), every further delivery is relayed by swarm members outside its control; a relaying member must hold what it forwards, so a scoped relay would either obtain records it is not authorized for — the very transfer Invariant 2 forbids — or tear a hole in the delivery tree; and filtering at every hop would require distributing the access matrix itself to every member. A broadcast presumes members are interchangeable with respect to the topic's content; per-record authorization breaks exactly that premise. Point-to-point sessions — reconciliation — are the only place a per-peer filter is enforceable, so all filtering stays there.

## Out of Scope (deferred)

- **Full UWill** (ADR-0007): delegation chains, chain validation, revocation, token encoding. This change carries only the degenerate single-link read capability the filter consumes; the real format and issuance migrate to the `uwill` module later.
- **The metadata a filtered session still reveals to an authorized peer** (count / opaque keys / timestamps of the records it _is_ authorized for) — accepted; addressed on the linkability axis by non-correlatable ids (KERI), not here.
- **The reconcile-trigger live path** (transport, coalescing, retry) — the separate `reconcile-trigger` change; subset-rbsr describes it (design D5, load profiles) but does not build it, and correctness does not depend on it (reconciliation-on-contact suffices).

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree, following the `components/pdn-node/uwill.md` convention.

| Capability (delta)                 | Archive destination                                             |
| ---------------------------------- | --------------------------------------------------------------- |
| `data-layer-read-capabilities`     | `openspec/specs/components/data-layer/read-capabilities.md`     |
| `data-layer-subset-reconciliation` | `openspec/specs/components/data-layer/subset-reconciliation.md` |

### New Capabilities

- `data-layer-read-capabilities`: the minimal read-capability — issuance, presentation, and per-record evaluation; the single-link precursor to UWill.
- `data-layer-subset-reconciliation`: capability-filtered reconciliation enforcing Invariant 2 — the serving node reveals only authorized records, hiding the rest (content and existence); the read-side counterpart of the ingest hook.

## Impact

- **`pdn-store`**: a new reconciliation-time egress filter (a per-session predicate over which records participate in fingerprints and item transmissions). Deeper than the ingest hook; touches the reconciliation engine (`ranger`).
- **`crates/data-layer`**: the read-capability type + issuance/evaluation; presentation of capabilities at session setup; wiring the per-peer filter into `SyncNode` reconciliation.
- **`crates/data-layer/tests`**: a new read-restriction scenario test; the same-identity suites (`sync_two_devices`, `device_linking`, `multi_identity`, `three_devices`) verified to still replicate in full.
- **Unaffected**: `pdn-types` addressing (issuer / `ClaimId`), `pdn-layer` domain model, and the fork's ingest hook (`validate_entry`, ADR-0008), which stays available and uninstalled. The old ingest gate was removed by multi-identity-node, so this filter is the first enforcement to land on the ungated, ticket-possession baseline — it composes with nothing and replaces nothing.
