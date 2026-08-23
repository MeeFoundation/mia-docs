# Tasks: own-grant-read

Small and self-contained: one operation added, one test-only operation removed, two arrange steps moved onto the product path. It lands before `mobile-host-surface`, which exports the operation, and it depends on nothing.

## 1. The operation (`pdn-node`)

- [ ] 1.1 `ConnectionsService` gains the read of the grants a hosted identity published toward a connected peer, over the pair's own half, opening the pair from the directory's tickets on demand (D1)
- [ ] 1.2 It reports the capability alone — granted issuer, exact claim set, write right per claim — and no ticket (D2)
- [ ] 1.3 It reports what is readable now and never waits; a record whose payload has not arrived reads as no grant (D3)
- [ ] 1.4 An unhosted identity is refused with the unknown-identity error, as every other connections operation is
- [ ] 1.5 The test-only `grant_visible` deleted (D5)

## 2. Callers moved onto the product path

- [ ] 2.1 The linking scenario's wait for a published grant to become readable moves onto the product call
- [ ] 2.2 The reachability suite's wait — the one that must know a grant record is serveable before the publishing device is stopped — moves onto the product call
- [ ] 2.3 Both proven to fail with the mechanism deliberately broken, so the moved arrange step is not merely compiling

## 3. Scenarios

- [ ] 3.1 The issuer reads what it published, and no ticket appears in the value
- [ ] 3.2 A republication reports the second claim set; a withdrawal reports no grant for that issuer
- [ ] 3.3 A sibling device reads a grant it did not publish — nothing before the record and its payload replicate, the same capability afterwards
- [ ] 3.4 The paired denial: a second identity hosted on the same runtime, with no pair toward that peer, obtains nothing (D4)
- [ ] 3.5 Each scenario proven to fail with its mechanism deliberately broken

## 4. Docs and spec tree (manual, not deltas)

- [ ] 4.1 Service docs of the new operation: the own half, the capability without a ticket, the observation contract, and that opening a pair writes
- [ ] 4.2 Sweep the spec tree and the active changes for statements this change invalidates — anything reading that an identity's own published grants cannot be read, or that the test-only helper is how a grant's readability is observed

## 5. Gates

- [ ] 5.1 `just check` and `just test` green
- [ ] 5.2 Stress pass per [flaky-tests](../../specs/code-practices/flaky-tests.md): the new scenarios plus the two suites whose arrange step moved, under `--stress-count`, sized by the rule of three. Those two suites are included because a defect in the new operation now surfaces as their failure
- [ ] 5.3 `openspec validate --all --strict` before archiving
