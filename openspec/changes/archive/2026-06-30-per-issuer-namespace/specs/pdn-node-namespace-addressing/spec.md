# pdn-node: namespace addressing

How PDN addresses and authorizes claims once the `(about, issued_by)` namespace pair is dropped (ADR-0009): a single addressing axis (`ClaimId`), a single authorization mechanism (UWill), one `pdn-store` namespace per issuer, and the namespace demoted to a `data-layer`-internal replication bucket invisible above `data-layer`.

## ADDED Requirements

### Requirement: Claims are addressed by ClaimId, not by namespace
Above `data-layer`, a claim SHALL be addressed by its `ClaimId`. No layer above `data-layer` SHALL name a `pdn-store` namespace or a domain `NamespaceId`, and the `(about, issued_by)` pair SHALL NOT exist as an addressing coordinate — `about` is a field inside the claim.

#### Scenario: pdn-node references a claim
- **WHEN** a layer above `data-layer` refers to a claim
- **THEN** it uses the claim's `ClaimId`, not a namespace coordinate

#### Scenario: about is claim content, not address
- **WHEN** a claim's subject (`about`) is needed
- **THEN** it is read from the claim (`Claim.about`), not from a namespace identifier

### Requirement: Access is authorized per claim by UWill
Authorization SHALL be granted per claim through UWill (`res = ClaimId`), not by possession of a namespace key. Sharing and visibility granularity SHALL come from UWill grants alone, with no parallel namespace-boundary mechanism.

#### Scenario: granting access to one claim
- **WHEN** an issuer grants a peer access to a single claim
- **THEN** a UWill capability for that `ClaimId` is issued, and no namespace-level grant is involved

### Requirement: One pdn-store namespace per issuer
At the data layer, all of an issuer's claims (about any subject) SHALL live in one `pdn-store` namespace, and the data binding SHALL be keyed by the issuer `PdnId` (`Binding::Data { issuer }`). There SHALL be at most one data replica per issuer, not one per _(subject, issuer)_.

#### Scenario: two claims about different subjects
- **WHEN** an issuer writes two claims about two different subjects
- **THEN** both live in that issuer's single data namespace

#### Scenario: data binding is keyed by issuer
- **WHEN** `data-layer` opens an issuer's data binding
- **THEN** it is `Binding::Data { issuer }`, with no `(about, issued_by)` pair

### Requirement: The namespace is a data-layer-internal replication bucket
The `pdn-store` namespace SHALL retain only its iroh-docs roles — the set-reconciliation unit and the gossip topic — and SHALL NOT carry addressing or write-authority. `Binding` and `BindingIndex` SHALL be `data-layer` internals, not surfaced above it.

#### Scenario: namespace carries no authority above data-layer
- **WHEN** a claim is addressed or authorized
- **THEN** the namespace is used for neither — addressing is `ClaimId`, authorization is UWill — and the namespace is not named above `data-layer`
