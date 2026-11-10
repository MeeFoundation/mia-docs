# CESR primitives

## Purpose

The CESR 2.00 primitives `kerita-cesr` reads and writes, in the text domain: keys, digests, plain and indexed signatures, numbers, tags, Base64 strings, count codes and the genus-version code, each read as keripy, the reference implementation, reads it, within the codes of the subset [kerita](../../kerita/encoding/spec.md) uses; every other code is refused as unsupported. Events, messages and the rules of KERI are kerita's.

## Requirements

### Requirement: A primitive of the subset reads as keripy reads it
The crate SHALL read a primitive or an indexed signature whose code is in the subset to the code, value and indices keripy reads it to, and SHALL write it back to its own text. It SHALL refuse as unsupported a primitive whose code keripy reads but the subset does not hold, and SHALL refuse a primitive keripy refuses, its refusal kept apart from unsupported.

**Example:** 4 primitives of the corpus.

| input | keripy | the crate |
|---|---|---|
| `1AAJAzab-oRBywLYIpK1zNIuih22BsBe0MgOEeNssEbQO86B` | P-256 key, code `1AAJ` | the same, written back as the same 48 characters |
| `2EAAACB43Hl4…` | P-256 signature, index 0, ondex 2 | the same |
| `1AABAg299p5IMvuw71HW…` | secp256k1 key, code `1AAB` | refused as unsupported |
| `AA_Z0jw5JCQwn2v7…` | refused: its pad bits are not zero | refused |

#### Scenario: A primitive of the subset reads to keripy's code and value
- **WHEN** a primitive or an indexed signature of the corpus whose code is in the subset is read
- **THEN** the crate reads it to keripy's code, value and indices, and writes it back to its own text

#### Scenario: A code outside the subset is unsupported
- **WHEN** a primitive whose code keripy reads but the subset does not hold is read
- **THEN** the crate refuses it as unsupported

#### Scenario: A primitive keripy refuses, the crate refuses
- **WHEN** a primitive keripy refuses is read, such as an indexed signature with non-zero pad bits
- **THEN** the crate refuses it, and not as unsupported

### Requirement: Count codes and the genus-version code read as keripy reads them
The crate SHALL read a count code of the subset, in its small form or its big one, to the code and the number of quadlets keripy reads it to, and SHALL refuse as unsupported a count code outside the subset. It SHALL read the genus-version code `-_AAA` to the CESR version its 3 digits name, apart from the count codes, since it carries a version and no length.

**Example:** 3 count codes of the corpus.

| input | keripy | the crate |
|---|---|---|
| `-KAW` | `-K`, 22 | controller signatures, 22 quadlets |
| `--CAABAA` | `--C`, 4096 | attachment group, 4,096 quadlets, read in its big form |
| `-_AAACAA` | `-_AAA`, count 8192 | the genus-version code naming CESR 2.00 |

#### Scenario: A count code reads as keripy reads it
- **WHEN** a count code of the corpus is read
- **THEN** the crate reads it to keripy's code and number of quadlets when it is in the subset, and refuses it as unsupported when it is not

#### Scenario: The genus-version code names its version
- **WHEN** `-_AAACAA` or `-_AAABAA` is read
- **THEN** the crate reads CESR 2.00 or CESR 1.00 respectively, and takes the code's 8 characters

### Requirement: A signature verifies under a key of its own algorithm
A signature SHALL verify only under a key whose algorithm is the signature's, over the exact bytes it signed. A P-256 signature SHALL verify with either of its S values, as keripy verifies it.

**Example:** one Ed25519 signature over the bytes `event`.

| checked under | over | verifies |
|---|---|---|
| its own key, code `D` | `event` | yes |
| its own key | `other` | no |
| a P-256 key, code `1AAJ` | `event` | no |

#### Scenario: A signature verifies under its own key alone
- **WHEN** an Ed25519 signature is checked under its own key over other bytes, or under a P-256 key over the bytes it signed
- **THEN** it does not verify, where it verifies under its own key over the bytes it signed

#### Scenario: A P-256 signature verifies with either S value
- **WHEN** a P-256 signature is checked with its high S value in place of its low one
- **THEN** it verifies
