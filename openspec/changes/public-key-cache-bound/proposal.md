# Proposal: public-key-cache-bound

## Why

Every store of pdn-store keeps a cache of the public keys it has parsed, `MemPublicKeyStore` in `src/store/pubkeys.rs`, and the cache has no bound: each 32-byte key that decodes into a valid curve point is added and stays for as long as the store lives, which is as long as the node hosts the identity. `validate_entry` in `src/sync.rs` checks an entry a peer offers in this order: its namespace, its key length, whether its hash and length agree on emptiness, its signatures through `SignedEntry::verify`, its timestamp, then the session's ingest verdict. `SignedEntry::verify` parses the entry's namespace key and author key through the cache before it checks either signature, so the author key of every entry a session receives is cached, whether the entry is then refused for a bad signature or dropped by the ingest verdict.

Only a caller the access provider admits reaches `validate_entry`: a device of the identity itself, on its private metadata store, and a member's device, on a pod's stores. A modified member device that sends entries under author keys it never used before therefore grows the cache by one key per entry, session after session, while the receiving node stores none of those entries. The same pull request against n0's `iroh-docs`, #93, reports the defect upstream.

**Example:** Bob's phone b1, a member of "Family", is modified and syncs the pod's record store with Alice's laptop a1; every entry b1 sends carries a fresh author key that decodes, and a signature that fails.

| b1 sends | a1 stores | a1's cache holds afterwards |
|---|---|---|
| one message of 10,000 such entries, about 2,400,000 bytes | nothing: each entry is refused for its signature | 10,000 more keys, each a 32-byte key beside its 32-byte parsed form |
| the same message in each of 100 sessions | nothing | 1,000,000 more keys, until the node restarts |

The cache saves little where it is consulted. iroh's `PublicKey` keeps the compressed point, and `PublicKey::verify` decompresses it again through `as_verifying_key` on every call, so a cache hit spares one decompression of the two each key costs a verification, beside the signature check itself.

Under [defect-reachability](../../specs/code-practices/defect-reachability.md) the defect is reachable over the network: a modified node's sync messages make an honest node spend memory without bound. That obliges a fix.

## What Changes

Nothing is decided. The change settles how a store parses the keys of the entries it verifies, and then specifies and builds the answer. The options are listed under Open Questions, and none of them is chosen.

## Open Questions

### How a store parses an entry's keys

- No cache. `SignedEntry::verify` parses both keys from the entry's bytes each time, and `MemPublicKeyStore` goes. Memory stays flat whatever a peer sends, and a verification costs one decompression more per key than a cache hit does today.
- A cache with a bound, as upstream's pull request proposes: the least recently used keys are evicted past a fixed count, 10,000 there. Memory is bounded by the count; a peer that sends fresh keys evicts the keys of the honest authors, and every honest entry then costs what it would cost with no cache.
- A cache filled only after an entry passes its signatures and the ingest verdict. A dropped entry leaves nothing behind; what an admitted caller can still add is one key per author whose entries the replica stores, which grows with the replica.

**Example:** b1's 100 sessions of 10,000 entries each, then 1,000 honest entries from Alice's phone a2 under her one author key.

| option | a1's cache after b1's sessions | a2's entries |
|---|---|---|
| no cache | no key held | 2 decompressions per key, as for any entry |
| a bound of 10,000 | 10,000 keys, all b1's | Alice's key parsed once, then a hit, unless b1 keeps sending meanwhile |
| filled after admission | no key of b1's held | Alice's key parsed once, then a hit |

## Operating conditions

Several identities on one node change the outcome of the second option: each identity's store holds a cache of its own, so a bound per store multiplies by the identities the node hosts. A restart empties every cache, which is why the growth lasts until the node restarts and no longer. Linking, an unstable connection, a disk that fills, clocks and a membership that moves leave the outcome as it is: the cache is in memory and keyed by bytes alone.

## Out of Scope

- The memory a single message holds while it arrives, which the sync-resource-bounds change weighs.
- The entries a member stores by writing under its own authors: those are its own writes, replicated by design.

## Capabilities

None is settled. Whichever option is taken touches `crates/pdn-store` alone; the data layer's [reconciliation sessions](../../specs/components/mee-pdn/data-layer/reconciliation-sessions/spec.md) spec, which states what a session admits, gains a requirement that a dropped or refused entry leaves nothing behind in memory, if the change puts it there.

## Impact

- **`crates/pdn-store`**: `src/store/pubkeys.rs`, `SignedEntry::verify` in `src/sync.rs`, and the `PublicKeyStore` impls in `src/store/fs.rs` and `src/filter.rs`.
