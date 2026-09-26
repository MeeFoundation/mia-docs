## Context

The store keeps one record per namespace, author and key, and the ranger `Store::put` in `crates/pdn-store/src/ranger.rs` inserts an entry only when it compares greater than every entry of its author at a byte prefix of its key, then removes that author's older entries at every longer key starting with its bytes. The comparison reads the prefix entries through `parents` in `store/fs.rs`, which excludes empty entries, so a delete never refuses an older entry at its own key. `Replica::delete_prefix` writes an empty entry at a key and so deletes a whole prefix; the directory's `prune_retractions` is its one caller that relies on the prefix, and every other delete on the platform — a connection, a pending device, a grant, a published device — already addresses one key. Proposal, Why, gives the two defects this produces.

Observed on the unfixed store, before any edit: an older entry offered after a delete at its key replaces the delete, and two replicas holding the delete and the older entry swapped them on each of four sessions, the side that opened alternating. Inferred from the code and not run: the access book classifies a grantee's session by the same grant record, so the publishing device holding the swapped-back record would serve the audience whose grant was withdrawn. A runtime-level run with the empty-entry check deliberately disabled held the withdrawal for 35 seconds, because the audience's pull after the announcement opened the session, the order that converges.

Measured with the empty-entry check disabled, in the data-layer withdrawal scenario: a publishing device opening the session right after the withdrawal caught the swap in 11 of 20 runs, and the cycle of publishing and withdrawing repeated eight times caught it in 8 of 20, each time on the first cycle only. Once the swarm links the publishing device and the audience's device, the audience's pull on the announcement always opens the session first. In the product the swap therefore needs a moment with no gossip link between the publishing device and a device holding the record: a swarm still forming, a link lost, or the publisher's reconcile pass firing before the announcement lands.

An implementation of D1 to D3 sits uncommitted in the working tree. Before any scenario of this change was added, the workspace's tests, the store's other feature sets, its tests marked flaky, the container suite and a 10-iteration stress pass over data-layer, pdn-node and pdn-store scenarios passed on it, with no test outside pdn-store changed.

## Goals / Non-Goals

**Goals:**

- One rule for every replica kind: an entry, empty or not, affects its own key and its own author only.
- A regression test per defect that fails on the unfixed store, and each spec scenario of the deltas backed by a test that fails with its mechanism broken.
- No subscriber, reading or not, holds up the store.

**Non-Goals:**

- Any change to the read side beyond its tie: the latest-per-key collapse across authors, and a key whose newest entry is empty reading as absent, stay as they are.

## Decisions

### D1. An entry affects only its own key

`put` reads the entry of the same author at the same key — an empty one included, from the live store even while a session serves a frozen view — and inserts the new entry when it compares strictly greater, replacing that one; no other key is read or written. `would_insert`, the gate on the rejection echoed to a sender, makes the same comparison. The ranger `Store` trait carries `entry_get` for that one read, beside `entry_put`, and the session store passes both through unfiltered, since ingest is the ingest hook's concern. The comparison is the entry's `Ord`: timestamp, then content hash. The read across authors picks the newest entry at a key by the same order, so two authors' entries with equal timestamps read as the one with the greater content hash, as the data layer's stores specify; `an_equal_timestamp_across_authors_resolves_by_content_hash` pins it.

**Rejected alternatives:**

- Keeping prefix semantics and counting empty entries in the prefix check.
  - **Pros:** fixes the swap alone, with the smallest diff.
  - **Cons:** a write at `contact` still erases `contact/email`; ingest keeps one lookup per byte of the key, up to 8,192 for the longest key the store admits.
- Prefix semantics by path component.
  - **Cons:** a write at `contact` still erases `contact/email`; the store's keys are bytes, and the directory's keys are not entry paths.
- An entry replacing every author's entries at its key.
  - **Cons:** one device's write would erase another device's entry at ingest, which the read side's latest-per-key collapse already hides.

### D2. The delete addresses one key

`Replica::delete` writes an empty entry at one key of one author, and the actor action, `Doc::del` and `DelRequest` carry that key. `del` returns 1 when the empty entry replaced an older entry at the key and 0 otherwise; no caller on the platform reads the count.

### D3. The directory prunes an issuer's markers one key at a time

`prune_retractions` lists the markers this device's author holds under `retractions/<issuer>/` and deletes each at its key. The author scope is the one the prefix delete had: each device drops the markers it recorded, and every device runs the grant binder's unbind for itself when it reads the withdrawal. On one device, recording a marker and pruning an issuer's markers both run under the runtime's state lock, so no marker is recorded between the listing and the deletes. `pruning_an_issuer_drops_every_own_marker_and_spares_a_siblings` in data-layer's `retraction_markers.rs` pins both halves: every own marker of the issuer goes, nested paths included, and a sibling's marker for that issuer stays.

### D4. Every scenario is proven where its mechanism runs

The store's two regression tests prove the rule itself: `an_older_entry_does_not_replace_a_delete_at_its_key`, and `replicas_converge_on_a_delete_whichever_side_initiates`, whose first session is opened by the deleting replica — the order that swapped the two on the unfixed store. The scenario of a delete inside a session gets a store test beside its retraction twin in `net/codec.rs`. The data store's and the directory's scenarios are data-layer scenario tests, each run once with the store's prefix removal put back to see it fail. The withdrawal scenario is a data-layer test whose publishing device opens the session of its own connection metadata store toward the audience's device while that device still holds the record. Two `test-util` hooks on `SyncNode` and the audience node's configuration hold that order: `sync_namespace_as_for_test` opens one session of a replica named by its namespace toward a contact, as `sync_as_for_test` does for a data replica named by its issuer, and `leave_swarm_for_test` takes the audience's replica out of its gossip swarm before the withdrawal through the store's `leave_gossip`, its reconciliation left running, so no announcement makes the audience pull first. The hook holds only until that node's next reconcile pass, which re-joins the swarm and opens the session itself, so the audience's node is spawned with a reconcile interval of an hour and runs no pass during the scenario. Afterwards the audience's data session is refused — the same session that was served before the withdrawal, its paired denial. With the empty-entry check disabled the scenario failed in 20 of 20 runs, and with the rule in place it passed in 20 of 20.

**Rejected alternatives:**

- The withdrawal proven through the runtime's own session order.
  - **Cons:** after a withdrawal the audience's pull on the announcement opens the session, which converges on the unfixed store too; the swap needs the publisher's reconcile pass to fire first, a race a scenario cannot hold.
- The publisher's session alone, the audience's replica left in the swarm.
  - **Cons:** the announcement races the publisher's dial; with the empty-entry check disabled the scenario caught the swap in 11 of 20 runs.
- The cycle of publishing and withdrawing repeated.
  - **Cons:** once the swarm links the two devices the audience always pulls first; eight cycles caught a disabled check in 8 of 20 runs, each on its first cycle.

### D5. The rule is specified where the store is consumed

The deltas state the rule in the data layer's specs — the data store, subset reconciliation, the directory, the connection metadata store — since the store crate's spec specifies no engine behaviour of its own. The store's `CLAUDE.md` records the divergence from upstream's prefix semantics, so that a patch taken from upstream touching `put`, `prefixes_of` or `delete_prefix` is read against it.

### D6. The store waits on no subscriber outside itself

Every subscription carries a delivery. A subscription opened through the store's interface — `Doc::subscribe`, `SyncHandle::subscribe`, `ReplicaInfo::subscribe` — is lossy: an event that finds the subscriber's channel full is dropped, and a `Lagged` event follows the last one the subscriber still receives. The channel's last slot is kept for the notice, so one always fits, and while a notice sits unread every later drop is covered by it, since the subscriber reads it after those events were emitted; a drop after the notice was read gets a notice of its own. The entries a dropped event reported are in the replica when the subscriber reads the notice, and the sessions and downloads it reported are lost. The live engine's subscription to the replica's events is blocking, the actor waiting for room as before, because an announcement of a local write and a queued download have no other trigger; `OpenOpts::subscribe`, the one way to open it, is closed to code outside the crate. The live engine delivers its own events — content arrived, neighbours, sessions finished — to its subscribers the lossy way too: blocked on one of them it would stop taking the replica's events, and the store would wait on it. The replica's event, the live engine's and the interface's `LiveEvent` each gain a `Lagged` variant, which the data layer's change streams report as one change and the directory's catch-up wait passes over.

Found in the review of this change, before it reached main: the withdrawal in the scenario of D7 left the audience's runtime locked for good at 400 markers and unbound at 200 in one second. Reached by modifying the store's subscription to wait for its subscriber, the data-layer scenario `a_subscriber_that_stops_reading_holds_up_no_sync` and the store scenario `an_unread_subscription_holds_up_no_sync` fail, and the store scenario also fails with the live engine's delivery made blocking alone; the unit tests in `subscribers.rs` pin the notice.

**Rejected alternatives:**

- The runtime reading its subscriptions outside the state lock.
  - **Pros:** local to pdn-node; events are not lost.
  - **Cons:** rests on every future subscriber keeping the rule, and one that breaks it stops the store again; covers only the subscribers written that way.
- Deleting the markers after the state lock is released.
  - **Cons:** a marker could be recorded between the listing and the deletes, which D3 rules out; the aged-marker pruning in the armer's own sweep keeps the same wait.

### D7. The runtime's consumers take every buffered change before they sweep

The connection armer and the grant binder read one change from their subscription, take the state lock, then take every change already buffered before the sweep, so the sweep covers them all and a burst — a binder's unbind deleting hundreds of markers — costs one sweep instead of one per change, each of which read every remaining marker. The binder's unbind still deletes the markers under the lock, as D3 needs; the runtime waits on it for as long as the deletes take, a fraction of a second for hundreds. Proven by `a_withdrawal_over_many_markers_leaves_the_runtime_serving` in `pdn-node/tests/scoped_writes.rs`: 400 markers, the withdrawal, the markers gone, and each call on the runtime answered within five seconds; with the store's delivery made blocking it fails on the first probe. The drain itself is not proven by a scenario: it changes the number of sweeps, not their outcome.

## Operating conditions

Walked from `specs/code-practices/operating-conditions.md`:

- One device or several — changes the outcome: the swap needs a second replica that still holds the entry a delete replaced, a sibling or a device of the audience. Backed by the store's convergence scenario and the connection metadata store's withdrawal scenario.
- Capabilities granted, narrowed, widened, revoked and granted again — changes the outcome for a withdrawal, as above. A grant published again after a withdrawal is a newer entry at the same key when the publishing device's clock dates it past the delete, and replaces the delete as before; the existing republication scenario covers it.
- A device that restarts — changes the outcome through the directory: a marker erased by a later marker at a shorter path was gone from the durable store, so a restarted device re-armed without it and admitted the refused entry again. Backed by the directory's marker scenario. A prefix delete already on disk stops acting on longer keys; the proposal leaves stores written before this change unmigrated.
- Several identities on one node — no change: each identity writes with its own author into its own replica store, and the rule is per author.
- A device linking before, during or after — no change beyond several devices: a device that catches up from a replica still holding a deleted entry receives it and then the delete, like any sibling.
- An unstable connection — changes the outcome on the unfixed store: a lost gossip link is one of the moments in which the publishing device opens the session first. The withdrawal scenario takes the link away through the swarm hook.
- A disk that fills — no change: a delete is one write, delivered or failed like any other.
- Clocks that disagree and step back — changes the outcome on one device: a delete repeated after its clock stepped back is dated before the device's own tombstone at the key and refused with `NewerEntryExists`, for a state it has already reached — a repeated withdrawal, a `confirm_device` repair after a restart. Left open: the fix is a platform decision about local timestamps.
- A consumer that stops reading its subscription, or reads it only after a lock it waits on — changes the outcome: the store stopped behind it. Backed by the change-subscription scenarios and the withdrawal scenario of D7.

## Risks / Trade-offs

- [A prefix delete already on disk loses its reach, and nodes on either side of the change disagree on writes at nested keys] → No real users and no mixed fleet; the proposal names both as out of scope.
- [Entries at longer keys no longer disappear when their author writes a shorter key] → Nothing on the platform relied on it: the data store has no delete, the connection metadata store's keys never nest, and in the directory only the retraction markers nest, which the marker scenario covers.
- [The runtime-level swap rests on a race, and the withdrawal scenario reaches it through two test-only hooks] → One hook opens an ordinary session from the side the product's reconcile pass also dials from, the other leaves the swarm through the store's own `leave_gossip`, which a scoped data import already calls; the store's regression test pins the mechanism without the runtime.
- [A stress pass of 10 iterations is below what the flaky-tests practice asks for a store change] → The apply ends with the full stress pass.
- [An event that no longer fits a subscriber's buffer is dropped] → The subscriber learns it from the notice and reads the replica again; the platform's consumers already reread on every change. A session event lost this way delays a directory's catch-up wait by one reconcile interval, and only when the watch was left unread past its buffer.
- [The notice's accounting assumes the store is the channel's only producer] → Every channel the store is handed is created for the subscription alone; a caller sending into it too can miss a notice, never block the store.

## Migration Plan

No data migration. The change rolls back by reverting it: the stored record format and the sync messages are unchanged.
