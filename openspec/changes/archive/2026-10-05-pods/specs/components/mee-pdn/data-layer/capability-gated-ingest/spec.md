# data-layer: capability-gated ingest — delta for pods

## MODIFIED Requirements

### Requirement: Own devices and unarmed replicas are not narrowed

A session peer resolving as a device of the issuer SHALL be admitted in full. The gate SHALL arm on replicas data-bound to a hosted identity; on a hosted issuer's data replica it judges by the session peer's write admission, as above. A [pod](../../../../architecture/language/pod.md)'s two stores SHALL hold every entry a session they serve carries, judged at ingest by nothing beyond what pdn-store drops on its own, and SHALL leave what an entry counts for to the membership fold and the record view, as the [pod stores](../pod-store/spec.md) spec states: they judge a record-store entry by its author key, checked against the device statements of the member the entry's key names (pods D43), and by that member's membership state at the membership sequence the entry's key names (pods D22), never by the session peer — a member device relays other members' entries, so the peer that sends an entry is not its author — reading a claim or an immutable-document from a device of the member under whose name it sits and a mergeable-document's operation from any member's device; and they judge the membership material as that spec states: a device-list statement by the signature embedded in it, against the member's announcement key, with the entry's author ignored; a promoted event by its actor being an owner at the actor's sequence the key names, a removed or demoted event by its actor being an owner there and not the subject, a joined event by its actor being a member there and not the subject and by its join statement, valid under an announcement key that derives the subject's `PdnId`, a left event by its actor being the subject, the created event by deriving the pod id and carrying a valid signature under the announcement key it names, which derives the creator's `PdnId` (pods D23, D25, D41, D44). Directories and connection metadata stores keep ticket-bounded admission (Invariants 1 and 3), and a grantee-held replica of a foreign namespace admits what the serving side's egress delivers. Retraction markers SHALL be consulted on data replicas only, the only replicas whose entries a marker can name, so no state of the marker set can reach the stores that carry device records and grants, nor a pod's stores.

**Example:** entries Bob's phone b1 sends Carol's phone c1 in the stores of "Family"; Alice's phone is a1, and Bob's laptop b2 was just linked into him; `<alice>`, `<bob>`: 64 lowercase hex chars of each `PdnId`; `<id>`: the id of Alice's claim.

| entry | its author | c1 reads it by | on c1 |
|---|---|---|---|
| Alice's claim at `by/<alice>/claim/<id>/1` | a1's | the author, Alice's device, a member at her sequence 1 | held, and read as Alice's claim |
| another entry at that key | b1's | the author, Bob's device, not Alice's | held, and read by nothing, b1 learning nothing |
| Bob's device statement `member/<bob>/devices/2` | b2's | the embedded signature under Bob's announcement key; the author ignored | held, and counted once its payload arrives and verifies |
| any state of the retraction markers in Carol's directory | — | nothing: markers are consulted on data replicas only | no effect on either store |

#### Scenario: Device replication is unaffected

- **WHEN** two devices of the issuer's identity reconcile its data namespace
- **THEN** every entry replicates between them, exactly as without the gate

#### Scenario: A sibling relay of the read slice is not write-gated

- **WHEN** a device of the audience identity catches up a granted replica from a sibling device holding read-only claims
- **THEN** the read-slice entries arrive, although the relaying sibling holds no write on them

#### Scenario: A relayed record-store entry is judged by its author

- **WHEN** a device of pod member C receives from a device of member B two entries under A's claims — one authored by a device of A, one authored by B's device
- **THEN** C's device holds both, reads the first as A's claim and nothing of the second, the session peer being B for both
