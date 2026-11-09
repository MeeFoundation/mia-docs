# Kerita encoding

## Purpose

How kerita reads and writes key events: one protocol version, one body and one domain, the codes within the subset [ADR-0017](../../../../architecture/adr/0017-keri-identity-layer.md) uses, a parse that is bounded before it reads, and an event that comes back as the bytes it was read from. Each primitive in an event is read by [kerita-cesr](../../kerita-cesr/primitives/spec.md); this spec says which an event of the subset may carry.

## Requirements

### Requirement: Events are KERI 2.00 in the native CESR body, in the text domain
The crate SHALL read and write key events of KERI protocol version 2.00 whose body is the native CESR fixed-field body under CESR genus version 2.00, in the text domain. It SHALL refuse every other event as unsupported — another protocol version, another body kind, a version field without a genus version, the binary domain — and SHALL keep that refusal apart from the refusal of an event that is malformed. A message MAY follow the genus-version code a stream carries to name the CESR version of what follows it: the crate SHALL read past one naming CESR 2.00, `-_AAACAA`, and SHALL refuse as unsupported one naming another version, and a second code right after the first, as keripy reads nothing past either.

**Example:** one inception, as 4 producers write it.

| input begins with | written by | outcome |
|---|---|---|
| `-FAu0OKERICAACAAXicpENcf5ii15MsVCx7wxKi4muIodYJULhkOaEbvbz4cF3d4…` | keripy, main line: KERI 2.00, native, genus 2.00 | read |
| `{"v":"KERICAACAAJSONAADR.","t":"icp","d":"EM47RHHi7oA__srCr3tgfzdsz9_O_ahatXmvl0IrfwFk",…` | keripy, main line: KERI 2.00, JSON body | refused as unsupported |
| `{"v":"KERI10JSON0000cf_","t":"icp","d":"EF6LmlLkfoNVY25RcGTsqKLW5uHq36FbnNEd…` | keripy: KERI 1.0, JSON body | refused as unsupported |
| `-FAtYKERICAAXicpEEx4oxGYbNrd6nZsdGu2KdN4MSDGD5IWS7hXjST7r8ewDG9X…` | keripy 1.3.6: native, version field without a genus version | refused as unsupported |
| `-_AAACAA-FAu0OKERICAACAAXicp…` | a stream naming CESR 2.00 before the event | read, the code's 8 characters counted in what the message took |
| `-_AAABAA-FAu0OKERICAACAAXicp…` | a stream naming CESR 1.00 before the event | refused as unsupported |

#### Scenario: A KERI 2.00 native event is read
- **WHEN** the crate is given an inception keripy's main line wrote in KERI 2.00, native CESR, genus 2.00
- **THEN** it reads the event's fields

#### Scenario: A message after the genus-version code of CESR 2.00 is read
- **WHEN** a stream carries `-_AAACAA` before its first message or between 2 messages
- **THEN** the crate reads the message after it

#### Scenario: A genus-version code of another version is refused as unsupported
- **WHEN** a stream carries a genus-version code naming CESR 1.00 or 2.01 before a message, or 2 genus-version codes in a row
- **THEN** the crate refuses the message as unsupported and reads nothing past it

#### Scenario: A KERI 1.0 event is refused as unsupported
- **WHEN** the crate is given an event whose version string names KERI 1.0
- **THEN** it refuses the event as unsupported, not as malformed

#### Scenario: A JSON body is refused as unsupported
- **WHEN** the crate is given a KERI 2.00 event with a JSON, CBOR or MGPK body
- **THEN** it refuses the event as unsupported

#### Scenario: A version field without a genus version is refused as unsupported
- **WHEN** the crate is given a native event as keripy 1.3.6 writes it, its version field carrying no genus version
- **THEN** it refuses the event as unsupported

#### Scenario: A broken native event is refused as malformed
- **WHEN** the crate is given a KERI 2.00 native event cut short in the middle of its key list
- **THEN** it refuses the event as malformed, not as unsupported

### Requirement: The crate reads and writes the events, attachments and algorithms of the subset alone
The crate SHALL read and write the events `icp`, `rot`, `ixn`, `dip`, `drt` and `rct`, and the attachments they carry in the subset: the controller's indexed signatures, the [witnesses](../../../../architecture/language/witness.md)' indexed signatures, non-transferable [receipt](../../../../architecture/language/receipt.md) couples, and the seal source couple that names a delegator's approving event. The seals SHALL be the [digest seal](../../../../architecture/language/digest-seal.md) and the [key event seal](../../../../architecture/language/key-event-seal.md). The key types SHALL be Ed25519 and P-256 (ECDSA over secp256r1), transferable and non-transferable, with their signatures in plain, indexed and dual-indexed form, and the one digest SHALL be Blake3-256. Every other event type, attachment, seal, key type, signature type and digest type SHALL be refused as unsupported.

**Example:** codes the crate meets in a [KEL](../../../../architecture/language/kel.md), and what it does with each.

| code | meaning | outcome |
|---|---|---|
| `D` | Ed25519 key, transferable | read |
| `1AAJ` | P-256 key, transferable, 48 characters | read |
| `1AAI` | P-256 key, non-transferable | read |
| `E` in a signature group | P-256 signature, same index in both key lists | read |
| `2E` | P-256 signature, dual-indexed | read |
| `E` as a digest | Blake3-256 | read |
| `1AAB` | secp256k1 key | refused as unsupported |
| `I` as a digest | SHA2-256 | refused as unsupported |
| `0A` | Ed448 indexed signature | refused as unsupported |

#### Scenario: A P-256 dual-indexed signature is read
- **WHEN** a rotation carries a P-256 signature whose index in the new key list differs from its index in the prior next-key list
- **THEN** the crate reads both indices

#### Scenario: A secp256k1 key is refused as unsupported
- **WHEN** an inception lists a secp256k1 key
- **THEN** the crate refuses the event as unsupported

#### Scenario: A digest other than Blake3-256 is refused as unsupported
- **WHEN** an event's SAID is a SHA2-256 digest
- **THEN** the crate refuses the event as unsupported

### Requirement: A parse is bounded before it reads
The crate SHALL take the limits on what it reads from its caller, and SHALL check every group's declared size against them before reading any of the group's content. A group declared larger than a limit, or larger than the bytes present, SHALL be refused without its content being read. The bytes past an event or a message SHALL not be read: a caller's buffer may hold the next message, or bytes that are no text at all.

**Example:** a key list declared by a modified node, against a caller's limit of 32 P-256 keys of 12 quadlets each, 384 quadlets.

| key list begins with | declared size | outcome |
|---|---|---|
| `-JAL` | 11 quadlets, 44 characters: one Ed25519 key | read |
| `-JF_` | 383 quadlets | read |
| `-J__` | 4,095 quadlets, 16,380 characters | refused after its 4 characters |

#### Scenario: An oversized group is refused before its content is read
- **WHEN** a key list declares a size above the caller's limit
- **THEN** the crate refuses the event having read only the list's count code

#### Scenario: A group larger than the bytes present is refused
- **WHEN** a group declares more quadlets than the input holds
- **THEN** the crate refuses the event as malformed without reading past the input's end

#### Scenario: Bytes past a message are not read
- **WHEN** a message, with attachments or without, is followed in its buffer by bytes that are no text
- **THEN** the crate reads the message and answers how many bytes it took

### Requirement: An event round-trips to the bytes it was read from, and its SAID is checked
An event the crate reads SHALL encode back to the same bytes, and an event whose text differs from what the crate writes for its fields SHALL be refused, as keripy refuses it: a number under a longer code than it needs, a group under the big count code where the small one holds it, seals split into groups where one holds them, a weight not reduced. The crate SHALL refuse an event whose SAID field is not the digest of its body computed as KERI 2.00 computes it, and an inception or delegated inception whose self-addressing prefix is not that SAID. An event the crate builds SHALL read back as itself: a draft carrying a field its event type does not carry SHALL be refused, and so SHALL a draft of a receipt, which names no event to receipt.

**Example:** the inception keripy's test reads and writes, and the same event with one character of its SAID changed.

| input | outcome |
|---|---|
| `-FAu0OKERICAACAAXicpENcf5ii15MsVCx7wxKi4muIodYJULhkOaEbvbz4cF3d4…`, 188 bytes | read, and written back as the same 188 bytes |
| the same, its SAID `ENcf5ii15MsVCx7wxKi4muIodYJULhkOaEbvbz4cF3d4` changed to `ENcf5ii15MsVCx7wxKi4muIodYJULhkOaEbvbz4cF3d5` | refused: the SAID is not the body's digest |
| the same, its sequence number 0 written `0HAAAAAA` where keripy writes `MAAA`, its body length and SAID made to fit | refused: not as keripy writes it |

#### Scenario: A read event writes back to the same bytes
- **WHEN** an event of the corpus is read and written back
- **THEN** the bytes written equal the bytes read

#### Scenario: A wrong SAID is refused
- **WHEN** an event's SAID field differs from the digest of its body
- **THEN** the crate refuses the event

#### Scenario: A self-addressing prefix that is not the SAID is refused
- **WHEN** a delegated inception's prefix differs from its SAID
- **THEN** the crate refuses the event

#### Scenario: An event not as keripy writes it is refused
- **WHEN** an event carries a number under a longer code than it needs, a list under the big count code, its seals split into 2 groups or a weight of 2/4, its SAID computed over that text
- **THEN** the crate refuses it

#### Scenario: A built event reads back as itself
- **WHEN** the crate builds an event of any type from a draft holding that type's fields
- **THEN** the event's text reads back as the same event

#### Scenario: A draft field the event type does not carry is refused
- **WHEN** a draft for an event type carries a field that type does not carry, such as a delegator for an inception or keys for an interaction event, or drafts a receipt
- **THEN** the crate refuses to build it
