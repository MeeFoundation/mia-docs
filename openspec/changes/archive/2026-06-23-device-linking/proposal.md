# Proposal: device-linking

## Why

The private metadata store is the bootstrap **directory** for an identity (its devices and the tickets to its other stores), but bringing a new device up from it exists only as ad-hoc steps in a test. We want device linking as a recognizable procedure: from a single seed (the private-metadata-store ticket, as carried in a QR), a new device converges on the directory, discovers and imports the rest of the stores, and **joins the device set** so the identity's other devices see it.

## What Changes

- **`SyncNode::node_id()`** — expose a node's on-the-wire identifier (its iroh endpoint id) as a `pdn_types::NodeId`, so a device can register itself.
- **`link_device(node, identity, seed, timeout) -> LinkedStores`** — a procedure that imports the private metadata store from `seed`, registers this device in it, then discovers the connections-store ticket from the directory and imports the connections store. Extensible to the remaining stores; returns the imported stores as a bundle.
- **Device self-registration** — a linking device adds its own `node_id` to the directory; the device set is therefore bidirectional (the existing device sees the new one).
- **Rewrite the two-device test** to drive `link_device` from a single seed and assert the bidirectional device set (both devices appear, on both sides) plus convergence on a discovered store's data.

## Capabilities

| Capability (delta)         | Archive destination                                     |
| -------------------------- | ------------------------------------------------------- |
| `data-layer-device-linking` | `openspec/specs/components/mee-pdn/pdn-node/device-linking.md` |

### New Capabilities
- `data-layer-device-linking`: the single-seed device bootstrap procedure — import the private metadata directory, self-register, and discover/import the identity's other stores through it, in order.

### Modified Capabilities
<!-- none -->

## Impact

- **`crates/data-layer`** (only): `SyncNode::node_id()`; a new `linking` module (`link_device`, `LinkedStores`); the two-device test rewritten. No fork change; `pdn-types` untouched.
- **Out of scope / deferred**: importing data namespaces during linking (ADR-0009 — data addressing in flux); progress events for the gradual bootstrap (the procedure blocks until each store is discoverable, with a caller-supplied timeout); identity-bound linking (the seed is a bearer ticket).
