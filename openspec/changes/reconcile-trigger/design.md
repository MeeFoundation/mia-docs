# Design: reconcile-trigger

## Context

subset-rbsr puts capability-scoped peers outside the gossip swarm and makes filtered reconciliation their only data path and the sole carrier of correctness. Without a live path a scoped peer sees new claims only when it next reconciles. This change adds a reconcile trigger — a directed, content-free message that prompts a covered peer to reconcile promptly — without the side channel a broadcast tick would open. subset-rbsr's worked examples (Example 1 sparse, Example 2 SMB) make the cost and the side channel concrete; this design does not repeat them.

## Goals / Non-Goals

**Goals:**

- A covered write promptly prompts exactly the covered scoped peers to reconcile.
- No side channel: a scoped peer is triggered only about activity on claims it can read.

**Non-Goals:**

- Carrying correctness or confidentiality — reconciliation does that (subset-rbsr). Triggers are best-effort latency only.
- Delivering claim content — a trigger is content-free; data flows through the filtered reconciliation.

## Decisions

### D1. Directed, not broadcast; reuse the capability index

On a write, the serving node resolves the scoped peers whose capabilities cover the written claim — the same capability / audience index the reconciliation filter already maintains — and sends each a content-free trigger over its existing direct connection. Directedness is what avoids the side channel: a broadcast tick would wake every scoped peer on every write and expose the issuer's whole write rate, far wider than any one peer's grant (subset-rbsr, Example 1).

### D2. Coalescing

A peer holds at most one pending trigger until it reconciles; consecutive covered writes collapse into that one pending tick. So what a peer receives is bounded by its own reconciliation cadence, not the write rate (subset-rbsr, Example 2: about a hundred covered writes a day become a few ticks, never a flood).

### D3. Best-effort; reconciliation heals

A trigger is never required for correctness: an unreachable or missed peer is left to reconciliation-on-contact, which subset-rbsr names the sole carrier of correctness. Delivery is best-effort, so the retry policy is a latency knob, not a correctness one.

## Open Questions

- Transport: which message carries the trigger — a small frame on the docs ALPN, or a dedicated protocol.
- Retry policy: how long to keep retrying an unreachable peer before leaving it to reconciliation-on-contact.
