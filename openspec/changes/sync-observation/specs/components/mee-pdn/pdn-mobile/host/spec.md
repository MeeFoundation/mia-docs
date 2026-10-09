# Mobile host

## ADDED Requirements

### Requirement: A test build exports the runtime's observation, and what ships does not
The facade SHALL have an observation feature, off in every build a device installs, that enables the runtime's test-only feature and exports exactly 5 further calls: a subscription to one hosted identity's stores of one pod, whose asynchronous next call answers the next record waiting in the runtime's buffer as one line of the runtime's own JSON, or nothing once the subscription has ended; the observed join of one hosted identity on an invite code, answering the same kind of subscription, which also names the pod joined; the record listing of that identity's record store as the runtime's JSON; a bring-up that names the pod interval beside the reconcile interval, each refused at 0 as the bring-up refuses its interval; and the build profile, `release` or `debug`. The subscription, the observed join and the listing SHALL each delegate to the one runtime call of the same purpose ([observation](../../pdn-node/observation/spec.md)) and SHALL report a refusal through the facade's own error table. The facade SHALL read no field of a record; a record crosses as the runtime wrote it. The feature SHALL compile in the release configuration a release is built in. Without the feature, the facade SHALL contain none of the 5 calls and remain the surface the requirements above state.

**Example:** the agent observing one pod, in the test build.

```
await node.bringUpWithPodInterval(dir, 10, 300)
profile = await node.buildProfile()           // 'release'
sub  = await node.observePod(me, pod)         // refused, as a refusal of the table, when me holds no store of the pod
joined = await node.joinPodObserved(me, code) // the join's refusals as joinPod's; joined.pod() names the pod, joined.next() from seq 0
line = await sub.next()                       // '{"sub":"c41e…","seq":0,"store":"records","kind":"insert_remote",…}'
list = await node.podRecordListing(me, pod)   // '[{"key":"by/…/immutable-document/…/1","author":"…","hash":"8c1d…","len":256,"present":true,"payload":"eyJ…","verdict":"counted"}]'
```

#### Scenario: The test build yields the runtime's records
- **WHEN** 2 handles of a facade built with observation are members of one pod, one places a record, and the other has subscribed to the pod
- **THEN** the subscriber's subscription yields an `insert_remote` line for that record's key naming the record store, the line parses as the record the runtime's JSON form defines, and the record listing holds the record `counted` with its payload

#### Scenario: An observed join yields the joiner's first session
- **WHEN** a handle of a facade built with observation joins, through the observed join, a pod in which another handle placed a record
- **THEN** the subscription it answers names the pod and yields, from `seq` 0, an `insert_remote` line for that record before the record-store `sync_finished` line of the session that carried it

#### Scenario: A handle without the pod is refused
- **WHEN** a third handle in the same test build, a member of no pod, subscribes to that pod or asks for its record listing
- **THEN** each call is refused through the facade's table and yields nothing

#### Scenario: A pod interval of 0 is refused at bring-up
- **WHEN** the test build's bring-up is asked for a pod interval of 0 seconds
- **THEN** it is refused as malformed and no node is brought up

#### Scenario: What ships has no observation
- **WHEN** the artifacts a device installs are built
- **THEN** the facade is compiled without its observation feature, and its exported surface names none of the 5 calls

### Requirement: The facade names its runtime's threads
The facade SHALL name every thread of its asynchronous runtime, worker and blocking alike, with the fixed prefix `pdn-node`, in every build, so a sampler in the same process can tell the node's threads from the application's. The name SHALL change nothing else the facade does.

**Example:** the threads of the application's process during a catch-up, as a sampler lists them.

| thread name | whose work |
|---|---|
| `pdn-node` (several) | the facade's runtime: sessions, the node's tasks, the observation's numbering |
| `sync-actor` (one per hosted identity) | the store's actor |
| the JavaScript thread, the main thread, others | the application, the agent included |

#### Scenario: The node's threads carry the prefix
- **WHEN** a node is brought up through the facade, in a test build or in what ships
- **THEN** every thread its asynchronous runtime starts is named with the prefix `pdn-node`
