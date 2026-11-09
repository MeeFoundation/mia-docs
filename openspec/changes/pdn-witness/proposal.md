# Proposal: pdn-witness

## Why

[ADR-0017](../../specs/architecture/adr/0017-keri-identity-layer.md) gives every identity exactly one witness (DR-15). The witness receipts the identity's events, refusing a second event at a position it has already receipted, and issues stamps (DR-20), which decide which records of a revoked device stay accepted. DR-3 makes the witness software part of the project's own implementation.

The witness is a server, and the KERI crate `kerita` is a library a phone embeds: synchronous, holding no key, keeping no state, touching no network. The witness needs everything that crate leaves out: a key of its own, durable state for each identity, a surface that devices reach, and stamps, which are a message of ADR-0017's own outside KERI (DR-1). It is therefore a crate of its own, `pdn-witness`, over `kerita`, and nothing of it enters `kerita`.

**Example:** what each crate does with Alice's rotation 9 and with her phone's stamp request.

| | `kerita` | `pdn-witness` |
|---|---|---|
| validating rotation 9 against Alice's KEL | decides | asks `kerita` |
| a rival rotation at position 9 | answers likely duplicitous | refuses to receipt it, having receipted the first |
| the receipt of rotation 9 | builds the receipt message, verifies it | signs it with the witness's key and sends it |
| the stamp the phone asks for | | signs it at position 9, the latest it receipted |
| state | none | Alice's latest receipted position, durable, never restored backward |

## What Changes

A new crate, `crates/pdn-witness`, holding what ADR-0017 gives the witness:

- **Receipting** — an identity's event is receipted only once it is valid against the identity's KEL, and only the first event at each position; the receipt is durable before it leaves (DR-15).
- **Stamps** — a stamp names the identity's AID, the position and digest of the latest event the witness has receipted, and the digest the requesting device supplies (DR-20). No stamp gives a position below an event the witness has already receipted (DR-3).
- **State** — durable and linearizable for each identity, and never restored backward (DR-3).
- **Load** — receipts never wait behind stamps, and request rates are limited for each connection, never for each identity (DR-3).
- **Serving KELs** — a device fetches its own identity's KEL before it writes and at least every 24 hours, another identity's KEL when no other source has confirmed its copy for 24 hours, and the latest KEL before it co-signs (DR-15, DR-16, DR-21).
- **A change of witness** — receipting a rotation that moves an identity to this witness or away from it (DR-16).
- **The witness's own AID** — non-transferable, with its key held by the witness alone (DR-20).
- **One software for every operator** — Tellipod's default witness and a witness another operator or the user hosts run the same crate (DR-15).

## Not settled here

How devices reach the witness, what it stores its state in, how a restore from a backup is kept from setting it back, the form a stamp takes on the wire, the receipt form it sends and its key type belong to this change's design.

## Out of Scope

- **What devices do with stamps** — when a device asks for one, publishing it into pods, and the acceptance of a revoked device's records (DR-20, DR-21) belong to the platform's crates over `kerita`, `pdn-keri` among them.
- **The co-signer and the recovery service** (DR-25 to DR-31) — servers of their own.
- **KERI itself** — validation, receipts as KERI messages and the answer to a rival event are `kerita`'s.

## Impact

- **`crates/pdn-witness`** (new), depending on `kerita`.
- **Operations:** a witness that Tellipod runs, and the documentation a user follows to host one.
