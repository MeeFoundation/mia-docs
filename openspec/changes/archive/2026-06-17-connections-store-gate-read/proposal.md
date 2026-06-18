# Proposal: connections-store-gate-read

## Why

Connections ("which PdnIds do I accept entries from") are identity-level state: every device of Alice must agree on them. Today they live in a per-device, in-memory set populated by hand (ADR-0008 Tier 1) — lost on restart and never shared between Alice's devices. The first concrete step is to lift them out of memory into a **dedicated replicated store that Alice's devices converge on**, replicated by plain pdn-store sync.

This change is deliberately scoped to exactly that: the connections store existing and syncing between two devices of one identity. Making the ingest gate *consume* that store to admit/reject data is a separate, larger follow-up (see Out of Scope) — proving device-sync first de-risks it and touches no fork code.

## What Changes

- **Dedicated connections store**: a per-identity pdn-store replica, deliberately *separate* from data namespaces (own doc, own ticket, own lifecycle). One entry per connection at path `connections/<pdnid-hex>`; payload is an opaque marker (the key carries the identity); disconnect = tombstone (empty entry). Replication between devices is plain pdn-store sync — ticket bootstrap, set reconciliation, live gossip.
- **Typed bindings in the registry**: the registry distinguishes `Data(NamespaceId)` (peer-visible `(about, issued_by)` pair) from `Connections { owner: PdnId }` (device-shared store, no domain `NamespaceId`). `IngestCtx` carries the resolved `Binding`. The domain id model in `pdn-types` is untouched.
- **Device axiom policy (`SelfOwned`)**: a node admits entries of bindings owned by its own PdnId *without any store read*. This is the whole enforcement needed in this scope — it lets the connections store replicate between Alice's devices *through* the existing gate, with no chicken-and-egg against an empty store. It reuses the current fork seam (`Fn(&SignedEntry) -> bool`); **the fork is not modified**.
- **New scenario test**: two devices of Alice (phone, laptop), same PdnId — `connect`/`disconnect` performed on phone, convergence observed on laptop (the connection appears, a later disconnect propagates). No second identity, no data-namespace gating.
- **Untouched**: the existing in-memory `ConnectionsPolicy` (Tier-1 data gating) and its `sync_two_nodes` test stay as they are — this change *adds* the connections store and device axiom alongside them.

## Out of Scope (deferred to a future change)

The motivating end state — the gate reading the connections store to admit/reject **data** entries — is intentionally **not** in this change. It requires:

- **Fork seam v2**: widening `CapabilityValidator` to receive a synchronous, read-only store snapshot (`snapshot_owned() -> ReadOnlyTables` already exists in the fork), so a store-reading policy can decide at validate time without an in-memory mirror. This is driven by the fact that, once UWill/KERI land, the gate's working set (key chains × connections × capabilities) will not fit in memory.
- **Store-reading `ConnectionsPolicy`** that admits a `Data(ns)` entry iff a live connection entry exists for `ns.issued_by`, and **removal** of the in-memory set.
- **Cross-identity enforcement** (a Bob whose data is gated on Alice's connection state), revocation-after-admission, and capability delivery.

Also still out: content-dependent UWill chain validation (needs blob payloads, not synchronously readable at the gate), real device linking (a Write `DocTicket` remains the stand-in), and mailbox delivery for non-overlapping online windows.

## Capabilities

Capability ids are component-prefixed (the openspec delta layout is flat: `specs/<capability>/spec.md`). Specs are component-owned: on archive they land in the component tree, following the `components/pdn-node/uwill.md` convention — not at the specs root. Nothing in this change specifies `pdn-node`-level behavior or touches pdn-store (the fork); its sole subject is the `data-layer` crate.

| Capability (delta)                       | Archive destination                                            |
| ---------------------------------------- | -------------------------------------------------------------- |
| `data-layer-connections-store`           | `openspec/specs/components/data-layer/connections-store.md`     |
| `data-layer-ingest-policies`             | `openspec/specs/components/data-layer/ingest-policies.md`       |

### New Capabilities
- `data-layer-connections-store`: the device-replicated connections registry — storage layout, replication between an identity's devices, mutation API (connect/disconnect), and its self-gating bootstrap via the device axiom.
- `data-layer-ingest-policies`: binding resolution (`Data` vs `Connections`), the device axiom (`SelfOwned`, no store read), and policy composition.

### Modified Capabilities
<!-- none: no existing openspec capability specs cover this area -->

## Impact

- **`crates/data-layer`** (only): registry `Binding` enum + resolution into `IngestCtx`; `SelfOwned` device-axiom policy + an `AnyOf` combinator; new `connections` module (`ConnectionsStore`: create/import/share_ticket/connect/disconnect, plus async `is_connected`/`list` for UI and tests).
- **`crates/data-layer/tests`**: new `connections_two_devices` test; the existing `sync_two_nodes` test is left intact.
- **Fork (`pdn-store`)**: **not touched** — the device axiom needs only namespace→binding resolution, which the current `Fn(&SignedEntry) -> bool` seam already supports.
- **Untouched**: `pdn-types` (`NamespaceId` stays a pair), `pdn-layer`.
- **Deferred**, as a future change: fork seam v2 (store-snapshot validator), store-reading data gating, removal of the in-memory set, cross-identity enforcement (see Out of Scope).
