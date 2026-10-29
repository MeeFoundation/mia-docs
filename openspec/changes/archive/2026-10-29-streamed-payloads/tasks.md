## 1. The store and the data layer

- [x] 1.1 `Doc::set_imported` in pdn-store's `src/api.rs`, holding the payload's temp tag until its entry is in, as `set_bytes` holds its own (D2)
- [x] 1.2 `src/payload.rs` in the data layer — `PayloadStream`, `ImportedPayload`, `PayloadReader` — and `import_payload`, `write_pod_record_imported` and `read_pod_record_streamed` in `src/node.rs` (D2, D3)

## 2. The pods service

- [x] 2.1 `put_record_streamed` in pdn-node's `src/pods.rs`: the membership checked before the stream is read and again at the write, the import outside the state lock, the key numbered by `fresh_record_key`, which `put_record` shares (D1, D4)
- [x] 2.2 `read_streamed`, refusing a mergeable-document as `read` does (D3)

## 3. Scenario tests

- [x] 3.1 "A streamed payload round-trips" and "A stream that fails places nothing": `a_streamed_payload_round_trips_and_a_failed_stream_places_nothing` in `tests/pods.rs`, a payload of 3 MiB from 3 pieces read on another member's device whole and through a reader in pieces of 64 KiB, and a stream failing after 2 MiB leaving the listing as it was
- [x] 3.2 "A non-member's stream is not read" and "A non-member opens no reader": the same test, a co-located identity that is no member refused with the unknown-pod error by both calls and its stream never polled; with the check before the stream removed, the stream is polled and the test fails
- [x] 3.3 "A stream that waits holds up no other call": `a_stream_that_waits_holds_up_no_other_call`, a claim placed while a stream that never yields is being placed; with the lock held across the import, the claim waits out the 30 s bound and the test fails

## 4. Docs

- [x] 4.1 The `CLAUDE.md` of `crates/pdn-store`, `crates/data-layer` and `crates/pdn-node`
- [x] 4.2 At archive: `put_record_streamed` and `read_streamed` in the service listing of `components/mee-pdn/pdn-node/pods/spec.md`, which no delta reaches

## 5. Gates

- [x] 5.1 `just check` and `just test` green
- [x] 5.2 Stress pass per [flaky-tests](../../../specs/code-practices/flaky-tests.md) on the scenarios of section 3: 100 iterations, no failure
- [x] 5.3 `openspec validate --all --strict` before archiving
