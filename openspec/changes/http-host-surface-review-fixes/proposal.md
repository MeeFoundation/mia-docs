## Why

The HTTP host change exposed cancellation, resource, liveness, and protocol-lifecycle defects that the completed implementation tasks do not cover. The most severe defect lets cleanup from a cancelled device link delete state committed by a later successful retry, so the review fixes need their own traceable change rather than being appended to the completed host change.

## What Changes

- Make device-linking reservation and rollback 1 ordered lifecycle so a retry cannot overtake cleanup from a cancelled attempt.
- Make post-burn storage failures locally observable while preserving the linking protocol's uniform remote refusal.
- Bound and reclaim abandoned pending-device registrations across unstable connections and restarts.
- Separate public HTTP error text from internal error chains, and add aggregate request resource limits.
- Separate process liveness from readiness for the runtime's coarse state lock so ordinary contention does not report a healthy process as dead.
- Add product-path regression scenarios for cancellation followed by immediate retry, lost-reply retry, storage failure, abandoned registrations, overload, and liveness under contention.
- Restore specification provenance for the `pdn-node`, `data-layer`, and durable device-linking behavior introduced while reviewing the original HTTP host change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pdn-node-device-linking`: cancellation cleanup, retry ordering, post-burn failure observability, and the bounded lifecycle of pending-device registrations become explicit requirements.
- `pdn-node-http-host`: public error disclosure, aggregate request resource bounds, and process-liveness semantics become explicit requirements.

## Impact

- **`crates/pdn-node`**: linking attempt ownership, rollback, shutdown integration, diagnostics, and product-path retry tests.
- **`crates/data-layer`**: pending-device record representation and bounded cleanup.
- **`crates/pdn-node-http`**: public error bodies, tracing, body/concurrency limits, liveness/readiness routes, and HTTP tests.
- **OpenSpec and ADRs**: explicit deltas and decisions for runtime, storage, and host behavior; corrected provenance and rollback boundaries.
- **Compatibility**: ceremony payload versions remain unchanged; pending-device record encoding may require backward-compatible decoding and migration behavior.
