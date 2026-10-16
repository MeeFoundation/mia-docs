---
status: accepted
date: 2026-10-14
---
# Join a pod over a raw iroh dialogue: the store tickets ride the reply, not the invite

## Context and Problem Statement

An identity becomes a member of a pod when a current member writes its joined event into the membership store, and it can act as one once its device holds write tickets to the pod's two stores. Before the join the newcomer shares nothing with the pod: it holds neither store, no member's device serves it, and no entry names it. The invite that starts the join is handed over outside the platform — shown as a QR code, sent in a message — so it is semi-public, and whoever sees it can present it. The question: over what channel do the invite's secret, the joined event and the tickets travel?

Facts about the stack:

1. A node's iroh endpoint multiplexes protocols by application-layer protocol negotiation (ALPN) identifier: document sync, gossip and blob transfer are three handlers on one router, and the data layer's node assembly takes externally supplied handlers beside them at spawn.
2. A pdn-store ticket is a bearer token with no expiry and no revocation: whoever holds one can import the store and sync it for as long as a member's device serves it.
3. Reconciliation is convergent and retryable: it has no request and no response, and no "verify, then act exactly once". An atomic check-and-burn of a one-time secret cannot be expressed as replica convergence.
4. The joined event depends on both sides at once: the sequence it takes has to lie past the newcomer's chain as the inviter's replica holds it and past the run the newcomer's own devices hold, since a departure may have reached one side and not the other.
5. Device linking already runs on this shape ([ADR-0012](0012-linking-over-raw-iroh.md)): a dedicated ALPN, a one-time secret verified and burned before any state change, uniform refusals, commit before the reply.

## Decision Drivers

* No shared state before the join: the mechanism cannot require a store, a ticket or a session the newcomer does not yet have.
* Nothing bearer-grade in the invite: a photographed invite must expire with its secret, and cannot be scoped to a newcomer unknown when it is minted.
* An atomic verify-and-burn of the one-time secret before any state changes, with refusals that look alike and leave nothing behind.
* The joined event names a sequence both sides agree on, and the newcomer signs nothing over a sequence it has not reached.
* pdn-store stays untouched: a join is not set reconciliation.
* One ceremony shape with linking, sharing its framing and its pending-invite set.

## Considered Options

* **A dedicated pod-join protocol on its own ALPN: verify-and-burn, the joined event written by the inviter, both write tickets in the reply** ← chosen
* **A ticket in the invite: the newcomer imports the stores and its joined event is written by reconciliation**
* **A message variant on the linking ALPN**

## Decision Outcome

Chosen option: **a dedicated pod-join protocol on its own ALPN**, because it is the only option that needs no shared state, keeps bearer material out of the invite, gives the secret's verify-and-burn one atomic home, and lets both sides agree on the joined event's sequence before anything is written.

The shape (the ceremony is specified in the [pods](../../components/mee-pdn/pdn-node/pods/spec.md) spec):

* **The invite carries** a format version, the inviting device's node address, a one-time short-lived secret and the pod id — no ticket and no identity proof. Any current member's device mints one, and minting writes nothing to either store.
* **The dialogue**: the newcomer's device dials the invite's address on the pod-join ALPN, `/pdn/pod-join/0` — a raw bidirectional QUIC stream, not a sync session. It presents the format version, the secret, its identity and the identity key that identity derives from, and the highest sequence of its own chain it holds. The inviter atomically verifies and burns the secret before any state change, names the sequence the newcomer's joined event takes, and sends the pod's created event. The newcomer refuses an offer whose created event does not derive the pod id or does not verify, or whose sequence lies more than one past its own history; otherwise it answers with its join statement, signed by its identity key over that sequence and the joining device.
* **Commit before the reply**: the inviter writes the joined event — the invite act, recording the newcomer as a plain member — into its own replica, and only then answers with write tickets to both stores. The newcomer refuses tickets to any stores but the two the created event names, and records both tickets and the pod's private metadata store (PMS) entry before it imports the stores, so a join a dropped connection or a restart interrupts after the dialogue is finished by the armer's sweep with no second invite.
* **A member presenting an invite**: the inviter writes no joined event, hands over both tickets again, and writes the member's device statement naming the presenting device when no statement of the member lists it, since member devices serve no device the member's statements do not list.
* **Refusals**: wrong, expired and already burned secrets, and an unknown version, get the same refusal, leave no observable state and burn no live pending invite. A failure of the inviter's own storage after the burn reaches a newcomer on another node as that same refusal, and is logged on the inviter.
* **Inside one node**: between two identities hosted on one node the dialogue runs inside the process, the secret verified and burned as between two nodes.
* **What the dialogue does not establish**: the join statement verifies under the key the newcomer's identity derives from, so the joined event is bound to that key; nothing proves that the key is still the identity's current one, which needs a key history ([ADR-0003](0003-mee-identity-represents-keri-autonomic-namespace.md)). Both devices are online for the dialogue, and pending invites for an offline inviter are not built.

**Example:** Bob's phone b1 mints an invite to "Family", and Carol's phone c1 presents it; `<x>` stands for the 64 hex characters of the identity x.

| step | b1 | c1 |
|---|---|---|
| 1 | verifies and burns the secret; names Carol's sequence 1; sends the created event of "Family" | checks that the created event derives the pod id and that sequence 1 is one past its own history |
| 2 | | signs its join statement over sequence 1 and c1 |
| 3 | writes `member/<carol>/1/joined/<bob>/2` into Bob's replica; sends both write tickets | records both tickets and the pod's PMS entry, imports both stores and catches up |
| a replay of the same secret | refuses, as it refuses a secret it never minted | |

### Consequences

* Good — no shared state before the join: the dialogue is what makes the newcomer a member, so there is no bootstrap circularity.
* Good — a photographed invite expires with its secret, and replay and a second presentation close at one atomic point.
* Good — the joined event's sequence is agreed before either side writes, so a departure that reached only one side is not left standing.
* Good — pdn-store stays untouched, and the framing and pending-invite set are those linking already uses.
* Bad — the store tickets transit the network; accepted because they cross an end-to-end encrypted QUIC stream to a peer that proved possession of the one-time secret, and a former member's ticket is judged by membership in every session ([ADR-0014](0014-store-sessions-judged-by-the-embedder.md)).
* Bad — a second ceremony surface beside linking to version and secure.
* Neutral — an observer of the invite learns the pod id and the inviting device's address.

## Validation

The pods scenario tests in `crates/pdn-node/tests/pods.rs` drive the ceremony end to end: `a_newcomer_joins_and_a_replayed_secret_is_refused`, `a_wrong_secret_burns_nothing`, `an_offer_past_the_joiners_history_is_refused`, `an_offer_naming_another_pods_creation_is_refused`, `tickets_to_stores_the_creation_does_not_name_are_refused`, `a_member_whose_join_lost_the_reply_joins_through_a_second_invite`, `a_join_cut_by_a_restart_before_its_import_is_finished_by_the_armer`, `a_storage_failure_after_the_burn_reaches_the_caller_on_the_inviters_node` and `two_identities_of_one_node_invite_and_join`. Each refusal is paired with the join it must not prevent, per the [access-control-tests practice](../../code-practices/access-control-tests.md).

## Pros and Cons of the Options

### A dedicated pod-join ALPN, tickets in the reply (chosen)

* Good — zero shared state before the join; one-time semantics on a request and response.
* Good — the invite stays free of bearer rights; the joined event's sequence is agreed by both sides.
* Bad — a new protocol surface; both online.

### A ticket in the invite

* Good — reuses the sync machinery end to end.
* Bad — the invite becomes a bearer write credential: a photograph lets anyone import the stores.
* Bad — no atomic one-time step: reconciliation is retryable, so a second holder converges just as well.
* Bad — the newcomer cannot write its own joined event, since only a current member's act counts, so the join still needs a member to act, with nothing to tell it when.

### A message variant on the linking ALPN

* Good — one ALPN fewer.
* Bad — two dialogues with different stakes in one wire format: a whole PMS write ticket for an identity's own device, two store tickets for another identity. Neither can evolve without versioning the other.
* Bad — one handler branches on intent before the burn, widening what both ceremonies expose before it.

## More Information

Open questions, none blocking this decision: the QR encoding of the invite (a host concern); invites that wait for an offline inviter.

Related: [ADR-0012](0012-linking-over-raw-iroh.md) (the ceremony shape this decision shares), [ADR-0013](0013-identity-isolation-on-one-node.md) (two identities of one node, joined inside the process), [ADR-0014](0014-store-sessions-judged-by-the-embedder.md) (the sessions that serve the newcomer after the join).

External references: iroh protocol multiplexing — one endpoint, several ALPN-keyed handlers on a router (`Router::builder(endpoint).accept(alpn, handler)`); pdn-store `DocTicket { capability, nodes }` — a bearer token carrying the replica capability and node addresses (`src/ticket.rs`).
