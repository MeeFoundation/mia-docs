# Tasks: per-issuer-namespace

Scope: realize ADR-0009 — drop the `(about, issued_by)` pair, one namespace per
issuer, pdn-node namespace-free. Interim: random namespace key + mapping (the
computed key is deferred until UWill — design D2). No fork change.

## 1. pdn-types

- [x] 1.1 Remove `NamespaceId = (about, issued_by)`; ensure `about` lives in the claim (`Claim.about` — already present)
- [x] 1.2 Update dependents of `NamespaceId` to the issuer-keyed model

## 2. data-layer: bind by issuer

- [x] 2.1 `Binding::Data { issuer }`; `BindingIndex` keyed by issuer
- [x] 2.2 `SelfOwned` data arm matches "issued by me" via issuer (no `(about, issued_by)`)
- [x] 2.3 Re-key the `DataLayer` trait: surface `&NamespaceId` → issuer `PdnId`; resolve claim → issuer → replica internally
- [x] 2.4 Namespace key stays random (interim, D2). Persisting `{nsId → Binding}` is N/A here — the stack is in-memory (`MemStore` / `Docs::memory`); persistence rides the future on-disk store.

## 3. pdn-node surface (namespace-free)

- [x] 3.1 Above `data-layer`, address claims by `ClaimId` + UWill; no namespace naming (`PdnOp::SyncOnce { issuer }`, `WriteClaim` doc)
- [x] 3.2 `Binding`/`BindingIndex` not surfaced above `data-layer` (pdn-layer names neither). `Binding` stays `data-layer`'s policy-API type (it is `IngestCtx`'s field); fully privatizing it would rework the public `IngestPolicy` surface — out of scope.

## 4. Specs & docs

- [x] 4.1 Update `components/mee-pdn/data-layer/{ingest-policies,connections-store}.md`: `Data(NamespaceId)` → `Binding::Data { issuer }`; drop the `(about, issued_by)` wording
- [x] 4.2 On archive: place `pdn-node-namespace-addressing` into `components/mee-pdn/pdn-node/namespace-addressing.md`

## 5. Validation

- [x] 5.1 `just precommit-check` (fmt + clippy + check + tests — green)
- [x] 5.2 Existing scenario tests pass under the issuer-keyed binding (`capability_gated_sync`, `connections_two_devices`, `device_linking_bootstrap`)
