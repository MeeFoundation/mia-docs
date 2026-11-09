# KERI conformance

## Purpose

How the KERI crate is held to keripy, the reference implementation: one pinned oracle in a container, a committed corpus whose every vector says where it came from, the check in both directions, the nightly run, and fuzzing. What the crate does is specified in the [encoding](../encoding/spec.md) and [key-state](../key-state/spec.md) specs; this spec says how a disagreement with keripy is found.

## ADDED Requirements

### Requirement: The oracle is keripy at one pinned commit, run in a container
The oracle SHALL be keripy at one commit of its main line, named in one file of the crate, and SHALL run only inside a container image built from that commit. What the oracle produces SHALL be committed as the crate's corpus, so that an ordinary `just test` runs the corpus without Python, a network or a container.

**Example:** where the oracle's pieces live and who reads them.

| file | holds | read by |
|---|---|---|
| `crates/kerita/oracle/KERIPY_PIN` | one commit, such as `94f5423a32e907f3837e49d35758fe7acb0cb1d1` | the image build |
| `crates/kerita/oracle/` | the image's definition and the generators that import keripy | the image |
| `crates/kerita/tests/corpus/` | the vectors the oracle produced or reproduced | `just test` |

#### Scenario: The corpus runs without Python
- **WHEN** `just test -p kerita` runs on a machine without Python and without a container daemon
- **THEN** every corpus test runs, and none is skipped

#### Scenario: The image takes only a commit
- **WHEN** the oracle's image is built with a pin that is not a full commit hash
- **THEN** the build fails before keripy is fetched

### Requirement: Every corpus vector names its source and its expected outcome
Every vector of the corpus SHALL name where it came from — a keripy test copied verbatim, a keripy test whose scenario the oracle replayed in KERI 2.00, a generator of the oracle, or a corpus of `cesr-rs` — with the keripy commit, and the file and test or generator it came from. It SHALL hold keripy's outcome and the crate's expected one: the same outcome, or unsupported for a vector outside the subset the crate reads.

**Example:** 2 vectors of the corpus.

| source | input begins with | keripy's outcome | the crate's expected outcome |
|---|---|---|---|
| keripy `94f5423a…`, `tests/core/test_serdering.py`, `test_keri_native_dumps_loads`, copied | `-FAu0OKERICAACAAXicp…` | read, SAID `ENcf5ii15MsVCx7wxKi4muIodYJULhkOaEbvbz4cF3d4`, 188 bytes | the same |
| keripy `94f5423a…`, `tests/core/test_weighted_threshold.py`, `test_weighted`, replayed in KERI 2.00 | an inception under `[["1/2","1/2","1/2"],["1","1"]]` | accepted | the same |

#### Scenario: A vector without a source fails the corpus check
- **WHEN** a vector of the corpus names no source or no keripy commit
- **THEN** the corpus check fails, naming the vector

#### Scenario: A vector outside the subset expects unsupported
- **WHEN** a keripy test carries an event the crate does not read, such as one signed with a secp256k1 key
- **THEN** its vector holds keripy's outcome and the crate's expected outcome unsupported, and the crate answers unsupported

### Requirement: The crate and keripy agree in both directions
For every [KEL](../../../../architecture/language/kel.md) of the corpus that keripy produced, the crate SHALL reach the [key state](../../../../architecture/language/key-state.md) keripy reached, and SHALL refuse every event keripy refused. For every KEL the crate's own tests produce, keripy SHALL reach the key state the crate reached. The corpus SHALL hold, among the crate's KELs, the cases of ADR-0017 the [key-state](../key-state/spec.md) spec names: an establishment-only identity, a partial rotation under weighted thresholds, a device [AID](../../../../architecture/language/aid.md) approved by a [key event seal](../../../../architecture/language/key-event-seal.md) in a rotation, and a change of [witness](../../../../architecture/language/witness.md).

**Example:** one KEL in each direction.

| KEL | written by | folded by | compared |
|---|---|---|---|
| keripy's partial rotation test, replayed in KERI 2.00 | keripy | the crate | current keys, next-key digests, thresholds, witness list, sequence number |
| Alice's identity: inception with `EO`, rotation 1 approving her phone's device AID, rotation 2 linking her laptop | the crate | keripy, in the oracle's image | the same |

#### Scenario: A KEL keripy wrote folds to keripy's key state
- **WHEN** the crate folds a KEL of the corpus that keripy wrote
- **THEN** it reaches the key state the vector records from keripy

#### Scenario: A KEL the crate wrote folds to the crate's key state in keripy
- **WHEN** the oracle folds a KEL the crate wrote
- **THEN** keripy reaches the key state the crate reached

#### Scenario: An event keripy refuses, the crate refuses
- **WHEN** the crate is given an event of the corpus that keripy refused, such as a rotation signed by a key the prior event never committed to
- **THEN** the crate refuses it or answers that it waits, as keripy did

### Requirement: The oracle runs every night against the committed corpus
A nightly job SHALL regenerate the corpus from the pinned keripy and SHALL run the check in both directions. A regenerated corpus that differs from the committed one, and a disagreement in either direction, SHALL fail the job. The pin SHALL move only through a change that commits the regenerated corpus with it.

**Example:** 3 nights.

| night | pin | keripy's main line | the job |
|---|---|---|---|
| 1 | `94f5423a…` | at `94f5423a…` | passes |
| 2 | `94f5423a…` | moved on | passes: the pin holds the oracle |
| 3 | moved to a later commit, without the corpus regenerated | | fails: the regenerated corpus differs from the committed one |

#### Scenario: A drifted corpus fails the nightly job
- **WHEN** the corpus regenerated from the pin differs from the committed corpus
- **THEN** the nightly job fails and shows the difference

#### Scenario: A disagreement in either direction fails the nightly job
- **WHEN** keripy folds a KEL the crate wrote to a key state other than the crate's
- **THEN** the nightly job fails

### Requirement: A vector of `cesr-rs` enters the corpus only when the oracle reproduces it
A vector taken from a corpus of `cesr-rs` SHALL enter the crate's corpus only when the oracle produces the same output for the same input. A vector the oracle does not reproduce SHALL stay out, listed with the oracle's output beside it.

**Example:** 2 primitives from the corpora of `cesr-rs`.

| vector | the oracle | in the crate's corpus |
|---|---|---|
| a P-256 key under code `1AAJ`, 48 characters | the same 48 characters | yes, naming both sources |
| a vector whose expected bytes differ from what the oracle produces | other bytes | no, listed with both outputs |

#### Scenario: A reproduced vector is admitted
- **WHEN** the oracle produces the output a `cesr-rs` vector expects
- **THEN** the vector enters the corpus, naming `cesr-rs` and the keripy commit that reproduced it

#### Scenario: A vector the oracle disagrees with is kept out and listed
- **WHEN** the oracle produces another output for a `cesr-rs` vector
- **THEN** the vector stays out of the corpus and is listed with both outputs

### Requirement: Every parser entry point is fuzzed, and a crash becomes a corpus case
Every entry point that reads bytes — a primitive, an attachment group, an event, a stream of events — SHALL have a fuzz target. A nightly job SHALL fuzz every target. An input that crashes the crate SHALL be stored as a corpus case that every ordinary `just test` replays on the workspace's own toolchain.

**Example:** an input found by fuzzing the event entry point.

```
1. the nightly fuzz job finds an input that crashes the event parser, and fails
2. the fix commits the input as a corpus case beside the fix
3. every `just test` from then on reads that input and expects a refusal
```

#### Scenario: A stored crash is replayed by an ordinary run
- **WHEN** `just test -p kerita` runs
- **THEN** every stored crash input is read again, and each is refused without a crash

#### Scenario: A crash found by fuzzing fails the nightly job
- **WHEN** the nightly fuzz job finds an input that crashes the crate
- **THEN** the job fails and keeps the input

### Requirement: A failed comparison names the field that differs
When the crate's bytes for a vector differ from keripy's, the failure SHALL name the first field that differs and SHALL show both events rendered field by field.

**Example:** the crate writes the inception of `test_keri_native_dumps_loads` with a wrong current threshold.

```
corpus case keripy 94f5423a… tests/core/test_serdering.py::test_keri_native_dumps_loads
first difference: kt
  keripy:  MAAB   kt = 1
  crate:   MAAC   kt = 2
```

#### Scenario: A byte difference is reported by field
- **WHEN** the bytes the crate writes for a vector differ from keripy's
- **THEN** the failure names the first differing field and renders both events field by field
