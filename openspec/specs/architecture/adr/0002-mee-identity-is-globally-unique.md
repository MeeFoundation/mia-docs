---
status: accepted
date: 2026-09-04
---
# One identifier per identity: a PdnId is presented to everyone

## Context and Problem Statement

An identity is named by a `PdnId`: 32 bytes, unique by construction, stable while operational keys rotate. A pod's membership store names its members by it, every record in a pod is placed under its author's, and the linking dialogue and a pod's join exchange it. The question is whether an identity carries one such identifier towards everyone, or a separate one per counterparty.

## Considered Options

* **One identifier per identity, presented to every counterparty** ← chosen
* **A pairwise identifier: a separate one per counterparty, with the mapping kept by the identity itself**

## Decision Outcome

Chosen option: **one identifier per identity**, because the pairwise alternative is substantial work this project has not taken up. Every place that names an identity — a pod's membership, the records placed under it, both ceremonies — would need a per-counterparty identifier and a mapping between them, and the identity system would have to mint those identifiers and prove control of each. Nothing in the current design argues against pairwise identity; this record states what is built.

### Consequences

* Good, because addressing is uniform: one name works in every store, every pod and every ceremony, with no mapping to keep consistent.
* Bad, because two counterparties that compare what they hold see one and the same person — the correlation a pairwise identifier exists to prevent.

## More Information

Pairwise identity stays the known alternative, deferred. Taking it up supersedes this decision rather than making it obsolete: what identifiers were before the change is what makes the change readable.

Related: [ADR-0003](0003-mee-identity-represents-keri-autonomic-namespace.md) (the root the identifier names), [ADR-0013](0013-identity-isolation-on-one-node.md) (several identities on one node, each named by its own identifier).
