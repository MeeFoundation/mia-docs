# Design: connections-store-gate-read

## Context

ADR-0008 gave us a capability-gated ingest: the forked iroh-docs (`pdn-store`) consults a `CapabilityValidator` (`Fn(&SignedEntry) -> bool`) at the `validate_entry` chokepoint, and `data-layer` bridges it to a domain `IngestPolicy`. The first policy (Tier 1) reads an in-memory `Connections` set, mutated by hand — per-device and lost on restart.

Connections are **identity-level state**: all of Alice's devices must converge on one connection list. The natural home is an iroh-docs replica synced between her devices like any other doc. This change builds exactly that replica and proves it replicates between two devices — nothing more.

It deliberately stops short of having the gate *read* the store to admit data (that is the larger follow-up motivated by the gate's working set outgrowing memory once UWill/KERI land — see Deferred). Proving device-sync first is valuable on its own and, crucially, **requires no fork change**: the only enforcement here is a device axiom that needs nothing but the namespace→binding resolution the current seam already affords.

## Goals / Non-Goals

**Goals:**

- A dedicated, device-replicated connections store: its own iroh-docs replica, separate from data namespaces, with `connect`/`disconnect` as entry writes/tombstones.
- That store replicates between two devices of one identity, passing the ingest gate via a **device axiom** that needs no store read.
- No fork change: reuse the current `Fn(&SignedEntry) -> bool` seam.

**Non-Goals (this change):**

- The gate reading the store to admit/reject **data** entries (fork seam v2; store-reading `ConnectionsPolicy`; removal of the in-memory set). Deferred — see the section below; the in-memory Tier-1 policy stays untouched meanwhile.
- Cross-identity enforcement (a Bob gated on Alice's connection state), revocation-after-admission, capability delivery.
- Content-dependent UWill chain validation (needs blob payloads, not synchronously readable at the gate).
- Real device linking (key distribution, device capabilities, rotation) — a Write `DocTicket` is the stand-in.
- Mailbox/asynchronous delivery for devices with non-overlapping online windows (future: always-on peer as "just another device").

## Decisions

### D1. Connections live in their own replica, not inside `alice/alice` data space

One iroh-docs doc per identity-on-node, holding only connection state. Layout:

```
path:    connections/<pdnid-hex>     (64 lowercase hex chars, fits EntryPath limits)
payload: opaque marker (identity is in the key)
disconnect: tombstone (iroh-docs empty entry via del; len == 0 == not live)
```

*Why:* separate ticket (transport access to metadata without data and vice versa), separate gate policy (structural, not key-prefix dispatch), no shared LWW key space with data, independent retention/encryption later. Replication is stock iroh-docs: ticket bootstrap at linking, set reconciliation for catch-up, gossip for live updates, per-key LWW for concurrent device edits.

*Alternative rejected:* `connections/` prefix inside the `alice/alice` data namespace — mixes lifecycles and forces one policy to serve two kinds of content (ADR-0008 explicitly separates metadata and data stores).

### D2. The connections store has no domain `NamespaceId`; the registry binds by kind

`pdn-types`'s `NamespaceId` stays the team-agreed `(about, issued_by)` pair, reserved for peer-visible data namespaces. The registry binds iroh namespaces structurally:

```rust
enum Binding {
    Data(NamespaceId),              // peer-visible (about, issued_by)
    Connections { owner: PdnId },   // device-shared connections store
}
// gate resolves: iroh NamespaceId -> Option<Binding>, carried in IngestCtx
```

*Why:* no change to the domain model; the metadata-vs-data dispatch becomes a `match`; the enum can grow (`Meta { owner, kind }`) when cross-party metadata arrives.

*Alternatives rejected:* kind inside `NamespaceId` (changes a team-level model decision ahead of need); well-known synthetic `about` constant (stretches `about` semantics, magic constants in a key-derived id space).

### D3. Device axiom (`SelfOwned`) — the only enforcement here, and it reads nothing

```rust
SelfOwned { me }   // Binding owned by me -> Accept, without any store read
AnyOf([...])       // first Accept wins (composition for when data gating is added later)
```

`SelfOwned` admits entries of `Connections { owner == me }` (and, naturally, `Data(ns)` with `ns.issued_by == me` — device-sync of one's own data namespaces). Because it only inspects the resolved `Binding`, it runs entirely within the existing seam — the bridge resolves the binding from `entry.namespace()` via the registry and hands it to the policy as `IngestCtx { binding }`. **No fork change, no store read.**

This is exactly what lets the connections store replicate between Alice's devices: phone's entries, arriving on laptop, are `Connections { owner: alice }`; laptop runs `SelfOwned { me: alice }` and admits them — even while laptop's own store is empty (no chicken-and-egg).

*Why an axiom, not "read the store":* a node always trusts state authored under its own identity; gating that on the store would be circular (the store can't authorize its own arrival). Keeping it read-free is what removes the fork dependency for this step.

### D4. `ConnectionsStore`: mutation API over the replica

`create(node)` / `import(node, ticket)` bind the doc as `Binding::Connections { owner }`; `share_ticket()` for linking; `connect(peer)` writes the marker entry; `disconnect(peer)` writes the tombstone (`del`). Reads for UI/tests go through normal async doc queries (`is_connected`, `list`). Nothing in this change reads the store from inside the gate.

## Deferred: the gate reads the store (fork seam v2)

Recorded here so the follow-up change inherits the analysis, not re-derives it. The end state is a store-reading `ConnectionsPolicy` that admits a `Data(ns)` entry iff a live `connections/<ns.issued_by>` entry exists — decided *inside* the gate, with no in-memory mirror (the working set will not fit once UWill/KERI land).

Key facts already verified against the fork (`pdn-store`, iroh-docs 0.100):

- `snapshot_owned() -> ReadOnlyTables` (`src/store/fs.rs:210`) gives an owned, read-only snapshot independent of the mutable store borrow held during replica ops; `get_exact`/`get_many` already take a namespace, and `records_by_key` supports by-key lookup across authors.
- Both validator call sites (`Replica::insert_remote_entry`; the `sync_process_message` reconciliation closure) run on the actor thread and can build a snapshot just before validation — one per entry on the insert path, **one per batch** on the reconciliation path.
- Seam v2 = widen `CapabilityValidator` to `Fn(&SignedEntry, &StoreSnapshot) -> bool`, snapshot exposing metadata only (key/author/timestamp/len/hash, never blob content). The snapshot sees **committed** state, so capabilities/connections must commit *before* the data they authorize (an ADR-0008 ordering constraint surfacing as MVCC staleness); revocation takes effect from the next committed batch.
- A snapshot (owned `ReadOnlyTables`), not read-through `&mut`, keeps `ranger.rs` — the most upstream-sensitive file — at a near-zero diff.

That change will also remove the in-memory `Connections`/Tier-1 policy and add cross-identity tests (a Bob gated on Alice's connection state).

## Risks / Trade-offs

- **[Multi-author LWW on one key]** (two devices flip the same connection while offline) → per-key latest-by-timestamp across authors; tombstones participate like ordinary entries; accepted for this tier, no custom merge.
- **[Online-window overlap]** → device-sync needs the two devices reachable at some overlapping time; relay stores nothing. Out of scope to solve here; the eventual always-on peer is "just another device" with the same store.
- **[Store exists but nothing gates on it yet]** → intentional: this is the replication half. Data admission still runs the in-memory Tier-1 policy until seam v2 lands. No regression, since the connections store and the in-memory set are independent.
- **[Device linking is faked by a Write ticket]** → real linking (key distribution, rotation) is deferred; the ticket is a stand-in for the scenario test only.

## Open Questions

- **One connections store per node or per identity-on-node**: nodes hosting multiple identities are not modeled yet; current shape (one per node) should not paint us into a corner — revisit with multi-identity work.
- **Should `SelfOwned` stay one axiom** (covering both `Connections` and own `Data`) or split? Current call: one axiom; split only if device-level write authority (which device may act as me) lands earlier than expected.
- **Liveness semantics on import**: when laptop imports an existing store, how long until first convergence is asserted in the test — wait on connection visibility explicitly rather than baking a fixed timeout (mirrors the flake-avoidance in `sync_two_nodes`).
