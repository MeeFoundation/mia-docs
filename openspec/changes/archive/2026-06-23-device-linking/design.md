# Design: device-linking

## Context

`PrivateMetadataStore` already exists: a device-internal replica holding an identity's devices and the typed tickets to its other stores (`tickets/<kind>`), admitted by Invariant 1. What's missing is the *procedure* that uses it as a bootstrap directory. Today the two-device test wires the steps by hand.

## Goals / Non-Goals

**Goals:**
- One procedure, `link_device`, that brings a new device up from a single seed.
- The new device joins the device set (self-registration), visibly to existing devices.
- No fork change; reuse the existing stores and Invariant 1.

**Non-Goals:**
- Importing data namespaces during linking (ADR-0009 — data addressing in flux). The directory already stores arbitrary typed tickets, so this extends without redesign.
- Streaming progress events. The procedure blocks until each store is discoverable, bounded by a caller-supplied timeout.
- Identity-bound linking / sealing the seed. The seed is a bearer ticket.

## Decisions

### D1. The seed is the private-metadata-store ticket (the QR payload)

Linking transmits exactly one ticket out of band — the private metadata store's. Everything else (connections, later data) is discovered from inside it. So a QR carries one bearer ticket; the directory expands it.

*QR direction (bearer model):* the existing device displays the seed, the new device scans it — the holder of the directory hands access to the newcomer. Under identity-bound access (UWill) this inverts: the new device presents its identity and the existing device authorizes it, with no bearer secret on screen.

### D2. Staged bootstrap, directory-first

`link_device(node, identity, seed, timeout)`:
1. Import the private metadata store from `seed`.
2. Register this device — `add_device(node.node_id())`.
3. Wait (up to `timeout`) for the `connections` ticket to appear in the directory, then import the connections store.
4. Return `LinkedStores { private_metadata, connections }`. Further stores extend step 3.

Ordering is intrinsic: a store can only be imported once its ticket has synced into the directory, so the directory necessarily comes first. The procedure returns once stores are imported; convergence on their *contents* is ongoing sync the caller observes.

### D3. `node_id` from the endpoint

`SyncNode::node_id()` returns `NodeId::from_bytes(*router.endpoint().id().as_bytes())` — the iroh endpoint id (an ed25519 public key) as a `pdn_types::NodeId`. Self-registration writes a real, reachable id, not a placeholder.

### D4. Bidirectional device set

Because the directory replicates between the identity's devices and both run Invariant 1, the new device's `add_device` propagates back: the existing device sees the newcomer, and the newcomer sees the existing device. The device set converges on every device.

## Risks / Trade-offs

- **[Blocking wait shape]** `link_device` blocks until the connections ticket is discoverable → bounded by the caller's `timeout`; a stalled directory surfaces as a timeout, not a hang. Progress events are future work.
- **[Bearer seed in the QR]** a photographed QR grants access; identity-bound linking is the fix, deferred to UWill.
- **[Online-window overlap]** linking needs both devices reachable while the directory and stores sync; relay stores nothing. Out of scope here.
