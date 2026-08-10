## 1. Ceremony lifecycle

- [x] 1.1 Transfer cancellation cleanup ownership atomically from the reservation to the rollback guard so rollback finishes before releasing the identity
- [x] 1.2 Make runtime shutdown wait within a named budget for supervised linking and establishment cleanup
- [x] 1.3 Add a deterministic cancellation-after-import and immediate-retry test that proves the successful retry remains hosted after old cleanup finishes
- [x] 1.4 Rewrite the lost-reply retry assertion through the public linking service while retaining the raw first attempt only as setup

## 2. Pending-device lifecycle and local failure diagnostics

- [x] 2.1 Encode pending-device creation time backward-compatibly and add 24-hour expiry cleanup in the private metadata store
- [x] 2.2 Invoke pending cleanup after startup/reconciliation and test multiple abandoned device ids across restart without confirming any device
- [x] 2.3 Record typed local diagnostics for pending-write and ticket-mint failures after invite burn while keeping the remote close uniform
- [x] 2.4 Add a failing-store test that proves a burned invite's local storage failure is observable and grants no device access

## 3. HTTP safety boundaries

- [x] 3.1 Split `HostError` into allow-listed public text and logged internal cause; test that nested 500 context never reaches the response
- [x] 3.2 Apply a 16 MiB entry-body limit and a 16-request shared concurrency limit with explicit 413 and 503 tests
- [x] 3.3 Make `/live` independent of the coarse state lock, add bounded `/ready`, and test liveness success beside readiness failure under held-lock contention

## 4. Specification provenance and cleanup

- [x] 4.1 Update ADR-0012 and the main device-linking and HTTP-host specs with supervised cleanup, pending expiry, local failure diagnostics, resource bounds, and liveness/readiness semantics
- [x] 4.2 Correct the original HTTP change's impact and migration text so it no longer claims runtime, data-layer, persisted state, and wire behavior are untouched
- [x] 4.3 Reduce changed production comments to critical invariants and apply the repository's digit style to changed OpenSpec documents

## 5. Verification

- [x] 5.1 Run the narrow tests after each task group and prove each new scenario fails when its mechanism is removed
- [x] 5.2 Run `just check`, `just test`, and `openspec validate --all --strict`
- [x] 5.3 Run focused nextest stress passes for linking cancellation/retry and the HTTP host suite according to `flaky-tests.md`
