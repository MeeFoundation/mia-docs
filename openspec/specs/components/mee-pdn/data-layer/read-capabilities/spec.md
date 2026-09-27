# Read capabilities

## Purpose

The minimal read grant that drives capability-filtered reconciliation ([subset reconciliation](../subset-reconciliation/spec.md)): how a grant is issued, how the serving node resolves a caller's effective grants from its own records, and how they are evaluated per entry. Deliberately the single-link, degenerate precursor to UWill — no delegation chains, revocation, or token encoding; those arrive with the `uwill` module.

## Requirements

### Requirement: A read capability authorizes reading specific claims

A read capability SHALL name an issuer, an audience, and the set of claims it grants read on within the issuer's data — and, per claim, whether write is granted alongside read. It SHALL be a single grant, not a delegation chain. Every granted claim SHALL grant read; write is optional per claim, mirroring UWill's flat command set (one delegation per claim, its commands beside it). Write enforcement is the ingest gate ([capability-gated ingest](../capability-gated-ingest/spec.md)); read enforcement stays the egress filter.

**Example:** Alice (issuer) grants Bob `contact/email` read-only and `contact/phone` read-write in one `ReadGrant`, its JSON one field per line.

```
"issuer":   "<alice-hex>"
"audience": "<bob-hex>"
"claims":   [{"claim":"<ClaimId of contact/email, hex>","write":false},     read
             {"claim":"<ClaimId of contact/phone, hex>","write":true}]      read and write
notes/diary derives a ClaimId neither item holds: the grant covers neither read nor write there
```

#### Scenario: Issuing a read grant

- **WHEN** an issuer grants an audience read on a claim
- **THEN** a read capability exists naming that issuer, audience, and claim, and no other claim is covered by it

#### Scenario: Issuing mixed rights in one grant

- **WHEN** an issuer grants an audience one claim read-only and another claim read-write
- **THEN** one capability covers both claims, carrying write on exactly the second

### Requirement: Claim identity is derived from the entry

The domain layer mints no claim identities of its own: the `ClaimId` of an entry SHALL be derived deterministically from the issuer and the entry path via a domain-separated key-derivation hash (`claim_id_of` in `data-layer`), so the identity is stable under payload edits and computable from the entry key alone.

**Example:** the `ClaimId` of Alice's entry at `contact/email`, as `claim_id_of` derives it.

```
hash       blake3 in key-derivation mode, context "pdn.claim-id.v0"
input      Alice's PdnId (32 bytes), then the key "contact/email" (13 bytes); no separator, the PdnId being fixed-width
output     the 32-byte digest
payload    not an input: rewriting "alice@example.org" as "alice@work.example" keeps the ClaimId, and Bob's grant still covers it
```

#### Scenario: Identity survives value edits

- **WHEN** an issuer overwrites the payload at an entry path covered by a grant
- **THEN** the entry's claim identity is unchanged and the grant still covers it

#### Scenario: Evaluation needs no mapping

- **WHEN** read authorization is evaluated for an entry
- **THEN** the decision is computed from the entry key and the granted set alone, with no id-to-location table

### Requirement: The serving node evaluates rights it has recorded

Before a serving node filters what it reveals, it SHALL determine the caller's effective grants from the grants its identity recorded (its own replicas of the connection metadata stores), keyed by the caller's transport-authenticated node id resolved to an identity through the published device sets. It SHALL NOT trust capability material sent by the caller: the minimal grant is unsigned, so wire presentation is unverifiable and no presentation protocol exists until UWill.

**Example:** Bob's phone b1 opens a session on Alice's data replica at a2, one of her devices a1 and a2; each store below is a2's own replica.

| input | where a2 takes it |
|---|---|
| the caller's node id | b1, as the transport authenticated it |
| b1 acting for Bob | the session names Bob; admitted as `devices/<b1-hex>` is in Bob's connection metadata store toward Alice |
| Bob's claims | `grants/<alice-hex>` in Alice's connection metadata store toward Bob, when it names issuer Alice, audience Bob |
| a grant just made on a1 | absent on a2 until that store replicates: a2 refuses the session, and a later session reveals the claims |

#### Scenario: Evaluation precedes filtering

- **WHEN** a peer reconciles a replica
- **THEN** the claims it may receive are exactly those covered by its effective recorded grants

#### Scenario: A stale grant book fails closed

- **WHEN** the serving device has not yet replicated a freshly issued grant
- **THEN** the session reveals at most what the device's recorded grants cover, and a later session, after the grant replicates, reveals the granted claims

### Requirement: A grant's ticket carries exactly the granted authority

The ticket published alongside a grant SHALL match the grant's commands as a whole: a grant carrying no write on any claim SHALL carry a read ticket (no namespace secret — the holder cannot produce a valid entry), and a grant carrying write on any claim SHALL carry a write ticket. The namespace secret is the transport interim of write authority: it lets the audience produce valid entries, and the scope of what the issuer keeps is the ingest gate's, judged per claim from this same grant.

**Example:** Alice (issuer) grants Bob; the ticket published beside the grant, and Bob's phone b1 writing `contact/email` over it.

| grant's claims | ticket | namespace secret | b1 writes `contact/email` |
|---|---|---|---|
| `contact/email` read | `ShareMode::Read` | no | fails on b1: `InsertError::ReadOnly` |
| `contact/email` read, `contact/phone` read-write | `ShareMode::Write` | yes | offered; Alice's gate: `ValidationFailure::Unauthorized` |
| `contact/email` read-write | `ShareMode::Write` | yes | kept by Alice |

#### Scenario: Read-only audience cannot write by construction

- **WHEN** a holder of a read-only grant attempts a local write into the granted replica
- **THEN** the write fails for lack of the namespace secret, and no entry authored by the holder ever appears in the replica

#### Scenario: Write grant keeps the write scenario reachable

- **WHEN** an issuer grants a claim with write and the audience writes that claim
- **THEN** the audience's write reaches the issuer over reconciliation

#### Scenario: A write ticket does not widen the write scope

- **WHEN** a grant carries write on one claim only and the audience produces an entry at another claim over the write ticket's secret
- **THEN** the issuer's gate refuses that entry, although the ticket that shipped with the grant carries the namespace secret

### Requirement: Per-claim evaluation

Given a claim and a caller's effective grants, the mechanism SHALL decide read-authorized or not from the grants alone.

#### Scenario: Covered claim is authorized

- **WHEN** a claim is covered by an effective grant
- **THEN** it is read-authorized for that peer

#### Scenario: Uncovered claim is not authorized

- **WHEN** a claim is covered by none of the effective grants
- **THEN** it is not read-authorized for that peer

### Requirement: Own-identity data needs no capability

An identity's own device SHALL be read-authorized for all of that identity's data without any grant, composing with Invariant 1.

**Example:** sessions on Alice's data replica at her laptop a2; a1 is listed at `devices/<a1-hex>` in Alice's directory and holds no grant.

| entry | a1 (Alice's device) | b1 (Bob's, read grant on `contact/email`) | a3 (acts for Alice, not listed) | c1 (Carol's, outsider) |
|---|---|---|---|---|
| `contact/email` | revealed | revealed | session refused | session refused |
| `notes/diary` | revealed | withheld | session refused | session refused |

#### Scenario: A device reads its own identity's data

- **WHEN** a device reconciles a replica bound to its own identity
- **THEN** every claim is read-authorized without any grant
