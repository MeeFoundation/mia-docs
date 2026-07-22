# Design: serve-granted-to-audience-devices

## Context

A granted data namespace is tracked `ContactsOnly` with `ServingPosture::Never`: the grantee's node reconciles it with the issuer's devices only, and refuses every incoming session for it before classification is even consulted. The refusal is pinned by the data-layer scenario `a_peer_store_catches_up_from_a_sibling_device_while_the_issuer_is_offline`: the grant record crosses device-to-device through the replicated connection pair, the claim does not. The subset-rbsr rationale for the blanket refusal is that a node cannot compute a third party's rights over foreign data — the grant book lives with the issuer. That argument does not cover the audience's own devices: a grant's audience is an identity, the identity's devices share its authorization, and every one of them holds the audience's copy of the grant record in the pair's replicated peer store.

## Goals / Non-Goals

**Goals:**

- A device of the grant's audience obtains granted claims from a sibling device while the issuer is offline.
- Acquisition stays capability-covered: the serving device judges each session against its local grant record, so a caller is never served past what the record it holds authorizes.
- Every caller that is not an audience device keeps the uniform `NotFound` refusal.

**Non-Goals:**

- Re-serving to third parties — that returns with UWill, when rights become presentable.
- Gossip membership for grantees — the swarm stays the issuer's devices; sibling catch-up is reconciliation the grantee initiates.
- The blob channel: payload fetch gating is untouched.

## Decisions

**D1 — The caller is judged an audience device through the hosted identity's directory.** The serving node resolves the session's authenticated node id against the `devices/` records of the audience identity's directory — the registry Invariant 1 already makes authoritative for "this node is one of my devices". The bilateral device records inside the connection metadata store are not used for this: they exist so the *counterparty* can resolve us, and reusing them here would let a record written for the issuer's benefit widen serving on ours. On a node hosting several identities, only the directory of the identity the grant is addressed to is consulted — a device of a co-located identity resolves nowhere and is refused.

**D2 — Rights come from the locally replicated grant record, read at session setup.** The serving device reads the grant for the namespace's issuer from its own copy of the pair's peer store — the same record its own access rides on. Present record → the same claim-set egress filter the issuer would apply (every grant is capability-scoped); absent, withdrawn, undecodable, or wrongly-addressed record → refuse. A record is honored only for the identity its capability names as audience — position in a directional store never substitutes for that name. The existing fail-closed decode rule and session-setup freezing carry over unchanged.

**D3 — A third serving posture, not a classification special case.** Granted bindings move from `Never` to a posture that admits exactly the audience-device path (`AudienceDevices`); device-replicated bindings stay `Serve`. Keeping the posture in the registry preserves the current shape — the accept path consults posture before classification — and keeps the refusal `NotFound`-uniform for everyone the posture does not admit.

**D4 — Scope parity with the issuer.** A sibling session over a scoped grant is filtered by the same claim set, so the transcript a sibling obtains is what the issuer would have served it — a sibling is a cache of the authorized subset, never a widening. The one divergence is temporal: a withdrawal the serving device has not yet received cannot refuse (the accepted window below).

**D5 — Sibling contacts are additional tracked contacts, and the runtime feeds them from its directories.** Granted tracking accepts contacts beyond the issuer's — an explicit add-contacts act on the node — and the reconcile pass and the before-access nudge dial them exactly as they dial the issuer. The runtime records them at every grantee import: the other devices of every hosted identity, read from the directories, as endpoint-id-only addresses — the endpoint resolves paths it has spoken to, so a sibling the node has synced with (the directory swarm guarantees one) is dialable, and one it never reached stays an inert contact until it is.

**D6 — Invariant 2 is kept by the local check, and the propagation window is accepted.** A device may catch up from a sibling after the issuer recorded a withdrawal but before the tombstone reached the serving device's replica. This is the same eventual-consistency window per-session right-freezing already accepts on the issuer's side, now bounded by the pair's own device replication instead of one node's session lifetime. Accepted knowingly; the alternative — confirming rights with the issuer per session — reintroduces the issuer's availability into exactly the path this change exists to free.

## Risks / Trade-offs

- [Stale local grant serves a revoked subset] → the window closes as fast as the pair replicates (its replicas are device-replicated and swarm-served); the withdrawal tombstone travels the same channel as the grant did.
- [A record written by the counterparty could steer serving] → only the *audience identity's directory* gates who is served (D1); the grant record gates *what* — and it can only narrow relative to the issuer's own record, never widen beyond what the issuer published.
- [Per-session cost of directory + grant lookups] → the same cost class as the issuer-side classification, which already reads device sets and grant records per session; the handles are the ones `host_identity` / `host_connection` already registered.
- [An endpoint-id-only contact is undialable for a sibling the node never reached] → the directory swarm makes every linked device a spoken-to peer before any granted import can name it; the contact resolves as soon as one directory exchange has happened.

## Open Questions

- None blocking.
