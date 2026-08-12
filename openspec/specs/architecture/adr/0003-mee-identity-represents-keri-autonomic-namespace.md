---
status: accepted
date: 2026-08-11
---

# A MEE identity is a KERI autonomic namespace with delegated device identifiers

## Context and Problem Statement

`PdnId` was minted as random bytes, so no cryptographic history established which devices controlled an identity or whether bootstrap stores belonged to it. Device linking could authenticate the transport endpoint and one-time secret, but the inviter's assertion about the identity and tickets was not independently verifiable.

The identity model must preserve `PdnId`'s 32-byte domain representation, allow any existing device to invite another without copying root private keys to every device, survive restart, and keep namespace read capabilities out of a public key-event log.

## Decision Drivers

- Derive the identity from reproducible signed history rather than an unauthenticated random label.
- Bind every full-access device record to its authenticated transport `NodeId`.
- Let any device invite without sharing its delegator's private keys.
- Commit to the fixed directory/data store set without publishing namespace capability bytes.
- Keep the version-1 protocol byte-for-byte interoperable and independently testable.
- Fail closed on forks, duplicate endpoint bindings, missing secrets, and incomplete recovery.

## Considered Options

- Keep random `PdnId` values and add only transport-level statements.
- Delegate every device directly from the root and copy root authority to inviters.
- Use a tree in which each device delegates the device it invites.
- Implement the whitepaper Figure 12.7 location-seal profile literally.
- Use a deliberately narrower `di`-only KERI profile with exact local wire rules.

## Decision Outcome

Chosen option: a self-addressing KERI root identifies the MEE identity, and devices form a delegation tree in which each inviter delegates its newcomer. The root inception seals opaque role-tagged commitments to exactly 2 device-replicated stores: private-metadata directory and data. The 32-byte digest behind the root AID maps canonically to the existing `PdnId` representation.

The first device is delegated by the root. Later devices are delegated by their inviting device and anchored in that delegator's accepted KEL. A complete endpoint binding is a replicated signed proof: linked devices retain request, inviter manifest, and newcomer confirmation; the founder retains a founder statement countersigned by the root. Full session access requires the authenticated `NodeId`, a valid proof for that exact endpoint, and an accepted anchored chain to the hosted root.

Profile 1 intentionally uses `di`-only delegated inception rather than the prospective delegating-location seal in KERI Design v2.63 Figure 12.7. Exact KERI JSON, algorithms, CESR codes, signature preimages, frames, limits, and golden vectors are normative in `pdn-node-keri-wire-profile`; the whitepaper and pinned `keripy` are reference/oracle material, not alternate wire specifications.

The implementation uses a narrow 3-event profile (`icp`, `dip`, `ixn`) over the workspace's Apache/MIT-compatible BLAKE3 and Ed25519 primitives. It does not link `keriox`. Key rotation, revocation, endpoint supersession, recovery, witnesses, receipts, and counterparty-device verification remain separate versioned decisions.

### Consequences

- Good: an identity, its device authority, endpoint binding, and store set are independently reproducible and verifiable.
- Good: any device can invite without distributing root or ancestor private keys.
- Good: raw namespace identifiers remain below the data-layer boundary.
- Bad: the tree has no implemented administrator; loss of a delegator freezes new establishment for its subtree until a later recovery/re-inception operation.
- Bad: the chosen profile is deliberately not byte-compatible with the Figure 12.7 location-seal construction.
- Bad: bounded full-history replay eventually needs a separately specified verifiable checkpoint.
- Neutral: KERI permits ancestor recovery, but this decision neither implements it nor claims that device-key loss is universally unrecoverable.

## Validation

- Strict OpenSpec validation covers the normative deltas.
- Golden vectors must match both the local implementation and pinned `keripy` before protocol code is accepted.
- Scenario tests cover creation, founder authorization, non-founder invitation, request/manifest/confirmation signatures, endpoint substitution, store commitment mismatch, competing histories, duplicate confirmed endpoints, restart recovery, and every size/depth bound.
- The durable-runtime-storage predecessor must pass process-level crash/reopen tests before this change is implemented.

## More Information

ADR-0012 remains the historical decision for the version-0 raw linking ceremony. The `keri-backed-device-linking` change replaces that protocol with `/pdn/linking/1` when implemented and archived. Existing `PdnOp` device/key variants are reserved and do not acquire KERI semantics through this ADR.
