## Context

Grants ride a connection's metadata pair: publishing writes into the identity's own store toward the peer, and reading opens the counterpart's store. The service offers the second direction and not the first, so nothing can answer what a hosted identity is currently sharing. The information is not missing from the node — it is in the identity's own half of every pair — it simply has no operation.

The same reading exists behind the runtime's test-only feature, where two scenarios use it to learn that a grant record has become readable on a device before that device is asked to serve.

## Goals / Non-Goals

**Goals**

- The runtime able to answer what a hosted identity has published toward a peer, on any device of that identity.
- One fewer test-only surface, and two arrange steps moved onto the product path.

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

One honesty note about the word: opening a pair is not free of writes. The helper both reads publish this device's record into the pair and register the connection, which is pre-existing behaviour shared with the peer-side read. "Observation" here means the read does not wait for a record and does not change any grant, not that no byte is written.

### D4. The paired denial is the co-hosted identity, and the disconnected outsider is not a scenario

The tightest party the operation can be asked about is a second identity hosted on the same runtime. It has a directory of its own, holds no pair toward that peer, and obtains nothing — and it is a path a regression could plausibly open, because the operation takes the acting identity as an argument and could read the wrong directory.

A disconnected identity on another node is a weaker control here: nothing lets it address the pair, so no call can be made and no assertion can fail. Its exclusion belongs in the requirement's prose as a statement about the store's addressing ([access-control-tests](../../specs/code-practices/access-control-tests.md) asks for the tightest party, not for every party).

### D5. The test-only helper goes rather than staying beside its replacement

It answered the same question with a boolean, and both its callers want exactly what the product call reports: whether the record for a given issuer is readable here yet. Keeping both would leave a test-only surface whose only justification was the absence of the product one, and would let a future scenario arrange itself off the product path for no reason.

## Risks / Trade-offs

**Two scenarios change their arrange step.** The linking scenario and the reachability suite's wait now depend on the operation this change adds, so a defect in it shows up as a failure in suites that were previously green for other reasons. That is the point of moving them, and it is why those two suites are in the stress pass rather than only the new scenarios.

**A read opens a pair, which writes.** Pre-existing and shared with the peer-side read, but a reader of the new operation may expect a pure read. D3 states it instead of leaving it to be discovered.

## Migration Plan

Nothing to migrate. One operation is added, one test-only operation is deleted with its two callers updated in the same change, and no persisted state or wire format changes.

## Open Questions

None. The mechanism, the right, and the denial are all settled by existing invariants and existing store behaviour.
