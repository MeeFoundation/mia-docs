# Design: subset-rbsr

## Context

Invariant 2 says a node receives a record only if it holds a read capability for it. Today reconciliation delivers every record to any peer that syncs — no per-record read control. This change enforces Invariant 2 by filtering what a serving node reveals during reconciliation, driven by the receiving peer's read capabilities. It is the read-side counterpart of the ADR-0008 ingest gate.

## Goals / Non-Goals

**Goals:**

- A serving node reveals only records the peer is read-authorized for; unauthorized records' content and existence stay hidden.
- A minimal, testable read-capability mechanism driving the filter.

**Non-Goals:**

- Full UWill (chains, revocation, token encoding) — ADR-0007.
- Efficiency — a filtered session may scan every record in the replica; accepted.

## Decisions

### D1. Filter at reconciliation time, applied consistently

The filter lives in `pdn-store` at reconciliation time (the `ranger` path), as a per-peer predicate over which records participate. It is new — the existing `validate_entry` hook is ingest-only. It MUST be applied uniformly: range fingerprints, split boundaries, offers, and item transmissions all computed over the filtered view. Partial application leaks — a fingerprint computed over the full set in a shared range would betray unauthorized neighbours.

### D2. Confidentiality = consistent filtering

Because every value the serving node sends is computed over the peer's authorized subset, the peer's transcript depends only on that subset. The peer's session is indistinguishable from reconciling with a node holding exactly that subset — so it learns neither content nor existence of the withheld records. No PIO/ZK needed; this is "don't send it," enforced at the serving node.

### D3. Minimal read capability — the single-link precursor to UWill

The capability the filter consumes is a single grant `{ issuer, audience, records }`, presented by the peer, evaluated per record. No delegation chain, no revocation crypto, no token encoding — the degenerate form, exactly as `ConnectionsPolicy` is the degenerate form of chain validation. The real format, chains, and revocation migrate to the `uwill` module (ADR-0007). Placement: the minimal type lives in `data-layer` for now (like `Connections`); the domain issuance surface (`pdn-layer` `Capability`, then UWill) supersedes it later.

### D4. Own-identity is fully authorized

An identity's own devices are read-authorized for all of that identity's data (composes with Invariant 1), so the filter admits everything for a same-identity peer with no capability presented. Same-identity reconciliation (connections store, private metadata, own data) stays full.

## Risks / Trade-offs

- **[Consistency discipline]** The filter must touch fingerprints + boundaries + offers + sends uniformly; any path over the unfiltered set leaks. Test the existence-hiding property explicitly.
- **[Side channels]** Timing and message sizes can leak the replica's total record count (the server scans every record to filter). Minor; note, don't block.
- **[Efficiency]** A filtered session may cost time linear in the number of records rather than logarithmic — accepted; performance is not a goal here.
