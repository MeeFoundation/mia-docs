# Proposal: streamed-payloads

## Why

A record's payload crosses the runtime as one buffer: `put_record` takes `&[u8]` and `read` answers `Vec<u8>`, and the data layer copies each once more, `set_bytes(…, payload.to_vec())` in `write_pod_entry` and `get_bytes(hash).await?.to_vec()` in `read_pod_record`. A host that lets a person place a file — the mobile host takes an immutable-document of up to 100 MiB — therefore holds the file whole several times at once while it places it and again while it shows it, and a host over a binding adds the binding's own copies to the runtime's. On a phone memory is the operating condition that ends the process rather than slowing it: Android caps the managed heap of an application at a few hundred megabytes whatever the device holds, so a second copy of a file beside the first is enough to stop the application.

**Example:** an immutable-document of 100 MiB placed and read back through the mobile host, as it stands and with this change.

| where | `put_record` and `read` | a stream |
|---|---|---|
| the host's own language | the whole file, 100 MiB | one piece at a time, at most 1 MiB |
| the binding | two more copies of the whole file for a moment | one piece |
| the runtime | one more copy for the whole write; on a read the store's bytes and a copy of them | one piece: the blob store writes the payload to a temp file of its own and reads it back from there |

A host that shows a file also needs it in order and rarely needs all of it at once: a picture is decoded as its bytes arrive, and a text is shown from its start. A payload read in order lets the host hold what it is using and nothing more.

## What Changes

- The pods service gains `put_record_streamed`, which places a record from a stream of pieces as `put_record` places one from a buffer. The identity's membership is checked before the stream is read and again at the write, the payload goes into the blob store while no lock of the runtime is held, and nothing is written unless the stream ends whole.
- The pods service gains `read_streamed`, which answers a reader of a claim's or an immutable-document's payload, read in order and held against blob collection while the reader lives; it answers `None` where `read` answers `None`.
- The data layer gains the import of a stream into the blob store, the write of a record-store entry naming an imported payload, and the reader (`payload.rs`); pdn-store gains `Doc::set_imported`, which writes an entry for a payload already in the blob store and holds the payload's temp tag until the entry is in.
- `put_record` and `read` stay as they are.

## Out of Scope

- Reading a payload from an offset, and a payload not yet whole on the device: a reader starts at the first byte of a payload the store holds whole.
- A mergeable-document's operations: `append_op` and `read_ops` keep their buffers, since an operation is small and every read of its document reads all of them.
- What a host exports of the two calls: each host's own specification says so.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `components/mee-pdn/pdn-node/pods`: one requirement added — a record's payload is placed from a stream and read as one.

## Impact

- **`crates/pdn-store`**: `Doc::set_imported` in `src/api.rs`.
- **`crates/data-layer`**: `src/payload.rs` with `PayloadStream`, `ImportedPayload` and `PayloadReader`; `import_payload`, `write_pod_record_imported` and `read_pod_record_streamed` in `src/node.rs`; the `bytes` dependency and tokio's `io-util`.
- **`crates/pdn-node`**: `put_record_streamed` and `read_streamed` in `src/pods.rs`, the key of a fresh record shared with `put_record` (`fresh_record_key`), and the two types re-exported.
- **Tests**: three scenarios in `crates/pdn-node/tests/pods.rs`.
- **Docs**: the `CLAUDE.md` of `crates/pdn-store`, `crates/data-layer` and `crates/pdn-node`; at archive, the service listing in `components/mee-pdn/pdn-node/pods/spec.md`.
