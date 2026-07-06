# data-layer: ingest policies (withdrawn)

The ingest-policy capability is withdrawn whole: the gate hard-codes the one-identity-per-node assumption (`SelfOwned { me }`) that multi-identity nodes remove, and the team decision is to run on ticket possession until subset-rbsr (Invariant 2, egress) and UWill (ADR-0007) restore enforcement. The `validate_entry` seam this capability bridged into remains in the pdn-store fork, uninstalled.

## REMOVED Requirements

### Requirement: Ingest context carries the resolved binding
**Reason**: The bridge from the fork's validator callback into domain terms (`Binding`, `BindingIndex`, `IngestCtx`) existed only to feed ingest policies; with the gate removed there is no consumer, and the resolution machinery goes with it.
**Migration**: None in code. The fork's `validate_entry` hook (the ADR-0008 seam) stays available in pdn-store; future enforcement (subset-rbsr egress filtering, UWill) defines its own context, which is per-peer and capability-carrying rather than binding-based.

### Requirement: Invariant 1 admits own bindings without store reads
**Reason**: `SelfOwned` is the one place in the codebase that pins a node to a single identity; hosting several identities removes it. Invariant 1 retains its ticket mechanism — a replica's ticket is handed only to that identity's devices — and loses its code mechanism for the interim window.
**Migration**: None in code; the invariants spec (`components/pdn-node/invariants.md`, Invariant 1) is edited in this change to state that enforcement rests on ticket possession until subset-rbsr and UWill.

### Requirement: Policies compose
**Reason**: With no policies left there is nothing to compose; `AnyOf` and the `IngestPolicy` trait are removed with the gate.
**Migration**: None. Composition of future enforcement mechanisms is designed where they land (subset-rbsr, UWill), not preserved as an empty interface.
