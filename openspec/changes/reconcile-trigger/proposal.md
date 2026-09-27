# Proposal: reconcile-trigger

## Why

subset-rbsr puts capability-scoped peers outside a replica's gossip swarm — a broadcast cannot be filtered per recipient — and makes capability-filtered reconciliation, which they initiate, their only data path and the sole carrier of correctness. Such a peer reconciles a replica it holds under a grant on two occasions: the node's periodic reconcile pass dials the replica's contacts once every `SpawnOptions::reconcile_interval` — 10 s by default, the value every host in the repository runs with — and a read or a list of the replica starts a filtered reconciliation without waiting for it, answering from what the replica already holds (`nudge_scoped` in `crates/data-layer/src/node.rs`). Nothing tells the peer that a write it may read has landed, so the interval is at once its latency bound and its idle cost: each pass dials every contact of every replica the peer holds under a grant, written to or not, over a connection opened for that one session — a peer holding 1,000 issuers' namespaces dials at least 1,000 times per pass, 100 dials a second at the default — and a host that lengthens the interval to open fewer of them lengthens the wait by as much. This change adds the live path — a **reconcile trigger**: a small, content-free message sent directly to exactly the covered peers on a covered write, prompting each to reconcile promptly, without the side channel a broadcast would open.

**Example:** Alice (issuer) writes `contact/email` on her laptop a1 at 0 s. Bob (read grant on `contact/email`) holds her namespace on his phone b1, outside the swarm; b1's last reconcile pass ran at -2 s.

| b1's `reconcile_interval` | b1 receives `contact/email` |
|---|---|
| 10 s, the default of `SpawnOptions` | at its next pass, at 8 s |
| 1 hour, a value a host may set; no host here sets it | at its next pass, at 59 min 58 s |
| A read of `contact/email` on b1 at 1 s answers `None` and starts a filtered reconciliation it does not wait for; a read after that reconciliation has fetched the entry and its payload finds the claim. | |
| Nothing tells b1 of the write itself. | |

Correctness and confidentiality do not depend on this change: reconciliation remains the sole carrier of correctness (subset-rbsr), and a missed trigger is healed by the next reconciliation on contact. It is a latency optimization: the wait for a covered write stops depending on the interval.

## What Changes

- **Directed trigger on write.** When a write lands in a replica, the serving node resolves the scoped peers whose grants cover the written claim from the grant records it already judges their sessions by, and triggers exactly those, directly (not by broadcast). It dials each: a scoped peer is outside the swarm, and no connection to it outlives the session it was opened for. The trigger carries no claim content and no digest; the triggered peer fetches through a capability-filtered reconciliation session (subset-rbsr).
- **Co-located peers through the write announcement, narrowed.** Every local write already announces itself to the node's other identities that hold its namespace (`CoLocatedRequest::Announce`, served by `reconcile_with_co_located` in `crates/data-layer/src/node.rs`), and each of them then reconciles with the writer inside the process, whether its grant covers the write or not. That announcement becomes the trigger for a co-located peer: on a data namespace it reaches only the identities entitled to read the written claim, and a write it cannot carry at once stays pending, as every trigger does, where today it can wait for the next periodic pass.
- **Coalescing.** Consecutive covered writes collapse into one pending trigger per peer until that peer reconciles, so a peer receives a tick, not a stream — bounded by both the write rate and the peer's own reconciliation cadence.
- **Best-effort delivery.** A trigger is not a correctness carrier: an unreachable or missed peer is left to reconciliation-on-contact. Retry policy and the trigger transport are settled in design.

## Out of Scope

- **The read filter, the read capability, and the swarm-membership rule** — those are subset-rbsr. This change assumes scoped peers are already outside the swarm and that filtered reconciliation is the data path; it only makes that path prompt.
- **Correctness / confidentiality** — carried entirely by subset-rbsr's reconciliation filter. A missing or wrong trigger cannot leak a claim (the peer still fetches through the filter) or lose one (reconciliation-on-contact heals it).
- **The self-initiated reconciliation schedule** — the periodic reconcile pass every `reconcile_interval`, and the filtered reconciliation a read or a list starts without waiting for it, subset-rbsr's baseline. This change leaves both as they are and adds only the writer-side push that prompts an out-of-schedule reconcile the moment a covered write lands.
- **The periodic co-located pass** (`reconcile_co_located`) — it reconciles a pair of co-located identities whenever either replica's write count has moved since the pair last reconciled, covered or not, so an identity the write does not cover still takes a session within one interval of it. This change narrows the announcement alone.

## Capabilities

| Capability (delta)             | Archive destination                                         |
| ------------------------------ | ----------------------------------------------------------- |
| `components/mee-pdn/data-layer/reconcile-trigger` | `openspec/specs/components/mee-pdn/data-layer/reconcile-trigger/spec.md`  |
| `components/mee-pdn/data-layer/in-process-sessions` | `openspec/specs/components/mee-pdn/data-layer/in-process-sessions/spec.md`  |

### New Capabilities

- `components/mee-pdn/data-layer/reconcile-trigger`: the live path for capability-scoped peers — a directed, content-free trigger on a covered write, coalesced per peer, best-effort, that prompts a filtered reconciliation.

### Modified Capabilities

- `components/mee-pdn/data-layer/in-process-sessions`: the write announcement reaches only the co-located identities that may read the written entry, and a write landing while the pair's previous session is being set up or running is carried by a further session rather than left to the periodic pass.

## Impact

- **`crates/data-layer`**: the covered-peer resolution on write, read from the grant records in the issuer's connection metadata stores (the records `AccessBook` builds each session's egress filter from), coalescing state per peer, the dial that sends the trigger, the triggered peer initiating a filtered reconciliation, and the co-located announcement narrowed to the entitled identities, with its in-flight drop (`announcements_in_flight`) replaced by a pending mark.
- **`pdn-store`**: the transport for the trigger (a frame on the docs ALPN or a dedicated protocol — see design), and the replay of an announced session that found its pair running (`resync_requested`), which has to reach the pair it was raised for.
- **Depends on**: subset-rbsr (the filter, the read capability, scoped-peers-outside-swarm). The worked load profiles that motivate the trigger live in subset-rbsr's proposal (Example 1, Example 2).
