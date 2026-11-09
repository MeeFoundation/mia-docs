# KERI crate

## Purpose

The KERI subset [ADR-0017](../../../../architecture/adr/0017-keri-identity-layer.md) uses, as a crate of the workspace: what it depends on and what it never does, the license it carries, and what it took from whom. What the crate reads, writes and decides is in the [encoding](../encoding/spec.md) and [key-state](../key-state/spec.md) specs; how it is held to the reference implementation is in the [conformance](../conformance/spec.md) spec.

## ADDED Requirements

### Requirement: The crate is a leaf of the workspace
The crate SHALL be a member of the workspace at `crates/kerita`, named `kerita`, and SHALL depend on no other crate of the workspace. Its product build SHALL depend on no async runtime, no network crate and no storage crate. It SHALL build for every target the workspace builds for, the mobile targets included.

**Example:** what the product build's dependency tree may and may not hold.

| dependency | in the product build |
|---|---|
| `p256` 0.14, `ed25519-dalek` 3, `blake3` | yes |
| `pdn-types`, `data-layer`, `pdn-node` | no |
| `tokio`, `iroh`, `redb` | no |

#### Scenario: The dependency tree names no workspace crate
- **WHEN** the dependency tree of `kerita`'s product build is listed
- **THEN** it holds no other crate of the workspace, no async runtime, no network crate and no storage crate

#### Scenario: The crate builds for the mobile targets
- **WHEN** `just build-mobile` builds for `aarch64-linux-android`, `aarch64-apple-ios` or `aarch64-apple-ios-sim`, with that target's C compiler, as the pipeline's Android job does for Android
- **THEN** `kerita` builds for that target beside the mobile facade

### Requirement: The crate holds no secret key
No public item of the crate's product build SHALL take, hold or return a secret key. To have an event signed, the crate SHALL hand the caller the exact bytes to sign and SHALL take the signature back. A key that signs in tests SHALL be reachable only from the crate's tests.

**Example:** Alice's laptop co-signs a rotation of her [KEL](../../../../architecture/language/kel.md); its key lives in the laptop's TPM.

```
1. the laptop's node asks the crate for the rotation's bytes to sign
2. the TPM signs those bytes with the laptop's P-256 key; the crate never sees the key
3. the node hands the signature to the crate, which verifies it against the
   laptop's current key and attaches it at the laptop's index
```

#### Scenario: No public item takes a secret key
- **WHEN** the public items of the crate's product build are listed
- **THEN** none of them takes, holds or returns a secret key

#### Scenario: A signature made outside the crate is attached
- **WHEN** the caller hands back a signature made over the bytes the crate gave it, by the key the event's key state expects at that index
- **THEN** the crate attaches it, and a signature over other bytes is refused

### Requirement: The crate does no I/O, reads no clock and draws no randomness
The crate's product build SHALL read no file, open no connection, read no clock and draw no randomness. Its results SHALL be determined by its inputs alone: the same bytes and the same [key state](../../../../architecture/language/key-state.md) SHALL yield the same result on every device and in every run.

**Example:** Bob's phone and Carol's laptop each fold Alice's KEL of 9 events. Both reach the same current keys, the same next-key digests and the same [witness](../../../../architecture/language/witness.md) list, whatever their clocks read and whichever ran first.

#### Scenario: The product build pulls in no source of randomness
- **WHEN** the dependency tree of the crate's product build is listed
- **THEN** it holds no crate whose job is to draw randomness or read the system clock

#### Scenario: Two folds of one KEL agree
- **WHEN** the same KEL is folded twice, in 2 separate processes
- **THEN** both folds reach the same key state

### Requirement: The crate carries its license and its provenance
The crate SHALL be licensed Apache-2.0 and SHALL carry a `LICENSE` file. Its `NOTICE` SHALL name keripy, under Apache-2.0, as the source of the test cases copied from it, and `cesr-rs` from devrandom-labs, under MIT OR Apache-2.0, as the source of the CESR primitives forked from it. `UPSTREAM.md` SHALL name the commit of `cesr-rs` the fork was taken from and SHALL list every divergence of the fork from that commit.

**Example:** what the crate's provenance files hold after the fork is taken.

| file | holds |
|---|---|
| `NOTICE` | keripy, WebOfTrust, Apache-2.0: test cases; `cesr-rs`, Joel DSouza, MIT OR Apache-2.0: CESR primitives |
| `UPSTREAM.md` | the `cesr-rs` commit taken, such as `3a02703ab892325b149bf4a477c5209191f12386`; the codes dropped; the move to `p256` 0.14 and `ed25519-dalek` 3 |

#### Scenario: The notice names both sources
- **WHEN** the crate's `NOTICE` is read
- **THEN** it names keripy and `cesr-rs`, each with its license and what the crate took from it

#### Scenario: The fork names its upstream commit
- **WHEN** `UPSTREAM.md` is read
- **THEN** it names one commit of `cesr-rs` and lists the fork's divergences from it

### Requirement: The crate's guidance carries the clean-room rule
The crate's `CLAUDE.md` SHALL state the rule every agent and model working in the crate follows: never open, fetch, search or quote the source, tests or docs of keriox — THCLab's keri-core, keri-controller, keri-sdk, cesrox and teliox — or of any project whose license is not on the allow list of `deny.toml`, and read a project's license from its metadata before opening any of its files. It SHALL name keripy, under Apache-2.0, as the reference whose test cases are copied verbatim with their source file and keripy commit recorded.

**Example:** an agent looking for how another implementation encodes a dual-indexed P-256 signature reads `cesr-rs` (MIT OR Apache-2.0) and keripy (Apache-2.0), and never opens `cesrox` (EUPL-1.2).

#### Scenario: The rule is in the crate's guidance
- **WHEN** `crates/kerita/CLAUDE.md` is read
- **THEN** it names keriox and its crates as never to be opened, ties every other project to the allow list of `deny.toml`, and names keripy as the reference to copy test cases from
