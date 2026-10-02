# Proposal: cells-scale-and-storage

## Why

A cell is two stores, the membership store and the record store, each held whole as a replica of its own by every member identity on every device that hosts it, and every record replicates to every member device with its payload ([cell stores](../../specs/components/mee-pdn/data-layer/cell-store/spec.md)). The standing cost grows with the cells a device holds: every replica takes a reconcile pass — each store of a cell every 5 minutes, over at most 5 peers drawn at random, and every other replica every `SpawnOptions::reconcile_interval`, 10 s by default — and the store's range fingerprint (`get_fingerprint` in `crates/pdn-store/src/store/fs.rs`) is a linear scan. The identity-scoped replicas measurement shows where the cost sits, on a store of 100,000 entries: a catch-up spends 93% of its time on the receiving store's actor thread and under 2% on the serving one's, while a pass over a converged pair is 97% fingerprint work, 39 milliseconds per pass. Storage grows the same way: every payload lands on every member device, and no quota bounds a cell. Load tests of cells produce the numbers these questions wait for; this change takes them and settles the questions.

**Example:** what a device holds as its identities join cells, each cell being two replicas per member identity the device hosts.

| device | identities it hosts | cells each is a member of | replicas the reconcile pass walks every 5 minutes |
|---|---|---|---|
| Bob's phone b1 | Bob | 1 | 2 |
| Bob's phone b1 | Bob | 50 | 100 |
| Alice's phone a1 | Alice | 300, each a personal folder she keeps alone | 600 |
| Alice's tablet a3 | Alice-leisure and Alice-work | 50 each, 10 of them shared | 200 |

## What Changes

Nothing is decided. The change settles the questions below from the load tests' numbers, strongest option first where a question has options, and then specifies and builds the answers.

## Open Questions

### When the linear-scan fingerprint gives way to a cached fingerprint tree

With two stores per cell the tree serves each store over its own order. By the measurement above the tree pays off on the standing cost of passes over quiet stores — two per cell for every member identity a device hosts — and not on catch-up; a record store with 100 writers is never quiescent, so every catch-up session scans it per round. The load tests show at how many cells and entries per device the passes over quiet stores become the cost that matters.

### Reachability beyond relays

Two devices on different networks without a relay and without DNS do not reliably reach each other, so a cell across networks rests on iroh relays, which the stack binds and the product is expected to run itself. Beyond them, always-on member devices can serve as the cell's hubs, and whether the platform prefers them as contacts is open.

### Swarm and cadence parameters for 200 nodes

A cell of 100 members on 2 devices each is a swarm of 200 nodes, in which an announcement reaches everyone in 3 to 4 hops of HyParView's active view. The active and passive view sizes and the churn of mobile devices are set from the load tests, and so are the numbers of the cell stores' pass, 5 minutes and 5 peers a run.

### What a device downloads

- Records everywhere, payloads on demand: a device holds every entry and fetches a payload when it is read, through the fork's download policy. A device's storage follows what its member reads, and a first read of a payload waits for a member device that holds it to be reachable.
- Records and payloads everywhere, as a cell does today: every read is local, and every device stores every payload of every cell its identities are members of.

**Example:** Carol's phone c1 holds "Family", in which Bob places a 20 MB scan that Carol never opens.

| option | c1's storage for the scan | Carol opens it a month later, with every other device offline |
|---|---|---|
| payloads on demand | the entry alone | cannot read it until a device that holds the payload is reachable |
| payloads everywhere | 20 MB | reads it at once |

### Files

Attachments as blobs, size limits, and a rename or a move of a file, which places a new record beside the old one while no record is deleted.

### Storage bounds

A quota per cell on a device, and a disk that fills in the middle of a sync: what the device keeps, what it refuses, and what the member sees.

## Operating conditions

Several identities on one node multiply the replicas a device holds by the cells each is a member of. A disk that fills is one of the questions above. Mobile devices come and go, which the swarm parameters answer to. Clocks decide none of these.

## Capabilities

None is settled. The fingerprint tree touches `components/mee-pdn/pdn-store/crate`; the download policy and storage bounds touch `components/mee-pdn/data-layer/cell-store` and `components/mee-pdn/pdn-node/cells`.

## Impact

- **`crates/pdn-store`**: the cached fingerprint tree; the download policy it already offers.
- **`crates/data-layer`**: the download policy of a cell's record store, quotas.
- **`crates/pdn-node`**: what the cells service reads when a payload is not local.
