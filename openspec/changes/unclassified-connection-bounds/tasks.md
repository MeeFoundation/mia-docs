## 1. Measure what a stranger costs today

- [ ] 1.1 A test that opens one connection to a node, sends on streams the node never accepts, and records the node's resident memory against the bytes sent — the figure the first question is decided on
- [ ] 1.2 A test that opens connections without credentials until the node stops answering, and records the count and the memory — the figure the second question is decided on
- [ ] 1.3 Record both measurements in `design.md`, with the machine and the storage profile they were taken on

## 2. Settle how much one connection may buffer

- [ ] 2.1 Measure what iroh-blobs and iroh-gossip need from the transport configuration on a high-latency path, so a window is chosen against a real transfer rather than a guess
- [ ] 2.2 Take the decision, and rewrite the open question in `design.md` as a decision with its `**Rejected alternatives:**` block
- [ ] 2.3 If the decision is to leave the defaults, amend `specs/code-practices/defect-reachability.md` with the argument, and say there what it covers beyond this change

## 3. Settle how many connections a node holds before classification

- [ ] 3.1 Derive the floor: the connections one honest node holds across every hosted identity, every device of every counterparty, and a redial over an unstable connection
- [ ] 3.2 Take the decision, and rewrite the open question in `design.md` as a decision with its `**Rejected alternatives:**` block
- [ ] 3.3 If the decision is to leave the count to the transport, amend `specs/code-practices/defect-reachability.md` with the argument

## 4. Specify

- [ ] 4.1 Add the delta at `specs/components/mee-pdn/data-layer/node-assembly/spec.md`, beside the requirement that bounds the first message, with a scenario per bound
- [ ] 4.2 Add a scenario for each operating condition in `design.md` that changes the outcome, and drop `skip_specs` from `.openspec.yaml`
- [ ] 4.3 `openspec validate unclassified-connection-bounds --strict` passes, and every `#### Scenario:` heading is checked by eye

## 5. Build

- [ ] 5.1 Implement each bound where the decision puts it, and `just check` passes
- [ ] 5.2 Turn the measurements of section 1 into the regression tests: each one fails with its bound removed, and passes with it
- [ ] 5.3 Every test that asserts a bounded caller is served carries the paired denial of the caller past the bound
- [ ] 5.4 The counter of connections held before classification is exported and readable

## 6. Stress

- [ ] 6.1 Stress the connection and sync scenario tests under nextest per [flaky-tests](../../specs/code-practices/flaky-tests.md), before anything is built on top
