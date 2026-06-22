# Tasks: device-linking

## 1. Node identity

- [x] 1.1 `SyncNode::node_id() -> NodeId` (`router.endpoint().id()` → `pdn_types::NodeId`)

## 2. Linking procedure

- [x] 2.1 New `linking` module: `LinkedStores { private_metadata, connections }`
- [x] 2.2 `link_device(node, identity, seed, timeout) -> LinkedStores`: import private metadata store → `add_device(node.node_id())` → wait (≤ timeout) for the `connections` ticket → import connections store
- [x] 2.3 Re-export `link_device` / `LinkedStores` from the crate

## 3. Test

- [x] 3.1 Rewrite `private_metadata_two_devices` to drive `link_device` from a single seed; existing device self-registers too
- [x] 3.2 Assert the bidirectional device set (both devices, on both sides) and convergence on the discovered connections store (Bob)
- [x] 3.3 Lints + flake check (`just check`; loop the test ≥8)

## 4. Documentation

- [x] 4.1 Audit every `Invariant 1` reference in code/docs to read as enforcement ("we run X to enforce Invariant 1"), never reliance on a convention
- [ ] 4.2 On archive: place the capability spec at `components/data-layer/device-linking.md`
