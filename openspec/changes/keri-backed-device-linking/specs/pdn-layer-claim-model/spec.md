# Claims carry attribution but no empty proof placeholder

## Purpose

The existing `PdnIdentityProof {}` has no bytes, verification rule, signer state, or authority semantics. This change removes that misleading placeholder while leaving real claim-issuance proof design to the later counterparty-verification work.

## ADDED Requirements

### Requirement: Claim attribution is not an identity proof

`Claim` SHALL retain `about`, `issued_by`, `attribute`, and `capability`, and SHALL NOT expose or serialize `proof_of_issued_by`. The empty `PdnIdentityProof` type SHALL be removed from `pdn-types`. In this profile, `issued_by` is attribution only: no runtime SHALL infer signature verification, KERI authority, device membership, or access from that field alone.

This is a breaking schema cleanup, not a proof migration. The repository has no deployed proof-bearing claim format to preserve, and this change discards its pre-profile local state. A serialized claim containing the former `proof_of_issued_by: {}` field SHALL be rejected rather than silently accepted as if it carried evidence; new writers SHALL omit the field, and repository fixtures SHALL be regenerated. A later counterparty-verification change MAY add a new, explicitly versioned proof type only together with canonical signed bytes, signer-key-state selection, verification, and failure semantics.

#### Scenario: A new claim has no empty proof field

- **WHEN** a `Claim` is serialized and deserialized under this profile
- **THEN** its representation contains the 4 retained fields and no `proof_of_issued_by` field

#### Scenario: Attribution grants no authority

- **WHEN** a claim names an identity in `issued_by` without a separately defined and verified proof
- **THEN** the runtime treats that value as attribution and grants no signing authority, device membership, or access on its strength

#### Scenario: The placeholder claim shape is rejected

- **WHEN** a reader receives a serialized claim containing the former empty `proof_of_issued_by` field
- **THEN** it rejects that shape instead of accepting the empty object as cryptographic evidence
