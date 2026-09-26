## Why

pdn-store inherits iroh-docs' prefix semantics: an entry removes the same author's older entries at every longer key that begins with its bytes, and an entry arriving later is refused when the author holds a newer one at any byte prefix of its key. Nothing on the platform uses that, and it has two defects a host reaches through pdn-node. A write at a data-store path erases, on every replica, the same device's earlier entries at longer paths sharing its bytes — `contact` erases `contact/email`, and `contacts/emergency` too, since the prefix is a byte prefix and not a path component — and a retraction marker at `contact` erases the marker at `contact/email` the same way. And the check that refuses an older entry skips empty entries, so an older entry offered after a delete at the same key replaces the delete: when the publishing device opens the next session toward a device still holding a withdrawn grant record, the two swap the record and the delete, and every later session swaps them back. The publishing device then reads the grant again, and its access book, which classifies sessions by the same record, would serve the audience whose grant was withdrawn.

Pruning an issuer's markers one key at a time, which the per-key rule needs, exposes a third defect the store already had. The store waits for every subscriber of a replica to take each event, and the runtime's grant binder prunes under the runtime's state lock, while the connection armer that reads the directory's events waits on that same lock. After a withdrawal reaching an audience that holds more than about 320 of the issuer's markers, the store stops at the delete whose event no longer fits, the binder never gets its answer, and every call of the runtime waits on the lock for good, across all its hosted identities; a restart does not bring the unbind back. An issuer that refuses every write of an honest audience and then withdraws reaches that on purpose.

## What Changes

- An entry, empty or not, affects only its own key, per author: it replaces the entry at that key when it is newer, an empty one included, and touches no other key. An entry is refused only by a newer or equal entry at its own key.
- The store's delete addresses one key. The prefix delete leaves the store, the Replica, the actor and the API (`delete_prefix` becomes `delete`; `DelRequest` carries `key`).
- The directory's pruning of an issuer's retraction markers deletes this device's markers for that issuer one key at a time.
- The store's ingest reads the entry at one key instead of every byte prefix of it: one lookup per entry where the current store makes one per byte of the key.
- Tests of prefix deletion itself are rewritten for deletion at one key; the regression tests of both defects fail on the current store.
- The store waits on no subscriber outside itself: a subscription opened through its interface drops what its full buffer cannot take and receives a lag notice after the last event it still gets; only the store's live engine subscribes with a delivery that waits. The live engine's own events reach their subscribers the same lossy way.
- The directory's and the connection metadata store's change streams report a lag notice as a change; the directory's catch-up wait goes on to the next session when it missed one.
- The connection armer and the grant binder take every change already buffered before they sweep, so a burst of changes costs one sweep.

Out of scope, by decision:

- Stores written before this change are not migrated, and nodes on either side of it are not expected to sync with each other: a prefix delete already on disk stops acting on longer keys. The platform has no real users.
- `disconnect` in the directory has the same exposure as grant withdrawal, but no host reaches it through pdn-node; the store's rule covers it, and it gets no scenario of its own.

## Capabilities

### New Capabilities

- `components/mee-pdn/data-layer/change-subscription`: a subscriber never holds up the store, dropped events leave a lag notice, and a change stream reports every change, a burst as one.

### Modified Capabilities

- `components/mee-pdn/data-layer/subset-reconciliation`: the removal requirement speaks of a delete at one key, which no older entry at that key replaces, and gains the scenario of a delete converging whichever side opens the session; the requirement is replaced under a new name, since its prefix-delete scenario describes nothing.
- `components/mee-pdn/data-layer/data-store`: a new requirement — a write affects only its own path; a write at a shorter path leaves the entries at longer paths standing.
- `components/mee-pdn/data-layer/connection-metadata-store`: the grant requirement gains the scenario of a withdrawal holding against a device that still holds the withdrawn record, the audience refused afterwards.
- `components/mee-pdn/data-layer/private-metadata-store`: the retraction-marker requirement gains the scenario of a marker at a path leaving the markers at longer paths, and prunes by issuer the device's own markers.
- `components/mee-pdn/data-layer/durable-storage`: the one-author requirement's prose speaks of replacement and deletion scoped to the writing author, without prefix deletion.
- `components/mee-pdn/data-layer/write-retraction`: the marker requirement says that a forgotten binding makes each device drop the markers it recorded for that issuer, as the private metadata store states.
- `components/mee-pdn/data-layer/private-metadata-store`: the catch-up wait requirement says that a session whose event the wait dropped goes unseen, and the wait returns on the next one.
- `components/mee-pdn/pdn-node/core`: the binding requirement gains the scenario of a withdrawal over more retraction markers than a subscription buffers, the runtime answering afterwards.

## Impact

- `crates/pdn-store`: the ranger `Store` trait (`entry_get` in place of `prefixes_of` and `remove_prefix_filtered`, `put` and `would_insert` over one key), the fs store and the session store beneath it, `Replica::delete`, the actor's delete action, `Doc::del` and `DelRequest`. The wire protocol and the sync messages do not change.
- `crates/pdn-store`, subscriptions: the `subscribers` module with its two deliveries, a `Lagged` event in the replica's, the live engine's and the API's event types, `OpenOpts::subscribe` closed to code outside the crate.
- `crates/pdn-node`: the connection armer and the grant binder take the buffered changes before each sweep; a scenario test of a withdrawal over 400 markers.
- `crates/data-layer`: `prune_retractions` in the directory; the change streams mapping the lag notice to a change; new scenario tests for the data store, the connection metadata store and the directory, and a test-only hook that opens one session of a metadata store from a chosen side.
- Documentation: the store's `CLAUDE.md` records the divergence from upstream; the archived changes that name the removed trait methods or prefix deletion (frozen-session-snapshots, disk-persistence, identity-scoped-replicas) are rewritten as present state.
