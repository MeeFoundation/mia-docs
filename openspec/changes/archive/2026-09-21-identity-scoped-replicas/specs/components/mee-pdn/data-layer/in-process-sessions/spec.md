# data-layer: in-process sessions — delta for identity-scoped-replicas

## Purpose

Two identities of one node cannot reach each other over the network, because a node refuses to dial its own endpoint, so what two identities of one node exchange runs inside the process. The path carries the same protocol under the same classification, gate and filter as a session between two nodes, so co-located identities behave toward each other exactly as identities on separate nodes do.

## ADDED Requirements

### Requirement: A dial to this node's own address runs inside the process

A dial whose target address carries this node's own wire identity SHALL run the sync session inside the process, over the same protocol as a session between two nodes, with the same session setup, the same rights resolution, the same egress filter and the same ingest gate on both sides. The choice SHALL follow from the address alone, so a contact list, a ticket, or a device record that names this node reaches the path without a caller choosing it. No entry SHALL move between two identities of one node by any other route.

#### Scenario: Two identities of one node converge a namespace both hold

- **WHEN** one hosted identity writes into a replica of a namespace a co-located identity also holds, with no other node reachable
- **THEN** the co-located identity's replica comes to carry that entry, payload included

#### Scenario: A co-located audience receives only what its grant covers

- **WHEN** one hosted identity grants a co-located identity one claim of its namespace and writes both that claim and another
- **THEN** the co-located identity's replica carries the granted claim alone, and the withheld one is absent from it

#### Scenario: A contact naming this node is reached after a restart

- **WHEN** a node whose two identities both hold one namespace restarts, and the contacts of one name this node's own address
- **THEN** the pair reconciles again with no dial failing, and no ceremony is repeated

### Requirement: A write reaches the co-located identities that hold its namespace

A write SHALL announce to the identities of its own node that hold the same namespace, which SHALL then reconcile over the in-process path; the announcement SHALL carry no entry content, so what the receiving identity obtains comes through the session and its filter. A write SHALL reach a co-located identity on the announcement, without waiting for the periodic pass.

#### Scenario: A co-located identity sees a write without the periodic pass

- **WHEN** an identity writes an entry a co-located identity is granted, within one reconcile interval
- **THEN** the co-located identity reads that entry before the interval elapses

#### Scenario: The announcement carries nothing by itself

- **WHEN** a write outside a co-located identity's grant announces to that identity
- **THEN** that identity's replica gains no entry, and the withheld claim stays absent from it

### Requirement: A quiet pair of co-located identities costs no session

The periodic reconcile pass SHALL reconcile a pair of co-located identities whose replicas differ, so an announcement that never arrived is healed, and SHALL leave a pair whose replicas match alone, so passes over a quiet namespace do not accumulate sessions.

#### Scenario: A missed announcement is healed by the pass

- **WHEN** a co-located identity is brought up holding an older view of a namespace and no write follows
- **THEN** the next pass reconciles the pair and the identity converges

#### Scenario: A quiet namespace opens no session

- **WHEN** two co-located identities hold a converged namespace and nothing is written for several reconcile intervals
- **THEN** no in-process session is opened for that pair in those intervals
