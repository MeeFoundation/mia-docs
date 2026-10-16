# Design: direct-device-linking

## Context

Linking today is ticket-first: the seed QR carries the private metadata store (PMS) write ticket, and `link_device` imports the PMS, waits for the connections-store ticket to sync in (`wait_for_ticket`), imports that store, registers itself, and waits again until the registration demonstrably reaches an existing device (`confirm_registration`). Both waits are retry loops over reconciliation, each the residue of a debugged flake, and the QR is a durable bearer credential. Establishment (ADR-0011, the connection-establishment change) built the alternative shape on this very codebase: a raw dialogue on a dedicated ALPN, `PendingInvites` with atomic verify-and-burn, uniform refusals, commit-precedes-reply, and a spawn-time protocol slot that takes any number of handlers. This change applies that shape to linking, merges the connections store into the PMS (both are device-internal under Invariant 1), and pulls the data namespace into the bootstrap. Everything below assumes the current in-memory storage and the pre-release posture: no deployed data, no migration.

## Goals / Non-Goals

**Goals:**

- No reconciliation wait in the linking critical path: the ceremony is one request/response exchange; the only wait left is a single bounded catch-up on the imported PMS against a peer that just answered.
- No bearer material in the QR: the payload is a version, an address, a one-time short-lived secret, and the identity's `PdnId` — same posture as the pairing invite.
- One device-internal replica per identity: PMS records for devices, tickets, and connections, so "one store synced, the other silently didn't" is unrepresentable.
- A linked device comes up with the identity's full store set: PMS and data namespace, both handed over in the reply.
- The linking access boundary is testable: refusals are protocol-level and uniform, and every positive scenario gets its paired denial.

**Non-Goals:**

- Identity-bound linking (KERI proof) — a marked, deferred step of the dialogue, as in pairing.
- Offline or pending linking invites; device removal or revocation.
- The reactive bootstrap cascade (PMS-watching auto-import) — connection metadata pairs still arrive by PMS sync, opened on demand.
- Deterministic namespace derivation (the concurrent-establishment own-replica split) — separate, ADR-level.
- Any change to the pdn-store fork.

## Decisions

### D2. Linking is its own ALPN, its machinery shared

The ceremony runs on `/pdn/linking/0`, a handler of its own in the spawn-time slot — not a message variant on another ceremony's ALPN. The stakes differ (a whole-PMS write ticket versus a pod's two store tickets), and separate protocols evolve their wire formats independently; registering another handler costs one vector element. The mechanics are shared: `PendingInvites` binds a 32-byte OS-random secret to an identity with lazy expiry and atomic verify-and-burn under the runtime lock (120-second default lifetime), and the length-prefixed postcard framing with one message-size cap carries the two messages: request `{version, secret}`, response `{pms ticket}`. Version refusal happens before dialing on the dialing side and uniformly on the accept side, as in a pod's join.

### D3. The inviter registers the newcomer; commit precedes the reply

The request carries no node id: the inviter reads the newcomer's node id from the connection's authenticated peer identity (the QUIC endpoint key), so a registration for a spoofed third-party device is unrepresentable. What it leans on is the transport's own guarantee: the accepted connection carries the remote endpoint's authenticated id, and the handler already holds it. After verify-and-burn, the inviter writes `devices/<node-id>` into its own replica — a local write on a device that already holds the PMS — then mints the reply tickets and answers. The registration therefore exists on an existing device from the start: `confirm_registration`'s delivery race is not solved but removed. A reply lost after commit leaves a registered-but-absent device record, which is harmless (device records carry no liveness semantics) and converges on the next fresh invite. Alternative — the newcomer self-registers after import, as today — rejected: it reintroduces the cross-node delivery wait this change exists to kill.

### D4. The bootstrap ticket rides the reply, minted fresh from the local replica

The reply carries the PMS's write ticket, produced by `share_ticket` on the replica the inviter hosts locally — no PMS reads in the ceremony, so no payload-waiting (`get_ticket` is blob-backed and lags record sync; reading it here would re-create the `wait_for_ticket` trap). The inviter can always mint it by induction: `create` provisions the PMS on the first device, `link` imports it on every further one, so every device that can mint an invite hosts the replica. Everything else the identity holds reaches the newcomer through the PMS.

### D5. `link` returns caught up, with rollback on failure

The dial side: check the payload version, dial, run the exchange, import the PMS (appending the inviter's live address to the ticket's contacts), then wait — bounded by the caller's timeout — for the first successful PMS sync session that started after the import. One wait against a peer that answered the dialogue moments ago, not a retry loop; the node's periodic reconcile pass remains the healer beyond it. This keeps today's contract (tests and callers rely on "returned means the PMS contents are here"). If the exchange or the wait fails, the dial side forgets the freshly imported PMS and the identity's half of the node, over the whole path after the import rather than a single failing step. The retry path is a fresh invite; the inviter-side registration may survive a post-commit failure, which D3 already accounts for. Both halves — the wait and the rollback — rest on data-layer surface that is not public today; see D8.

### D6. Ceremony code and spec live in pdn-node; data-layer keeps stores

`provision_identity` and `link_device` leave data-layer: provisioning becomes part of the identity service's `create` (PMS + device record), and linking becomes a ceremony module of pdn-node — payload, handler, dial side, all state under the runtime's one lock, taken per phase and never held across the round-trip with the peer. That is the ceremonies' discipline stated precisely: the request is read before the lock is taken and the answer written after it is dropped, while local store writes and ticket mints do run under it (with the late-bound `StateSlot` and the brief hold that keeps `shutdown` bounded). The linking hold is short — a burn, one device write, one ticket mint, no replica assembly. What must not creep back under the lock is a wait on delivery to another device: that is exactly today's documented exception, which this change removes. `linking.rs` and data-layer's `IdentityStores` are deleted; the runtime keeps its own hosted-identity value (now just the PMS handle). The spec follows the code: the procedure is `mee-pdn/pdn-node/device-linking.md`, while data-layer retains the store specs. ADR-0012 records the transport decision.

### D7. Service surface: invite / link replace the seed

`linking_invite(identity, lifetime) -> LinkingPayload` mints the secret and the self-contained payload; `link(payload, timeout)` runs the dial side. The payload names the identity, so `link` drops the separate identity argument (the old justification — the seed carries access but not the id — dissolves with the seed). `linking_seed` is removed, not deprecated: pre-release, callers rewritten. A runtime already hosting the payload's identity refuses `link` before dialing, as today.

### D8. The wait and the rollback are data-layer additions

This change is mostly subtraction from data-layer, but two of the things D5 promises stand on surface that is not public today, and the honest move is to add that surface rather than to reach around the layer.

The catch-up wait is the load-bearing one. Its semantics exist in exactly one place: `link_device`'s confirmation loop, which subscribes to the PMS replica's events and returns on the first sync-finished event whose session both started after a chosen instant and succeeded. That subscription is crate-private, the fork's event type is not re-exported, and pdn-node does not depend on the fork at all — so moving the ceremony to pdn-node while deleting `linking.rs` would leave `link` with no way to observe a sync session. Polling the PMS's contents is not a substitute: it proves that something arrived, never that this replica caught up, and it cannot separate "synced, nothing new" from "never synced". So the addition is a store-level primitive — the PMS states the property itself, with a bounded wait and a namespace accessor — not an exported event stream. Alternative — publish the subscription and re-export the fork's event type — rejected: it spends the layer's vocabulary boundary (the fork stays behind data-layer; pdn-node's dependency list is the proof) on a single consumer, for a property the store can state in one method. What does die is the *trigger*, `sync_with`: importing a replica already starts its first session and enrols it in the periodic reconcile pass with the ticket's contacts, so the retry cadence the old code hand-rolled is now the node's, running inside the wait's own budget.

The rollback must be able to name what it forgets: the PMS exposes its namespace for it, and dropping the identity's half of the node takes everything the link brought up with it, so a rolled-back link leaves the identity unknown rather than resolving to a dropped replica.

## Risks / Trade-offs

- [The PMS write ticket transits the network] → over an end-to-end encrypted QUIC channel to a peer that proved possession of a one-time, short-lived secret — strictly narrower exposure than today's QR, which shows the same ticket in plaintext on a screen with unlimited lifetime.
- [A reply lost after commit leaves a dangling device record] → harmless by construction (no liveness semantics) and specced as a scenario; a fresh invite converges.
- [Concurrent linking of two new devices via two invites] → two local writes on distinct `devices/` keys — no conflict; two invites presented for the same new device write the same record — idempotent.
- [`link` failure after import could leak replicas] → explicit forget-on-failure rollback (D5) over the whole post-import path, on surface that has to be added first (D8).
- [The confirmation loop this change deletes was a *measured* cure for a linking flake of about 1.2% per act (`code-practices/flaky-tests.md`)] → what replaces it is structural rather than another measurement: the registration is written by the inviter, on a device that already holds the PMS, so the cross-node delivery the loop waited on is out of the critical path entirely and the race has no site left. The wait that remains is a different property — the newcomer's own catch-up on the replica it just imported. The argument is checked, not assumed, by the counted stress pass over the linking suite, and the precedent gains a line recording what superseded it.
- [The linking secret guards a write ticket to the whole PMS — higher stakes than a pod's store tickets] → same mint quality (32 OS-random bytes), same one-shot burn, same uniform refusals; the stake difference is exactly why the ALPN is separate (D2) and the exposure window is the invite lifetime instead of forever.

## Migration Plan

None: pre-release, in-memory storage, no deployed identities. Rollback is reverting the change.

## Open Questions

- Settled: `PendingInvites` lives in pdn-node's `ceremony.rs`, shared by linking and a pod's join.
