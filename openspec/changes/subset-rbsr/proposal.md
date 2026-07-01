# Proposal: subset-rbsr

## Why

Invariant 2 requires that a node receive a data record only if it holds a read capability for it — but today reconciliation delivers every record to any peer that syncs, with no per-record read control. This change adds capability-filtered reconciliation ("subset-RBSR"): a serving node reveals only the records the receiving peer is authorized to read, enforcing Invariant 2 during reconciliation (the read-side counterpart of the ADR-0008 ingest gate).

## What Changes

- **Egress capability filter in reconciliation.** The serving node computes range fingerprints, split boundaries, offers, and item transmissions over the *filtered* view — the records the peer holds read capabilities for. A record the peer cannot present a capability for is never fingerprinted, offered, or sent, so its existence is not revealed. This runs at reconciliation-time in `pdn-store` (the `ranger` path), distinct from the existing ingest-only `validate_entry` hook — this change **modifies `pdn-store`**.
- **A minimal read-capability mechanism.** Issuance (an issuer grants an audience read on a set of records), presentation (a peer presents its capabilities at session start), and per-record evaluation (does a presented capability cover this record?). This is the **single-link, degenerate precursor to UWill** — no delegation chains, no revocation cryptography, no token encoding yet — mirroring how `ConnectionsPolicy` is the degenerate precursor of capability-chain validation.
- **Own-identity sync is unaffected.** An identity's own devices are authorized for all of that identity's data (composes with Invariant 1), so reconciliation between them stays full — the filter admits everything for a same-identity peer.
- **Existing tests use the mechanism.** `sync_two_nodes` becomes a read-restriction scenario: an issuer grants a peer read on a subset of records, and the test asserts the peer receives exactly that subset while the withheld records never arrive (existence hidden). `connections_two_devices` and `device_linking` (same-identity) must keep replicating in full under the filter.

## Out of Scope (deferred)

- **Full UWill** (ADR-0007): delegation chains, chain validation, revocation, token encoding. This change carries only the degenerate single-link read capability the filter consumes; the real format and issuance migrate to the `uwill` module later.
- **The metadata a filtered session still reveals to an authorized peer** (count / opaque keys / timestamps of the records it *is* authorized for) — accepted; addressed on the linkability axis by non-correlatable ids (KERI), not here.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree, following the `components/pdn-node/uwill.md` convention.

| Capability (delta)                 | Archive destination                                             |
| ---------------------------------- | --------------------------------------------------------------- |
| `data-layer-read-capabilities`     | `openspec/specs/components/data-layer/read-capabilities.md`      |
| `data-layer-subset-reconciliation` | `openspec/specs/components/data-layer/subset-reconciliation.md`  |

### New Capabilities

- `data-layer-read-capabilities`: the minimal read-capability — issuance, presentation, and per-record evaluation; the single-link precursor to UWill.
- `data-layer-subset-reconciliation`: capability-filtered reconciliation enforcing Invariant 2 — the serving node reveals only authorized records, hiding the rest (content and existence); the read-side counterpart of the ingest gate.

## Impact

- **`pdn-store`**: a new reconciliation-time egress filter (a per-session predicate over which records participate in fingerprints and item transmissions). Deeper than the ingest hook; touches the reconciliation engine (`ranger`).
- **`crates/data-layer`**: the read-capability type + issuance/evaluation; presentation of capabilities at session setup; wiring the per-peer filter into `SyncNode` reconciliation.
- **`crates/data-layer/tests`**: `sync_two_nodes` becomes a read-restriction scenario; `connections_two_devices` / `device_linking` verified to still replicate in full (same-identity).
- **Unaffected**: `pdn-types` addressing (issuer / `ClaimId`), `pdn-layer` domain model, the ingest gate (`SelfOwned` / `ConnectionsPolicy`) — the egress filter composes with it, does not replace it.
