# Design: kerita

## Context

See proposal.md for why. The state this design starts from:

- **No KERI in the workspace.** An identity is named by a `PdnId` derived from an identity key that never rotates. [ADR-0017](../../../specs/architecture/adr/0017-keri-identity-layer.md) is proposed, and its DR-3 decides an implementation of our own, checked against keripy.
- **keripy, the reference implementation, has 2 lines.** The releases, 1.3.6 the latest (31 July 2026), validate KELs in KERI 1.0. They know KERI 2.00 message structures and CESR 2.00 code tables, but write a version field without the genus version and use earlier code assignments: the same inception begins `-FAtYKERICAAXicp…` and lists keys under `-I`. The main line, published as 2.x development releases, writes KERI 2.00 in the native CESR body by default (`eventing.Kind = Kinds.cesr`), validates KELs in it, and matches the KERI specification: `-FAu0OKERICAACAAXicp…`, lists under `-J`. Its v2 tests of KEL validation — `test_eventing_v2.py`, `test_escrow_v2.py`, `test_partial_rotation_v2.py` — use the native body, and its tests of delegation, witnesses and weighted thresholds are written in KERI 1.0.
- **`cesr-rs`** (devrandom-labs/cesr, MIT OR Apache-2.0) is a tested CESR primitive library with a nightly differential check against a pinned keripy commit and fuzzing. Its own capability matrix scopes it to KERI 1.0 JSON messages: CESR 2.00 count codes and the version grammar exist, typed KERI 2.00 messages and native bodies do not, and its KERI crate is not yet trusted to authenticate an inception. It builds on `ed25519-dalek` 2.2, `signature` 2.2, `rand_core` 0.6 and `p256` 0.13; the workspace builds on `ed25519-dalek` 3.0, `signature` 3.0 and `rand_core` 0.10.
- **The workspace's Python rule.** A script imports the standard library only. The oracle imports keripy, so it needs a place outside that rule.

## Goals / Non-Goals

**Goals:**

- A validator that reaches keripy's key state for every KEL of the subset, proven by a corpus built before the validator.
- A crate that a phone, a desktop node and a witness can all embed: synchronous, key-free, storage-free.
- A disagreement with keripy that shows up the night it appears, named by field.

**Non-Goals:**

- Completeness against the KERI specification. The crate refuses what the subset does not use, and says so as unsupported.
- Speed. Nothing here is tuned; ADR-0017 DR-13 sizes KELs at kilobytes.

## Decisions

### D1. KERI 2.00 in the native CESR body, in the text domain, and nothing else

The crate reads and writes KERI 2.00 events in the native CESR fixed-field body under genus 2.00, in the text domain. SAIDs and signatures are computed over the text-domain bytes, so the bytes a device signs are the bytes it stores and sends. A KEL never mixes protocol versions.

**Example:** keripy's one-key inception from `test_keri_native_dumps_loads`, 188 bytes, field by field.

```
-FAu          fixed-field body, 46 quadlets
0OKERICAACAA  protocol KERI 2.00, genus 2.00
Xicp          event type
ENcf5ii1...   d, the SAID
DG9XhvcV...   i, a basic prefix: the event's one Ed25519 key
MAAA          s = 0
MAAB          kt = 1
-JAL ...      k: a list of 11 quadlets, one key
MAAA -JAA     nt = 0, n = []
MAAA -JAA     bt = 0, b = []
-JAA -JAA     c = [], a = []
```

**Rejected alternatives:**

- KERI 1.0 with a JSON body
  - **Pros:** every deployed KERI implementation reads it; keripy's releases are its oracle; the message corpora of `cesr-rs` cover it.
  - **Cons:** the KERI specification and keripy's main line have moved to 2.00; with no mixing of versions in a KEL, moving later costs every identity issued by then a new AID.
- KERI 2.00 with a JSON body
  - **Pros:** a person reads it; a canonical JSON writer could be taken from `cesr-rs`.
  - **Cons:** keripy's v2 tests of KEL validation run on the native body, so every vector would be regenerated; a second grammar in the path of trust, with its own class of disagreements — duplicate keys, number spellings, escapes; 255 bytes for the inception above instead of 188.
- Reading KERI 1.0 events as well, as the specification asks of a 2.00 implementation
  - **Pros:** compliance with the specification as a whole.
  - **Cons:** a second codec for KELs that never occur in the platform.
- The binary domain
  - **Cons:** a conversion between domains between signing and storing would break the equality of signed and stored bytes; nothing needs the compactness now.

### D2. The crate holds KERI alone

What keripy decides about a KEL, the crate decides, and nothing else; keripy's rule for an own event that arrives from another source is the caller's (D3). What ADR-0017 adds on top of KERI — the roles a role statement gives and the weight each role carries (DR-9 to DR-11, DR-14), the limits on a KEL (DR-13), the old witness's receipt on a change of witness (DR-16), stamps (DR-20), the fork rule for devices (DR-22) and records — belongs to the crates that consume this one. The crate hands them what those rules read: the slots that signed an event, the seals it anchors, the witness list it sets, and the rival of an accepted event, answered as likely duplicitous with its signatures unchecked.

The crate is also usable on its own, outside the platform, as an implementation of a KERI subset, a goal set by the organization rather than by the platform's needs. What the subset holds behaves as keripy does, what it does not hold is answered as unsupported, and widening the subset is weighed by its cost rather than taken by default: a case the platform does not need still enters when keripy's tests carry it and it costs little, as the genus-version code a stream carries before a message does. The crate stays unpublished while the work on it goes on; once it is done, publishing it as a standalone implementation of a KERI subset is likely.

**Example:** who checks what in rotation 3 of Alice's identity KEL, which links her laptop.

| check | where |
|---|---|
| the laptop's and the co-signer's keys match their prior next-key digests, and their weights reach both thresholds | `kerita` |
| rotation 3 anchors a key event seal of the laptop's device AID's inception | `kerita` |
| W-tellipod's receipt is attached | `kerita` |
| slot 1 belongs to the co-signer according to the role statement of rotation 2, and the co-signer's weight is 1/2 | the consuming crate, from the slots `kerita` reports |
| Alice's KEL stays under its size limit | the consuming crate |

**Rejected alternatives:**

- One identity crate holding KERI and the rules of ADR-0017
  - **Pros:** one place to read the whole identity layer.
  - **Cons:** a rule of ours inside would make the crate refuse KELs keripy accepts, and the conformance check could no longer tell a defect from a rule.

### D3. A pure core: no I/O, no storage, no keys, and escrow as verdicts

The crate is a set of functions from bytes and key state to key state or a verdict. It reads no file, opens no connection, reads no clock and draws no randomness. The caller gives each event with what it is checked against: the AID's accepted events, its delegator's, and who checks it — its controller, a witness its controller gave it to receipt, or a remote validator given it from another node, the validator's own AID's event included. KERI accepts a controller's and a witness's event without receipts and without the delegator's approval, so that a witness can give its receipt and a delegate ask for its approval. keripy's rule for an own event that arrives from another source is the caller's: the caller's transport knows the source, the crate does not. Key state holds no history, so a fold stays linear in the KEL's length. To have an event signed, it hands the caller the bytes to sign and takes the signature back. An event it cannot validate yet comes back as a verdict naming what the event waits for; the caller keeps the event, applies its own quotas (ADR-0017 DR-4), and gives the event again once the awaited input arrives.

**Example:** Bob's phone receives Alice's rotation 7 before her rotation 6.

| step | the node | the crate |
|---|---|---|
| 1 | gives rotation 7 with Alice's key state at 5 | waits for the prior event at sequence number 6 |
| 2 | keeps rotation 7 in Alice's share of its escrow | |
| 3 | gives rotation 6 | accepted; key state 6 |
| 4 | gives rotation 7 again from its escrow | accepted; key state 7 |

**Rejected alternatives:**

- An escrow store inside the crate, as libkeri keeps in LMDB and keripy in its databases
  - **Pros:** one call accepts whatever becomes acceptable.
  - **Cons:** the storage engine, the quotas per identity and per sender (DR-4) and durability across a kill are the node's; a store inside would be a second storage engine beside `pdn-store`, holding a policy of ours in a KERI crate.
- A signer trait the crate calls
  - **Cons:** hardware signing asks for the user's presence (DR-23) and may run on another thread or be refused; a trait invites holding a key; bytes out and a signature in keep the crate synchronous and key-free.
- A flag saying whether the validator controls or witnesses the AID
  - **Cons:** it hands the caller the consequence, receipts skipped, instead of the fact the caller knows; read as keripy's `local`, which names the event's source, it invites setting it for an own event that came from the network.
- keripy's source rule inside the crate
  - **Pros:** the corpus would compare the KELs that rest on it too.
  - **Cons:** the crate would need to know which nodes make up one controller of an identity AID shared by several devices, which keripy models as a group and ADR-0017 does not settle.

### D4. Functional Rust on current libraries

Key state is an immutable value. Accepting an event is a function that returns the next key state or a verdict, and folding a KEL is a `try_fold` over its events. Types hold only valid values: a weight is a fraction from 0 to 1, a threshold is a count or a list of clauses each of which some signers can meet, a prefix carries how it was derived, a sequence number cannot be negative. Errors are enums. The crate has no interior mutability and no global state. keripy's logic is followed closely, and its class structure is not.

**Example:** a node folding a stored KEL after a restart, in the shape the crate offers.

```
let state = events
    .iter()
    .try_fold(KeyState::unestablished(aid), |state, event| state.accept(event, &inputs))?;
```

**Rejected alternatives:**

- keripy's class structure — a key state object mutated in place, an event processor holding databases
  - **Pros:** reading keripy side by side with the crate maps one class to one type.
  - **Cons:** state hidden across calls has to be rebuilt after a restart, and "the same events fold to the same key state" holds by discipline rather than by construction.

### D5. CESR primitives from a fork of `cesr-rs`, on the workspace's RustCrypto

The `cesr` module, kerita-cesr's (D13), is taken from `cesr-rs` at one commit, trimmed to the codes of the subset, and moved onto `p256` 0.14, `ed25519-dalek` 3, `signature` 3 and `blake3`. `UPSTREAM.md` names the commit and lists every divergence; `NOTICE` keeps the attribution. The fork's tests come with it wherever their codes are within the subset, and each of their vectors enters the corpus only once the oracle reproduces it (D10).

**Example:** the dependencies of `cesr-rs`'s crypto feature, and the fork's.

| `cesr-rs` | the fork |
|---|---|
| `ed25519-dalek` 2.2, `signature` 2.2 | `ed25519-dalek` 3, `signature` 3 |
| `p256` 0.13 | `p256` 0.14 |
| `blake3` | `blake3` |
| `k256`, `blake2`, `sha3`, `argon2` | dropped: secp256k1, other digests and key stretching are outside the subset |
| `rand_core` 0.6, `getrandom` | dropped from the product build: the crate generates no key |

**Rejected alternatives:**

- `cesr-rs` as a dependency
  - **Pros:** its nightly check against keripy keeps tracking; no copy to maintain.
  - **Cons:** a second RustCrypto generation in the mobile binary; an API that changes before 1.0; its KERI 2.00 support is the grammar alone.
- CESR primitives written from scratch
  - **Cons:** the same code, without the tested code tables and the corpus that come with the fork.
- The CESR module of libkeri
  - **Cons:** tokio, LMDB and libsodium through C in its dependency tree; a port of keripy's classes.
- `cesride` and `parside`
  - **Cons:** unmaintained since 2024, and on CESR 1.0 code assignments.

### D6. Ed25519 and P-256 keys, Blake3-256 digests

The crate verifies Ed25519 and P-256 signatures, transferable and non-transferable keys of both, and Blake3-256 digests. P-256 is the product's curve (ADR-0017 DR-2). Ed25519 is the key nearly every keripy test signs with, so the borrowed test suite needs it. Every other algorithm is refused as unsupported.

**Example:** the keys of one KEL of each kind.

| KEL | keys |
|---|---|
| Alice's identity | P-256 (`1AAJ`) for her devices and the co-signer; the recovery keys' type is decided with the recovery sheet |
| keripy's `test_partial_rotation`, replayed in KERI 2.00 | Ed25519 (`D`) |
| a witness's AID | non-transferable: Ed25519 (`B`) or P-256 (`1AAI`), whichever the witness software uses |

**Rejected alternatives:**

- P-256 alone
  - **Pros:** the smallest set the product needs.
  - **Cons:** nearly every vector of keripy's tests would become unsupported, and the borrowed suite would test little.

### D7. Thresholds as counts or clause lists; configuration traits limited to `EO`

A threshold is a hexadecimal count or a list of one or more clauses of fractional weights, every clause met. A nested weight map is refused as unsupported. The configuration trait `EO` is read from an inception; any other trait, and any trait in a rotation, is refused as unsupported.

**Example:** the thresholds keripy's `test_weighted` steps through, all read by the crate.

```
inception:  ["1/2","1/2","1/2"]
rotation 1: ["1/2","1/2","1/2"]
rotation 2: [["1/2","1/2","1/2"],["1","1"]]
rotation 3: [["1/2","1/2","1/2"],["1/1","1/1"]]   "1/1" weighs as "1"
```

**Rejected alternatives:**

- One clause alone, the form ADR-0017 DR-9 uses
  - **Pros:** the smallest grammar.
  - **Cons:** keripy's weighted threshold test moves to 2 clauses at its second rotation, and its vectors from there on would be unusable; the difference in code is a loop over clauses.
- Nested weight maps
  - **Pros:** keripy reads them.
  - **Cons:** no case of ADR-0017 uses them, nor any keripy test within the subset.
- `DND`, `DID`, `RB` and `NRB`
  - **Cons:** each changes what is accepted, none is used, and a trait half-honoured is worse than one refused.

### D8. A delegation is approved by a key event seal, found among the delegator's accepted events

A `dip` or `drt` is accepted once an accepted event of the delegator's KEL anchors a key event seal `{i, s, d}` of it. The caller gives the delegator's accepted events with the delegated event; the seal source couple attached to the delegated event names which of them to look in, and without it the crate looks through all of them. The approving event may be a rotation, which is how an establishment-only delegator approves. ADR-0017 DR-6 calls this seal a digest seal; see "ADR-0017 as it stands".

**Example:** rotation 3 of Alice's establishment-only identity KEL approves her laptop's device AID.

```
rotation 3, a:    [{"i": "E-laptop", "s": "0", "d": "E-laptop"}]
E-laptop's dip:   seal source couple attached: sequence number 3, SAID of rotation 3
outcome:          accepted, once rotation 3 is
```

**Rejected alternatives:**

- A digest seal of the delegated event, as ADR-0017 DR-6 is worded
  - **Cons:** keripy's `validateDelegation` finds an approval only as a key event seal, so a `dip` approved by a digest seal waits in keripy's escrow for good, and the crate would accept KELs keripy never does.

### D9. Receipts against the witness list the event falls under; the first accepted event stays

An event of a witnessed KEL needs receipts from the threshold of the witness list it falls under: an inception's own list, and for a rotation the prior list without its cuts and with its adds — the computation keripy's `deriveBacks` does. An event at a taken position never replaces the accepted one: a repeat is a duplicate, and a different event is answered as likely duplicitous before its signatures are checked, as keripy answers it, carrying both events with their signatures and receipts. The crate does not implement superseding recovery.

**Example:** rotation 9 of Alice's identity KEL cuts W-tellipod and adds W-home, witness threshold 1.

| receipts | the crate | ADR-0017's rule above it |
|---|---|---|
| W-home's | accepted | a rotation signed by a device needs W-tellipod's receipt too (DR-16) |
| W-tellipod's alone | waits for receipts | |

**Rejected alternatives:**

- Requiring the old witness's receipt inside the crate
  - **Cons:** keripy accepts the rotation with the new witness's receipt alone; the crate would refuse KELs keripy accepts, and DR-16's recovery rotation relies on exactly that acceptance.
- Superseding recovery
  - **Cons:** ADR-0017 uses none (DR-3), and it lets a later rotation undo accepted events.

### D10. The test suite first: an oracle in a container, a committed corpus

The work runs in this order: the oracle's image, the corpus from keripy's tests, the vectors of `cesr-rs` the oracle reproduces, the fuzz targets, and only then the crate. The oracle is keripy at the commit named in `oracle/KERIPY_PIN`, installed in an image together with the generators, which are Python scripts importing keripy. That is the one exception to the workspace's rule that a script imports the standard library alone, and `CLAUDE.md` says so in its `## Scripts` section; the generators run nowhere but in the image.

The corpus is files of JSON lines, one vector per line, each naming its source, its input, keripy's outcome and the crate's expected outcome. A keripy test written in KERI 2.00 native is copied with its values; a test written in KERI 1.0 is replayed by a generator that runs the same scenario through keripy in KERI 2.00. Every corpus file lists how many vectors it holds, and a corpus test that reads fewer fails, so a file emptied by mistake does not pass as zero cases.

A test is copied by running it: the oracle runs keripy's own test files at the pin under a recorder that notes every primitive, indexed signature, counter and event they build, and every event a validator is given with its answer. A passing test asserts its literal values, so what it built is its cases. A replay is the same file with its protocol version and body kind renamed, its value checks unable to fail and its hand-built counts recomputed in quadlets. The tests run twice and only what both runs recorded is kept, since a test that draws a random key gives other values each run; for the same reason keripy's P-256 signing runs with a deterministic nonce (RFC 6979) inside the oracle, its verification untouched. A test that fails records nothing and is named in the corpus instead, so that the corpus check fails rather than shrinking unseen. The image stands on a base image named by digest and installs the Python packages keripy resolves to at the pin from a frozen list, so a night rebuilds the oracle the pin names.

**Example:** the crates' trees around the corpora (D13).

```
crates/kerita/
  oracle/KERIPY_PIN            94f5423a32e907f3837e49d35758fe7acb0cb1d1
  oracle/Dockerfile            keripy at the pin, libsodium, the generators
  oracle/constraints.txt       the Python packages keripy resolves to at the pin
  oracle/gen_*.py              one generator per family of vectors
  tests/corpus/keripy/*.jsonl  copied and replayed keripy tests: events, KELs, streams
  tests/corpus/keripy/FAILED   keripy tests that failed at the pin, empty
  tests/corpus/crate/*.jsonl   KELs the crate wrote, with keripy's verdict
  tests/corpus/fuzz/           inputs the fuzzer found
crates/kerita-cesr/
  tests/corpus/keripy/*.jsonl  keripy's primitives, indexed signatures and count codes
  tests/corpus/keripy/FAILED   the same list as kerita's
  tests/corpus/cesr-rs/*.jsonl vectors of cesr-rs the oracle reproduced
```

**Rejected alternatives:**

- Calling keripy from the tests
  - **Cons:** every `just test` would need Python, keripy and libsodium.
- The corpora of `cesr-rs` taken as they are
  - **Cons:** one implementation's word, with no second source; its message corpora are KERI 1.0.
- keripy 1.3.6 as the oracle
  - **Pros:** a release rather than a commit of a development line.
  - **Cons:** its KERI 2.00 version field lacks the genus version and its codes predate the current tables; it validates KELs in KERI 1.0 alone.

### D11. A nightly job runs the oracle and the fuzzer

A nightly job builds the oracle's image at the pin, regenerates the corpus, fails on any difference from the committed corpus, folds the crate's KELs in keripy, and fuzzes every target for a fixed time on a pinned nightly toolchain. Fuzzing uses cargo-fuzz in `crates/kerita/fuzz/`, outside the workspace's members, so the nightly toolchain never reaches an ordinary build; an input that crashes the crate is committed under `tests/corpus/fuzz/`, which `just test` replays on the workspace's toolchain. Round-trip properties — read then write gives the same bytes — run as property tests in every ordinary run.

**Example:** the fuzz targets, one per entry point that reads bytes.

| target | reads |
|---|---|
| `primitive` | one CESR primitive |
| `attachments` | one attachment group |
| `event` | one event with its attachments |
| `stream` | a run of events, as a peer sends a KEL |

**Rejected alternatives:**

- Following keripy's main line head every night
  - **Cons:** a job failing because keripy moved says nothing about the crate, and a byte disagreement with a moving oracle is ambiguous.
- Property tests alone
  - **Pros:** they run on the stable toolchain.
  - **Cons:** they generate from the crate's own types and miss the byte-level edges a coverage-guided fuzzer finds.

### D12. An annotator renders an event field by field

The crate renders a native event one field per line — its code, the field's name, its value — and every corpus test that fails on bytes prints both events so rendered, naming the first differing field. An example binary renders an event given on the command line.

**Example:** see the conformance spec, "A failed comparison names the field that differs".

**Rejected alternatives:**

- keripy's `annotate`
  - **Cons:** it needs Python, and a Rust test cannot put its output into a failure message.

### D13. Two crates, `kerita-cesr` for CESR and `kerita` for KERI, named apart from the platform

CESR and KERI are two specifications: CESR encodes primitives, indexed signatures and count codes, KERI defines events, messages, key state and the rules that fold one into the other. The crate is split along that line. `kerita-cesr` holds the fork of `cesr-rs` (D5) as a private module, the primitives' facade with the codes of the subset, count codes and the genus-version code, number codes and signature verification; it depends on no crate of the workspace. `kerita` holds events, messages, thresholds, key state, the annotator, and depends on `kerita-cesr` alone among the workspace's crates, re-exporting its primitives so that a caller of kerita needs no second dependency. One refusal type, kerita-cesr's, serves both. The oracle (D10), the fuzz targets (D11) and the nightly job stay kerita's: one pin, one image and one fuzz workspace write and drive both crates, and each crate's tests read its own corpus. Neither name carries the platform's, as the crates are usable on their own (D2): *-ita* is the Spanish diminutive suffix, so Kerita is "little KERI". What ADR-0017 adds on top of KERI goes to `pdn-keri`, a crate of the platform that consumes kerita, and the witness to `pdn-witness`.

**Example:** where the parts of the crate went.

| part | crate |
|---|---|
| `src/cesr/`, `primitive.rs`, `count.rs`, `number.rs`, `signature.rs`, `subset.rs`, `UPSTREAM.md` | `kerita-cesr` |
| `event.rs`, `message.rs`, `threshold.rs`, `state.rs`, `annotate.rs`, `oracle/`, `fuzz/` | `kerita` |
| the vectors of `matter`, `indexer` and `counter`, and those of `cesr-rs` | `kerita-cesr`'s corpus |
| the vectors of events, KELs and streams, the crate's KELs and the fuzz inputs | `kerita`'s corpus |
| the rules of ADR-0017 over key state, DR-22's proof of duplicity if the platform's | `pdn-keri`, which does not exist yet |

The specs of kerita-cesr, `components/mee-pdn/kerita-cesr/crate` and `components/mee-pdn/kerita-cesr/primitives`, were written in the spec tree with the split; this change's deltas hold kerita's four.

**Rejected alternatives:**

- One crate, CESR as a module
  - **Pros:** one manifest, one corpus, no public surface between the layers.
  - **Cons:** CESR and KERI are separate specifications a user of either may want alone, and a module boundary lets KERI code reach into CESR's internals unseen.
- An oracle and a fuzz workspace for each crate
  - **Cons:** 2 images at one pin, 2 locks to audit and 2 nightly steps, for a harvest that already yields both crates' vectors in one run.
- A refusal type of each crate's own
  - **Cons:** every `?` across the boundary needs a conversion, and kerita's callers would match 2 types for one input.

## ADR-0017 as it stands

This change does not edit ADR-0017 and contradicts none of its decisions. Where the ADR's wording is less precise than KERI or than what this change settles, it is recorded here for the ADR's own revision.

- **DR-6 names the wrong kind of seal.** It says a rotation of the identity's KEL carries a digest seal of the device AID's inception, and of each rotation of the device AID. KERI approves a delegation by a key event seal `{i, s, d}`, and keripy finds no approval in a digest seal (D8). The intent of DR-6, the identity approving the device AID as delegation requires, holds; the change that writes these seals writes key event seals.
- **DR-1 says existing KERI implementations verify the KELs.** In KERI 2.00 with the native body (D1), those are keripy's main line and implementations of KERI 2.00; keripy's releases do not read them.
- **DR-3 lists what the implementation includes.** The witness software is a crate of its own over this one (D2). The crate reads weighted thresholds as clause lists, beyond the one clause DR-9 uses (D7), so that keripy's tests carry over.
- **DR-22 acts on duplicity, which this change does not prove.** ADR-0017 defines duplicity as 2 validly signed events at one position, and DR-22 marks a device compromised on a fork of its device AID's KEL. The crate answers a rival event as likely duplicitous before checking its signatures, as keripy answers it with `LikelyDuplicitousError`, and an unsigned rival gets the same answer as a signed one; keripy itself proves duplicity nowhere, its duplicitous event log staying empty and `Kevery.duplicity` a placeholder. The change that implements DR-22 proves the rival before acting on it: its signatures checked against the key state at the rival's position, either by a function this crate gains for it or by that change itself, which is that change's decision. **Example:** the icp of Alice's laptop's device AID is accepted at position 0; an `ixn` at position 0 with no signature, sent by anyone, and one signed by the laptop's key both come back likely duplicitous, and only the second is duplicity.
- **The deferred item on Apache 2.0 KERI building blocks** is answered by D5.
- **"To verify" items the oracle answers**, each with its vectors in `tests/corpus/keripy/kel-generated.jsonl`. DR-6: keripy approves a delegated inception by a key event seal in a rotation of an establishment-only delegator, and a digest seal approves nothing (`test_identity_in_order`, `test_digest_seal_approves_nothing`). DR-16: keripy counts receipts from the witness list after a rotation's cuts and adds, so a rotation receipted by the new witness alone is valid KERI and one receipted by the cut witness alone waits (`test_cut_witness_receipt`). DR-20: keripy's validator accepts a receipt from a transferable basic witness, whose prefix is its key, and refuses an event whose witness is self-addressing; its writer refuses to write a receipt by a transferable prefix (`test_transferable_basic_witness`, `test_self_addressing_witness`). KERI as keripy runs it therefore does not require a non-transferable witness; that requirement is ADR-0017's own, and contradicts nothing here.

## Operating conditions

Two conditions change the crate's outcome, and the specs carry both. **An unstable connection** delivers events out of order, twice, or before their receipts or their delegator's approval: D3's verdicts and the key-state spec's waiting, duplicate and likely duplicitous answers meet it. **A modified node** sends bytes built to exhaust the parser or to fork a KEL: the encoding spec bounds every group before reading, and a rival event comes back as likely duplicitous, never as proven duplicity.

**A restart** reaches the crate only as a fold of a stored KEL, each event in the context it was accepted in, which reaches the same key state (key-state spec, "Key state is a fold of the KEL"). The other conditions do not reach a crate that keeps no state, touches no disk or network and handles events that carry no time: several identities on one node, one device or several, a device linking at any moment, a full disk, a kill, a write to several places, clocks, and a moving membership.

## Risks / Trade-offs

- **keripy's KERI 2.00 is a development line, and its codes have moved before** (1.3.6 against the main line, D10). → The pin and the nightly diff catch a move the night it is pinned. No identity exists before a consuming change lands, so a move until then costs a regenerated corpus; after it, a move that changes the bytes of issued KELs is a decision for ADR-0017, since KELs do not mix versions.
- **The specification's table of indexed signatures has no P-256 code** (ADR-0017 DR-2). → The crate uses keripy's codes `E`, `F`, `2E` and `2F`, and the corpus pins them.
- **The tables of `cesr-rs` may differ from keripy's main line.** → No vector of `cesr-rs` enters the corpus unreproduced (conformance spec).
- **A P-256 signature with a high S value.** → keripy accepts it (`kel-generated.jsonl`, `test_high_s_signature`), so the crate verifies both forms. ADR-0017 DR-17's low-S rule concerns records, not KEL events.
- **keripy may disagree with the specification.** → keripy breaks the tie; a deviation of the crate from keripy needs a reason in the specification and a vector, listed in the corpus.
- **Native CESR is unreadable to a person.** → The annotator (D12).
- **The oracle needs Python and a container, the fuzzer a nightly toolchain.** → Both stay in their image and their job; an ordinary run needs neither.

## Migration Plan

None: the crate is new and nothing consumes it.
