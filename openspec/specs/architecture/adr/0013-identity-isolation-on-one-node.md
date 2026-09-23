---
status: accepted
date: 2026-09-18
---
# Identities on one node are isolated by their own replicas, over one shared endpoint

## Context and Problem Statement

A node hosts the store sets of several identities of one person — Alice-at-work and Alice-at-leisure — and co-location is not a trust boundary: the platform holds two identities of one person as separate as two strangers. The node itself does not hold them apart. It keeps one replica per namespace, one author for every store it writes, and classifies a session by the caller's node id, which resolves to every identity that published it; so what two identities acquire is stored together, written under one name, and told apart only by a check at each point that reads it. The decision is what level of isolation between identities on one node the platform commits to.

## Decision Drivers

* One person acts on one device under several identities, and an act of one must not read, write, or answer as another.
* An entry has to say which identity wrote it, because a cell binds an author key to a member and a counterparty judges a write by its author.
* Isolation that rests on a check at every read fails wherever the check is forgotten; isolation that follows from where the bytes live does not.
* A transport's costs — a socket, a relay connection, address discovery, a probing schedule — are paid per endpoint, and a phone pays them.
* An identity holds no key material, so a session cannot prove which identity it acts as.
* The node's process holds the material of every identity it hosts, whatever arrangement sits above it.

## Considered Options

* **Replicas, author and sessions per identity, over the node's one endpoint** ← chosen
* One replica per namespace, with every local read filtered by the acting identity
* An endpoint, and with it a node id, per identity
* No isolation: one replica, one author, and rights unioned across the identities a node hosts

## Decision Outcome

Chosen: **replicas, an author and sessions per hosted identity**, over the endpoint the node already has. It removes the mixing where the mixing happens, in storage and in authorship, without paying a transport per identity; and what it gives holds without anyone remembering to apply it.

The shape, specified by the identity-scoped replicas and in-process sessions capabilities under `components/mee-pdn/data-layer/` and by [multi-identity](../../components/mee-pdn/data-layer/multi-identity/spec.md):

* Every replica belongs to exactly one hosted identity, and the act that creates or imports it names that identity. Two identities that acquired one namespace hold a replica each.
* A sync session names the identity whose replica it addresses and the identity its caller acts as, as opaque bytes the store compares and never interprets. A node may name only an identity whose device set lists its node id; anything else is refused as not hosted.
* A session's rights, its egress filter and its write admission follow the named identity alone, and are never unioned across the identities a node hosts.
* Each identity writes with its own author, persisted with its own stores.
* Two identities of one node reach each other through a path inside the process, because a node does not dial its own endpoint; they establish, grant and converge exactly as identities on two nodes do.

The arrangement is sized for a personal device carrying between 1 and 10 identities of one person. A node shared by different people is a question of process boundaries rather than of how one node divides itself, and is not what this decision answers.

### Consequences for access

* Good — a session serves exactly what the identity named in it was granted, so a node holding two grants of one issuer receives each on its own.
* Good — a withdrawal toward one identity closes that identity's access and leaves a co-located identity's untouched, the two holding separate replicas.
* Good — a local read answers from the acting identity's own stores, so an issuer only a co-located identity holds is unknown to the caller.
* Good — an entry names the identity that wrote it, so a cell member and a counterparty bind an author to an identity rather than to a device.
* Neutral — a node's claim to act as an identity is checked against that identity's device set rather than proven; a node that legitimately hosts two identities can act as either, which it can do in any arrangement, holding the material of both.
* Bad — payload bytes stay content-addressed in one store per node and are served to any caller that asks for a hash, so the isolation covers entries and not payload transfer; closing it belongs with identity-bound authorization.
* Neutral — a compromised process holds the material of every identity it hosts: what this decision separates is honest storage, authorship and serving.

### Consequences for linkability

* Bad — one endpoint is one node id, published in the device set of every identity the node hosts, so a counterparty of two identities of one person sees that they share a node.
* Neutral — the network says as much: those identities share an address and a relay, and they are online together.
* Good — the author no longer correlates them, each identity writing under its own.
* Neutral — separating the node ids is what an endpoint per identity would take; this decision leaves everything above the hosted identity independent of how many endpoints a node binds, so that arrangement stays open.

### Other consequences

* Bad — a namespace two identities of one node hold is stored twice, and the fixed cost of a replica store is paid per identity.
* Good — the cases where two identities of one person meet — a connection between them, a cell they are both members of — become ordinary cases rather than unreachable ones.
