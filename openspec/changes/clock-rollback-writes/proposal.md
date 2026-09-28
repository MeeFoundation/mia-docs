# Proposal: clock-rollback-writes

## Why

A device dates each of its writes by its own clock, and the store keeps, per author and key, the entry that compares greatest — timestamp first, then content hash. A local write compares against the device's own entry at the key, an empty one included, and one that does not compare greater is refused: `Replica::delete` and `Replica::insert` take the timestamp from the wall clock, and `insert_entry` in `crates/pdn-store/src/sync.rs` turns the refusal into `InsertError::NewerEntryExists`. Two deletes at one key have the same content hash, so the timestamp alone decides between them. Nothing above the store tells that refusal apart from a failure.

A clock that steps back — a time server correcting it, the person setting it by hand, a phone booting without a battery-backed clock — therefore makes a device refuse its own repeated act. Each device writes with an author of its own, so a clock that differs between siblings does not lead here; the step has to happen on the device itself.

**Example:** A host repeating `withdraw_grant` after its first call timed out, on a device whose clock stepped back five minutes in between: Alice (issuer) withdraws Bob's read grant on her device a1; the grant record's key is `grants/<alice>`.

```
12:00:00  withdraw_grant   tombstone at grants/<alice>, timestamp 12:00:00       Ok
          the clock steps back five minutes; the host did not see the answer and repeats the call
11:55:03  withdraw_grant   tombstone at grants/<alice>, timestamp 11:55:03
          compared with 12:00:00 → not greater → refused                        Err(NewerEntryExists)
```

The grant is withdrawn, and the call reports an error the host cannot tell from a store failure. `PrivateMetadataStore::disconnect` and `ConnectionMetadataStore::withdraw_device` would refuse a repeat the same way, but nothing in pdn-node calls either of them, so no host repeats them.

**Example:** A newly linked device confirming itself, killed between the two writes of `confirm_device` in `crates/data-layer/src/private_metadata.rs` — the delete of its pending record, then the write of its device record — and restarted with its clock ten minutes behind.

```
10:00:00  confirm_device: delete pending-devices/<laptop>, timestamp 10:00:00          ok
          the process is killed before add_device; after the restart the clock reads 09:50:00
09:50:10  sweep → confirm_device → delete pending-devices/<laptop>                     refused; add_device not reached
…         the same on every sweep
10:00:01  sweep → the delete passes → add_device writes devices/<laptop>               siblings start dialing the laptop
```

Until the clock passes the timestamp of its own tombstone, the device is not in its identity's device set, and its siblings do not reach it as one of the identity's devices. The delay is bounded by the size of the step.

A write replacing the device's own entry at the key is exposed the same way, whether that entry holds a record or is a tombstone. A grant published again with `publish_grant` on the device that withdrew it, on a clock behind the withdrawal, is refused with `NewerEntryExists` until the clock passes the device's own tombstone. Published from a sibling, whose author has no entry at the key, the same grant is written and then loses to the tombstone on every replica, as any older entry does; that order is set by the clocks of two devices, not by a step back on one.

Under [defect-reachability](../../specs/code-practices/defect-reachability.md) both paths, the repeated `withdraw_grant` and the `confirm_device` the sweep repeats, are reached by a host through the public surface of pdn-node under an operating condition, [a clock that steps back](../../specs/code-practices/operating-conditions.md), which obliges a fix. `disconnect` and `withdraw_device` are reached neither way while no operation of pdn-node calls them, and the first operation that does makes them reachable in the same way.

## What Changes

Nothing is decided. The change settles one question — what a device's local write does when its clock dates it before the device's own entry at the key — and then specifies and builds the answer. The options are listed under Open Questions, and none of them is chosen.

## Open Questions

### What a local write dated before the device's own entry does

- **A local delete of a key already deleted by this author succeeds.** `Replica::delete` answers a refusal over this author's own tombstone at the key as the state it asked for, and returns 0; ingest from a peer stays strict. About 10 lines and a store test with a chosen timestamp. The later tombstone stays and wins on every replica. A non-empty write dated before the device's own entry is still refused.
- **A device's own history at a key is monotonic.** Every local insert and delete takes the later of the clock and one past the timestamp of this author's entry at the key, an empty one included. 10 to 15 lines and tests. Every rewrite of the device's own entry passes whatever its clock does; the order against other authors' entries hardly changes. Another divergence from upstream, recorded in the store's `CLAUDE.md`. It is the rule the KERI Request Authentication Mechanism (KRAM) keeps per sender — a request is accepted only with a timestamp later than the last one accepted from the same sender — applied by the writer to itself ([KRAM](https://hackmd.io/@SamuelMSmith/B1A5jlKXd)).
- **A local write is monotonic at its key across every author.** The same, taking the latest entry at the key over all authors, read through the latest-per-key collapse the read side uses. One more read on the local write path. This also closes the case of a record withdrawn from a device whose clock is behind the one that published it, where the withdrawal loses to the record it withdraws; the timestamp then stops being a pure clock reading, shifted by at most the skew the device has observed, and ingest already accepts entries up to 10 minutes ahead.
- **The refusal stays and is documented.** The [data store](../../specs/components/mee-pdn/data-layer/data-store/spec.md) requirement "A write affects only its own path" says that a local write dated before the device's own entry at the path is refused, and the host repeats its act later. KRAM waits the same way on the receiving side: a recipient whose clock reads earlier than the latest time it has seen refuses every request until its clock catches up.

**Example:** the repeated withdrawal above, second call at 11:55:03 on the device's clock.

| answer | the call returns | the tombstone kept | a later `publish_grant` at 11:56 |
|---|---|---|---|
| a repeated delete succeeds | `Ok` | 12:00:00 | refused, `Err(NewerEntryExists)`, until 12:00:00 |
| own history monotonic | `Ok` | 12:00:00.000001 | dated past the tombstone, and wins |
| monotonic across authors | `Ok` | 12:00:00.000001 | dated past the tombstone, and wins |
| documented | `Err(NewerEntryExists)` | 12:00:00 | refused, `Err(NewerEntryExists)`, until 12:00:00 |

## Operating conditions

- A clock that steps back — changes the outcome, and it is the question itself.
- The process ends without warning — changes the outcome: it is what leaves `confirm_device` between its two writes.
- One device or several — changes the outcome only for the option across authors: siblings' clocks then shift one another's timestamps.
- Several identities on one node, a disk that fills, an unstable connection, a device linking late — no change: each is a local write of one author.

## Out of Scope

- Ordering entries by anything but their timestamps, a version or a logical clock among them.

## Capabilities

None is settled. The documenting option modifies `components/mee-pdn/data-layer/data-store`; the others add a requirement of their own on local writes.

## Impact

- **`crates/pdn-store`**: `Replica::delete` and `Replica::insert` in `sync.rs`, and the store's `CLAUDE.md` for a monotonic option.
