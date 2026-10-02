# Proposal: blob-egress-gate

## Why

A node serves payload bytes by hash to any caller that asks. `SyncNode::spawn_with` in `crates/data-layer/src/node.rs` mounts blob transfer, `/iroh-bytes/4`, with no event sender, and iroh-blobs then serves every get, get-many and observe request without telling the node of it; only push, which writes into the store, is disabled. The blob store is one per node, under the replicas of every identity the node hosts, so what a session withholds as an entry, a request for its hash hands out as bytes: a party that learns a hash outside the platform fetches the payload whatever it was granted, a member kicked from a cell fetches every payload whose hash it saw before the kick, and, while its device stays in the cell's swarm, every payload placed after it, whose hash a member device announces to its swarm neighbours once its download completes (`Op::ContentReady` in the fork), and a party that holds the hash of a known file learns whether the node keeps it. ADR-0013 records the gap: the isolation it gives covers entries and not payload transfer.

**Example:** requests to Bob's phone b1 today; Bob granted Alice-leisure `contact/email` of his data namespace, the payload of his `notes/diary` entry has the hash `<diary>`, Alice's tablet a3 hosts Alice-leisure and Alice-work, Carol was kicked from "Family", of which Bob is a member, and Dave's phone d1 holds a connection with nobody.

| caller | asks b1 for | b1 answers |
|---|---|---|
| a3 | the payload of Bob's `contact/email` entry | the payload, which Alice-leisure's grant covers |
| a3 | `<diary>`, learned outside the platform | the diary, which neither identity on a3 was granted |
| Carol's phone c1 | the hash of a scan in "Family" she saw before the kick | the scan |
| c1, still in the swarm of Family's record store | the hash of a photo Alice placed after the kick, which a member device announced there | the photo |
| d1 | the hash of a public tax form Bob keeps in his data namespace | the form, and with it the fact that Bob keeps it |

Closing the gap needs no proof of which identity asks. A session admits its caller by the authenticated node id against the device sets the serving identity's records hold, and a request for a hash can be judged by the same records. The request names no identity, and it needs none: a node acts as every identity it hosts (threat model), so what all of them may read is what the node reaches anyway, one session per identity. A request judged before the store is read gets one answer for a hash the node keeps and a hash it lacks alike, whenever the caller is not entitled to it.

## What Changes

Nothing is decided. The change settles what a request for a hash is checked against and how the node finds the entries that reference a hash, and then specifies and builds the answer. Whichever option wins, the mechanism is the one iroh-blobs 0.103 offers: blob transfer mounted with an event sender whose mask intercepts get, get-many and observe requests and notifies connections, each request joined to its caller's endpoint id through the connection id the connect event carries, a refused request aborted with `AbortReason::Permission`, and push left disabled.

## Open Questions

### What a request for a hash is checked against

- The entries that reference the hash. A payload is served only to a caller that one of the node's hosted identities would serve, in a session, an entry referencing that hash: a device of that identity itself, a counterparty whose grant's egress filter covers the entry, a member of the cell whose store holds it. Through a hash the caller reaches exactly what it reaches through a session, and nothing more.
- The replicas that reference the hash. A payload is served to a caller that one of the node's hosted identities would serve a session on a replica holding an entry with that hash, whatever the entry. A grantee under a claim-scoped grant then fetches the payload of any claim of the namespace whose hash it learns.
- Known callers. A payload is served to a caller whose node id the records of any hosted identity place at all — a sibling, a counterparty, a cell member — and the node keeps no lookup from hash to entry. It stops a stranger and a stranger's probe; a grantee, a counterparty of a co-located identity, and a kicked member that is still a counterparty fetch every payload whose hash they hold.
- Accepted, as the node does today, and recorded in the threat model.

Whatever the answer, a kicked member reads no payload placed after its kick: the swarm hands a member's device that stays in it the hash of every new payload, so an answer that serves such a device leaves a kick without effect on payloads. Accepting does so for good, and known callers for as long as the kicked member is a counterparty of a hosted identity.

**Example:** the requests of Why under each option.

| request to b1 | the entries | the replicas | known callers | accepted |
|---|---|---|---|---|
| a3 asks for the `contact/email` payload | served | served | served | served |
| a3 asks for `<diary>` | refused: no grant covers `notes/diary` | served: Alice-leisure holds a session on Bob's namespace | served | served |
| c1 asks for the scan or the photo | refused: Carol is no member | refused: Carol is served no session on the cell's stores | served while Bob holds a connection with Carol, refused otherwise | served |
| d1 asks for the tax form | refused | refused | refused | served |

### How the node finds the entries that reference a hash

- An index beside each replica, from content hash to the keys whose entries carry it, which pdn-store keeps on every insert and on every entry it replaces or removes. A request costs one lookup; the index costs one row per entry and a change to the fork, which brings the stress pass of the flaky-tests practice with it.
- A scan of every replica the node holds, per request. No new storage and no change to the fork, but linear in the entries the node holds, per request: a caller any record places — a counterparty with the narrowest grant — makes the node read everything it holds once for every request it sends.

The question arises under the first two options of the first question alone.

**Example:** a node holding 100,000 entries across its replicas receives 1,000 requests from one counterparty.

| option | entries read |
|---|---|
| an index | 1,000 lookups |
| a scan per request | 100,000,000 |

## Operating conditions

Several identities on one node change the outcome on both sides: the serving node judges by each hosted identity's own records, and the caller's node id resolves to every identity whose records list it. A grant narrowed or revoked changes it too: the gate reads the grant records as the next session would, so a caller loses a payload from its first request after the narrowing reaches the serving node, and what it fetched before stays with it, since revocation is not recall (invariants). A freshly linked device is placed by its identity's own directory, as its sessions are, before any counterparty has heard of it. A restart changes nothing the index does not carry: an index is durable state of the replica it indexes. Clocks and a disk that fills leave the outcome as it is.

## Capabilities

None is settled. Every option but the last touches `components/mee-pdn/data-layer/node-assembly`, where blob transfer is mounted, and `components/mee-pdn/data-layer/subset-reconciliation`, whose egress filter the gate reads; an index touches `components/mee-pdn/pdn-store/crate`. The threat model's section on payload bytes changes with the answer.

## Impact

- **`crates/data-layer`**: the event sender blob transfer is mounted with, and the verdict from a caller's endpoint id and a hash, over the records the access book already reads.
- **`crates/pdn-store`**: the hash index, if the second question picks it.
- **ADR-0013**: its consequence that places closing payload transfer with identity-bound authorization changes to name this gate.
