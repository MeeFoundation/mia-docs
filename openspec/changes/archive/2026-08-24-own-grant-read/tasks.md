# Tasks: own-grant-read

Small and self-contained: one operation added, one test-only operation removed, three suites' steps moved onto the product path. It lands before `mobile-host-surface`, which exports the operation, and it depends on nothing.

## 1. The operation (`pdn-node`)

- [x] 1.1 `ConnectionsService` gains the read of the grants a hosted identity published toward a connected peer, over the pair's own half, opening the pair from the directory's tickets on demand (D1)
- [x] 1.2 It reports the capability alone — granted issuer, exact claim set, write right per claim — and no ticket (D2)
- [x] 1.3 It reports what is readable now and never waits; a record whose payload has not arrived reads as no grant (D3)
- [x] 1.4 It answers for the device it runs on, and one empty answer covers no connection to that peer, a pair not yet replicated here, and nothing granted — no state of the sibling or of the peer is reported, and none is inferable (D6)
- [x] 1.5 An unhosted identity is refused with the unknown-identity error, as every other connections operation is
- [x] 1.6 The test-only `grant_visible` deleted; the contact-set observation stays, having no product caller (D5)

## 2. Callers moved onto the product path

- [x] 2.1 The linking scenario's wait for a published grant to become readable moves onto the product call
- [x] 2.2 The reachability suite's wait — the one that must know a grant record is serveable before the publishing device is stopped, behind four scenarios — moves onto the product call
- [x] 2.3 The restart-recovery scenario's assertion that the recovered sibling holds the record it will serve by moves onto the product call. It is that suite's own subject rather than an arrange step, so it stays an assertion and reads as one
- [x] 2.4 The linking scenario's claim corrected: a call on the grant surface now runs on the serving device, so either the scenario reaches the pair the armer opened before it reads, or it says that what it claims of that device is that no grant was published or withdrawn there (D3)
- [x] 2.5 All three proven to fail with the mechanism deliberately broken, so a moved step is not merely compiling
  - Broken arm: the read taken from the pair's counterparty half instead of the identity's own. All 3 moved steps starve and fail — linking, reachability's core scenario and the restart-recovery one — beside the 3 new scenarios, 6 of 6 red. Restored, 6 of 6 green.

## 3. Scenarios

- [x] 3.1 The issuer reads what it published, and no ticket appears in the value
- [x] 3.2 A republication reports the second claim set; a withdrawal reports no grant for that issuer
- [x] 3.3 A sibling device reads a grant it did not publish, and reads the same capability once the record and its payload have replicated to it. The scenario asserts that convergence alone: nothing holds replication back, so an assertion that the sibling reads nothing beforehand would be a race the suite pays for later — the contract's other half is stated in the docs and the spec, and its guard is named as the stress configuration rather than pretended to be a pin ([flaky-tests](../../specs/code-practices/flaky-tests.md), rule 8)
- [x] 3.4 The paired denial in two degrees (D4): a second identity hosted on the same runtime with no pair toward that peer obtains nothing, and — the tighter one — a second identity that does hold its own connection to the same peer reads its own grants and never the first identity's
- [x] 3.5 Each scenario proven to fail with its mechanism deliberately broken. For a denial whose expected answer is empty, the discriminating half is the positive read beside it: an implementation that answered nothing to everyone would pass the denial alone
  - Second broken arm, for the denials: the pair resolved by peer alone rather than through the acting identity's directory — exactly the lookup the tighter degree exists for. All 3 scenarios red, the co-hosted denial among the failing assertions.

## 4. Docs and spec tree (manual, not deltas)

- [x] 4.1 Service docs of the new operation: the own half, the capability without a ticket, the observation contract, what the empty answer covers and what it is not evidence of, that the answer is this device's, and that opening a pair writes and registers the connection
- [x] 4.2 Sweep the spec tree and the active changes for statements this change invalidates — anything reading that an identity's own published grants cannot be read, or that the test-only helper is how a grant's readability is observed. `mobile-host-surface` exports this read and cites its contract, so what it says about both grant reads is checked against what lands here

## 5. Gates

- [x] 5.1 `just check` and `just test` green
  - `just test`: 164 of 164 passed, 15 skipped (the container scenarios, which need a daemon).
- [x] 5.2 Stress pass per [flaky-tests](../../specs/code-practices/flaky-tests.md): the new scenarios plus the three suites whose steps moved — linking, reachability, restart recovery — under `--stress-count`, sized by the rule of three. They are included because a defect in the new operation now surfaces as their failure, and because moving a step opens a new measurement pool: a streak measured before the move is not a control for the code after it, and any hunt in flight over these suites is re-baselined rather than carried across
  - Pool A, the new binary alone, 300 iterations in 31 minutes: 300 of 300 green (900 scenario runs). By the rule of three that bounds a failure of one iteration at about 1%.
  - Pool B, the 3 suites whose steps moved, 100 iterations in 85 minutes: 100 of 100 green (3,800 test runs), bounding an iteration's failure at about 3%.
  - Both pools are this change's own measurement, taken after the move. Nothing from before it is a control for them: the arrange step is not the one those suites had.
- [x] 5.3 `openspec validate --all --strict` before archiving
  - 5 of 5 changes valid.
