## MODIFIED Requirements

### Requirement: A pod store holds whatever a session it serves carries

Either store of a pod SHALL hold every entry a session carries from a caller it serves — a member device's session whole, a former member's over its departure's past, and, on a replica whose own identity departed, a member device's over what the requirement on a departed member's tombstone lets that replica take — and SHALL drop only what pdn-store drops on its own: a key over 8,192 bytes, a timestamp more than 10 minutes ahead, an entry whose signature does not verify, an entry whose hash and length disagree on whether it is empty. Outside a dial toward a callee the store serves nothing and a replica whose own identity departed, no entry SHALL be judged at ingest by its author, its key or the membership, and no entry SHALL wait at ingest. What an entry counts for SHALL follow from the whole set of entries a device holds, whatever order they arrived in: the membership view counts an event, and the record view reads a record's entry, by the rules the requirements below state, and an entry whose payload or whose dependencies have not arrived counts once they have. Every member device then holds the same entries, and a forged entry is held and relayed by every member device and counts on none. A dial toward a callee the store serves nothing SHALL take from it only the entries a device of a current member signed — a device the counted statements of a member the membership view counts list — and the device statements of the current member the callee names, whose member's signature the membership view checks whoever authored the entry, and SHALL take everything while the membership view counts no member or lists no device of the current member the callee names, as while a newcomer's first entries and the payloads of its statements are on their way; a replica whose own identity departed SHALL take nothing from such a callee. A callee the store does not serve vouches for nobody, while a current member's signature makes the same entry whichever node relays it.

**Example:** Bob's modified phone b1, Bob being a plain member of "Family", carries into a session with Carol's phone c1 Alice's claim, an entry of its own at that claim's key, and a promoted event for Bob it wrote; `<alice>`: 64 lowercase hex chars of Alice's `PdnId`; `<id>`: the claim's id.

| entry b1 carries | its author | on c1 |
|---|---|---|
| `by/<alice>/claim/<id>/1` | a1's | held, and read as Alice's claim |
| `by/<alice>/claim/<id>/1` | b1's | held, and read by nothing: Alice's claim reads unchanged |
| a promoted event in Bob's chain | b1's | held, and counted for nothing: Bob is no owner |
| a later session between c1 and b1 | | finds no difference |

**Example:** Bob's phone b1 dials, on the record store of "Family", devices it serves nothing, each serving the session whole: Dave's phone d1, which holds the store's ticket and no membership; Carol's modified phone c1, Carol having been removed; and a node answering as Alice that no statement of Alice lists. `<dave>`, `<carol>`: 64 lowercase hex chars of their `PdnId`s.

| entry the callee carries | its author | on b1 |
|---|---|---|
| Alice's claim, relayed by d1 | a1's | held, and read as Alice's claim |
| `by/<dave>/claim/<id>/1` | d1's | not taken |
| `by/<carol>/claim/<id>/1`, placed after Carol's removal | c1's | not taken |
| `by/<alice>/claim/<id>/1`, from the node answering as Alice | that node's | not taken |
| `member/<alice>/devices/1`, from the node answering as Alice | that node's | held, and counted for nothing: Alice did not sign it |

#### Scenario: A forged entry is held and counts for nothing

- **WHEN** a device of member B, no owner, carries into a session with a device of member C member A's claim, an entry of its own at that claim's key, and a promoted event for B
- **THEN** C's device holds all three, reads A's claim as A's and nothing of B's entry at its key, lists B as a plain member, and a later session between the two devices finds no difference

#### Scenario: A dial takes from a callee it serves nothing only what current members signed

- **WHEN** a member device dials a device it serves nothing — a removed member's, or that of a ticket holder that is no member — which serves the session whole and carries a current member's record beside a claim of its own
- **THEN** the dialing device holds and reads the current member's record and holds neither callee's own claim

#### Scenario: A device no statement lists passes its member's statement to a member pulling from it

- **WHEN** a device of member C whose node no statement lists holds C's statement listing it and a record of its own, and a device of member A dials it as C
- **THEN** A's device takes the statement and lists the device among C's, and takes its record in a session after that

#### Scenario: A node answering as a member no statement lists it for passes nothing it signed

- **WHEN** a member device dials, as a current member, a node no statement of that member lists, and that node carries an entry it signed under that member's name
- **THEN** the dialing device does not hold the entry

#### Scenario: Entries arriving in any order converge

- **WHEN** two member devices take the same entries of both stores — a newcomer's joined event, its device statement and its first claim among them — one in that order and the other in the reverse
- **THEN** both hold the same entries, list the same members and read the same records
