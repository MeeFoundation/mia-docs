# Proposal: own-grant-read

## Why

The connections service reads the grants a peer published toward a hosted identity and offers no counterpart for the grants that identity published itself. A host built on the runtime can therefore show a person what others share with them and not what they share with others, and the withdrawal of a grant becomes an act with nothing to name. The one question a sovereignty product is asked — what am I sharing right now — is answerable only from what the caller happens to remember publishing, which is wrong on the second device and stale after a sibling withdraws.

The reading exists already, behind the test-only feature, because scenarios in three suites need it to know a grant record has become readable on the device that will serve. Turning it into a product operation both answers the question and removes a test-only surface: those scenarios then arrange themselves the way a product does.

## What Changes

- **The connections service reads the grants a hosted identity published toward a connected peer.** It reads the identity's own half of the connection's metadata pair, which is where publishing writes and withdrawal clears, opening the pair from the directory's tickets on demand so a device that joined later reaches a pair established elsewhere.
- **The read reports the capability alone.** The granted issuer, the exact claim set, and per claim whether write accompanies read. No ticket: the caller issues the namespace the record addresses, so a ticket to it answers nothing, and no host over this runtime has to decide whether to drop one.
- **It is an observation, like the peer-side read.** What is readable at the moment of the call, never waiting. A grant published on one device of an identity reaches that identity's other devices by replication of the pair, so a device that did not publish it reads nothing until the record and its payload have arrived.
- **It answers for the device it runs on, and one empty answer covers four states.** The read reports what this device holds: on the device that published a grant it is evidence the record is here, never that it reached a sibling or the peer. And an empty answer means one of "no connection to that peer", "the pair has not replicated here yet", "a record is here whose payload cannot be read yet" and "nothing is granted" — the peer-side read already answers that way for the same reason, and a host that presented it as the fact that nothing is shared would say the one thing the read cannot support.
- **The test-only helper goes.** It answered the same question as a boolean; the product call subsumes it, and its callers move onto the product call, which is where an arrange step belongs ([product-path-arrangement](../../specs/code-practices/product-path-arrangement.md)). There are three: one linking scenario, the reachability suite's wait behind four scenarios, and the restart-recovery scenario in which a sibling that comes back holds the record only because the audience still had it — the last an assertion of that suite's own subject rather than an arrange step.
- **The paired denial is the co-hosted identity, in two degrees.** A second identity on the same runtime reads its own directory, finds no pair toward that peer, and obtains nothing; and a second identity that does hold its own connection to that peer reads the claim set it published itself and never the other's. The first catches a lookup keyed on the peer instead of on the acting identity's directory: publishing opens and caches the pair, so such a lookup hands the identity that holds no pair of its own the other's record. The second catches the narrower slip the first cannot — a lookup keyed on the peer among the identities that do hold one. Beside both stands the positive read, without which a denial whose expected answer is nothing would be satisfied by an implementation that answers nothing to everyone. A disconnected third identity elsewhere cannot address the pair at all, so its exclusion is a property of the store's addressing rather than a scenario.

## Out of Scope (deferred)

- **Any host.** No host exports this read here. `pdn-node-http` gains no route and `mobile-host-surface` exports it as one of its calls, each in its own change. The consequence is named rather than left to be met: the container stand's stopped-device scenario cannot see the sibling's grant record, so it waits on one of the four preconditions its in-process counterpart waits on and keeps the rare failure that costs — about 1 failure in 100 iterations — until a route exists. The `/debug/` subtree is scaffolding whose route names nothing outside the repository may rest on, so putting the read there is a question for that host's own change rather than one about the platform surface.
- **Reading a peer's own half.** Nothing new is offered toward a peer's published grants; that read exists and is untouched.
- **Grant history.** The read reports the record that is there, and a withdrawal leaves no record behind. Nothing here retains what was granted before.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree.

| Capability (delta) | Archive destination                          |
| ------------------ | -------------------------------------------- |
| `pdn-node-core`    | `openspec/specs/components/mee-pdn/pdn-node/core.md` |

### New Capabilities

None.

### Modified Capabilities

- `pdn-node-core`: the connections service requirement gains the own-grant read, states that both grant reads are observations rather than waits, states that the own-side read carries no ticket, and states what an answer of theirs is about — the device it ran on, with one empty answer covering no connection, a pair not yet replicated here, a record here whose payload cannot be read yet, and nothing granted.

## Impact

- **`crates/pdn-node`**: one operation added to `ConnectionsService` and its runtime implementation, reading the pair's own half through the same helper the removed test-only call used. The test-only `grant_visible` is deleted.
- **`crates/pdn-node/tests`**: the three suites that observe a grant record's readability move onto the product call — linking, reachability, and the restart-recovery scenario of a sibling recovering the record from the audience. New scenarios for the read itself, including the co-hosted denial.
- **`crates/data-layer`**: untouched. The connection metadata store already reads a grant from either half by issuer and audience.
- **Hosts**: untouched. Neither existing host exports the operation, and no behaviour any host relies on changes.
