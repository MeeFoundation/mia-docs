# Proposal: reconcile-trigger

## Why

subset-rbsr puts capability-scoped peers outside a replica's gossip swarm — a broadcast cannot be filtered per recipient — and makes capability-filtered reconciliation, which they initiate, their only data path and the sole carrier of correctness. subset-rbsr has them reconcile on their own schedule — before access and on an interval (hourly to start, its D7). That leaves no proactive freshness: a scoped peer sees a new claim only on its next scheduled reconcile, not the moment the write lands. This change adds the live path — a **reconcile trigger**: a small, content-free message sent directly to exactly the covered peers on a covered write, prompting each to reconcile promptly, without the side channel a broadcast would open.

Correctness and confidentiality do not depend on this change: reconciliation remains the sole carrier of correctness (subset-rbsr), and a missed trigger is healed by the next reconciliation on contact. It is a latency optimization and can ship after subset-rbsr — a demo can run on reconciliation-on-contact alone.

## What Changes

- **Directed trigger on write.** When a write lands in a replica, the serving node — which already maintains the capability index the reconciliation filter consumes — triggers exactly the scoped peers whose read capabilities cover the written claim, directly (not by broadcast) over their existing connections. The trigger carries no claim content and no digest; the triggered peer fetches through a capability-filtered reconciliation session (subset-rbsr).
- **Coalescing.** Consecutive covered writes collapse into one pending trigger per peer until that peer reconciles, so a peer receives a tick, not a stream — bounded by both the write rate and the peer's own reconciliation cadence.
- **Best-effort delivery.** A trigger is not a correctness carrier: an unreachable or missed peer is left to reconciliation-on-contact. Retry policy and the trigger transport are settled in design.

## Out of Scope

- **The read filter, the read capability, and the swarm-membership rule** — those are subset-rbsr. This change assumes scoped peers are already outside the swarm and that filtered reconciliation is the data path; it only makes that path prompt.
- **Correctness / confidentiality** — carried entirely by subset-rbsr's reconciliation filter. A missing or wrong trigger cannot leak a claim (the peer still fetches through the filter) or lose one (reconciliation-on-contact heals it).
- **The self-initiated reconciliation schedule** (reconcile before access + on an interval) — that is subset-rbsr's baseline (its D7). This change adds only the writer-side push that prompts an out-of-schedule reconcile the moment a covered write lands.

## Capabilities

| Capability (delta)             | Archive destination                                         |
| ------------------------------ | ----------------------------------------------------------- |
| `data-layer-reconcile-trigger` | `openspec/specs/components/mee-pdn/data-layer/reconcile-trigger.md`  |

### New Capabilities

- `data-layer-reconcile-trigger`: the live path for capability-scoped peers — a directed, content-free trigger on a covered write, coalesced per peer, best-effort, that prompts a filtered reconciliation.

## Impact

- **`crates/data-layer`**: the trigger on write (reusing subset-rbsr's capability / audience index), coalescing state per peer, the direct-connection send, and the triggered peer initiating a filtered reconciliation.
- **`pdn-store`**: the transport for the trigger (a frame on the docs ALPN or a dedicated protocol — see design).
- **Depends on**: subset-rbsr (the filter, the read capability, scoped-peers-outside-swarm). Ships after it; the worked load profiles that motivate the trigger live in subset-rbsr's proposal (Example 1, Example 2).
