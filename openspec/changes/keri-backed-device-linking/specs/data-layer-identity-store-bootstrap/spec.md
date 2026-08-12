# Identity-store bootstrap

The data-layer boundary for preparing the 2 identity stores before the identity identifier exists, deriving opaque commitments without exposing namespace capabilities, and binding the prepared pair after inception.

## ADDED Requirements

### Requirement: Identity stores can be prepared before their issuer exists

The data layer SHALL expose one 2-phase identity-store bootstrap operation. Its prepare phase SHALL create exactly 1 private-metadata directory replica and 1 data replica without an issuer binding, persist a versioned catalog intent before either backend side effect, and return only a durable opaque local handle plus the 2 role-tagged `StoreCommitment` values defined by profile 1. The handle SHALL identify the prepared pair across reopen without exposing either namespace identifier above the data-layer boundary.

The bind phase SHALL accept the handle and the derived `PdnId`, bind only the prepared data replica to that issuer, commit the hosted identity-store-set catalog record, and be idempotent for the same inputs. A handle that is missing, consumed by another identity, has the wrong profile version, or names a partial or role-swapped pair SHALL fail closed. Recovery SHALL complete or roll back a recorded preparation deterministically. A backend replica that no committed record or unfinished intent names SHALL remain unclassified and SHALL NOT be adopted as a prepared or hosted store.

#### Scenario: Creation derives the issuer after preparation

- **WHEN** creation prepares the 2 stores, seals their returned commitments into the root inception, derives the `PdnId`, and binds the recorded handle
- **THEN** exactly those stores become that identity's directory and data replicas without a namespace identifier crossing the data-layer API

#### Scenario: Reopen resumes the recorded pair

- **WHEN** the process stops after the prepare intent or either backend creation and reopens the same profile
- **THEN** recovery uses the identifiers fixed by that intent, produces at most 1 pair, and returns or rolls back the same opaque handle

#### Scenario: An unrecorded prepared-looking replica is not adopted

- **WHEN** a backend contains a replica that no bootstrap intent or committed catalog record names
- **THEN** recovery does not classify, bind, host, or expose it

### Requirement: Store commitments are computed below the capability boundary

The data layer SHALL compute profile-1 `StoreCommitment` values from the exact raw namespace identifiers and role octets defined by `pdn-node-keri-wire-profile`. Above the data layer a commitment is an opaque qualified digest. No API for preparation, binding, ticket verification, diagnostics, or error reporting SHALL return, log, or embed the raw namespace identifier.

#### Scenario: Commitments are stable across reopen

- **WHEN** a prepared handle is reopened and its commitments are requested again
- **THEN** the returned values are byte-for-byte identical to the values recorded before shutdown

### Requirement: Bootstrap-ticket verification is byte-bound to one consuming import

The data layer SHALL accept the 2 canonical ticket byte strings together, the expected profile-1 directory and data commitments, and the authenticated inviter's fallback transport address in one verification call. It SHALL decode both tickets internally, require write capability, recompute each profile-1 commitment under its fixed `directory` or `data` role, and produce for each role exactly one typed verdict: `MatchWritable`, `CommitmentMismatch`, `InsufficientCapability`, or `MalformedTicket`. The result SHALL be total and deterministic: it SHALL evaluate both roles even when the first fails and represent the 2 verdicts in `directory`, then `data` order. A failed pair SHALL return only that complete typed role/verdict mapping and SHALL have no import, issuer-binding, tracking, or catalog side effect.

Only when both verdicts are `MatchWritable` SHALL the call return an opaque process-local `VerifiedBootstrapPair`. That value SHALL be non-constructible and non-cloneable above `data-layer`, SHALL own the exact canonical ticket bytes and their decoded capabilities, SHALL bind their roles and expected commitments, and SHALL bind the authenticated fallback address. It SHALL expose no ticket fields or namespace identifier and SHALL NOT be reconstructed after restart from remembered verdicts. Adding that fallback to the verified directory ticket's transport hints SHALL happen only inside `data-layer` and SHALL NOT replace or alter the verified namespace or capability.

The only identity-bootstrap import API SHALL consume one `VerifiedBootstrapPair`, the hosted identity, and the attempt's opaque recovery owner. It SHALL import exactly the capabilities represented by the byte strings the pair owns, in directory-then-data order, and SHALL reject reuse, role substitution, another ticket byte string, another expected commitment, or another fallback address. Before its first backend side effect it SHALL preallocate a protected generic-secret handle and persist a data-layer import intent bound to that handle, digests of both canonical ticket byte strings, both roles, the identity, fallback address, and recovery owner. Through the predecessor's crash-consistent secret lifecycle it SHALL then store the exact canonical ticket bytes and decoded capability material only in that owner-only secret record; raw tickets and namespace capabilities SHALL NOT enter the general catalog. Reopen SHALL validate the stored bytes against the intent digests and idempotently complete or roll back that exact pair.

The protected pair record SHALL remain registered while either backend import might still need replay. It SHALL be deleted only after a final catalog transition names the exact imported replica identifiers, roles, identity binding, and completed import state from which reopen needs no ticket capability; rollback SHALL unregister and delete it after undoing every side effect. A stop around create, either import, final catalog commit, or secret deletion SHALL therefore leave either a resumable exact pair or a complete cataloged result, never an intent whose only recovery input was a non-secret digest. No API SHALL accept a prior verdict or Boolean together with caller-supplied tickets. Thus bytes cannot be checked, swapped in `pdn-node`, and imported on the strength of the earlier result.

This requirement applies only to identity bootstrap and device linking. Independently authorized grant import SHALL retain its existing issuer and capability path and SHALL NOT be rejected merely because the imported namespace is outside the hosted identity's 2-store set.

#### Scenario: A role swap is refused before import

- **WHEN** genuine directory and data tickets are presented under the opposite expected roles
- **THEN** verification returns commitment mismatch for both and no replica or issuer binding is created

#### Scenario: A matching read ticket is insufficient

- **WHEN** a ticket recomputes to the sealed commitment but lacks write authority
- **THEN** verification returns `InsufficientCapability` and performs no import

#### Scenario: Simultaneous ticket failures are both reported

- **WHEN** the directory ticket is malformed and the data ticket has a commitment mismatch
- **THEN** the failed pair returns the complete mapping `directory` → `MalformedTicket`, then `data` → `CommitmentMismatch`, and returns no `VerifiedBootstrapPair`

#### Scenario: Ticket bytes cannot change between verification and import

- **WHEN** both tickets verify but a caller tries to import a substituted ticket, swapped roles, or a different fallback address
- **THEN** no consuming import API accepts those inputs; only the opaque pair can be consumed, and it imports the exact verified capabilities and internally bound hint

#### Scenario: A crash cannot detach import from the verified pair

- **WHEN** the process stops after the consuming import records its intent or after either replica import
- **THEN** reopen reads only the intent's protected pair handle, validates its exact bytes against the recorded digests, and completes or rolls back that pair before deleting the secret record

#### Scenario: Ticket capabilities do not leak through recovery metadata

- **WHEN** bootstrap import is interrupted and the runtime catalog and diagnostics are inspected
- **THEN** they reveal only the protected handle, digests, roles, identity, fallback address, owner, and transition state — never either ticket, namespace identifier, or decoded capability

#### Scenario: Grant import remains independent

- **WHEN** a namespace is imported through a valid peer grant rather than identity bootstrap
- **THEN** the grant path continues to decide its issuer binding without claiming that namespace as part of the hosted identity's store set
