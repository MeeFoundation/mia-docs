# Design: direct-device-linking

## Context

Linking today is ticket-first: the seed QR carries the directory's write ticket, and `link_device` imports the directory, waits for the connections-store ticket to sync in (`wait_for_ticket`), imports that store, registers itself, and waits again until the registration demonstrably reaches an existing device (`confirm_registration`). Both waits are retry loops over reconciliation, each the residue of a debugged flake, and the QR is a durable bearer credential. Establishment (ADR-0011, the connection-establishment change) built the alternative shape on this very codebase: a raw dialogue on a dedicated ALPN, `PendingInvites` with atomic verify-and-burn, uniform refusals, commit-precedes-reply, and a spawn-time protocol slot that takes any number of handlers. This change applies that shape to linking, folds the connections store into the directory (both are device-internal under Invariant 1), and pulls the data namespace into the bootstrap. Everything below assumes the current in-memory storage and the pre-release posture: no deployed data, no migration.

## Goals / Non-Goals

**Goals:**

- No reconciliation wait in the linking critical path: the ceremony is one request/response exchange; the only wait left is a single bounded catch-up on the imported directory against a peer that just answered.
- No bearer material in the QR: the payload is a version, an address, a one-time short-lived secret, and the identity's `PdnId` — same posture as the pairing invite.
- One device-internal replica per identity: directory records for devices, tickets, and connections, so "one store synced, the other silently didn't" is unrepresentable.
- A linked device comes up with the identity's full store set: directory and data namespace, both handed over in the reply.
- The linking access boundary is testable: refusals are protocol-level and uniform, and every positive scenario gets its paired denial.

**Non-Goals:**

- Identity-bound linking (KERI proof) — a marked, deferred step of the dialogue, as in pairing.
- Offline or pending linking invites; device removal or revocation.
- The reactive bootstrap cascade (directory-watching auto-import) — connection metadata pairs still arrive by directory sync, opened on demand.
- Deterministic namespace derivation (the concurrent-establishment own-replica split) — separate, ADR-level.
- Any change to the pdn-store fork.

## Decisions

### D1. Connections are directory records; the dedicated store is gone

`connections/<pdnid-hex>` entries live in the private-metadata directory next to `devices/` and `tickets/`, with the connections-store semantics verbatim: identity in the key, opaque marker payload, tombstone disconnect, record-level liveness, per-key last-writer-wins. The prefixes are disjoint, so nothing collides; the store surface moves onto `PrivateMetadataStore` (`connect` / `disconnect` / `is_connected` / `list_connections` — renamed from `list` to keep `list_devices` unambiguous). Alternative — keep two replicas — rejected: the audiences are identical (Invariant 1), so the separation bought no isolation, while costing a second reconciliation unit and gossip topic per identity and keeping the cross-replica skew state alive. One fewer swarm per identity is also a small win on the many-stores scale axis.

### D2. Linking is its own ALPN, sharing pairing's machinery

The ceremony runs on `/pdn/linking/0`, a second handler in the same spawn-time slot — not a message variant on the pairing ALPN. The stakes differ (a whole-directory write ticket versus per-connection read tickets), and separate protocols evolve their wire formats independently; registering a second handler costs one vector element. The mechanics are shared: `PendingInvites` works unchanged (a second instance in runtime state — the map already binds a 32-byte OS-random secret to an identity with lazy expiry and atomic verify-and-burn under the runtime lock; 120-second default lifetime), and the length-prefixed postcard framing with the same message-size cap carries the two messages: request `{version, secret}`, response `{directory ticket, data ticket}`. Version refusal happens before dialing on the scanner side and uniformly on the accept side, exactly as in pairing.

### D3. The inviter registers the newcomer; commit precedes the reply

The request carries no node id: the inviter reads the newcomer's node id from the connection's authenticated peer identity (the QUIC endpoint key), so a registration for a spoofed third-party device is unrepresentable. This is new ground rather than an inherited mechanic — pairing binds its counterparty by the bearer secret alone and takes that counterparty's `PdnId` and address from claimed request fields — so what it leans on is the transport's own guarantee: the accepted connection carries the remote endpoint's authenticated id, and the handler already holds it. After verify-and-burn, the inviter writes `devices/<node-id>` into its own replica — a local write on a device that already holds the directory — then mints the reply tickets and answers. The registration therefore exists on an existing device from the start: `confirm_registration`'s delivery race is not solved but removed. A reply lost after commit leaves a registered-but-absent device record, which is harmless (device records carry no liveness semantics) and converges on the next fresh invite — the same recovery posture as re-establishment. Alternative — the newcomer self-registers after import, as today — rejected: it reintroduces the cross-node delivery wait this change exists to kill.

### D4. Both bootstrap tickets ride the reply, minted fresh from local replicas

The reply carries the directory's write ticket and the data namespace's write ticket, both produced by `share_ticket` on replicas the inviter hosts locally — no directory reads in the ceremony, so no payload-waiting (`get_ticket` is blob-backed and lags record sync; reading it here would re-create the `wait_for_ticket` trap). The inviter can always mint both by induction: `create` provisions directory and data namespace on the first device, `link` imports both on every further one, so every device that can mint an invite hosts both replicas. The directory still carries `tickets/data` (published at creation): the reply is the bootstrap path, the directory copy is the flat model's durable record for everything that is not the linking critical path. Alternative — directory-only discovery — rejected: without the reactive cascade nothing would import it, and with a wait it would be the old loop again.

### D5. `link` returns caught up, with rollback on failure

The dial side: check the payload version, dial, run the exchange, import the directory (appending the inviter's live address to the ticket's contacts, as establishment does), import the data namespace and register it under the payload's identity, then wait — bounded by the caller's timeout — for the first successful directory sync session that started after the import. One wait against a peer that answered the dialogue moments ago, not a retry loop; the node's periodic reconcile pass remains the healer beyond it. This keeps today's contract (tests and callers rely on "returned means the directory contents are here"). If the exchange or the wait fails, the dial side forgets the freshly imported replicas — the no-orphan posture establishment takes toward a fresh `own`, but applied to the whole path after the import rather than to a single failing step: establishment's own rollback covers only a failed ticket mint and leaves an orphan behind a failed assembly, so this is the shape to copy, not the code. The retry path is a fresh invite; the inviter-side registration may survive a post-commit failure, which D3 already accounts for. Both halves — the wait and the rollback — rest on data-layer surface that is not public today; see D8.

### D6. Ceremony code and spec live in pdn-node; data-layer keeps stores

`provision_identity` and `link_device` leave data-layer: provisioning becomes part of the identity service's `create` (directory + device record + data namespace + `tickets/data`), and linking becomes the ceremony module next to `pairing.rs` — payload, handler, dial side, all state under the runtime's one lock, taken per phase and never held across the round-trip with the peer. That is pairing's discipline stated precisely: the request is read before the lock is taken and the answer written after it is dropped, while local store writes and ticket mints do run under it (with the late-bound `StateSlot` and the brief hold that keeps `shutdown` bounded). The linking hold is strictly shorter than pairing's — a burn, one device write, two ticket mints, no replica assembly. What must not creep back under the lock is a wait on delivery to another device: that is exactly today's documented exception, which this change removes. `linking.rs` and data-layer's `IdentityStores` are deleted; the runtime keeps its own hosted-identity value (now just the directory handle). The spec follows the code: the procedure is `mee-pdn/pdn-node/device-linking.md` beside `connection-establishment.md`, while data-layer retains the store specs. ADR-0012 records the transport decision in ADR-0011's form.

### D7. Service surface: invite / link replace the seed

`linking_invite(identity, lifetime) -> LinkingPayload` mints the secret and the self-contained payload; `link(payload, timeout)` runs the dial side. The payload names the identity, so `link` drops the separate identity argument (the old justification — the seed carries access but not the id — dissolves with the seed). `linking_seed` is removed, not deprecated: pre-release, callers rewritten. A runtime already hosting the payload's identity refuses `link` before dialing, as today.

### D8. The wait and the rollback are data-layer additions

This change is mostly subtraction from data-layer, but two of the things D5 promises stand on surface that is not public today, and the honest move is to add that surface rather than to reach around the layer.

The catch-up wait is the load-bearing one. Its semantics exist in exactly one place: `link_device`'s confirmation loop, which subscribes to the directory replica's events and returns on the first sync-finished event whose session both started after a chosen instant and succeeded. That subscription is crate-private, the fork's event type is not re-exported, and pdn-node does not depend on the fork at all — so moving the ceremony to pdn-node while deleting `linking.rs` would leave `link` with no way to observe a sync session. Polling the directory's contents is not a substitute: it proves that something arrived, never that this replica caught up, and it cannot separate "synced, nothing new" from "never synced". So the addition is a store-level primitive — the directory states the property itself, with a bounded wait and the namespace accessor its sibling store already has — not an exported event stream. Alternative — publish the subscription and re-export the fork's event type — rejected: it spends the layer's vocabulary boundary (the fork stays behind data-layer; pdn-node's dependency list is the proof) on a single consumer, for a property the store can state in one method. What does die is the *trigger*, `sync_with`: importing a replica already starts its first session and enrols it in the periodic reconcile pass with the ticket's contacts, so the retry cadence the old code hand-rolled is now the node's, running inside the wait's own budget.

The rollback must be able to name what it forgets, and today it cannot: the directory exposes no namespace (its metadata-store sibling does, which is how pairing's rollback names a fresh `own`), and registering a data namespace has no counterpart — `forget_doc` is namespace-keyed and never touches the issuer registry. This settles what the first draft left open: forgetting the doc alone does **not** suffice. A rolled-back link would leave the issuer resolving to a dropped replica, so reads under it would fail as storage errors rather than the unknown-issuer refusal the timed-out-link scenario asserts — the residue would be invisible to the test that exists to catch it. The pair of `import_namespace(issuer, ticket)` is `forget_namespace(issuer)`: untrack, drop, and unregister as one act.

## Risks / Trade-offs

- [The directory write ticket transits the network] → over an end-to-end encrypted QUIC channel to a peer that proved possession of a one-time, short-lived secret — strictly narrower exposure than today's QR, which shows the same ticket in plaintext on a screen with unlimited lifetime.
- [One replica concentrates all device-internal state] → the audience and the total data are unchanged (the two replicas always replicated to the same devices); prefixes are disjoint; per-key last-writer-wins semantics are untouched. What is genuinely lost is the option to hand out one store without the other — an option nothing used or planned to use.
- [A reply lost after commit leaves a dangling device record] → harmless by construction (no liveness semantics) and specced as a scenario; a fresh invite converges.
- [Concurrent linking of two new devices via two invites] → two local writes on distinct `devices/` keys — no conflict; two invites presented for the same new device write the same record — idempotent.
- [`link` failure after import could leak replicas] → explicit forget-on-failure rollback (D5), in establishment's shape but over the whole post-import path, and on surface that has to be added first (D8) — establishment's own rollback fires on one step and cannot name a data namespace at all.
- [The confirmation loop this change deletes was a *measured* cure for a linking flake of about 1.2% per act (`code-practices/flaky-tests.md`)] → what replaces it is structural rather than another measurement: the registration is written by the inviter, on a device that already holds the directory, so the cross-node delivery the loop waited on is out of the critical path entirely and the race has no site left. The wait that remains is a different property — the newcomer's own catch-up on the replica it just imported. The argument is checked, not assumed, by the counted stress pass over the linking suite, and the precedent gains a line recording what superseded it.
- [The linking secret guards a write ticket to the whole directory — higher stakes than pairing's read tickets] → same mint quality (32 OS-random bytes), same one-shot burn, same uniform refusals; the stake difference is exactly why the ALPN is separate (D2) and the exposure window is the invite lifetime instead of forever.

## Migration Plan

None: pre-release, in-memory storage, no deployed identities. Rollback is reverting the change; sibling changes (`subset-rbsr`, `reconcile-trigger`) are unstarted, and their texts are swept rather than rebased.

## Open Questions

- Where `PendingInvites` physically lives once two protocols use it (stay in `pairing.rs` and be imported, or move to a small shared module) — code placement, decided at implementation. The struct itself needs no reshaping: it binds a 32-byte secret to an identity with lazy expiry, which is exactly what a linking secret binds too.
