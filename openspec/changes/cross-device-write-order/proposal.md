# Proposal: cross-device-write-order

## Why

Every device of an identity writes with an author of its own: each identity's store creates a random author the first time it opens on a device, under `provision_identity`, and a store on disk keeps it in the `default-author` file at that store's path; linking does not carry it over. The store keeps one entry per author at a key, so a device's write or delete replaces only its own author's entry and leaves every sibling's entry standing beside it. A read picks the entry with the newest timestamp across authors and only then drops it if it is empty (`single_latest_per_key`, whose `LatestPerKeySelector` compares the timestamp and then the content hash, so on equal timestamps the larger hash wins). The timestamp is the writing device's wall clock, with nothing tying it to the entries already at the key. The [private metadata store](../../specs/components/mee-pdn/data-layer/private-metadata-store/spec.md) states that rule — concurrent mutations of one key on different devices resolve to the entry with the newest timestamp — and states no assumption about clocks.

A write made later on a device whose clock is behind therefore loses to an earlier write of a sibling. For a pending-device record this is a confirmation that does not clear it. Alice has two devices; the phone's clock is right, the laptop's is five minutes behind. The phone answers the laptop's linking dialogue at 12:00 and writes the laptop's pending record; at 12:00:30 real time the laptop confirms itself and deletes that record (`confirm_device`):

**Example:** the two entries at `pending-devices/<laptop>` after the laptop confirms itself.

```
pending-devices/<laptop>   author phone    timestamp 12:00:00   pending     ← the read picks it: the newer timestamp
pending-devices/<laptop>   author laptop   timestamp 11:55:30   tombstone   ← loses, although written later
```

**Example:** what each device reads after the confirmation, against what the requirement asks.

| after the confirmation | Alice's phone (invited) | Alice's laptop (confirmed) | what the requirement asks |
|---|---|---|---|
| `list_pending_devices` lists the laptop | yes | yes | no |
| `list_devices` lists the laptop | yes | yes | yes |

No error and no warning reaches anyone, and the pending record stands until a device's cleanup of expired records deletes it, by its own clock again. The same holds for every record the identity's devices both write and delete at one key, and for every such record a later change brings. A pod's record in the private metadata store (PMS) is not among them: it is keyed by the identity's sequence in the pod's membership store, and the entry at the highest sequence decides, whatever the timestamps.

Under [defect-reachability](../../specs/code-practices/defect-reachability.md) the standing record is reached by a host through the public surface of pdn-node — a link between two devices of one identity — under an operating condition, [clocks that disagree](../../specs/code-practices/operating-conditions.md); it obliges a fix.

## What Changes

Nothing is decided. The change settles one question — what orders a device's write at a key against the entries its siblings wrote there — and then specifies and builds the answer. The options are listed under Open Questions, and none of them is chosen.

## Open Questions

### What orders a write against a sibling's entry at the same key

- **A local write is dated past every entry it has seen at the key.** `Replica::insert` and `Replica::delete` take the later of the clock and one past the newest timestamp at the key across all authors, read by the same collapse the read uses. One read on the local write path and a store test with a chosen timestamp through `insert_remote_entry`.
  - A delete and any rewrite hold on every device that has seen the earlier entry; truly concurrent writes, neither of which has seen the other, stay last-writer-wins by clock.
  - Every local write path, the future ones of pods included, carries the rule; the timestamp stops being a pure clock reading, shifted by at most the skew the device has observed, and ingest already admits entries up to 10 minutes ahead.
  - The same rule answers a device refusing its own repeated delete after its clock stepped back, since that write too is dated past the device's own tombstone.
  - It is Lamport's clock rule applied to the wall clock, a hybrid logical clock. With no cryptographic binding such a clock is the writer's word, which costs little here: at these keys only the identity's own devices write, and a node acts as every identity it hosts ([threat model](../../specs/components/mee-pdn/threat-model.md)).
- **A delete is a record with a version.** A non-empty deletion record with a version at the same key; readers take every author's entries and pick by version. A medium change: the format of the pending-device record and its readers, `list_pending_devices`, `confirm_device` and the cleanup of expired records.
  - A delete stops depending on clocks at all.
  - A second ordering mechanism above the store; an empty entry no longer means "no record", and those readers no longer go through `single_latest_per_key`.
- **The condition is documented.** The last-writer-wins requirement of the private metadata store states the assumption about clocks, and a scenario "written on one device, deleted on another" pins today's behaviour.
  - Behaviour does not change; the condition becomes explicit.

The first two options are exclusive: a monotonic timestamp and a version order two ways, and mixing them leaves each record kind ordered by a different rule. The third combines with either. A pod's record in the PMS is ordered by a version already, the identity's membership sequence, so under the first option the PMS holds records ordered both ways.

**Example:** the confirmation above, the laptop having seen the phone's pending record before it deletes it.

| answer | the laptop's tombstone | `list_pending_devices` after the confirmation |
|---|---|---|
| dated past what it has seen | 12:00:00.000001 | no laptop, on every device |
| a versioned deletion record | a deletion record, version 2 over the pending record's 1 | no laptop, on every device |
| documented | 11:55:30 | the laptop, on every device |

## Operating conditions

- Clocks that disagree between devices — changes the outcome, and it is the question itself.
- One device or several — changes the outcome: the defect needs a second device of the identity.
- A device linking before, during or after — changes the outcome under the first option: a device that has not yet seen the earlier entry dates its write by its clock alone.
- Several identities on one node, a disk that fills, an unstable connection — no change beyond replication.

## Out of Scope

- Ordering entries by a logical clock or a version across the whole store.
- A single author shared by all of an identity's devices, which would make a device's delete replace its sibling's entry: it is ruled out by the per-author rule the store keeps and by the device's own signature being the proof of which device wrote.

## Capabilities

None is settled. Every option modifies `components/mee-pdn/data-layer/private-metadata-store`, and the first adds a requirement on local writes.

## Impact

- **`crates/pdn-store`**: `Replica::insert` and `Replica::delete` in `sync.rs`, and the store's `CLAUDE.md`, under the first option.
- **`crates/data-layer`**: the pending-device record's format and its readers in `private_metadata.rs`, under the second.
