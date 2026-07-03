# Proposal: multi-identity-node

## Why

A person runs several identities from the same device — Alice-at-work and Alice-at-leisure today, groups and organizations (each an identity with its own `PdnId`) later — but the node hard-codes "one identity per node" in exactly one place: the `SelfOwned` ingest policy. This change removes that assumption so one node hosts any number of identities, each added to a device by an explicit act.

## What Changes

- **A node hosts multiple identities.** One `SyncNode` carries any number of identities side by side, each with its own store set: private metadata store, connections store, data namespace. Addressing stays per identity; the stores of different identities never mix.
- **BREAKING — the ingest gate is removed from `data-layer`.** `SelfOwned`, `ConnectionsPolicy`, `Connections`, `AnyOf`, the `IngestPolicy`/`IngestCtx`/`Admission` surface, the `gate.rs` bridge, and `Binding`/`BindingIndex` are deleted; `SyncNode::spawn()` takes no policy. The `validate_entry` hook stays in the pdn-store fork untouched — the ADR-0008 seam lives there and is simply not installed.
- **Interim security is ticket possession.** Until subset-rbsr lands (egress filtering, Invariant 2) and UWill after it, access to a replica is gated by holding its ticket and by nothing else: whoever imported a replica syncs all of it. This window is accepted for the experiment stage and stated in the specs.
- **Adding an identity to a device is explicit.** `link_device` is called once per identity with that identity's seed; nothing cascades, nothing propagates automatically. Automation (for example, UX offering to add all identities to a new device) comes later as a layer over these explicit acts.
- **Tests follow.** `sync_two_nodes` (it tested the gate) is deleted. `sync_two_devices` and `device_linking` drop the policy argument. A new scenario test covers one pair of devices hosting two identities, each linked separately, with both identities' stores replicating.
- **Specs are corrected in the same change.** Invariant 1 loses `SelfOwned` from its enforcement mechanisms (ticket gating remains); the subset-rbsr design gets an open-question note that its "same-identity peer" decision must be reread for a multi-identity node.

## Out of Scope (deferred)

- **Group functionality.** A group is conceptually an identity, but no group mechanics (membership, roles, invitation, cascading bootstrap) are designed or implemented here.
- **Automation of adding identities to a device** — cascading bootstrap, live propagation of a new identity to already-linked devices, UX prompts. Later, as automation of the explicit acts this change defines.
- **Any replacement ingest or egress enforcement** — that is subset-rbsr (Invariant 2) and UWill (ADR-0007).

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree, following the `components/pdn-node/uwill.md` convention.

| Capability (delta)            | Archive destination                                            |
| ----------------------------- | -------------------------------------------------------------- |
| `data-layer-multi-identity`   | `openspec/specs/components/data-layer/multi-identity.md`        |
| `data-layer-ingest-policies`  | removes `openspec/specs/components/data-layer/ingest-policies.md` |
| `data-layer-connections-store`| `openspec/specs/components/data-layer/connections-store.md`     |
| `data-layer-device-linking`   | `openspec/specs/components/data-layer/device-linking.md`        |

### New Capabilities

- `data-layer-multi-identity`: one node hosts several identities, each with its own store set, added explicitly and addressed independently; interim admission is ticket possession.

### Modified Capabilities

- `data-layer-ingest-policies`: the capability is withdrawn — every requirement is removed with the gate. The seam it documented remains in the pdn-store fork.
- `data-layer-connections-store`: drops the gate-dependent requirements ("bootstraps through its own gate", binding resolution for admission); registration of the replica on the node is for addressing, not admission, and several connections stores coexist on one node.
- `data-layer-device-linking`: linking stays single-seed per identity; adds the requirement that linking the same node into further identities is independent and repeatable.

## Impact

- **`crates/data-layer`**: `gate.rs` deleted; `registry.rs` shrinks to per-identity doc addressing (no `Binding`, no `BindingIndex`); `SyncNode::spawn()` signature changes (no policy); `lib.rs` exports shrink accordingly. `ConnectionsStore` / `PrivateMetadataStore` / `link_device` keep their surfaces.
- **`crates/data-layer/tests`**: `sync_two_nodes.rs` deleted; `sync_two_devices.rs` and `device_linking.rs` updated; new `multi_identity.rs` scenario test.
- **pdn-store fork**: untouched — the `validate_entry` / `capability_validator` seam stays, uninstalled.
- **`mia-docs` specs**: `components/pdn-node/invariants.md` Invariant 1 enforcement mechanisms edited; `changes/subset-rbsr/design.md` gains an open-question note (D4 "same-identity peer" under multi-identity).
- **Unaffected**: `pdn-types`, `pdn-layer`.
