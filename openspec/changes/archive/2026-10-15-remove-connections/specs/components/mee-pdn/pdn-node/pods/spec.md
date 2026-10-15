## MODIFIED Requirements

### Requirement: Hosted pods survive a restart

A directory-configured runtime SHALL host again, after a restart, every pod its hosted identities are members of, from durable state alone — both stores keep replicating and its members' devices are served — while a memory runtime's pods end with the process. The hosted pods SHALL be re-derived from each hosted identity's PMS: every pod whose record in the [private metadata store](../../data-layer/private-metadata-store/spec.md) is live, both stores opened from the pod's published tickets in the identity's own replica store, and a contact that names this node's own address reached inside the process. The identity's hosting record SHALL name no pod.

**Example:** Alice's tablet a3 runs on a storage directory and hosts Alice-leisure and Alice-work, both members of "Wedding"; Alice-work left a second pod, `684aad236ce530cd7b5dedb6ab6b755a`, before a3 stops.

| step | a3 |
|---|---|
| a3 stops | on disk, the entry at the highest sequence under `pods/f942dfc21acd0218d48f61f714ddfff3/` is non-empty in Alice-leisure's PMS and in Alice-work's, and the one under `pods/684aad236ce530cd7b5dedb6ab6b755a/` is a tombstone in Alice-work's |
| Erin places a claim from her phone e1 meanwhile | — |
| a3 starts on the same directory | opens Wedding's two stores for Alice-leisure and for Alice-work, each from the tickets in the identity's own PMS, and for `684aad236ce530cd7b5dedb6ab6b755a` Alice-work's tombstone alone, no record store; neither hosting record names a pod |
| a3's first sessions | Erin's claim arrives, and Alice-leisure's and Alice-work's replicas converge inside the process |

#### Scenario: A pod is hosted again after a restart

- **WHEN** a runtime on a storage directory hosts a member of a pod, stops, and starts again on the same directory, while another member wrote an entry in between
- **THEN** the identity lists the pod, and the entry written meanwhile arrives

#### Scenario: Two members hosted on one node come back each with its own copy

- **WHEN** a runtime on a storage directory hosts two members of one pod, restarts on the same directory, and one of them places a record, with no other node reachable
- **THEN** both list the pod and the other reads the record

#### Scenario: A pod left before the restart stays left

- **WHEN** a runtime on a storage directory hosts a member of a pod, the member leaves the pod, and the runtime stops and starts again on the same directory
- **THEN** the identity lists no such pod, the record store is neither opened nor served, and the membership store stays as the pod's tombstone
