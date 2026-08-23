# Proposal: own-grant-read

## Why

The connections service reads the grants a peer published toward a hosted identity and offers no counterpart for the grants that identity published itself. A host built on the runtime can therefore show a person what others share with them and not what they share with others, and the withdrawal of a grant becomes an act with nothing to name. The one question a sovereignty product is asked — what am I sharing right now — is answerable only from what the caller happens to remember publishing, which is wrong on the second device and stale after a sibling withdraws.

The reading exists already, behind the test-only feature, because two scenarios need it to know a grant record has become readable on the device that will serve. Turning it into a product operation both answers the question and removes a test-only surface: the two scenarios then arrange themselves the way a product does.

## What Changes

- **The connections service reads the grants a hosted identity published toward a connected peer.** It reads the identity's own half of the connection's metadata pair, which is where publishing writes and withdrawal clears, opening the pair from the directory's tickets on demand so a device that joined later reaches a pair established elsewhere.
- **The read reports the capability alone.** The granted issuer, the exact claim set, and per claim whether write accompanies read. No ticket: the caller issues the namespace the record addresses, so a ticket to it answers nothing, and no host over this runtime has to decide whether to drop one.
- **It is an observation, like the peer-side read.** What is readable at the moment of the call, never waiting. A grant published on one device of an identity reaches that identity's other devices by replication of the pair, so a device that did not publish it reads nothing until the record and its payload have arrived.
- **The test-only helper goes.** It answered the same question as a boolean; the product call subsumes it, and its two callers — one linking scenario and the reachability suite's wait for a grant record to become serveable — move onto the product call, which is where an arrange step belongs ([product-path-arrangement](../../specs/code-practices/product-path-arrangement.md)).
- **The paired denial is the co-hosted identity.** A second identity on the same runtime reads its own directory, finds no pair toward that peer, and obtains nothing. That is the tightest party the operation can be asked about and the one path a regression would break; a disconnected third identity elsewhere cannot address the pair at all, so its exclusion is a property of the store's addressing rather than a scenario.

## Out of Scope (deferred)

- **Any host.** No host exports this read here. `pdn-node-http` gains no route and `mobile-host-surface` exports it as one of its calls, each in its own change.
- **Reading a peer's own half.** Nothing new is offered toward a peer's published grants; that read exists and is untouched.
- **Grant history.** The read reports the record that is there, and a withdrawal leaves no record behind. Nothing here retains what was granted before.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree.

| Capability (delta) | Archive destination                          |
| ------------------ | -------------------------------------------- |
| `pdn-node-core`    | `openspec/specs/components/pdn-node/core.md` |

### New Capabilities

None.

### Modified Capabilities

- `pdn-node-core`: the connections service requirement gains the own-grant read, states that both grant reads are observations rather than waits, and states that the own-side read carries no ticket.

## Impact

- **`crates/pdn-node`**: one operation added to `ConnectionsService` and its runtime implementation, reading the pair's own half through the same helper the removed test-only call used. The test-only `grant_visible` is deleted.
- **`crates/pdn-node/tests`**: the linking scenario and the reachability suite's wait move onto the product call. New scenarios for the read itself, including the co-hosted denial.
- **`crates/data-layer`**: untouched. The connection metadata store already reads a grant from either half by issuer and audience.
- **Hosts**: untouched. Neither existing host exports the operation, and no behaviour any host relies on changes.
