---
status: proposed
date: 2026-05-13
---

# UWill: UCAN-shaped capabilities for Willow

## Context and Problem Statement

Mee PDN uses the Willow protocol for P2P data sync (see [ADR-0005](0005-why-willow.md)). Willow's default capability system, Meadowcap, has four gaps that block production use:

1. **No revocation.** Once a capability is delegated, it cannot be invalidated.
2. **No wall-clock expiry.** Meadowcap's `TimeRange` restricts which entries a capability covers, not when the capability itself stops being valid.
3. **No key rotation.** A compromised receiver key cannot be rotated; every delegation through it is permanently compromised.
4. **No identity-system integration.** Capabilities reference raw ed25519 keys and are tied to specific physical willow nodes — but a Mee participant has multiple devices, and capabilities must be anchored to **identities** (MeeId-backed DIDs), per [ADR-0004](0004-capabilities-should-refer-to-mee-id.md).

The decision to fork willow (see [ADR-0006](0006-why-fork-of-willow.md)) makes a non-trivial replacement of Meadowcap feasible. The question is what replaces it.

## Decision Drivers

- Revocation, expiry, and key rotation must be expressible in the capability format.
- Capabilities must be bound to MeeId-backed DIDs, not per-device keys.
- Willow's Private Interest Overlap (PIO) requires structurally extractable rectangular `Area`s from capabilities.
- Ecosystem alignment over bespoke crypto / serialization.
- Read/write attenuation along the chain is not currently required.

## Considered Options

- **Keep Meadowcap as-is.**
- **Layer a separate capability system above Meadowcap.**
- **Pure UCAN delegations, no canonical Area extraction.**
- **Hierarchical UCAN + Areas, with command-level narrowing** — earlier UWill draft using `/willow`, `/willow/read`, `/willow/write` paths for attenuation.
- **Bind capabilities to per-device willow keys**, with PDN holding a translation table.
- **Biscuit** (Datalog-based capabilities).
- **Custom capability system from scratch.**
- **UWill: hybrid UCAN delegation chain + Willow Area policy, flat command set, bound to MeeId.** ← chosen

## Decision Outcome

Chosen option: **UWill**. It is the only option that addresses three Meadowcap gaps (revocation, expiry, rotation), satisfies the MeeId-binding constraint, preserves PIO's structural Area requirement, and reuses ecosystem-standard formats (UCAN, DID, CBOR/IPLD).

Technical specification — token format, command semantics, Area encoding, chain validation rules, revocation propagation, identity resolution — lives in [components/pdn-node/uwill.md](../../components/pdn-node/uwill.md). The implementation crate is the `MeeFoundation/iroh-willow` fork.

### Consequences

- Good, because revocation, expiry, and key rotation — three of the four Meadowcap gaps — are addressed.
- Good, because capabilities are bound to MeeId, so devices can be added or removed under an identity without re-issuing delegations.
- Good, because reuse of the UCAN Invocation model and the DID / CBOR / IPLD ecosystem reduces bespoke surface.
- Good, because revocation propagates over willow sync — no separate distribution channel.
- Bad, because tokens are roughly 2–2.5× larger than Meadowcap.
- Bad, because chain verification gains complexity: UCAN verification + Area narrowing + MeeId↔key resolution.
- Bad, because the `ucan` crate requires a fork (upstream lacks `verify()` methods).
- Bad, because `cmd` carries a list (non-standard UCAN), so off-the-shelf UCAN implementations cannot consume the tokens.
- Bad, because there is no read/write attenuation along chains; reintroducing it would require a future revision.
- Known gap: capabilities are sent in cleartext; restoring Meadowcap's PIO-relative encoding is out of scope for the initial implementation.

## Validation

Capability shape and chain-validation rules are specified in [components/pdn-node/uwill.md](../../components/pdn-node/uwill.md). Conformance is the responsibility of the `MeeFoundation/iroh-willow` fork.

## Pros and Cons of the Options

### Keep Meadowcap as-is

- Bad, because all four Meadowcap gaps remain unaddressed.
- Bad, because capabilities stay tied to physical nodes, violating [ADR-0004](0004-capabilities-should-refer-to-mee-id.md).

### Layer above Meadowcap

- Neutral, because the wire format is preserved.
- Bad, because Meadowcap is not pluggable — its types are hardwired into PIO, sync, and storage.

### Pure UCAN, no Area extraction

- Good, because it reuses UCAN unchanged.
- Bad, because PIO needs structurally extractable rectangular Areas; UCAN's freeform policy cannot guarantee that.

### Hierarchical UCAN + Areas

- Good, because it supports command-level attenuation.
- Bad, because attenuation is not currently needed and the hierarchy adds chain-validation complexity without paying for itself.
- Neutral, because reintroducing a hierarchy later is straightforward.

### Bind to per-device willow keys

- Good, because the capability format stays simple.
- Bad, because every device change forces re-issuing delegations.
- Bad, because revocation of one device does not propagate to the identity.
- Bad, because it contradicts [ADR-0004](0004-capabilities-should-refer-to-mee-id.md).

### Biscuit

- Good, because Datalog attenuation is more expressive; revocation is built in; binary format is compact.
- Bad, because it lacks DID integration.
- Bad, because it does not align with the CBOR/IPLD ecosystem.
- Neutral, because its revocation model did inform UWill's design.

### Custom from scratch

- Bad, because it reinvents UCAN's delegation, signature verification, DID resolution, and revocation infrastructure with no ecosystem alignment.

## More Information

- The design evolved through an earlier draft that included a `/willow`-rooted UCAN command hierarchy for read/write narrowing. The hierarchy was dropped when the narrowing it enabled turned out not to be required for current use cases.
- External references: [UCAN spec v1.0.0-rc.1](https://github.com/ucan-wg/spec), [UCAN revocation](https://github.com/ucan-wg/revocation), [Willow](https://willowprotocol.org/specs/), [Meadowcap](https://willowprotocol.org/specs/meadowcap/), [Biscuit](https://www.biscuitsec.org/), [KERI](https://weboftrust.github.io/ietf-keri/draft-ssmith-keri.html).
- Related ADRs: [ADR-0004](0004-capabilities-should-refer-to-mee-id.md), [ADR-0005](0005-why-willow.md), [ADR-0006](0006-why-fork-of-willow.md).
