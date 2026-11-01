## ADDED Requirements

### Requirement: A record's payload is placed from a stream and read as one

The pods service SHALL place a claim or an immutable-document from a stream of its payload's pieces, in order, as `put_record` places one from a buffer: under the placing identity's name, at a fresh id, read back by every member as the bytes the stream yielded. The service SHALL check that the identity is a member before it reads the stream and again when it writes the entry, SHALL hold no lock of the runtime while it reads the stream, and SHALL write nothing for a stream that yields an error. The service SHALL also answer a reader of a claim's or an immutable-document's payload, read in order, for a member alone, answering no reader where `read` answers no value. No copy of the whole payload SHALL be held in memory on either path.

**Example:** Bob places a scan of 3 MiB in "Family" from 3 pieces of 1 MiB, and Alice reads it on her laptop in pieces of 64 KiB; Erin is hosted on Bob's phone and is no member.

| call | result |
|---|---|
| `put_record_streamed(Bob, Family, ImmutableDocument, 3 pieces)` | a `RecordRef` under Bob; `read` on Alice's laptop answers the 3,145,728 bytes |
| `read_streamed(Alice, Family, that record)` | a reader of length 3,145,728 answering 48 pieces and then an empty one |
| `put_record_streamed(Bob, Family, ImmutableDocument, 2 pieces and an error)` | an error; the pod lists what it listed before |
| `put_record_streamed(Erin, Family, ImmutableDocument, …)` | the unknown-pod error, the stream never read |
| `read_streamed(Erin, Family, the scan)` | the unknown-pod error |

#### Scenario: A streamed payload round-trips

- **WHEN** member B places an immutable-document from a stream of several pieces and member A reads it, whole and through a reader
- **THEN** A reads the bytes B's stream yielded, and the reader answers their length before the first piece

#### Scenario: A stream that fails places nothing

- **WHEN** member B places an immutable-document from a stream that yields an error after some pieces
- **THEN** the call fails and B's device lists the records it listed before

#### Scenario: A non-member's stream is not read

- **WHEN** a hosted identity that is no member of the pod places a record from a stream
- **THEN** the call fails with the unknown-pod error and the stream is never read

#### Scenario: A non-member opens no reader

- **WHEN** a hosted identity that is no member of the pod asks for a reader of one of its records
- **THEN** the call fails with the unknown-pod error

#### Scenario: A stream that waits holds up no other call

- **WHEN** member B's stream waits on its host, and B places a claim meanwhile
- **THEN** the claim is written while the stream still waits
