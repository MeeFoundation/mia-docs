# Multi-identity node

## Purpose

One node hosts several identities — for example Alice-at-work and Alice-at-leisure — each with its own store set — its private metadata store (PMS) and the stores of the pods it holds — added to a device explicitly and addressed independently. A group of people is no identity a node hosts: its members share a [pod](../../../../architecture/language/pod.md), whose stores each member identity holds as replicas of its own. Admission to each of those stores is classified per session, by the records of the identity the session names ([reconciliation sessions](../reconciliation-sessions/spec.md), Invariant 2).

## Requirements

### Requirement: An identity is added to a device explicitly
Each identity SHALL arrive on a device through its own explicit linking act, from a linking invite minted by one of that identity's devices ([device-linking](../../pdn-node/device-linking/spec.md)). Linking one identity SHALL NOT import, discover, or propagate any other identity: no cascade at linking time, and no automatic appearance of an identity on already-linked devices.

#### Scenario: Second identity requires its own linking
- **WHEN** a device is linked into identity A and identity B's stores exist elsewhere
- **THEN** identity B's stores appear on the device only after a separate linking act with a linking invite for identity B

### Requirement: A node hosts several identities, each with replicas of its own

A `SyncNode` SHALL host the store sets of any number of identities concurrently, each with stores of its own ([identity-scoped replicas](../identity-scoped-replicas/spec.md)): each identity's private metadata store (the PMS, carrying its device set, its tickets, its identity key and its records of the pods it holds) is a replica of its own, and so is each store of every pod the identity is a member of, created or imported on the same node. A pod's stores are addressed by the pod id within the identity that holds them; the PMS is reached through its store handle. The stores of different identities SHALL NOT share a replica, and neither SHALL two identities that acquired one namespace — two members of one pod hosted on one node: each holds a replica of its own.

**Example:** node a1 hosting Alice-work and Alice-leisure.

| one per node | one per hosted identity |
|---|---|
| the endpoint, and the node id it binds with | a docs engine and its replica store |
| the router and its ALPNs | a registry: a pod's two stores by pod id |
| gossip | an access book: its PMS |
| the blob store | an author |
| the reconcile passes, walking every identity | |

#### Scenario: Two identities' private stores on one node

- **WHEN** private metadata stores are created on one node for identity A and identity B
- **THEN** they are two distinct replicas, each reached through its own handle and holding only its identity's entries — device records and pod records included

#### Scenario: One namespace acquired by two identities is two replicas

- **WHEN** two identities hosted on one node are both members of one pod
- **THEN** the node holds two replicas of each of the pod's stores, one per identity, and one identity forgetting the pod leaves the other's replicas held

### Requirement: No session is served without a verdict

Every replica a node holds SHALL be held for an identity that node hosts, and every reconciliation session SHALL be judged before it serves anything: the store SHALL take the verdict of a session access provider on both session roles, and a node SHALL NOT be assemblable without one. A pod's store SHALL be judged by the records of the identity that holds it — its PMS for its own devices, its membership view for every other member's — as the [pod stores](../pod-store/spec.md) spec states, judging it by the identities the session names. A session for a replica the identity holds in no role SHALL be refused indistinguishably from the replica not being hosted, and possession of a pod store's ticket SHALL admit nobody by itself.

A PMS SHALL keep the bound Invariant 1 gives it — its ticket — rather than the records: a PMS is where the records that judge every other session arrive, and judging it by its own device set, before that set has converged, would close the bootstrap that delivers it.

**Example:** Bob's replicas on node b1, each synced by a holder of its ticket; b2 is Bob's laptop, and Dave holds the ticket of the record store of "Family" without being a member of it.

| replica | judged by | ticket holder | session |
|---|---|---|---|
| Bob's PMS | its ticket (Invariant 1) | b2 | served: Bob's device records reach b2 |
| the record store of "Family" | Bob's membership view of "Family" | Dave | refused as not hosted: Dave is no member |

#### Scenario: A pod store refuses a ticket holder that is no member

- **WHEN** a node holds a pod's stores for a member identity, and a holder of the stores' tickets that is no member of the pod requests a sync
- **THEN** the request is refused indistinguishably from the store not being hosted, and no entry is served

#### Scenario: A PMS still replicates between the identity's devices

- **WHEN** a device of an identity syncs that identity's PMS with a sibling holding its ticket
- **THEN** the session proceeds, so the device records that judge every other session arrive
