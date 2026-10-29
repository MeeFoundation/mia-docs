## Context

Both ceremonies keep their one-time secrets in `PendingInvites` in `crates/pdn-node/src/ceremony.rs`, one instance per ceremony inside the runtime's state: `pending_linking_invites` keyed to the identity, `pending_pod_invites` keyed to the identity and the pod. `mint` sweeps the entries whose lifetime ended and inserts a fresh secret with its `expires_at`, an `Instant`. `verify_and_burn` removes a presented secret and answers what it was minted for when it was live. The serving halves — `serve` in `crates/pdn-node/src/linking.rs` and `serve_join` in `crates/pdn-node/src/pods.rs`, which serves both a newcomer on another node and an identity of the same node over the in-process pipe — burn the secret under the state lock and then run the dialogue; the newcomer each one serves is known there: the connection's authenticated peer for a linking, `request.joiner` for a join. Nothing of this is persisted, and nothing reaches a host but the dialing side's answer.

## Goals / Non-Goals

**Goals:**

- A host that minted an invite learns, by asking, whether someone came in on that invite and who.
- The answer costs a lookup in memory, so a host can ask every few seconds for every invite on show.

**Non-Goals:**

- Telling a host about invites it did not mint, or about joins through another member's invite.
- Telling the dialing side anything new: its answers are untouched.

## Decisions

### D1. The pending set keeps a presented secret and marks what became of it

An entry of `PendingInvites` carries its state beside what it was minted for and its `expires_at`: pending, burned, or used by the newcomer. `verify_and_burn` marks a live entry burned and keeps it; an entry presented after its lifetime, or presented again, is left as it is and refused as before. `mint` sweeps every entry whose lifetime ended, whatever its state. The serving half marks its entry used once its last write to the newcomer returned, through a call that takes the secret and the newcomer.

**Example:** a1's `pending_linking_invites` while a2 links with an invite a1 minted at 10:00:00 for Alice, with the default lifetime of 2 minutes.

| at | event | the entry |
|---|---|---|
| 10:00:00 | minted | pending, Alice, `expires_at` 10:02:00 |
| 10:00:30 | a2 presents the secret | burned, Alice, 10:02:00 |
| 10:00:31 | a1's reply written | used by a2's node id, Alice, 10:02:00 |
| 10:00:40 | the secret presented again | unchanged; the presentation is refused |
| 10:03:00 | a1 mints another invite | swept |

**Rejected alternatives:**

- A second map of outcomes beside the pending set.
  - **Cons:** two maps keyed by one secret, kept in step under one lock and swept in two places, for what one entry carries.

### D2. Used means the serving half handed over what the newcomer came for

An invite reads used once the serving half has written its last message to the newcomer without an error: the reply with the PMS write ticket for a linking, the stores' write tickets for a join. Every other way out of the serving half after the burn — a storage failure, a refused offer, a connection lost, a future dropped by a shutdown — leaves the entry burned, because burned is what the burn wrote and nothing after it overwrote it. A join that reaches a member already listed ends with the same write and reads used by that member.

**Example:** Carol's phone c1 presents Bob's invite to b1, three times over three invites.

| what happens on b1 after the burn | the invite reads |
|---|---|
| Carol's joined event written, both stores' tickets written to c1 | used by Carol |
| the joined event's write fails | burned |
| the joined event written, the connection lost before the tickets | burned, Carol listed; a second invite she presents reads used by her |

**Rejected alternatives:**

- A state of its own for a serving half that failed, apart from one in flight.
  - **Pros:** a host could tell a code being served from one wasted.
  - **Cons:** every exit path must write it, a dropped future included, whose cleanup cannot take the asynchronous state lock from a destructor; a host acts on used alone.
- Used marked at the burn.
  - **Cons:** an invite whose dialogue failed reads used, and a screen closes on nobody.

### D3. A host asks; the runtime answers from the pending set

The pods service answers `invite_state(identity, invite)` and the identity service `linking_invite_state(payload)`, each a read of the matching pending set under the state lock that writes nothing. Each answers `InviteState`: `Pending`, `Burned`, `Used(by)`, `Expired` or `Unknown`, `by` a `PdnId` for a pod invite and a node id for a linking invite. A host that wants to see a change asks again, at the pace it refreshes everything else.

**Example:** a host showing Bob's invite on b1 asks every 2 seconds.

```
10:02:00  invite_state(Bob, invite) -> Pending
10:02:02  invite_state(Bob, invite) -> Burned          c1's dialogue in flight
10:02:04  invite_state(Bob, invite) -> Used(Carol)     the screen closes
```

**Rejected alternatives:**

- A callback from the runtime into the host when an invite is used.
  - **Cons:** an event nobody listens to at that moment is lost, so a host needs the state anyway; the call arrives on a runtime thread; the burn holds the state lock, and a host calling back into the runtime from it deadlocks; the mobile host gains its first channel from the runtime into the application, on two platforms.
- An asynchronous call that answers once an invite's state changes.
  - **Pros:** no delay between the change and the host seeing it.
  - **Cons:** one outstanding call per invite on show, a rotating screen adding one a minute; whether the binding cancels such a call when the application drops it is unverified. It builds on this state, unchanged, if a host ever needs it.
- The host reading a pod's members or an identity's devices before and after.
  - **Cons:** a member who came in on another invite, or on another member's, looks the same; an identity's devices are listed to no host.

### D4. A pod invite is answered for the identity asking; a linking invite for the identity it names

`invite_state` takes the identity as every pods operation does, refuses one this runtime does not host as unknown, and answers `Unknown` for a secret held for another identity or another pod than the invite names. `linking_invite_state` takes the payload alone and answers `Unknown` for a secret held for another identity than the payload names.

**Example:** Alice's phone a1 hosts Alice-work and Alice-leisure; Alice-work mints an invite to "Office", and Alice-leisure joins with it inside the process.

| asked | answer |
|---|---|
| `invite_state(Alice-work, invite)` | `Used(Alice-leisure)` |
| `invite_state(Alice-leisure, invite)` | `Unknown` |
| `invite_state(Carol, invite)`, Carol not hosted on a1 | refused: `UnknownIdentity` |

**Rejected alternatives:**

- A pod invite answered by its secret alone, whoever asks.
  - **Cons:** the one pods operation that names no identity, on a surface that addresses everything through one.

### D5. Unknown covers every secret the runtime does not hold

A secret never minted here, minted before the runtime last started, or swept after its lifetime reads `Unknown`, and so does one held for another identity (D4). A secret whose lifetime ended and that was never swept reads `Expired` if it was never presented, and keeps reading `Burned` or `Used` if it was.

**Example:** b1 minted an invite at 10:00 with a lifetime of 2 minutes and nobody presented it.

| at | event | the invite reads |
|---|---|---|
| 10:01 | | `Pending` |
| 10:03 | | `Expired` |
| 10:04 | b1 mints another invite | `Unknown` |

**Rejected alternatives:**

- A state of its own for a secret minted before a restart.
  - **Cons:** it needs a durable record of every secret minted, where the runtime keeps its secrets in memory alone.

### D6. The facade carries both calls and the answer as its own type

`crates/pdn-mobile` exports `pod_invite_state(identity, code)` and `linking_payload_state(code)`, each decoding the code as its consuming call does and delegating to one service call, and an exported enum `InviteState { Pending, Burned, Used { by }, Expired, Unknown }`, `by` the identity's or the node's id as text. A code that does not decode is refused as malformed input, and an identity the runtime does not host as unknown, as the facade's other calls refuse them. Their requirements go into the delta of `mobile-host-surface`, which holds the facade's spec until it is archived: the operations the facade covers, the exact exported set, and a requirement of their own.

**Example:** a host on b1 asks about the code it shows, and about one that is no code.

| call | answer |
|---|---|
| `pod_invite_state(<bob>, <the code on show>)` | `InviteState.Used { by: <carol> }` |
| `linking_payload_state(<a pod invite's code>)` | refused: malformed input |

**Rejected alternatives:**

- A delta of this change creating the facade's spec.
  - **Cons:** the tree would hold a facade spec of one requirement while the rest of it waits in the other change, and that change's archive would land its preamble on an existing spec and lose it.

## Operating conditions

- **Several identities on one node** change the outcome: an invite is answered for the identity it was minted for (D4), and a join between two identities of the node marks it used inside the process.
- **One device or several** change it: an invite's state lives on the device that minted it, and the identity's other devices read it unknown, since nothing of it is replicated.
- **A device that restarts** changes it: every state is forgotten with the secrets, and an invite reads unknown afterwards (D5).
- **An unstable connection** changes it: a dialogue cut short after the burn reads burned, and one whose last write returned reads used even if the newcomer never read it (D2, Risks).
- **A disk that fills** changes it: a storage failure after the burn reads burned.
- **A membership that moves**: a member who joined and lost the reply is named by the invite it presents next, which writes no joined event. Leaving and joining again changes nothing here.
- **Clocks** change nothing: lifetimes run on the monotonic clock of the inviting device, as they do today.
- **A device linking before, during or after a process** changes nothing beyond a linking invite's own state.

## Risks / Trade-offs

- [An invite reads used when the newcomer never read the last message] → Used says what the inviter did. A pod join's joined event is written before the tickets, so the newcomer is listed either way, and a second invite hands it the tickets again; a linking newcomer stays pending, and a fresh invite converges, as the device-linking spec states. A host closing its screen on used shows the person a member or a device that its own lists show too.
- [Entries live until their lifetime ends whatever their state] → the set holds what it held before plus presented secrets until their expiry, bounded by what a host mints: a screen minting one invite a minute with a lifetime of 2 minutes keeps 3 entries at most, and the facade caps a lifetime at 24 hours.
- [A host asking often] → each question takes the state lock for one lookup in a hash map; a host asking every 2 seconds for a handful of invites costs nothing next to the refresh it already runs.
