## Context

The completed HTTP host change accumulated runtime and data-layer fixes during review without a matching change boundary. Source review and an executed 137-test workspace run show that the current suite is green while leaving cancellation followed by immediate retry, aggregate HTTP memory, disk failure after invite burn, and abandoned pending registrations untested.

The conditions that change the outcome are an unstable connection, a full disk, a process restart, several identities on 1 node, and a device linking after an abandoned attempt. Multiple devices change the replication cost of pending cleanup; capability scope changes do not alter these fixes and remain covered by the existing grant scenarios.

## Goals / Non-Goals

**Goals:**

- Make cleanup from 1 linking attempt unable to mutate a later attempt.
- Make every asynchronous cleanup owned by a runtime task with an observable completion boundary.
- Bound durable pending-device state and rebuild its cleanup after restart.
- Preserve uniform remote ceremony refusals while reporting local post-verification failures.
- Bound aggregate HTTP request resources and prevent internal cause disclosure.
- Give `/live` process semantics and expose coarse-lock availability as readiness.
- Add tests that execute the exact cancellation, retry, overload, restart, and failing-storage paths.

**Non-Goals:**

- Authenticate the debug HTTP surface or make its routes stable product API.
- Change ceremony payload versions or reveal refusal reasons to unauthenticated peers.
- Add device revocation policy beyond reclaiming expired pending registrations.
- Stream entry bodies through a new runtime storage API.

## Decisions

### D1: A ceremony attempt owns 1 supervised task

`link` and `establish` execute their inner ceremony in a spawned task that owns reservation and rollback state. Dropping the caller-facing future cancels the attempt through an explicit cancellation signal, and the task completes rollback before releasing the reservation; runtime shutdown joins the same task set. This ordering is chosen over independent `Drop` tasks because spawn order does not order mutex acquisition, and over generation-only cleanup because the simpler invariant also guarantees cleanup completion.

### D2: Pending registrations expire by durable timestamp

A pending-device value carries its creation time and remains backward-compatible with the existing marker value. Every directory read or explicit cleanup pass tombstones records older than a named 24-hour lifetime; runtime startup and periodic reconciliation invoke the cleanup. The lifetime bounds abandoned state across restart without granting access, and a fresh invite for the same device replaces the pending timestamp.

### D3: Invite burn remains before durable registration

The inviter keeps atomic verify-and-burn before any state change. Failures after verification remain a uniform close on the wire, but they emit a typed server-side tracing event and increment a diagnostic counter; this preserves probe indistinguishability while satisfying the requirement that local storage failures are loud.

### D4: HTTP errors have public and internal representations

`HostError` stores a stable public message separately from the logged `anyhow` source. Typed client refusals expose an allow-listed outer message; internal server errors expose `internal server error` and retain the full chain only in tracing.

### D5: The host applies aggregate admission control

The router uses a 16 MiB entry-body limit, a smaller JSON limit where practical, and a shared concurrency limit of 16 in-flight requests. Overload answers 503 without entering a handler. This bounded stand policy is chosen over streaming because the runtime service currently accepts complete byte slices.

### D6: Liveness and readiness are separate

`GET /live` confirms that the process and embedded runtime handle exist without waiting for the coarse business mutex. `GET /ready` attempts the bounded state read and reports non-success under prolonged contention; debug status remains an ordinary operation rather than an orchestrator liveness signal.

## Risks / Trade-offs

- **A cancelled caller no longer means immediate task destruction** → the supervised attempt receives cancellation and remains reserved until rollback finishes; shutdown has a bounded join.
- **Clock skew can retain a pending record longer or expire it early** → expiry uses the author's stored wall-clock timestamp only for non-authorizing state, and confirmation remains the only access transition.
- **A lower body limit rejects large demo fixtures** → 413 is explicit and the stand can use product-level data generation rather than 1 oversized HTTP body.
- **A fixed concurrency limit can reject healthy bursts** → 503 is retryable and protects every identity sharing the process.
- **Generic 500 bodies reduce remote diagnostics** → full chains remain in structured logs.
- **Readiness can fail during legitimate long work** → orchestrators use `/live` for restart decisions and `/ready` only for traffic admission.

## Migration Plan

Pending marker values decode as having no timestamp and receive a timestamp when first observed; they are not confirmed or deleted solely because of the encoding migration. Deploy the runtime and HTTP changes together, run the focused cancellation and linking stress suites, then archive this change before the original HTTP change so its deltas preserve the remediation boundary. Rollback restores the old marker writer but leaves timestamped pending values readable as pending through backward-compatible decoding.

## Open Questions

None.
