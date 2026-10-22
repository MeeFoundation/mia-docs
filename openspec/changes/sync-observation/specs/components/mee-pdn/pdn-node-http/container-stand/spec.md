# Container stand

## MODIFIED Requirements

### Requirement: Convergence is waited for at the runtime's own cadence
A scenario SHALL wait for convergence by repeating a read, bounded by a budget above the delivery it waits for: a record placed in a pod reaches another member through the announcement in its store's swarm and the pull that announcement triggers, and a wait for it SHALL take a budget of several PMS reconciliation intervals; a wait for what only a pod store's periodic pass delivers — a record announced to no neighbor — SHALL take a budget above that pass's interval. No route, environment variable, or harness call SHALL force a reconciliation or shorten the runtime's cadence, through the host's pod interval setting or otherwise: `PDN_POD_RECONCILE_INTERVAL_SECS` stays unset on every container of the stand.

**Example:** Bob waits to read a claim Alice placed in "Family"; `<record>` is its reference and `<bob>` his identity in hex.

| part | what it does |
|---|---|
| the runtime reconciles | a PMS every 10 s and a pod's stores every 300 s, its defaults, which nothing on the stand shortens: `PDN_POD_RECONCILE_INTERVAL_SECS` is unset on every container |
| the record arrives | through the announcement in the record store's swarm and the pull it triggers |
| the scenario reads | every 100 ms: 409 until Bob's node holds the pod, 404 until the record arrives, then 200 |
| its budget | 2 min, `CONVERGENCE_BUDGET` |
| on expiry | `"<record> never read back as expected for <bob>"`, the last answer, the node's log tail |

#### Scenario: A wait ends when the value arrives
- **WHEN** a scenario waits for a value written on another container
- **THEN** it repeats the read until the value appears or its budget expires, and a failed wait names what it waited for

### Requirement: The pods demo runs on the stand's image
The pods demo SHALL run the same image the suite runs, with every node on one container network and each node's HTTP port published on loopback of the demo host. Each node SHALL have a volume of its own for its state. The demo SHALL remove its nodes, its network and those volumes on every exit, the failing one included, and it SHALL drive the nodes over HTTP alone, so what passes between nodes is the runtimes' own traffic.

**Example:** `just demo-pods`, with a compose file and a project of its own, every node on network `demo` with `PDN_DEBUG=1` and, for the demo's browser screens, `PDN_ANY_ORIGIN=1` ([host](../host/spec.md), "The debug surface opens to a browser's page of any origin only when asked": every page open in a browser on the demo host then reads what the nodes' debug surfaces answer).

```
just demo-pods           ops/compose-pods.yml, project pdn-demo-pods, 6 nodes, PDN_DEBUG=1 and PDN_ANY_ORIGIN=1 on each
  alice-phone      127.0.0.1:3021 → 3011    volume alice-phone-state; stopped and started mid-show with alice-laptop, same node id
  …
  dave-phone       127.0.0.1:3026 → 3011    volume dave-phone-state
on every exit            docker compose -f ops/compose-pods.yml down --remove-orphans --volumes
```

#### Scenario: A demo brings up the nodes it names
- **WHEN** the demo recipe runs
- **THEN** it builds the image, brings up every node its compose file names, and waits for each of them to answer liveness before the first step

#### Scenario: A run never meets the previous run's state
- **WHEN** the demo exits, whether it finishes or fails
- **THEN** its containers, its network and its volumes are removed

#### Scenario: A demo publishes on loopback
- **WHEN** a node of the demo publishes its HTTP port
- **THEN** the port is bound to loopback, because the debug surface is unauthenticated and mints live ceremony secrets

#### Scenario: The pods show carries on without its creator's devices
- **WHEN** the pods demo stops every device of the pod's creator mid-show and starts them again later
- **THEN** while they are down a newcomer joins on another member's invite and reads what was placed before, and an edit reaches every online member device; started again, they come back as the same nodes and read what happened without them; and an owner's removal stops what reaches the removed member

## ADDED Requirements

### Requirement: The stand's image carries no observation surface, and a second image does
The stand's image SHALL be built without the host's observation feature, and the image build SHALL take the features to enable as a build argument that is empty by default. The container suite SHALL build a second image with the observation feature, in the release profile as the stand's image is, and SHALL run against it only the scenarios of the observation routes, beside a scenario asserting that the stand's image serves none of them.

**Example:**

| image | built with | used by |
|---|---|---|
| the stand's image | no feature | every scenario of the stand, the live demos, and the observation routes' absence |
| the observation image | `FEATURES=observation` | the observation routes' scenarios |

#### Scenario: The stand's image has no observation routes
- **WHEN** a container starts from the stand's image with the debug surface enabled
- **THEN** requests to the observation routes return HTTP 404, and its status states `observation off`

#### Scenario: The observation image serves them
- **WHEN** a container starts from the observation image with the debug surface enabled
- **THEN** the observation routes answer, its status states `profile release` and `observation on`, and every other route answers as on the stand's image
