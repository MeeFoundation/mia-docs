# Proposal: pods-scale-and-storage

## Why

A pod is two stores, the membership store and the record store, each held whole as a replica of its own by every member identity on every device that hosts it, and every record replicates to every member device with its payload ([pod stores](../../specs/components/mee-pdn/data-layer/pod-store/spec.md)). The standing cost grows with the pods a device holds: every replica takes a reconcile pass — each store of a pod every 5 minutes, over at most 5 peers drawn at random, and every other replica every `SpawnOptions::reconcile_interval`, 10 s by default — and the store's range fingerprint (`get_fingerprint` in `crates/pdn-store/src/store/fs.rs`) is a linear scan. The identity-scoped replicas measurement shows where the cost sits, on a store of 100,000 entries: a catch-up spends 93% of its time on the receiving store's actor thread and under 2% on the serving one's, while a pass over a converged pair is 97% fingerprint work, 39 milliseconds per pass. Storage grows the same way: every payload lands on every member device, and no quota bounds a pod. Load tests of pods produce the numbers these questions wait for; this change takes them and settles the questions.

**Example:** what a device holds as its identities join pods, each pod being two replicas per member identity the device hosts.

| device | identities it hosts | pods each is a member of | replicas the reconcile pass walks every 5 minutes |
|---|---|---|---|
| Bob's phone b1 | Bob | 1 | 2 |
| Bob's phone b1 | Bob | 50 | 100 |
| Alice's phone a1 | Alice | 300, each a personal folder she keeps alone | 600 |
| Alice's tablet a3 | Alice-leisure and Alice-work | 50 each, 10 of them shared | 200 |

## What Changes

Nothing is decided. The change settles the questions below from the load tests' numbers, strongest option first where a question has options, and then specifies and builds the answers.

## Open Questions

### When the linear-scan fingerprint gives way to a cached fingerprint tree

With two stores per pod the tree serves each store over its own order. By the measurement above the tree pays off on the standing cost of passes over quiet stores — two per pod for every member identity a device hosts — and not on catch-up; a record store with 100 writers is never quiescent, so every catch-up session scans it per round. The load tests show at how many pods and entries per device the passes over quiet stores become the cost that matters.

### When the membership view is remembered

A device builds the membership view over a pod's whole membership store again on every classification of a session on either of the pod's stores, in both roles, on every derivation of the pod's contacts and on every read, and nothing remembers the result (`membership_view_and_entries` in `crates/data-layer/src/access.rs`, `MembershipView::new` in `crates/data-layer/src/pod/membership_view.rs`). A pull of one new record-store entry builds it three times on each side — the classification of the membership store's session that `order_after` puts first, the derivation its end prompts, and the classification of the record store's session — and `append_op` and `act` build it twice each under the runtime's state lock.

- A memo per pod, kept while the membership replica's entries and the payloads it holds stay as they are: a pull or a read on a quiet membership store builds nothing, at the cost of state that has to follow the replica. A memo keyed on the replica's write count alone goes stale when a payload arrives, since an arriving payload changes an entry's verdict.
- One membership view shared by the two sessions of a pull and the derivation after them: a pull builds it once on each side, a read still builds it every time, and the engine carries the view from one session to the next.
- Signature verdicts cached by key, author and content hash: the cost of the signature checks goes, and every build still reads every entry and payload.

**Example:** a pod of 100 members on 2 devices each, 300 entries in its membership store, each build of its membership view about 15 ms on a desktop in a release build; Alice's laptop a2 pulls one new operation from one neighbor and serves it to another.

| option | membership view builds on a2 for that operation | time on a2 |
|---|---|---|
| as today | 6 | about 90 ms |
| a memo per pod | 0 | reading the memo |
| one build per pull | 2 | about 30 ms |
| cached signature verdicts | 6, none checking a signature | 6 reads of 300 entries and their payloads |

### Reachability beyond relays

Two devices on different networks without a relay and without DNS do not reliably reach each other, so a pod across networks rests on iroh relays, which the stack binds and the product is expected to run itself. Beyond them, always-on member devices can serve as the pod's hubs, and whether the platform prefers them as contacts is open.

### Swarm and cadence parameters for 200 nodes

A pod of 100 members on 2 devices each is a swarm of 200 nodes, in which an announcement reaches everyone in 3 to 4 hops of HyParView's active view. The active and passive view sizes and the churn of mobile devices are set from the load tests, and so are the numbers of the pod stores' pass, 5 minutes and 5 peers a run.

### What a device downloads

- Records everywhere, payloads on demand: a device holds every entry and fetches a payload when it is read, through the fork's download policy. A device's storage follows what its member reads, and a first read of a payload waits for a member device that holds it to be reachable.
- Records and payloads everywhere, as a pod does today: every read is local, and every device stores every payload of every pod its identities are members of.

**Example:** Carol's phone c1 holds "Family", in which Bob places a 20 MB scan that Carol never opens.

| option | c1's storage for the scan | Carol opens it a month later, with every other device offline |
|---|---|---|
| payloads on demand | the entry alone | cannot read it until a device that holds the payload is reachable |
| payloads everywhere | 20 MB | reads it at once |

### Files

Attachments as blobs, size limits, and a rename or a move of a file, which places a new record beside the old one while no record is deleted.

### Storage bounds

A quota per pod on a device, and a disk that fills in the middle of a sync: what the device keeps, what it refuses, and what the member sees.

## Operating conditions

Several identities on one node multiply the replicas a device holds by the pods each is a member of. A disk that fills is one of the questions above. Mobile devices come and go, which the swarm parameters answer to. Clocks decide none of these.

## Capabilities

None is settled. The fingerprint tree touches `components/mee-pdn/pdn-store/crate`; the download policy and storage bounds touch `components/mee-pdn/data-layer/pod-store` and `components/mee-pdn/pdn-node/pods`.

## Impact

- **`crates/pdn-store`**: the cached fingerprint tree; the download policy it already offers.
- **`crates/data-layer`**: the download policy of a pod's record store, quotas, a memo of the membership view.
- **`crates/pdn-node`**: what the pods service reads when a payload is not local.
