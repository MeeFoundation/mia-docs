# Proposal: cross-device-write-order

## Why

Every device of an identity writes with an author of its own: each identity's store creates a random author the first time it opens on a device, under `provision_identity`, and a store on disk keeps it in the `default-author` file at that store's path; linking does not carry it over. The store keeps one entry per author at a key, so a device's write or delete replaces only its own author's entry and leaves every sibling's entry standing beside it. A read picks the entry with the newest timestamp across authors and only then drops it if it is empty (`single_latest_per_key`, whose `LatestPerKeySelector` compares the timestamp and then the content hash, so on equal timestamps the larger hash wins). The timestamp is the writing device's wall clock, with nothing tying it to the entries already at the key. The [connection metadata store](../../specs/components/mee-pdn/data-layer/connection-metadata-store/spec.md) states that rule — "Concurrent edits resolve by last-writer-wins", by the newest timestamp across authors — and states no assumption about clocks.

A write made later on a device whose clock is behind therefore loses to an earlier write of a sibling. For a grant this is a withdrawal that does not withdraw. Alice has two devices; the phone's clock is right, the laptop's is five minutes behind. The phone publishes a grant for Bob at 12:00, and at 12:02 real time the laptop withdraws it through `ConnectionsService::withdraw_grant`:

**Example:** the two entries at `grants/<alice>` after the laptop withdraws the grant.

```
grants/<alice>   author phone    timestamp 12:00:00   grant       ← the read picks it: the newer timestamp
grants/<alice>   author laptop   timestamp 11:57:00   tombstone   ← loses, although written later
```

**Example:** what each party reads and is served after the withdrawal, against what the grant requirement asks.

| after the withdrawal | Alice's phone (published) | Alice's laptop (withdrew) | Bob (audience) | what the grant requirement asks |
|---|---|---|---|---|
| `read_grant` reads the grant | yes | yes | yes | no |
| Bob's data session is served | yes | yes | — | no |
| Bob reads Alice's data under the grant | — | — | yes | no |

No error and no warning reaches anyone. The reverse holds too: a grant published again on a device whose clock is behind a sibling's tombstone never takes effect, and Bob loses access without explanation. The same holds for every other record the identity's devices both write and delete at one key: the pending-device record `pending-devices/<device>`, which the inviting device writes and the new device deletes when it confirms itself (`confirm_device`). A pod's record in the directory is not among them: it is keyed by the identity's sequence in the pod's membership store, and the entry at the highest sequence decides, whatever the timestamps. A published device record and a connection record have deletes in data-layer, `withdraw_device` and `disconnect`, but nothing in pdn-node calls either, so no device deletes them. The grant requirement of the connection metadata store promises that only the last published record is read, which a clock behind breaks.

Under [defect-reachability](../../specs/code-practices/defect-reachability.md) the withdrawal is reached by a host through the public surface of pdn-node — a withdrawal from any device of the identity — under an operating condition, [clocks that disagree](../../specs/code-practices/operating-conditions.md); it obliges a fix.

## What Changes

Nothing is decided. The change settles one question — what orders a device's write at a key against the entries its siblings wrote there — and then specifies and builds the answer. The options are listed under Open Questions, and none of them is chosen.

## Open Questions

### What orders a write against a sibling's entry at the same key

- **A local write is dated past every entry it has seen at the key.** `Replica::insert` and `Replica::delete` take the later of the clock and one past the newest timestamp at the key across all authors, read by the same collapse the read uses. One read on the local write path and a store test with a chosen timestamp through `insert_remote_entry`.
  - A withdrawal, a publication again and any rewrite hold on every device that has seen the earlier entry; truly concurrent writes, neither of which has seen the other, stay last-writer-wins by clock.
  - Every local write path, the future ones of pods included, carries the rule; the timestamp stops being a pure clock reading, shifted by at most the skew the device has observed, and ingest already admits entries up to 10 minutes ahead.
  - The same rule answers a device refusing its own repeated delete after its clock stepped back, since that write too is dated past the device's own tombstone.
  - It is Lamport's clock rule applied to the wall clock, a hybrid logical clock. With no cryptographic binding such a clock is the writer's word, which costs little here: at these keys only the identity's own devices write, and a node acts as every identity it hosts ([threat model](../../specs/components/mee-pdn/threat-model.md)).
- **A withdrawal is a record with a version.** A non-empty withdrawal record with a version at the same key; readers take every author's entries and pick by version. A medium or large change: the format of the grant and of the device record, `read_grant`, `granted_rights`, `device_listed`.
  - A withdrawal stops depending on clocks at all.
  - A second ordering mechanism above the store; an empty entry no longer means "no grant", and the access book no longer reads through `single_latest_per_key`.
- **The condition is documented.** The last-writer-wins requirement of the connection metadata store states the assumption about clocks, and a scenario "published on one device, withdrawn on another" with its paired denial pins today's behaviour.
  - Behaviour does not change; the condition becomes explicit.

The first two options are exclusive: a monotonic timestamp and a version order two ways, and mixing them leaves each record kind ordered by a different rule. The third combines with either. A pod's record in the directory is ordered by a version already, the identity's membership sequence, so under the first option the directory holds records ordered both ways.

**Example:** the withdrawal above, the laptop having seen the phone's grant before it withdraws.

| answer | the laptop's tombstone | `read_grant` after the withdrawal |
|---|---|---|
| dated past what it has seen | 12:00:00.000001 | no grant, on every device |
| a versioned withdrawal record | a withdrawal record, version 2 over the grant's 1 | no grant, on every device |
| documented | 11:57:00 | the grant, on every device |

## Operating conditions

- Clocks that disagree between devices — changes the outcome, and it is the question itself.
- One device or several — changes the outcome: the defect needs a second device of the identity.
- A device linking before, during or after — changes the outcome under the first option: a device that has not yet seen the earlier entry dates its write by its clock alone.
- Capabilities granted, withdrawn and granted again — changes the outcome, as above, in both directions.
- Several identities on one node, a disk that fills, an unstable connection — no change beyond replication.

## Out of Scope

- Ordering entries by a logical clock or a version across the whole store.
- A single author shared by all of an identity's devices, which would make a device's delete replace its sibling's entry: it is ruled out by the per-author rule the store keeps and by the device's own signature being the proof of which device wrote.

## Capabilities

None is settled. Every option modifies `components/mee-pdn/data-layer/connection-metadata-store`; the first adds a requirement on local writes, and the second touches `components/mee-pdn/data-layer/private-metadata-store` as well.

## Impact

- **`crates/pdn-store`**: `Replica::insert` and `Replica::delete` in `sync.rs`, and the store's `CLAUDE.md`, under the first option.
- **`crates/data-layer`**: the grant and device record formats and their readers in `connection_metadata.rs` and `access.rs`, under the second.
