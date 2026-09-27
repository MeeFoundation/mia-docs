# Proposal: retraction-marker-lifetime

## Why

A retraction marker belongs to the device that recorded it. Each device writes its markers with its own author, and both prunes filter by that author: `prune_aged_retractions` in the directory ages out only the markers whose author is this device's, and `prune_retractions`, run by the grant binder's unbind, lists and deletes only this device's markers for the issuer. A sibling that read a marker arms an ingest refusal from it, and the refusal is taken down only by what its own prune returns (`apply_retractions` in pdn-node): arming only ever widens, and a marker that disappears from the listing leaves its refusal standing.

Two cases follow on an identity with two devices, a phone and a laptop. Bob, the issuer, refuses a write of the phone at `notes/x`; the phone records the marker `retractions/<bob>/<phone-author>/notes/x`, its bound the refused entry's timestamp t1 in microseconds, and the laptop reads it, arms the refusal and retracts its copy. In the first case, 14 days later the phone ages the marker out; the laptop no longer lists it but keeps refusing, until it restarts or forgets Bob's namespace. In the second case the phone is lost before the 14 days pass; nothing ever deletes its marker — no device ages it out and no device's unbind prunes it — and the laptop arms the refusal again every time it binds Bob's namespace.

The harm shows where the issuer holds an entry the marker matches — Bob accepted an earlier value of the phone at `notes/x`, timestamp at or below t1, and serves it. The operation below is taking in that entry at ingest:

**Example:** Bob's earlier value at `notes/x` taken in at ingest, in the first two cases.

| moment | phone | laptop | a refusal that ends with the marker's retention |
|---|---|---|---|
| day 0, marker recorded | refused | refused | refused |
| day 14, the phone ages its marker out | accepted | refused | accepted |
| the laptop restarts after day 14 | accepted | accepted | accepted |
| the phone lost before day 14; day 30, the laptop binds Bob again | — | refused | accepted |

A third case needs one device only. The grant binder's unbind (`unbind_withdrawn` in pdn-node) forgets the issuer's namespace, then deletes the device's markers for that issuer one key at a time; it drops the result of that pruning, and removes its record of the binding whatever the pruning did — a record that lives in memory alone. A process killed between two of those deletes, or a delete refused by a full disk, leaves the rest of the markers standing, and nothing deletes them again: after a restart there is no record of the binding to unbind, and the markers go only when their retention ends. Bob withdraws the grant while the laptop holds five markers for him; the laptop forgets Bob's namespace, deletes two markers and is killed. After the restart three markers are still listed, and when Bob grants again before day 14 the laptop arms their refusals on its first sweep and refuses the earlier value Bob accepted and serves.

**Example:** the laptop's unbind of Bob (issuer), five markers for him; the record of the binding is in memory, so no restart finds it.

| step of `unbind_withdrawn` | markers listed after a kill right after it and a restart |
|---|---|
| 1. `forget_namespace` drops Bob's replica | 5 |
| 2. `prune_retractions` deletes marker 1 | 4 |
| 3. `prune_retractions` deletes marker 2 | 3 ← the case above |
| 4. `prune_retractions` deletes markers 3 to 5 | 0 |
| Bob grants again on day 3: the binder's sweep that imports his replica arms the listed markers' refusals, and the laptop refuses Bob's earlier value | |

[Write retraction](../../specs/components/mee-pdn/data-layer/write-retraction/spec.md) and the [private metadata store](../../specs/components/mee-pdn/data-layer/private-metadata-store/spec.md) state this behaviour as it stands, and the directory's tests pin it, author scope included: a device prunes only the markers it recorded, and a refusal it armed from a sibling's marker comes down only when it restarts or forgets the issuer's replica. The consequence falls on the accepted window of a wrong verdict, which write retraction describes: the marker's retention bounds it on the device that recorded the marker, a sibling goes on refusing past that retention until it restarts or forgets the replica, and the marker of a device that never runs again leaves it without a bound. The question is what bounds a marker's life, and the refusals it arms, on every device of the identity.

Under [defect-reachability](../../specs/code-practices/defect-reachability.md) the first case is reached by a host through the public surface of pdn-node, on the product path of an identity with more than one device; it obliges a fix. The second needs a device that never runs again, which the platform cannot yet revoke. The third is reached by a host under an operating condition — [the process ends without warning](../../specs/code-practices/operating-conditions.md), the ordinary end of an app on a phone, or a disk that fills — and obliges a fix too.

## What Changes

Nothing is decided. The change settles two questions — whose lifetime a retraction marker has, the lifetime of the device that recorded it or the lifetime of the identity, and what removes the markers an interrupted unbind left — and then specifies and builds the answers. The options are listed under Open Questions, and none of them is chosen.

Every option includes one piece: the refusals a device armed are derived from the markers it lists, so a sweep that no longer lists a marker takes its refusal down. Without it the first case stays open under either answer. That piece leaves the third case open: the markers an interrupted unbind leaves are still listed, so it asks a question of its own, below.

## Open Questions

### Whose lifetime a marker has

- **The identity's.** Every device ages out every marker it lists, whatever its author, judged by the marker entry's timestamp, and writes a tombstone of its own at the marker's key; the unbind prunes the issuer's markers of every author. The read side's latest-per-key collapse already picks the newest entry across authors before it drops empty ones, so one device's tombstone ends the marker on every device. About 50 lines and two scenarios: age-out on two devices, and the marker of a device that is gone.
  - The first case closes without a restart, and the second closes at the retention of any surviving device.
  - The accepted window is bounded by retention on every device.
  - A marker's end is decided by whichever device's clock passes the retention first, and there are as many tombstones as devices times markers in the worst case.
- **The recording device's.** Author scope stays; the refusals are derived from the listing, as above. The limit write retraction and the private metadata store state stays: a marker of a device that never runs again is pruned by no device, and its refusal stands whenever the identity binds the issuer's namespace. About 15 lines and a sentence of spec for the refusals derived from the listing.
  - The first case closes; the second stays, recorded as an accepted limit.
  - The accepted window stays without a bound for the marker of a device that is gone, as write retraction states.

**Example:** the two answers on the table above, second case — the phone lost before day 14.

| day 30, the laptop binds Bob again | the identity's lifetime | the recording device's lifetime |
|---|---|---|
| the phone's marker | gone: the laptop aged it out on day 14 | still listed |
| the laptop takes in Bob's earlier value | accepted | refused |

### What removes the markers an interrupted unbind left

- **A sweep prunes the markers of an issuer whose grant reads withdrawn.** The armer's sweep deletes this device's markers — every author's, under the identity's lifetime — for an issuer whose grant record toward the identity reads absent in the counterparty's connection metadata store. The evidence is durable, so a restart meets it again; the absence of a binding in memory is not evidence, since right after a restart no issuer is bound yet and a marker waiting for its binding would go with it.
  - Closes the kill and the full disk alike, at the next sweep once the disk has room.
  - The sweep reads the grant records of every connection, a read only the binder makes as the code stands.
- **The unbind keeps its record until the pruning went through.** The binder removes its record of the binding only when `prune_retractions` returned without error, and retries on its next sweep.
  - Closes the full disk; the kill stays open, since the record is in memory and a restart loses it.
- **The markers wait out their retention.** Write retraction's statement that an interrupted unbind leaves the rest of the device's markers for the issuer until they age out stays, as an accepted limit.
  - Nothing to build; a grant made again within the retention meets the stale refusals.

**Example:** the five markers above, Bob granting again on day 3.

| after the restart, day 3 | a sweep by the withdrawn grant | the unbind retries | wait out the retention |
|---|---|---|---|
| the three markers left | gone at the first sweep after the restart | still listed: the record went with the process | still listed until day 14 |
| the laptop takes in Bob's earlier value | accepted | refused | refused |

This question and the first combine freely: under the identity's lifetime a sweep prunes every author's markers for the withdrawn issuer, under the recording device's only its own.

## Operating conditions

- One device or several — changes the outcome: the first two cases need a second device.
- A device that restarts — changes the outcome: a refusal is in-memory state, so as the code stands a restart takes it down; the derived refusals make a sweep do it.
- A device that is lost — changes the outcome, and it is the question itself.
- Capabilities granted, narrowed and revoked — a bare re-grant of write does not prune a marker under either answer, as the private metadata store requires.
- Several identities on one node — no change: markers live in the directory of the identity whose author they name.
- The process ends without warning — changes the outcome: a kill between two of the unbind's deletes is the third case.
- A disk that fills — changes the outcome: a delete it refuses leaves the rest of the markers, as a kill does.
- An unstable connection, a device linking late — no change beyond replication: a late device reads the markers and the tombstones like any directory entry.

## Out of Scope

- Revoking a device. Under the recording device's lifetime it would be the way a lost device's markers go; it is a change of its own.
- The accepted window of a wrong verdict itself, which write retraction leaves open with three options of its own.

## Capabilities

None is settled. Either option modifies `components/mee-pdn/data-layer/write-retraction` and `components/mee-pdn/data-layer/private-metadata-store`, and adds scenarios to both.

## Impact

- **`crates/data-layer`**: `prune_aged_retractions` and `prune_retractions` in `private_metadata.rs` under the identity's lifetime.
- **`crates/pdn-node`**: `apply_retractions` in `retraction.rs` deriving the refusals from the listing, under either answer; `unbind_withdrawn` in `connections.rs` and the armer's sweep, under the answer to the interrupted unbind.
