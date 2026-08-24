## Context

Grants ride a connection's metadata pair: publishing writes into the identity's own store toward the peer, and reading opens the counterpart's store. The service offers the second direction and not the first, so nothing can answer what a hosted identity is currently sharing. The information is not missing from the node — it is in the identity's own half of every pair — it simply has no operation.

The same reading exists behind the runtime's test-only feature, where scenarios in three suites use it to learn that a grant record has become readable on a device before that device is asked to serve.

## Goals / Non-Goals

**Goals**

- The runtime able to answer what a hosted identity has published toward a peer, on any device of that identity.
- One fewer test-only surface, and every step that observes a grant record's readability moved onto the product path.

**Non-Goals**

- Exporting the read from any host. Each host does that in its own change.
- Any change to how grants are published, withdrawn, or enforced.
- Grant history. A withdrawal leaves no record, and nothing here keeps one.

## Decisions

### D1. The read is the identity's own half of the pair, and the right to it is Invariant 3

A connection metadata store is written only by its issuing identity's devices, and read by those devices and the counterparty's ([invariants](../../specs/components/pdn-node/invariants.md), Invariant 3). Every device of the identity therefore already has the right, and mechanically already holds the instrument: the pairing ceremony publishes the write ticket for the own-side store in the identity's directory under its own kind, so a device that replicated the directory can open that store without asking anyone.

That is the whole argument. It says nothing about what the peer knows, because the peer's knowledge does not bear on whether the issuer's own devices may read — the peer holding a read ticket to the same store explains how the peer reads these grants, not how the issuer does.

### D2. The read reports the capability and no ticket

The record's ticket is the one the granting side minted for the peer, addressing the granting identity's own data namespace. Handing it back to the issuer answers nothing it does not already have, and it forces every host above to decide whether to drop it. Reporting the capability alone removes the question.

This differs from the peer-side read on purpose: there the ticket is what the grantee's binder acts on, so the runtime hands it over.

### D3. It is an observation, not a wait

Both grant reads report what is readable at the moment of the call. A record whose payload has not been fetched reads as no grant, and the caller repeats the read — the same contract, for the same reason, as reading a peer's grant.

This matters most on a device that did not publish the grant. The pair replicates between the identity's devices, so a second device reads nothing until the record and its payload arrive, and a caller that treated the first empty answer as final would tell a person they share nothing at the moment they share something.

One honesty note about the word: opening a pair is not free of writes. Both reads publish this device's record into the pair and register the connection for session classification, which is pre-existing behaviour shared with the peer-side read. "Observation" here means the read does not wait for a record and does not change any grant, not that no byte is written.

That registration is why the moved arrange steps have to say what they arrange. On a device that has not opened the pair yet the read opens it — the same act the connection armer performs on its own sweep, idempotent and identical, but performed now rather than awaited. A scenario whose subject is that a device serves without any act on its grant surface therefore either reaches an already-open pair before it reads, or states that what it claims is that no grant was published or withdrawn there. It also gains something: nothing is readable until the pair opens, so a wait on this read is a wait for an open pair too, which is the precondition a scenario that stops a publishing device has to hold — the connection record alone leaves the pair's tickets payload-waiting, and where the publishing device held those payloads alone, nothing recovers them.

### D4. The paired denial is the co-hosted identity, in two degrees, and the disconnected outsider is not a scenario

The tightest party the operation can be asked about is a second identity hosted on the same runtime. It has a directory of its own, holds no pair toward that peer, and obtains nothing — and it is a path a regression could plausibly open, because the operation takes the acting identity as an argument and could read the wrong directory. This degree is what catches a lookup keyed on the peer alone: publishing opens and caches the pair, so by the time the second identity reads, the first identity's pair is there for such a lookup to hand it.

Worth having beside it, for the slip that one cannot reach: a second identity that does hold its own connection to the same peer. Both identities then have a pair toward P, so a lookup keyed on the peer only among the identities that hold one — narrower than the plain peer-keyed lookup, and invisible to the empty-directory case — hands one identity the other's grants. It also supplies what an empty expectation lacks: a denial whose expected answer is nothing is satisfied by an implementation that answers nothing to everyone, so the assertion that discriminates is the positive read standing beside it.

A disconnected identity on another node is a weaker control here: nothing lets it address the pair, so no call can be made and no assertion can fail. Its exclusion belongs in the requirement's prose as a statement about the store's addressing ([access-control-tests](../../specs/code-practices/access-control-tests.md) asks for the tightest party, not for every party).

### D5. The test-only helper goes rather than staying beside its replacement

It answered the same question with a boolean, and every one of its callers wants exactly what the product call reports: whether the record for a given issuer is readable here yet. There are three — one linking scenario, the reachability suite's wait behind four scenarios, and the restart-recovery scenario in which a sibling that comes back holds the record only because the audience still had it. Keeping the helper would leave a test-only surface whose only justification was the absence of the product one, and would let a future scenario arrange itself off the product path for no reason.

The observation of a replica's contact set stays where it is. It has no product caller — it is the reconciliation's own working-out in terms of node ids — so it remains an instrument: admitted, annotated, absent from product builds.

### D6. The read answers for this device, and one empty answer covers three states

The read is a local one: it opens the pair from this device's directory and reads the replicas this device holds. On the publishing device it says the record is here and never that it reached a sibling or the peer; on any device it says nothing about what the counterparty has received. A publishing device cannot learn the fate of its publication from it, and nothing else in the runtime offers that either — such an answer needs a per-peer synchronization progress out of the engine, or an acknowledgement a sibling writes into the pair, and neither exists. As an indicator that is a change of its own; as a precondition of publishing it is refused, because one device is a first-class configuration and a promise that degenerates where there is no sibling is worse than no promise.

The same locality makes one answer serve three states: this identity holds no connection to that peer, the pair's tickets have not replicated to this device yet, and nothing is granted toward that peer. The peer-side read already answers that way, and refusing instead wherever no pair opens would turn a linked device's first minutes into failures — a directory that has not caught up is a normal state, not a caller's error. What no host may do is present the empty answer as the fact that nothing is shared.

## Risks / Trade-offs

**Three suites change their arrange step.** Linking, reachability and restart recovery now depend on the operation this change adds, so a defect in it shows up as a failure in suites that were previously green for other reasons. That is the point of moving them, and it is why all three are in the stress pass rather than only the new scenarios.

**The move fixes nothing that flakes, and must not be read as fixing it.** Those waits exist because a grant record rides best-effort replication and a scenario that stops the publishing device races it. Reading the same record through a product call renames the wait and changes nothing about the race: a green suite afterwards means the property holds where the precondition held, and that precondition is one the product does not promise. A device that still holds the pair's own half — the audience holds that same replica — can supply the record to a device that lacks it, which is hardening rather than a measured repair, and the loss stands where the publishing device goes for good before the record crosses.

**A suite under a flake hunt is a measurement pool.** The container counterpart of these waits carries a rare failure that is not diagnosed, and the suites moved here are where its mechanism is exercised in process. Changing an arrange step opens a new pool ([flaky-tests](../../specs/code-practices/flaky-tests.md), rules 3 and 9): streaks measured before this change are not controls for the code after it, so a hunt in flight is re-baselined rather than continued across the move.

**A read opens a pair, which writes.** Pre-existing and shared with the peer-side read, but a reader of the new operation may expect a pure read. D3 states it instead of leaving it to be discovered.

## Migration Plan

Nothing to migrate. One operation is added, one test-only operation is deleted with all three of its callers updated in the same change, and no persisted state or wire format changes.

## Open Questions

None. The mechanism, the right, and the denial are all settled by existing invariants and existing store behaviour.
