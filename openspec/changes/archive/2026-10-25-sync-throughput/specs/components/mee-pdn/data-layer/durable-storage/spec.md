# Durable storage

## MODIFIED Requirements

### Requirement: A write is on disk within the stores' settle window, and at once after a flush
Each of a node's two stores SHALL commit what it was written on a timer of its own — the replica store within 500 milliseconds of its last write, the blob store's metadata, where a small payload lies inline, within a second — so a write is on disk within that settle window, an entry and its payload apart. A commit that only makes a write readable — the one a session's snapshot or a read makes — SHALL skip the file sync, and the replica store SHALL sync it within the same window, from the oldest write it holds, whether or not anything else reaches the store meanwhile: a sync per session would hold every session behind the disk. The node SHALL offer a flush of an identity's writes (`SyncNode::flush_stores`, over the store's `DocsApi::flush`) after which every write of that identity so far is on disk, the payloads its entries reference included, and which answers the error of a commit that failed, where a commit on the stores' own timer only logs it. A caller SHALL flush before anything durable outside the stores names what it wrote, and before a write that names an earlier one whose payload has to be readable: a hosting record names a PMS and its identity key ([restart recovery](../../pdn-node/restart-recovery/spec.md)), and a pod's record in the PMS names the pod's tickets ([pods](../../pdn-node/pods/spec.md)). A write whose payload other entries rest on SHALL be on disk when it returns: a pod's membership store entry is, since the membership view waits on its payload and no other device holds it yet, so a kill within the settle window would leave an event that every device waits on forever. A record store's entry is not flushed: one a kill cuts within the settle window is read as absent, as one whose payload has not arrived from a peer is. A commit the stores' own timer runs and sees fail SHALL reach the next write or flush on that store, and the node's store check, as that call's error. The node SHALL count the entries this device wrote into an identity's PMS and its pods' membership stores whose payload is not on disk, and report them when a pod starts.

**Example:** the commit point of `create()` on Alice's first device a1, in the order it runs.

| step | replica store | blob store | `identities/<alice-hex>/pms` |
|---|---|---|---|
| `put_identity_key` | the entry in the open write batch | the key's 32 bytes inline in the open write batch | absent |
| `flush_stores(alice)` | committed | committed first | absent |
| the hosting record written, synced, renamed in | committed | committed | names the PMS |

#### Scenario: A flushed write is on disk at once
- **WHEN** a write is made, the store is flushed, and the store's directory is copied at that moment, as a kill would leave it
- **THEN** the copy holds the write's entry and its payload

#### Scenario: A membership write is on disk whole when it returns
- **WHEN** an entry is written into a pod's membership store, the replica store syncs its write batch while the blob store's is still open, and the node's directory is copied at that moment
- **THEN** the copy holds the entry's payload

#### Scenario: A session's commit reaches the disk on a store that is never idle
- **WHEN** a write lands in the replica store's batch, a session's snapshot commits it, and requests keep reaching the store every 50 milliseconds for 2 seconds before the store's file is copied
- **THEN** the copy holds the write

#### Scenario: A commit the stores' own timer saw fail reaches a caller
- **WHEN** a commit the replica store runs on its own timer fails, as on a full disk
- **THEN** the store's next write fails with that commit's error, and the write after it goes through
