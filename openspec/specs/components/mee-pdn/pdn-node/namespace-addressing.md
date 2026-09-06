# Namespace addressing

## Purpose

How PDN addresses and authorizes claims with the `(about, issued_by)` namespace pair dropped (ADR-0009): one addressing axis — the issuer and the entry path, from which the `ClaimId` derives — one authorization mechanism — the per-claim grant ([read capabilities](../data-layer/read-capabilities.md)) — one `pdn-store` namespace per issuer, and the namespace kept below `data-layer` as a replication bucket the runtime holds only as the handle of a replica it opened.

## Requirements
### Requirement: Claims are addressed by issuer and path, never by namespace
Above `data-layer`, an entry SHALL be addressed by its issuer's `PdnId` and its `EntryPath`, and a claim in a grant by its `ClaimId`, derived from those two. No service of the runtime SHALL take a `pdn-store` namespace as an argument, and the `(about, issued_by)` pair SHALL NOT exist as an addressing coordinate — `about` is a field inside the claim. The runtime MAY hold a namespace id as the handle of a replica it opened — the hosted-identities record names each identity's directory namespace, the grant binder records which namespace a grant's ticket bound — but never as the address of a claim.

#### Scenario: pdn-node addresses an entry
- **WHEN** the data service writes, reads, or lists
- **THEN** the call names an issuer and a path, and no namespace

#### Scenario: a grant names its claims
- **WHEN** the connections service publishes a grant
- **THEN** the call names the claims' `ClaimId`s, each derived from the issuer and a path, and no namespace

#### Scenario: about is claim content, not address
- **WHEN** a claim's subject (`about`) is needed
- **THEN** it is read from the claim (`Claim.about`), not from a namespace identifier

### Requirement: Access is authorized per claim by the recorded grant
Authorization SHALL be granted per claim through the issuer's recorded grant — the resource of the UWill format the grant grows into is one `ClaimId` ([uwill](../pdn-layer/uwill.md)) — not by possession of a namespace key. Sharing and visibility granularity SHALL come from grants alone, with no parallel namespace-boundary mechanism.

#### Scenario: granting access to one claim
- **WHEN** an issuer grants a peer access to a single claim
- **THEN** a grant naming that `ClaimId` is published, and no namespace-level grant is involved

### Requirement: One pdn-store namespace per issuer
At the data layer, all of an issuer's claims (about any subject) SHALL live in one `pdn-store` namespace, and the data replica SHALL be keyed by the issuer `PdnId`. There SHALL be at most one data replica per issuer, not one per _(subject, issuer)_.

#### Scenario: two claims about different subjects
- **WHEN** an issuer writes two claims about two different subjects
- **THEN** both live in that issuer's single data namespace

#### Scenario: the data replica is keyed by issuer
- **WHEN** `data-layer` opens an issuer's data namespace
- **THEN** it is keyed by the issuer `PdnId` alone, with no `(about, issued_by)` pair

### Requirement: The namespace is a data-layer replication bucket
The `pdn-store` namespace SHALL retain only its iroh-docs roles — the set-reconciliation unit and the gossip topic — and SHALL NOT carry addressing or write-authority: a write ticket's namespace secret lets a device produce entries, and what the issuer keeps is judged per claim at ingest ([capability-gated ingest](../data-layer/capability-gated-ingest.md)). The namespace-to-issuer mapping SHALL be a `data-layer` internal (its registry), surfaced above only as the unknown-issuer error when an issuer resolves to nothing.

#### Scenario: namespace carries no authority above data-layer
- **WHEN** a claim is addressed or authorized
- **THEN** the namespace is used for neither — addressing is issuer and path, authorization is the grant — and no service of the runtime names it
