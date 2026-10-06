---
status: proposed
date: 2026-09-04
---
# An identity is rooted in a KERI autonomic identifier, and PdnId names it

## Context and Problem Statement

An identity needs a root name that outlives the keys it operates with, and control of that name has to be provable to a counterparty that has never met it. An identity's `PdnId` is derived from the public key of the announcement key pair minted with the identity — 32 bytes of BLAKE3 in its key-derivation mode under the context string `pdn/pdn-id/v1` — so a signature under that key proves the `PdnId` is the signer's own. A [pod](../language/pod.md) asks for that proof: a newcomer signs a join statement under its announcement key, and every member device counts the join only when that key derives the `PdnId` the newcomer presents. Pairing and linking take the `PdnId` they are handed on trust. And a name derived from a key holds only while that key does: the announcement key pair does not rotate, so replacing a lost or compromised key would rename the identity, and every grant, namespace and membership record naming it would go stale.

## Considered Options

* **A KERI autonomic identifier as the root, with `PdnId` as its domain-layer name** ← chosen direction
* **The identity is a public key**: rotation renames the identity, and every grant, namespace and membership record naming it goes stale
* **An external identity system** with its own resolution infrastructure

## Decision Outcome

Chosen direction: **a KERI autonomic identifier**, derived from an inception key and unchanged as operational keys rotate, with control provable offline from the key event log. `PdnId` is the domain-layer name for it, so nothing above the identity service depends on the identity implementation.

Nothing in this generation implements it, which is what the name v4-non-keri records: `PdnId` is derived from a key that does not rotate, and pairing ([ADR-0011](0011-pairing-over-raw-iroh.md)) and linking ([ADR-0012](0012-linking-over-raw-iroh.md)) each carry a marked, unbuilt step for the proof of control. The status stays `proposed` until a KERI-backed identity service exists.

### Consequences

* Good, because the identity's name survives key rotation, so grants, namespaces and membership records that name it stay valid across a rotation.
* Good, because `PdnId` isolates the rest of the platform: the KERI-backed service arrives as a second implementation behind the same domain type.
* Bad, because until it lands both ceremonies authenticate the transport peer and the one-time secret, never the claimed identity.
* Bad, because the implementation is ours to write.

## More Information

Pods hold a stand-in for the missing key event log, and its shape is what this decision has to replace. An identity publishes into each pod's membership store device-list statements signed by its announcement key, each carrying a version counter inside the signed bytes, and every member device counts a statement by that signature, whoever wrote the entry. Two properties of the stand-in therefore have to survive the arrival of a key event log: the device set is enumerable and verifiable by anyone holding what the identity published about itself, and its ordering comes from the statements themselves, never from entry timestamps. The `PdnId` derived from the announcement key is the slot the autonomic identifier of this decision fills.

The implementation is written in-house: the mature Rust library (keriox) is EUPL-1.2, which a statically linked embeddable SDK cannot take, and test vectors come from the Apache-2.0 reference implementation (keripy).

Related: [ADR-0002](0002-mee-identity-is-globally-unique.md) (one identifier per identity — pairwise identity, if taken up, lands on this root), [ADR-0011](0011-pairing-over-raw-iroh.md) and [ADR-0012](0012-linking-over-raw-iroh.md) (the deferred proof step in the ceremonies).
