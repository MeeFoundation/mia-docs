# Proposal: range-fingerprint-cost

## Why

A pod of 100 member nodes on one laptop keeps up with its writers while it is small and falls behind as it grows: in the ramp at 20 records a second (`mee-pdn/sync-test/load.md`), the median delay from a write to the record readable on the reader `r` grows with the records the pod holds, while the laptop's cores stay above 90% busy.

A profile of `r` and of a writer at 7,500 records names the cost that grows: computing a range's fingerprint. `StoreInstance::get_fingerprint` in `crates/pdn-store/src/store/fs.rs` (marked `TODO: optimize`) reads every entry of the range from redb, builds each `SignedEntry`, and hashes each with BLAKE3 in `SignedEntry::as_fingerprint` (namespace, author, key, timestamp, content hash), for every range of every reconciliation message. A session's first message covers the whole store, and its first split covers it again in parts, so every session costs work linear in the store's size, on both sides, and a record costs many sessions across the pod.

**Example:** the reader `r` sampled for 10 s at 7,500 records, the frames that run rather than wait.

| frame | samples |
|---|---|
| BLAKE3's compression under `as_fingerprint`, under `get_fingerprint` in `sync_process_message` | 1,117 |
| the same under `Message::init`, a session's first message | 112 |
| redb's range cursor, its key decoding and the `SignedEntry` the range yields | about 800 |
| the stores' file syncs | 456 |

| records in the pod | median delay | 95th percentile | laptop busy |
|---|---|---|---|
| 1,000 | 1.6 s | 2.3 s | 81% |
| 5,000 | 5.6 s | 8.3 s | 91% |
| 10,000 | 9.5 s | 12.8 s | 93% |

## What Changes

Nothing is decided. The change settles how a range's fingerprint is computed at a cost below linear in the store, and then specifies and builds it; the fingerprint itself, which both sides of a session compare, stays as it is.

## Open Questions

### How a range's fingerprint stops costing a pass over the range

- **Fingerprints kept in the store's tree.** Each node of an index over a namespace's entries keeps the XOR of the fingerprints below it, updated as an entry is put or replaced, so a range's fingerprint combines a logarithmic number of kept values. The cost moves to every write, which rewrites a path of kept values, and the store's format changes, with no migration for a store an older build wrote.
- **Each entry's fingerprint kept beside it.** The records table keeps the entry's BLAKE3 fingerprint, so a pass reads it instead of hashing; the pass over the range stays, about 40% of the cost measured. The store's format changes as above.
- **The whole namespace's fingerprint kept by the replica's write count.** A session's first message reads it at once; every split after it still passes over its part. Nothing on disk changes.
