# pdn-node: namespace addressing — delta for identity-scoped-replicas

## MODIFIED Requirements

### Requirement: One pdn-store namespace per issuer
At the data layer, all of an issuer's claims (about any subject) SHALL live in one `pdn-store` namespace, and the data replica SHALL be keyed by the issuer `PdnId` within the scope that holds it. There SHALL be at most one data replica per issuer in a scope, not one per _(subject, issuer)_, and a node SHALL hold one replica of that namespace for each scope that acquired it — its issuer's own, and one per identity granted access to it.

#### Scenario: two claims about different subjects
- **WHEN** an issuer writes two claims about two different subjects
- **THEN** both live in that issuer's single data namespace

#### Scenario: the data replica is keyed by issuer
- **WHEN** `data-layer` opens an issuer's data namespace in a scope
- **THEN** it is keyed by the issuer `PdnId` alone, with no `(about, issued_by)` pair

#### Scenario: one namespace, one replica per scope holding it
- **WHEN** two identities on one node are granted claims of one issuer's namespace
- **THEN** the node holds one replica of that namespace per identity, each keyed by the same issuer in its own scope
