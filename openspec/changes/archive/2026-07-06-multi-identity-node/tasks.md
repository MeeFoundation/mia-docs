# Tasks: multi-identity-node

## 1. Remove the ingest gate from data-layer

- [x] 1.1 Delete `crates/data-layer/src/gate.rs` (`SelfOwned`, `ConnectionsPolicy`, `Connections`, `AnyOf`, `IngestPolicy`, `IngestCtx`, `Admission`, the `capability_validator` bridge) and prune the `lib.rs` module list and re-exports
- [x] 1.2 Shrink `registry.rs` to doc addressing: remove `Binding` and `BindingIndex`, keep the issuer-to-doc map that `read`/`write`/`share_ticket` resolve through
- [x] 1.3 Change `SyncNode::spawn()` to take no policy and install no validator into the fork's `Docs` builder; drop the `bind_*` registration steps while keeping doc creation and import (collapsed to generic `new_doc`/`import_doc` — the per-store variants differed only in the binding they registered, and the stores' `create`/`import` and `link_device` lose their now-dead `identity` parameters)
- [x] 1.4 Reword module and item docs that lean on the gate (`connections.rs`, `private_metadata.rs`, `linking.rs`, `node.rs`, `layer.rs`, crate root): admission language becomes ticket-possession language, with the fork's `validate_entry` seam noted as remaining uninstalled (ADR-0008)

## 2. Tests

- [x] 2.1 Delete `crates/data-layer/tests/sync_two_nodes.rs` (it tested the gate)
- [x] 2.2 Update `sync_two_devices.rs`: `SyncNode::spawn()` without a policy; module doc rewritten to the ticket-possession stance
- [x] 2.3 Update `device_linking.rs` the same way
- [x] 2.4 Add `multi_identity.rs` scenario test: one pair of devices hosts two identities (for example Alice-at-work and Alice-at-leisure); each identity is linked by its own explicit `link_device` call with its own seed; both identities' connections stores and data namespaces replicate; linking the second identity leaves the first identity's stores operating and brings nothing of one identity through the other
- [x] 2.5 Run `just precommit-check` (fmt, clippy, full test suite) and fix fallout

## 3. First-device provisioning

- [x] 3.1 Add `provision_identity` to `linking.rs` (create the connections store, publish its ticket under the directory's connections key, register the device; returns `LinkedStores`) and export it
- [x] 3.2 Simplify the tests over it: `device_linking.rs` replaces its inline provisioning; `multi_identity.rs`'s helper shrinks to provisioning plus test fixtures (peer connection, data namespace)
- [x] 3.3 Run `just precommit-check` and fix fallout

## 4. Spec corrections in mia-docs

- [x] 4.1 Edit `openspec/specs/components/mee-pdn/invariants.md`, Invariant 1: remove the `SelfOwned` ingest-policy mechanism, leaving the store ticket as the sole enforcing mechanism (bearer today, identity-bound with UWill; the spec states the present, not the removal's history)
- [x] 4.2 Add an open-question note to `openspec/changes/archive/2026-07-20-subset-rbsr/design.md`: D4 ("own-identity is fully authorized", "same-identity peer") predates multi-identity nodes and must be reread as "a peer holding one of the identities this node hosts"; its proposal's "Unaffected: ingest gate" line and the `sync_two_nodes` repurposing plan also predate this change (the test is deleted, the baseline is ungated)
