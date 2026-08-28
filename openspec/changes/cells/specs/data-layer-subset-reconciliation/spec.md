# data-layer: subset reconciliation — delta for cells

## MODIFIED Requirements

### Requirement: Same-identity reconciliation is unfiltered

Reconciliation between devices of the identity a replica belongs to SHALL deliver every claim of that replica — all are read-authorized by Invariant 1 — so the filter does not restrict an identity's own devices. A cell store extends the same rule to every member: reconciliation between devices of the cell's members SHALL deliver every entry, since a cell has no narrower audience than its members. On a multi-identity node this SHALL be judged per replica: a node is an own device for the replicas of the identities it is linked into, a member device for the cell stores of the cells those identities are members of, and a scoped peer elsewhere.

#### Scenario: Own devices replicate in full

- **WHEN** two devices of one identity reconcile a replica bound to that identity
- **THEN** all claims replicate, with no capability presented

#### Scenario: Being an own device is per replica, not per node

- **WHEN** a node linked into identity A but not identity B reconciles a replica of B under a capability covering one claim
- **THEN** the filter applies — only that claim is delivered — even though the node is fully authorized for A's replicas

#### Scenario: Member devices of a cell replicate in full

- **WHEN** a device of member A and a device of member B reconcile the cell store of a cell both are members of
- **THEN** every entry replicates, with no capability presented

### Requirement: Grantees stay outside the gossip swarm

A peer whose access arrived through a grant SHALL NOT be a member of the replica's gossip swarm. The swarm SHALL consist of the replica's device set: the issuer's own devices for a data store or a directory, the counterparty's devices too for a connection metadata store, and the devices of every member for a cell store — a cell has no grantees, its members are its whole audience, so member devices join the swarm as an identity's own devices do. A grantee's only data path is the reconciliation it initiates. This composes with the content-free topic above: membership conveys announcements, so removing a grantee from the swarm (rather than serving it filtered) keeps even activity metadata about unauthorized claims off its wire, and spares the relaying cost a broadcast presumes members share.

Membership SHALL follow the recorded sync strategy in both directions: a grantee import of a replica that had already joined the swarm — a device-replicated import downgraded to a grantee binding — SHALL leave the swarm as part of the import, not merely stop re-joining (the fork's leave-gossip operation: the topic subscription closes in both directions while the replica stays open, syncing, and subscribed to). A data import SHALL refuse a ticket naming a replica that is tracked but not data-bound (a directory, a connection metadata store, a cell store): repurposing a device-shared replica's tracking — and, with the downgrade now leaving the swarm, cutting its live path — must not be reachable on the word of whoever minted a ticket.

#### Scenario: A scoped peer receives nothing over gossip

- **WHEN** a claim is written into a replica whose swarm is the issuer's devices, while scoped peers hold capabilities on other claims
- **THEN** no scoped peer receives the claim or any digest of it over gossip, and the issuer's devices receive the claim itself

#### Scenario: A grantee receives entries by reconciliation only

- **WHEN** the issuer writes after a peer imported the replica's ticket, past the window in which a swarm would have formed
- **THEN** a granted peer receives the write, filtered to its granted claims, over its next classified reconciliation, and a bare-ticket holder with no recorded grant receives nothing — the write never arrives over gossip

#### Scenario: A swarm member is served only while authorized

- **WHEN** a peer that is a swarm member of a replica holds a grant, converges on a write, then has the grant withdrawn and the issuer writes again
- **THEN** the post-withdrawal write never reaches it although it is still a swarm member — content follows the access book, not swarm membership, and what was delivered while granted is retained

#### Scenario: A device-shared replica refuses a data import

- **WHEN** a data import — device or grantee — is handed a ticket naming a replica that this node tracks as a directory, a connection metadata store or a cell store
- **THEN** the import is refused, and the device-shared replica's tracking, swarm membership, and live path are untouched

#### Scenario: Member devices of a cell form its swarm

- **WHEN** a member writes into a cell store while devices of the other members are subscribed to its topic
- **THEN** those devices converge on the entry through the content-free announcement and the pull it triggers, none of them holding a grant
