---
status: accepted
date: 2026-09-04
---
# Capabilities name identities, not device keys

## Context and Problem Statement

A capability says who may do what with a claim, and the holder can be named at two levels: the identity, or the key of the device that carries out the access. An identity has several devices, gains and loses them over its life, and every one of them needs the same access the identity was given.

## Considered Options

* **Name the identity in the capability**, and resolve the connecting device to its identity when the capability is checked ← chosen
* **Name device keys**, with the platform expanding each identity-level grant into one delegation per device and keeping the set consistent as devices come and go

## Decision Outcome

Chosen option: **capabilities name the identity**. `Capability.holders` is a list of `PdnId`, and a UWill token's `iss`, `aud` and `sub` are PdnId-backed. Enforcement matches: the ingest gate resolves the transport-authenticated session peer to an identity and judges it against that identity's recorded grant ([capability-gated ingest](../../components/data-layer/capability-gated-ingest.md)). Linking a device re-issues nothing.

### Consequences

* Good, because a device joins or leaves an identity without touching a single grant — there is no per-device set to expand or to keep consistent.
* Good, because withdrawal and revocation act on one record per audience instead of a set that grows with the audience's device count.
* Bad, because every check depends on resolving a device to its identity, so a device set that is stale or wrong weakens each grant judged through it.
* Bad, because until identity proofs land ([ADR-0003](0003-mee-identity-represents-keri-autonomic-namespace.md)) that resolution rests on records the identity's own devices wrote, not on proof of control over the named identity.

## More Information

Related: [ADR-0002](0002-mee-identity-is-globally-unique.md) (the one identifier a capability names), [ADR-0007](0007-uwill.md) (UWill, the capability format built on this decision), [ADR-0008](0008-iroh-without-willow.md) (the ingest gate that enforces it).
