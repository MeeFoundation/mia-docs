# Node assembly

## ADDED Requirements

### Requirement: Every replica the node holds open outside a pod joins a periodic reconcile pass, at a cadence the spawn names
`SyncNode` SHALL run a periodic pass that re-requests a sync for every document it holds open outside a pod — the private metadata store (PMS) and every other replica that is no pod store — whichever synchronization strategy that document follows, and the interval SHALL be named at the spawn with a default of 10 seconds. The pass SHALL skip a pod's stores: those are reached by the pod stores' own pass at `pod_reconcile_interval` ([pod store](../pod-store/spec.md), "A pod store's periodic pass reaches at most 5 peers every 5 minutes"). The pass's step over the pairs of identities one node hosts SHALL reconcile every replica the two share in process, a pod's two stores included, the membership store before the record store.

The interval is what bounds every convergence no read of its own nudges outside a pod: a write reaching another device of the same identity, and a linking catch-up, whose re-dial cadence is that pass. It is written down here because a host that configures its own value — a phone trading battery against how long a person waits — needs somewhere to configure it *from*, and because the resulting speed is otherwise read as a property of the network rather than of a number somebody chose.

**Example:** Alice's phone with her PMS and the pod "Family", spawned with the defaults: the PMS is re-requested from her other devices every 10 seconds; Family's membership store and record store are left to the pod pass, which first runs within 45 seconds of the spawn and then every 300 seconds.

#### Scenario: A spawn that names no interval gets the default
- **WHEN** a node is spawned without naming a reconcile interval
- **THEN** its periodic pass runs at 10 seconds

#### Scenario: A host's own interval is what the node runs at
- **WHEN** a node is spawned with an interval of its embedder's choosing
- **THEN** the periodic pass runs at that interval, and no route, environment variable or harness call changes it afterwards

#### Scenario: A pod's store is not re-requested by this pass
- **WHEN** a node holding a pod's two stores and its PMS runs the pass at its 10-second default
- **THEN** the PMS is re-requested from the node's contacts and neither pod store is, their next sessions with another node coming from the pod stores' pass at its own interval
