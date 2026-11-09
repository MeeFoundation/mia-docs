# Proposal: kerita

## Why

[ADR-0017](../../../specs/architecture/adr/0017-keri-identity-layer.md) makes KERI the identity layer: every identity is an AID, every device a delegated AID, and linking and revoking a device are rotations of the identity's KEL. Its DR-3 decides that the project writes its own KERI implementation, limited to the subset the design uses and checked against keripy, the reference implementation. Nothing in the workspace parses or validates a key event yet. An identity is named by a `PdnId` derived from an [identity key](../../../specs/architecture/language/identity-key.md) that never rotates, so losing that key renames the identity.

Every later step of ADR-0017 — device AIDs, linking as a rotation, records verified against two KELs, the witness — stands on a validator that reaches the same key state keripy reaches. This change builds that validator alone, before any of its consumers, and builds its test suite before the validator.

**Example:** keripy's own test of a one-key inception, which the crate reproduces byte for byte (keripy `tests/core/test_serdering.py`, main line).

```
key:     DG9XhvcVryHjoIGcj5nK4sAE3oslQHWi4fBJre3NGwTQ   (Ed25519, transferable)
event:   -FAu0OKERICAACAAXicpENcf5ii15MsVCx7wxKi4muIodYJULhkOaEbvbz4cF3d4DG9XhvcVryHj
         oIGcj5nK4sAE3oslQHWi4fBJre3NGwTQMAAAMAAB-JALDG9XhvcVryHjoIGcj5nK4sAE3oslQHWi
         4fBJre3NGwTQMAAA-JAAMAAA-JAA-JAA-JAA                              188 bytes
SAID:    ENcf5ii15MsVCx7wxKi4muIodYJULhkOaEbvbz4cF3d4
outcome: the crate encodes the same fields to these 188 bytes and decodes them back;
         one byte of difference fails the test
```

## What Changes

- **A new crate, `crates/kerita`, holding KERI and nothing else.** It reads and writes the events `icp`, `rot`, `ixn`, `dip`, `drt` and the receipt `rct` with their attachments, and folds a KEL into key state: pre-rotation and partial rotation, numeric and weighted thresholds, the establishment-only configuration, delegated inception and rotation approved by a key event seal in the delegator's KEL, digest seals, and witness receipts against the witness list the KEL sets. An event at a position already taken never replaces the accepted one, and a different event at that position comes back as likely duplicitous, with both events, as keripy answers it. An event that cannot be validated yet comes back as a verdict naming what it waits for.
- **What ADR-0017 adds on top of KERI stays out of the crate.** The roles a role statement gives, the weight each role carries, the limits on a KEL's size, the old witness's receipt on a change of witness, stamps and records belong to the layers that consume the crate. The crate answers what keripy answers, and hands those layers what their rules read: which signing slots signed, the seals an event anchors, the witness list.
- **No I/O, no storage, no secret keys.** The crate turns bytes and key state into key state or a verdict. It gives a signer the bytes to sign and takes the signature back, so a key that lives in a Secure Enclave or the Android Keystore never passes through it.
- **KERI 2.00 alone, in the native CESR body, in the text domain.** KERI 1.0, a JSON, CBOR or MGPK body, the version string of keripy's 1.x releases and the binary domain are refused as unsupported. A KEL never mixes versions.
- **CESR primitives from a fork of `cesr-rs`** (devrandom-labs/cesr, MIT OR Apache-2.0), trimmed to the codes in use and moved onto the RustCrypto generation the workspace already builds. `UPSTREAM.md` records the commit taken and every divergence.
- **The test suite comes first.** keripy at a pinned commit of its main line is the oracle. It runs in a container, and what it produces is committed as a corpus, so an ordinary `just test` needs no Python. keripy's tests within the subset are carried over: their vectors verbatim where keripy wrote them in KERI 2.00 native CESR, their scenarios verbatim with values the oracle regenerates where keripy wrote them in KERI 1.0. Everything devrandom's corpora hold within the subset is taken too, and a vector of theirs enters the corpus only once the oracle reproduces it. Only then is the crate written against the corpus.
- **Conformance in both directions, every night.** What keripy produces the crate accepts with the same key state, and what the crate produces keripy accepts with the same key state. A nightly job regenerates the corpus from the pinned keripy and runs both directions; the pin moves only by a deliberate change.
- **Fuzzing of every parser entry point.** An input that crashes the crate becomes a corpus case that every ordinary run replays.
- **An annotator** renders a native CESR event field by field, for a person debugging and for the message of a failed corpus test.
- **ADR-0017 is left as it stands.** The change contradicts none of its decisions. Where its wording is less precise than KERI or than what this change settles, and where the oracle answers one of its "To verify" items, design.md records it under "ADR-0017 as it stands", for the ADR's own revision.

## Rules for agents and models working on this change

These rules hold for every agent and model that works on this change or later in `crates/kerita`. They are copied into the crate's `CLAUDE.md`, which outlives this change.

- **Agents and models never open, fetch, search or quote the source, tests or docs of keriox (THCLab: keri-core, keri-controller, keri-sdk, cesrox, teliox) or of any project whose license is not on the allow list of `deny.toml`.** A project's license is read from its metadata before any of its files is opened.
- **keripy (Apache-2.0) is the reference.** Its test cases are copied verbatim, each with its source file and keripy commit recorded, and its logic may be followed closely.
- **The code is idiomatic Rust, functional where it can be,** on current libraries: immutable values, a KEL folded into key state, types that cannot hold an invalid value. keripy's class structure is not carried over.

## Out of Scope

- **The witness software** — receipting, stamps and the witness's durable state belong to a crate of its own over this one.
- **Everything that consumes the crate:** `PdnId` as an AID, device AIDs, linking and revoking as rotations, records verified against KELs, role statements and the rules ADR-0017 sets on top of KERI, the store an escrowed event waits in and its quotas (DR-4), and the limits on a KEL (DR-13). Each is a change of its own after this one.
- **Keys in hardware** (DR-2) and **the recovery sheet** (DR-27).
- **What ADR-0017 does not use:** superseding recovery, ACDC and TELs, query, reply and key state notice messages, the messages that coordinate a group of signers, secp256k1 and Ed448 keys.
- **Operating conditions that do not reach the crate.** Two conditions change its outcome and the specs carry them: an unstable connection delivers events out of order, twice or before their receipts, and a modified node sends bytes built to exhaust the parser. The rest do not reach a crate that keeps no state, touches no disk or network and handles events that carry no time: several identities on one node, a full disk, a kill, a write to several places, clocks and a moving membership. A restart is a fold of the stored KEL from its first event, and reaches the same key state.

## Capabilities

A capability id is the spec's path under `specs/`; the delta sits at the same path in the change and lands there on archive.

| Capability (delta) | Archive destination |
|---|---|
| `components/mee-pdn/kerita/crate` | `openspec/specs/components/mee-pdn/kerita/crate/spec.md` |
| `components/mee-pdn/kerita/encoding` | `openspec/specs/components/mee-pdn/kerita/encoding/spec.md` |
| `components/mee-pdn/kerita/key-state` | `openspec/specs/components/mee-pdn/kerita/key-state/spec.md` |
| `components/mee-pdn/kerita/conformance` | `openspec/specs/components/mee-pdn/kerita/conformance/spec.md` |

### New Capabilities

- `components/mee-pdn/kerita/crate`: the crate as a member of the workspace — what it depends on and what never, that it holds no secret key and does no I/O, its license and what it took from whom.
- `components/mee-pdn/kerita/encoding`: the one protocol version and body it reads and writes, what it refuses, that a parse is bounded before it reads, and that an event round-trips to the same bytes.
- `components/mee-pdn/kerita/key-state`: how a KEL folds into key state, and the verdict for every event that does not advance it.
- `components/mee-pdn/kerita/conformance`: the oracle, the corpus and where each vector came from, the 2 directions of the check, the nightly run, and fuzzing.

### Modified Capabilities

None.

## Impact

- **`crates/kerita`** (new): the library; `oracle/`, the container image and the generators that import keripy; `fuzz/`, outside the workspace's members; the corpus under `tests/`; `LICENSE`, `NOTICE`, `README.md` and `CLAUDE.md`.
- **`crates/kerita-cesr`** (new): the CESR primitives, split out of `crates/kerita` along the line between the CESR and KERI specifications (design D13): the fork of `cesr-rs` with its `UPSTREAM.md`, and the corpus of primitives and count codes.
- **The workspace:** a new member and its entry in the crate list of `CLAUDE.md`. The `## Scripts` section gains one exception: the oracle's generators import keripy, so they run only inside the oracle's image. Recipes for regenerating the corpus, for the reverse direction and for fuzzing; a nightly job for the oracle and the fuzzer.
- **Dependencies:** `p256` 0.14 is new to the workspace; `blake3`, `ed25519-dalek` 3 and `signature` 3 are there already. Every one is under a license `deny.toml` allows.
- **mia-docs:** glossary entries for the KERI terms the new specs use. ADR-0017 is not edited.
- **Nothing consumes the crate**, so no node behaves differently when this lands.
