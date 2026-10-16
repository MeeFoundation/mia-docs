# Identity-scoped replicas

## Purpose

A hosted identity owns its own half of the node: the replicas it acquired, the author its writes carry, and the sessions it takes part in. On the wire that party travels as 32 opaque bytes pdn-store compares and never interprets, filled here with the identity's `PdnId`: the store keeps the value, not the vocabulary that gives it meaning. What one identity holds is stored, written and served apart from what another identity of the same node holds, so co-location separates by where the bytes live rather than by a check at each read. ADR-0013 states the level of isolation this carries and what it leaves to a counterparty's observation.

## Requirements

### Requirement: A sync session names the replica's identity and the caller's

A sync session SHALL name the identity whose replica is addressed and the identity the caller acts as, and the serving side SHALL admit the caller's named identity only when the records it holds of that identity list the caller's authenticated node id among its devices — the device statements its membership view counts where a member's device serves another member's in one of a pod's stores. A PMS SHALL be served whole to a session naming the identity it belongs to, the caller unchecked: its ticket gates it (Invariant 1), and its namespace id reaches only that identity's devices, over the linking dialogue, so the id is a secret of the ticket's rank. A caller naming an identity it is not a device of SHALL be refused indistinguishably from the replica not being hosted, and so SHALL a session naming an identity the node does not host; the one exception is the membership store's, which takes a current member's own device statements from a node they do not list yet, as the [pod stores](../pod-store/spec.md) spec states. The session's egress and its write admission SHALL follow the named identities alone.

**Example:** Alice (node a1) and Bob (node b1) are members of "Family", and Bob's device statement lists b1 alone; m1 hosts Dave, no member.

| caller node | `Init.caller` | `Init.identity` | `Init.namespace` | a1 answers |
|---|---|---|---|---|
| b1 | Bob | Alice | the record store of "Family" | a session: the store whole |
| m1 | Bob | Alice | the record store of "Family" | `00 00 00 02 02 00`, `Message::Abort { reason: AbortReason::NotFound }` |
| b1 | Bob | Carol, not hosted on a1 | the record store of "Family" | `00 00 00 02 02 00` |
| b1 | Bob | Alice | one a1 does not hold | `00 00 00 02 02 00` |

#### Scenario: A caller naming an identity it is not a device of is refused

- **WHEN** a node that is a device of no identity of the caller's choosing names that identity in a session on a pod's record store
- **THEN** the session is refused indistinguishably from the replica not being hosted, and no entry is served

#### Scenario: A device of the named identity is served

- **WHEN** a device listed in an identity's records names that identity and addresses a replica that identity's records admit it to
- **THEN** the session proceeds, serving what those records admit

#### Scenario: An identity the node does not host is refused

- **WHEN** a session names an identity the serving node does not host
- **THEN** it is refused indistinguishably from the replica not being hosted

### Requirement: Every replica belongs to the identity its create or import names

Every replica a node holds SHALL belong to exactly one hosted identity, and the act that brings it there — the creation or import of a PMS, the creation of a pod, the import of a pod's stores at a join or from the identity's own PMS — SHALL name that identity. Two identities SHALL NOT share a replica, whether they are two members of one pod or one of them imported a ticket the other minted. An act naming an identity the node does not host SHALL be refused with nothing registered, for that identity or for any other. A replica an identity holds is no evidence that it is a member: what one of a pod's stores serves and what its entries count for follow the membership view of the identity that holds it ([pod stores](../pod-store/spec.md)).

**Example:** Alice-work and Alice-leisure are hosted on node a1, and Alice-work alone is a member of "Family"; `<x>` is x's `PdnId` in hex.

| replica | in | brought by | serves |
|---|---|---|---|
| Alice-work's PMS | `identities/<Alice-work>/docs.redb` | `create` of Alice-work | Alice-work's devices |
| the record store of "Family" | `identities/<Alice-work>/docs.redb` | Alice-work's join | the members' devices |
| the record store of "Family" | nowhere for Alice-leisure | — | — |
| an import of the stores of "Family" naming Carol, hosted on no node here | nowhere | refused: Carol is not hosted | — |

#### Scenario: An import naming an identity the node does not host registers nothing

- **WHEN** a pod's stores are imported naming an identity the node does not host
- **THEN** the import is refused, and nothing is registered for the named identity or for any identity the node hosts

#### Scenario: A pod one identity holds is unknown to a co-located identity

- **WHEN** an identity is a member of a pod and a co-located identity is no member of it
- **THEN** the co-located identity reads and lists nothing of the pod, and is answered as it is for a pod no identity here holds

### Requirement: A PMS starts syncing once it is armed

A PMS created or imported for an identity SHALL start its sync only once it is armed for that identity's sessions, which happens when the identity is hosted on it. Until then the identity's own book knows nothing to judge the store's sessions by and refuses them, and a first session refused that way is retried by nothing before the next reconcile pass.

**Example:** a2 links into Alice from a1; a2 imports her PMS from the linking reply.

| step on a2 | its PMS |
|---|---|
| import | held, not syncing: a session a1 opens now is refused |
| `host_identity`: armed | dials a1 as Alice; sessions from a1 are served |
| the first session ends | holds Alice's device records, ready for the link's catch-up wait |

#### Scenario: A PMS converges from the sessions its arming starts

- **WHEN** a device imports an identity's PMS and the identity is then hosted on it
- **THEN** the device's PMS converges with its sibling's from the sessions that hosting starts

### Requirement: Admission is the named identity's and is never unioned across a node's identities

A serving node SHALL decide a session from the identity the caller names alone, and SHALL NOT add to it what any other identity the caller's node id resolves to would be admitted to. A node that hosts a member of a pod and a co-located identity that is no member SHALL therefore be served, in each session, exactly what the identity named there is admitted to.

**Example:** Bob and Erin are hosted on node t1, and Bob alone is a member of "Family", which Alice holds on a1.

| session from t1 to a1, naming | on the membership store of "Family" |
|---|---|
| Bob | served |
| Erin | refused as not hosted, though Bob shares the node's id |

#### Scenario: A co-located non-member is refused where its node mate is served

- **WHEN** a node hosts a member of a pod and a co-located identity that is no member, and a session from that node names the non-member on the pod's membership store
- **THEN** the session is refused, while a session naming the member is served
