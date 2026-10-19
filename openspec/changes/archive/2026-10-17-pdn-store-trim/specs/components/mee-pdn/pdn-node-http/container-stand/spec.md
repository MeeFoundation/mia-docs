## MODIFIED Requirements

### Requirement: Convergence is waited for at the runtime's own cadence
A scenario SHALL wait for convergence by repeating a read, bounded by a budget above the delivery it waits for: a record placed in a pod reaches another member through the announcement in its store's swarm and the pull that announcement triggers, and a wait for it SHALL take a budget of several PMS reconciliation intervals; a wait for what only a pod store's periodic pass delivers — a record announced to no neighbor — SHALL take a budget above that pass's interval. No route, environment variable, or harness call SHALL force a reconciliation or shorten the runtime's cadence.

**Example:** Bob waits to read a claim Alice placed in "Family"; `<record>` is its reference and `<bob>` his identity in hex.

| part | what it does |
|---|---|
| the runtime reconciles | a PMS every 10 s and a pod's stores every 300 s, its defaults, which nothing on the stand shortens |
| the record arrives | through the announcement in the record store's swarm and the pull it triggers |
| the scenario reads | every 100 ms: 409 until Bob's node holds the pod, 404 until the record arrives, then 200 |
| its budget | 2 min, `CONVERGENCE_BUDGET` |
| on expiry | `"<record> never read back as expected for <bob>"`, the last answer, the node's log tail |

#### Scenario: A wait ends when the value arrives
- **WHEN** a scenario waits for a value written on another container
- **THEN** it repeats the read until the value appears or its budget expires, and a failed wait names what it waited for

### Requirement: The stand restarts a node and asserts what came back
The stand SHALL stop a node's container and start it again with its state directory intact, and SHALL assert that the node came back as itself: the same node id, the identity still hosted, its pod still listed, and a record placed before the stop still readable; a record placed on it after the restart reaching the pod's other member with no ceremony repeated, within the convergence budget after a kill as after a stop — the restarted node's swarm forms again at once, and the other member reaches it at the address it came back on ([node assembly](../../data-layer/node-assembly/spec.md)); and that member still listing the restarted node's identity as a member. The stand SHALL also kill a node's container — no grace, no shutdown path — and start it again, asserting the same recovery, because a process that ends without warning is the ordinary end of a process, and recovery that differs by the manner of stopping depends on a goodbye a kill does not provide. One kill SHALL land in the middle of a stream of writes: every write acknowledged before the stores' settle window — the bounded delay after which an acknowledged write has committed, since the replica store and the blob store each commit after the acknowledgement, on a timer — SHALL be readable after the restart, and a write the kill cut inside that window, acknowledged or not, SHALL be absent or whole — never a torn value and never a read error. The assertion SHALL be paired, in the same scenario, with the tightest denial: a node started from the same image on an empty state directory holds none of it. Without that arm the scenario passes just as well against a node that quietly re-created everything.

**Example:** a kill mid-stream of placements into the pod "Stream", the indices as one run cuts them; settle window 2 s (the replica store commits within 500 ms).

| writes | acknowledgement | read back |
|---|---|---|
| records 0 to 41, "value-0000" … "value-0041" | acknowledged over 2 s before the kill | after the restart each reads whole |
| records 42 to 49 | acknowledged in the last 2 s | each 404, or whole |
| record 50 | cut by the kill, never acknowledged | unlisted, or listed and read whole |
| none of them | a torn value, or a status besides 200 and 404 | |

#### Scenario: A restarted node is the same node
- **WHEN** a node holding an identity that is a member of a pod is stopped and started again on its own state directory
- **THEN** it reports the same node id, hosts the same identity, lists the same pod, and reads a record placed before the stop, and the pod's other member still lists that identity as a member

#### Scenario: A killed node comes back the same way
- **WHEN** a node holding an identity that is a member of a pod is killed without grace and started again on its own state directory
- **THEN** it reports the same node id, hosts the same identity, lists the same pod, and reads a record acknowledged before the stores' settle window, and the pod's other member still lists that identity as a member

#### Scenario: A kill mid-stream loses nothing settled
- **WHEN** records are being placed on a node in a stream and its container is killed without grace mid-stream, then started again
- **THEN** every record whose placement was acknowledged before the stores' settle window is readable with its payload, and a record the kill cut inside that window — acknowledged or not — is either absent or read whole, never partial

#### Scenario: A node on an empty directory holds nothing
- **WHEN** a node is started from the same image on an empty state directory
- **THEN** it reports a node id of its own, hosts no identity, and refuses reads addressed to the identity the restarted node hosts

#### Scenario: A peer converges with the restarted node without a new ceremony
- **WHEN** the restarted node places a record after coming back, stopped or killed before
- **THEN** the pod's other member converges on that record within the convergence budget, with no invite minted and no linking performed after the restart
