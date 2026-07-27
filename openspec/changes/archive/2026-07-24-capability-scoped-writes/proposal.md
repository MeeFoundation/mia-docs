# Proposal: capability-scoped-writes

## Why

A grant carrying write ships the namespace secret, so its holder can write every claim of the issuer's store, and the authority cannot be withdrawn — the accepted interim recorded in subset-rbsr D3/D11, pinned by a data-layer scenario that asserts the undesired behaviour and waits to be flipped. The grant record cannot even express the target scenario — one write flag covers the whole claim set, so "this claim read-only, that claim read-write" over one connection is unwritable. The fork's ingest hook (ADR-0008) exists precisely for this and is uninstalled.

## What Changes

- The grant vocabulary becomes per-claim: a grant names, for each claim, whether write is granted alongside read — one record per issuer still, mixed rights inside it. **BREAKING**: the record payload changes shape (old records decode as no grant, fail-closed) and the publish surface changes signature; live grants must be republished.
- The fork's ingest hook is installed. The hook learns the session peer; a hosted issuer's data replica admits a synced entry only when the sender resolves as a device of the issuer, or the entry's claim is in the sender identity's recorded write set. Everything else is dropped before persisting — the write-side counterpart of subset reconciliation.
- Foreign writes become provisional at the writer: the issuer's gate signals a capability refusal back on the reconciliation reply, and the writer retracts the entry at once — physically removed locally, the verdict replicated to sibling devices as a directory marker so a sibling that has not itself reached the issuer converges too, and the issuer's accepted state wins.
- The retraction verdict is observable: a log line and a runtime event carrying the address of the lost entry — the refusal is no longer silent, and the marker keeps the payload's address as the seed of a future recovery surface.
- The writing surface refuses out-of-scope writes up front: a write addressed at a granted namespace outside the local record's write set fails at the API, before the replica is touched.
- The accepted last-write-wins window is documented: an admitted audience write competes by timestamp, and the fork admits timestamps up to 10 minutes ahead of the receiving clock.
- The pinned data-layer scenario flips into its write-denial pair, and a runtime-level scenario exercises the target shape: one claim read-only, one claim read-write, over one connection.

## Capabilities

### New Capabilities

- `data-layer-capability-gated-ingest`: which entries a hosted issuer's data replica admits over sync — judged from the transport-authenticated session peer and the issuer's recorded grants (ADR-0008), with the last-write-wins window of admitted writes stated.
- `data-layer-write-retraction`: provisional foreign writes — how the issuer's in-band rejection reaches the writer, which retracts locally, replicates the verdict to siblings as a marker (an accelerator, aged out by a retention window), and surfaces the outcome.

### Modified Capabilities

- `data-layer-read-capabilities`: the capability carries per-claim commands (write alongside read, per claim); write enforcement stops being deferred; the ticket-mode requirement covers mixed grants (any write in the record ships a write ticket — the secret stays the transport interim, scope moves to the gate).
- `data-layer-connection-metadata-store`: the grant record's payload carries the per-claim commands; the ticket-mode sentence follows.
- `data-layer-subset-reconciliation`: the independence scenario stops describing the ingest hook as uninstalled — egress filtering and ingest gating now run together, still independently.
- `data-layer-private-metadata-store`: the directory gains the retraction-marker record family, keyed by granted issuer, author, and entry path, bounded by a timestamp.
- `pdn-node-core`: the connections service publishes per-claim commands; the data service refuses out-of-scope writes up front and exposes the retraction event surface; the write side stops being described as unscoped.

## Impact

- `./pdn-store`: the ingest validator learns the session origin (peer) and returns a capability refusal to the sender as a new reconciliation message part (a minimal, deliberate wire addition), plus a rejection observer on the receiving side and a local physical-retract operation; full pre-push checklist.
- `crates/data-layer`: grant vocabulary, access book write sets and the validator installed at spawn (session-scoped write-set snapshot filled by the session classifier), the rejection observer feeding retraction (act, markers, retention-window prune), `tracing` for verdicts; scenario tests including the pinned-gap flip in `tests/read_restriction.rs`.
- `crates/pdn-node`: `publish_grant` signature (**BREAKING**), courtesy refusal in the data service, retraction event surface, the runtime scenario test (read-only claim next to read-write claim over one connection).
- Accepted windows, recorded in the design: per-session right freezing now also covers writes; an admitted write can pin a claim by future-dating up to 10 minutes; a retraction discards the writer's local value in favour of the issuer's (the event carries what was lost).
