## Context

A record's payload enters the runtime through `put_record` in `crates/pdn-node/src/pods.rs` as `&[u8]`, and the data layer's `write_pod_entry` hands pdn-store's `Doc::set_bytes` a copy of it, which iroh-blobs' file store writes to a temp file of its own and moves into its data directory once the payload is whole. `read` answers `Vec<u8>`: `read_pod_record` takes the store's bytes with `get_bytes` and copies them. `put_record` holds the runtime's state lock from the read of the identity's membership to the write of the entry, so two writes of one identity number their keys in turn. iroh-blobs already imports a payload from a stream (`add_stream`) and reads one in order (`reader`, a tokio `AsyncRead`), both through the temp file and the data file without holding the payload in memory.

## Goals / Non-Goals

**Goals:**

- A record placed and read with no copy of its whole payload in memory, at any layer of the runtime.
- A placing that waits on its host holds up no other call of the runtime.
- Nothing written for a stream that fails, and nothing left referenced by it.

**Non-Goals:**

- Reading from an offset, or reading a payload that is not yet whole on the device.
- Streaming a mergeable-document's operations.

## Decisions

### D1. The payload goes into the blob store before the runtime's lock is taken

`put_record_streamed` takes the state lock to check that the identity is a member of the pod and releases it at once. It then imports the stream into the blob store, takes the lock again, checks the membership again, numbers the record's key exactly as `put_record` does (`fresh_record_key`) and writes the entry. A non-member's stream is refused before a byte of it is read, and a member removed while its stream was read places nothing, since the second check is the one the write rests on.

**Example:** Bob's phone b1 places a scan of 100 MiB in "Family" from a stream its host feeds from the file at 20 MB/s, so the import takes about 5 seconds.

| second | b1's runtime |
|---|---|
| 0 | the lock taken, Bob a member, the lock released; the import starts |
| 2 | a claim Bob places through `put_record` takes the lock and is written |
| 5 | the import ends; the lock taken, Bob still a member, the scan's entry written |

**Rejected alternatives:**

- The lock held from the first check to the write.
  - **Cons:** a stream fed at the host's pace, or one that never ends, holds every call that takes the lock — every placing, act and join of every identity on the node.
- The membership checked at the write alone.
  - **Cons:** a non-member's whole stream is read and stored before it is refused.

### D2. An imported payload is held by its temp tag until its entry is written

The data layer's `import_payload` answers an `ImportedPayload`: the temp tag iroh-blobs hands out once the payload is whole, and its length. pdn-store's `Doc::set_imported` takes that tag beside the author and the key, writes the entry as `set_bytes` writes its own, and hands the tag to the engine's held payloads, which keep it until the next collection reads the replicas. iroh-docs upstream offers `Doc::set_hash(author, key, hash, size)`, which writes an entry for a payload already in the store and leaves protecting the payload to its caller; no open pull request there changes that.

**Example:** what keeps Bob's scan from blob collection, moment by moment.

| moment | what holds the scan |
|---|---|
| the import has ended | the temp tag inside the `ImportedPayload` |
| the entry is written | the engine's held payloads, until the next collection reads the replicas |
| that collection has read them | the entry |

**Rejected alternatives:**

- An entry written by hash and length, as upstream's `set_hash`.
  - **Cons:** a collection run between the import and the write sweeps the payload, and the entry then names a payload the device does not hold.
- One call of pdn-store that imports the stream and writes the entry.
  - **Cons:** it leaves no point between the import and the write at which the runtime takes its lock and checks the membership again.

### D3. A reader reads a whole payload in order, held against collection

`read_streamed` checks the membership as `read` does and answers `None` where `read` does: for a record no entry of which reads here, and for one whose newest entry's payload is not yet whole on the device. Otherwise it answers a `PayloadReader` holding a temp tag on the payload and an iroh-blobs reader of it: `len` answers the payload's length before anything is read, and each `read(max)` answers up to `max` of the next bytes, an empty answer once the payload is read whole. The tag keeps the payload for as long as the reader lives, so a reader is not cut short by a collection that runs after the pod was left.

**Example:** a reader of a payload of 3 MiB read in pieces of 64 KiB answers 48 pieces of 65,536 bytes and then an empty one, and `len` answers 3,145,728 before the first.

**Rejected alternatives:**

- The payload exported to a path the caller names.
  - **Cons:** a whole copy of the payload on disk, outside the store, that the host has to remove, written to its last byte before the host can show its first.

### D4. A stream that fails is written nowhere

A stream that yields an error ends the import with that error, and `put_record_streamed` fails with it before it takes the lock a second time. What the import had written lies in the blob store's temp directory, named by no entry and by no temp tag, and the next start of the node removes it (iroh-blobs-010).

**Example:** a stream that yields 2 pieces of 1 MiB and then an error: the call fails, the pod lists the records it listed before, and a temp file of 2 MiB stays in `blobs/temp/` until the node starts again.

## Operating conditions

- **A disk that fills:** the import fails partway, the call fails, and nothing is written (D4).
- **A device that restarts:** an import cut by the restart wrote no entry; its temp file goes at the next start.
- **A membership that moves:** a member removed during its stream places nothing, by the check at the write (D1).
- **Several identities on one node:** each call names its identity and checks that identity's membership, as `put_record` does; the lock D1 releases is the one every identity shares, which is why it is not held across the stream.
- **An unstable connection** and **clocks that disagree** change nothing here: an import and a read are local, and the entry carries the timestamp `put_record` gives its own.

## Risks / Trade-offs

**A reader keeps its payload for as long as it lives.** A host that never releases a reader of a record of a pod it has left keeps that payload on disk until the reader goes, and a node's stop ends every reader's reads with an error.

**A stream that never ends keeps its import open.** The temp file and the task stay until the host ends or drops the stream; the runtime sets no deadline on a host's own pace.

## Migration Plan

Nothing to migrate: both calls are new, and `put_record` and `read` are unchanged.

## Open Questions

None.
