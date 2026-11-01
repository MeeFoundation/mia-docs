# Proposal: invite-state

## Why

A host hands out ceremony codes and learns nothing of what became of them. A pod invite or a linking invite is a one-time secret pending on the inviting runtime; when it is presented, the runtime burns it and serves the dialogue, and the host that minted it hears nothing. A screen that shows a code therefore cannot tell the person when someone came in on it, and the only signal a host can build from what the runtime answers today is a guess: a pod's member list grows whoever invited the newcomer and with whichever code, and an identity's devices are not listed to a host at all. The runtime already holds the answer — the secret and, once its dialogue is served, who presented it — and drops it at the burn.

**Example:** Alice opens an invite screen for "Family" on her phone a1 at 10:00, copies a code C1 for Bob and closes the screen; at 10:03 she opens it again, and it shows code C2.

| at | what happens | what the host can tell today | what the host can tell after this change |
|---|---|---|---|
| 10:05 | Bob joins with C1 | "Family" lists one member more | C1 was used by Bob; C2 is pending |
| 10:06 | Carol joins with C2 | "Family" lists one member more | C2 was used by Carol |
| A screen closing when someone came in on its code closes at 10:05 on the first column's signal, wrongly, and at 10:06 only on the second's. | | | |

## What Changes

- **The runtime keeps what became of every invite it minted, for as long as the invite would have lived.** A presented secret is burned as before and refused to every later presentation as before; it stays in the pending set marked burned, and once the serving half of its dialogue has handed the newcomer what it came for, marked used by the newcomer: the joiner's `PdnId` for a pod invite, the new device's node id for a linking invite. An invite expires and is swept as today, whatever it reads.
- **Two read-only service calls answer an invite's state.** The pods service answers for a pod invite minted by one of its identities, the identity service for a linking invite: pending, burned, used by whom, expired, or unknown — unknown for a code this runtime never minted, minted for another identity, swept after its lifetime, or minted before the runtime last started. Nothing is pushed: a host asks again, as it asks for everything else.
- **The HTTP host's debug surface exposes them,** a route each, as its own requirement asks of every pods operation.
- **The mobile host exposes them,** a call each and the answer as an exported type. The facade's spec is not in the tree yet: it is the delta of the change `mobile-host-surface`, whose open tasks lie outside this one. This change edits that delta — the operations the facade covers and the exact exported set — so the facade's spec reaches the tree with the two calls whenever that change is archived.

## Out of Scope (deferred)

- **A call that waits for an invite's state to change.** It would build on the state kept here and spare a host its repeated question; nothing needs it while a host refreshes every few seconds.
- **Revocation.** An invite still cannot be withdrawn before it expires; the state is read, never written, by a host.
- **Durability.** The state lives where the pending secret lives, in the runtime's memory, and a restart forgets it with the secrets themselves.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `components/mee-pdn/pdn-node/pods`: the pods service answers a pod invite's state; the inviting runtime marks an invite used once its join was served.
- `components/mee-pdn/pdn-node/device-linking`: the identity service answers a linking invite's state; the burn marks the secret rather than dropping it, and the inviter marks it used once the reply is handed over.
- `components/mee-pdn/pdn-node-http/host`: the debug surface covers the two state calls.

The mobile host's requirements change in the delta of `mobile-host-surface`, at `components/mee-pdn/pdn-mobile/host`, which this change edits in place.

## Impact

- `crates/pdn-node`: `ceremony.rs` (the pending set keeps a burned secret and its outcome), `pods.rs` and `linking.rs` (the serving halves mark the outcome), the pods and identity services (the two state calls and their answer type), with scenario tests in `tests/`.
- `crates/pdn-node-http`: two debug routes, with a container test.
- `crates/pdn-mobile`: two exported calls and the exported answer type, with facade tests.
- No wire format, store layout or payload changes: the dialogues and the codes are untouched, so nodes on either side of the change complete ceremonies together.
