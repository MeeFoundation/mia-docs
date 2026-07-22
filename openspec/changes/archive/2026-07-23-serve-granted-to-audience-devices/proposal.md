# Proposal: serve-granted-to-audience-devices

## Why

A grantee's devices replicate the grant but not the data behind it: a granted namespace is never re-served, so a device that opens the pair while the issuer is offline holds the right to read claims it cannot obtain. The ban is wider than its own argument — a node cannot compute a *third party's* rights over foreign data, but the audience of a grant is the identity, and the identity's devices share one authorization; the serving device also holds the audience's grant record locally, so intra-audience rights are computable.

## What Changes

- A granted (imported) data namespace is re-served to callers that resolve as devices of the grant's audience identity; every other caller keeps the uniform refusal.
- Serving rights come from the serving device's locally replicated grant record: the grant serves through the same claim-set egress filter, and an absent, withdrawn, or wrongly-addressed local record refuses.
- A grantee's devices reconcile a granted namespace with sibling devices as well as with the issuer's devices, so claims catch up device-to-device while the issuer is offline.
- The pinned data-layer scenario flips: the sibling claim catch-up becomes the allowed path, with the outsider refusal as its paired denial.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `data-layer-subset-reconciliation`: the re-serving refusal narrows to callers whose rights the serving node cannot compute — a granted replica SHALL be served to the audience identity's devices, judged by the serving device's local grant record; refusal stays uniform for everyone else.

## Impact

- `crates/data-layer`: a serving posture for granted bindings that admits audience devices, an access-book classification branch (audience device set resolved through the hosted identity's directory, rights read from the local connection-metadata replica), sibling contacts for granted tracking, and the scenario tests in `tests/connection_metadata.rs` / `tests/read_restriction.rs`.
- `crates/pdn-node`: no service-surface change — the runtime already hands the classification the directory and pair handles it needs (`host_identity` / `host_connection`); internally, the grantee imports record sibling contacts from the hosted directories, and the ceremony-level scenario (`tests/sibling_serving.rs`) proves the catch-up end to end.
- Accepted window: a device may catch up from a sibling while a withdrawal is still propagating, until the tombstone reaches the serving device's replica — the same eventual-consistency window that per-session right-freezing already accepts on the issuer's side.
