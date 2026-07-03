# Tasks: multi-identity-node

## 1. Remove the ingest gate from data-layer

- [ ] 1.1 Delete `crates/data-layer/src/gate.rs` (`SelfOwned`, `ConnectionsPolicy`, `Connections`, `AnyOf`, `IngestPolicy`, `IngestCtx`, `Admission`, the `capability_validator` bridge) and prune the `lib.rs` module list and re-exports
- [ ] 1.2 Shrink `registry.rs` to doc addressing: remove `Binding` and `BindingIndex`, keep the issuer-to-doc map that `read`/`write`/`share_ticket` resolve through
- [ ] 1.3 Change `SyncNode::spawn()` to take no policy and install no validator into the fork's `Docs` builder; drop the `bind_*` registration steps while keeping doc creation and import (`new_connections_doc`, `import_connections_doc`, `new_private_metadata_doc`, `import_private_metadata_doc`, `create_namespace`, `import_namespace`)
- [ ] 1.4 Reword module and item docs that lean on the gate (`connections.rs`, `private_metadata.rs`, `linking.rs`, `node.rs`, crate root): admission language becomes ticket-possession language, with the fork's `validate_entry` seam noted as remaining uninstalled (ADR-0008)

## 2. Tests

- [ ] 2.1 Delete `crates/data-layer/tests/sync_two_nodes.rs` (it tested the gate)
- [ ] 2.2 Update `sync_two_devices.rs`: `SyncNode::spawn()` without a policy; module doc rewritten to the ticket-possession stance
- [ ] 2.3 Update `device_linking.rs` the same way
- [ ] 2.4 Add `multi_identity.rs` scenario test: one pair of devices hosts two identities (for example Alice-at-work and Alice-at-leisure); each identity is linked by its own explicit `link_device` call with its own seed; both identities' connections stores and data namespaces replicate; linking the second identity leaves the first identity's stores operating and brings nothing of one identity through the other
- [ ] 2.5 Run `just precommit-check` (fmt, clippy, full test suite) and fix fallout

## 3. Spec corrections in mia-docs

- [ ] 3.1 Edit `openspec/specs/components/pdn-node/invariants.md`, Invariant 1: remove the `SelfOwned` ingest-policy mechanism, leaving ticket gating as the enforcing mechanism, and state the accepted interim window until subset-rbsr (Invariant 2, egress) and UWill (identity-bound access) land
- [ ] 3.2 Add an open-question note to `openspec/changes/subset-rbsr/design.md`: D4 ("own-identity is fully authorized", "same-identity peer") predates multi-identity nodes and must be reread as "a peer holding one of the identities this node hosts"; its proposal's "Unaffected: ingest gate" line and the `sync_two_nodes` repurposing plan also predate this change (the test is deleted, the baseline is ungated)
