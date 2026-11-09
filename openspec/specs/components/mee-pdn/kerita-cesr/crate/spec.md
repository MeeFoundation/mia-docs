# Kerita CESR crate

## Purpose

The [CESR](https://trustoverip.github.io/kswg-cesr-specification/) 2.00 primitives [kerita](../../kerita/crate/spec.md) reads, as a crate of their own, `kerita-cesr`: what it depends on and what it never does, the license it carries, and what it took from whom. Like kerita, it is usable on its own, outside the platform, within its subset. What it reads and writes is in the [primitives](../primitives/spec.md) spec; it is held to keripy by the corpus the [kerita conformance](../../kerita/conformance/spec.md) spec describes.

## Requirements

### Requirement: The crate is a leaf of the workspace
The crate SHALL be a member of the workspace at `crates/kerita-cesr`, named `kerita-cesr`, and SHALL depend on no other crate of the workspace. Its product build SHALL depend on no async runtime, no network crate and no storage crate, and on no crate whose job is to draw randomness or read the system clock. It SHALL build for every target the workspace builds for, the mobile targets included.

**Example:** what the product build's dependency tree may and may not hold.

| dependency | in the product build |
|---|---|
| `p256` 0.14, `ed25519-dalek` 3, `blake3` | yes |
| `kerita`, `pdn-types` | no |
| `tokio`, `getrandom`, `chrono` | no |

#### Scenario: The dependency tree names no workspace crate
- **WHEN** the dependency tree of `kerita-cesr`'s product build is listed, as part of kerita's
- **THEN** it holds no other crate of the workspace, no async runtime, no network or storage crate and no source of randomness or of the clock

### Requirement: The crate holds no secret key
No public item of the crate's product build SHALL take, hold or return a secret key: the crate verifies signatures and makes none. A key that signs in tests SHALL be reachable only from the crate's tests.

**Example:** upstream `cesr-rs` generates key pairs, signs and stretches seeds; the fork drops all of it, and the seed codes that stay in its code tables are outside the subset, so `Primitive::read` answers a seed such as an Ed25519 seed under code `A` as unsupported.

#### Scenario: No public item takes a secret key
- **WHEN** the public items of the crate's product build are listed
- **THEN** none of them takes, holds or returns a secret key

### Requirement: The crate carries its license and its provenance
The crate SHALL be licensed Apache-2.0 and SHALL carry a `LICENSE` file. Its `NOTICE` SHALL name `cesr-rs` from devrandom-labs, under MIT OR Apache-2.0, as the source of the CESR primitives forked from it and of the vectors taken from its corpora, and keripy, under Apache-2.0, as the source of the test cases copied from it. `UPSTREAM.md` SHALL name the commit of `cesr-rs` the fork was taken from and SHALL list every divergence of the fork from that commit.

**Example:** what the crate's provenance files hold.

| file | holds |
|---|---|
| `NOTICE` | `cesr-rs`, Joel DSouza, MIT OR Apache-2.0: CESR primitives and corpus vectors; keripy, WebOfTrust, Apache-2.0: test cases |
| `UPSTREAM.md` | the `cesr-rs` commit taken, `3a02703ab892325b149bf4a477c5209191f12386`; the move to `p256` 0.14 and `ed25519-dalek` 3; the refusal of non-zero pad bits |

#### Scenario: The notice names both sources
- **WHEN** the crate's `NOTICE` is read
- **THEN** it names `cesr-rs` and keripy, each with its license and what the crate took from it

#### Scenario: The fork names its upstream commit
- **WHEN** `UPSTREAM.md` is read
- **THEN** it names one commit of `cesr-rs` and lists the fork's divergences from it

### Requirement: The crate's guidance carries the clean-room rule
The crate's `CLAUDE.md` SHALL state the rule every agent and model working in the crate follows: never open, fetch, search or quote the source, tests or docs of keriox — THCLab's keri-core, keri-controller, keri-sdk, cesrox and teliox — or of any project whose license is not on the allow list of `deny.toml`, and read a project's license from its metadata before opening any of its files. It SHALL name keripy, under Apache-2.0, as the reference whose test cases are copied verbatim with their source file and keripy commit recorded.

**Example:** an agent looking for how another implementation encodes a P-256 key under code `1AAJ` reads `cesr-rs` (MIT OR Apache-2.0) and keripy (Apache-2.0), and never opens `cesrox` (EUPL-1.2).

#### Scenario: The rule is in the crate's guidance
- **WHEN** `crates/kerita-cesr/CLAUDE.md` is read
- **THEN** it names keriox and its crates as never to be opened, ties every other project to the allow list of `deny.toml`, and names keripy as the reference to copy test cases from
