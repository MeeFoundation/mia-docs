# Tasks: cells

Scope: the cell as a platform primitive — a keyless id, one cell store replicated whole among member devices, authorship-judged admission, equal-rank membership joined under a one-time secret, claims and documents as content. Nothing existing changes shape. Group 0 is the gate: the design's blocking open questions are answered and recorded before any implementation task starts.

## 0. Decisions before implementation (design, Open Questions marked blocking)

- [ ] 0.1 A1 — the form of the cell id: random bytes or the hash of a founding record; and A2, its form at the app boundary
- [ ] 0.2 B1 — where membership lives, and who writes a device's record into the cell
- [ ] 0.3 B4 — the join path: a dedicated ALPN dialogue, an invite record over an existing channel, or both
- [ ] 0.4 C2 — claims and graph versions: one claim per edit with a head, or graphs as documents; history retained or head only
- [ ] 0.5 C5 — documents under concurrency: whole value under last-writer-wins, or an operation log merged above the platform
- [ ] 0.6 C7 — deletion on cell stores: the tombstone surface a cell needs
- [ ] 0.7 Record the answers as design decisions D16 and following, and rewrite the affected scenarios in the specs before implementation starts

## 1. Vocabulary and types

- [ ] 1.1 `CellId` in `pdn-types`, in the byte-id family of `PdnId`
- [ ] 1.2 Glossary entry `architecture/language/cell.md`, covering the cell, the record with its two kinds, and the owner role; the platform's claim and document mapped onto mia-ontologies' graph and DataBook (C1), linked from the specs' first use
- [ ] 1.3 `pdn-layer`: the record kinds — claim, document with its mode — and the key layout of a cell store per the answers to C2, C4 and C5

## 2. data-layer: the cell store

- [ ] 2.1 The cell store as a replica kind: create, import from its write ticket, forget — registered by cell id, with the unknown-cell error distinguishable from transport and storage failures
- [ ] 2.2 Membership material per B1: member and device records, the author-key-to-member binding, and the classification of a caller as a member device — every other caller refused as for an unhosted replica, ticket holders included
- [ ] 2.3 The authorship policy in the ingest gate: a claim from a device of its issuer, a document per its mode, everything else dropped silently; the verdict on the entry's author, never on the session peer
- [ ] 2.4 Swarm membership on create and import; tracked contacts derived from the member device records and replaced wholesale on each derivation; the download policy per D5'
- [ ] 2.5 Removal: sessions refused and the removed member's authors dropped from the first session set up after the removal record arrives; what was delivered is retained

## 3. pdn-node: the cells service

- [ ] 3.1 `create`, `list`, `members`, the name carried with the cell and never used as an address
- [ ] 3.2 The invite and join dialogue per B4: one-time short-lived secret, bearer-free payload, verify-and-burn before any state, uniform refusals, no state on refusal, the newcomer recorded as a plain member and handed the store's ticket, catch-up before the join returns
- [ ] 3.3 Writing a claim (immutable; a write addressed at an existing claim refused with a typed error) and a document with its mode; reading and listing by cell id
- [ ] 3.4 Remove and leave: the removal record; removal an owner-only act, its target an owner or a plain member alike; leaving forgets the store locally
- [ ] 3.5 A member's other devices: the cell's tickets in the identity's directory under a cell kind, opened on demand by the armer's sweep, the opening device registering itself into the cell's member device records
- [ ] 3.6 Restart recovery per G1: hosted cells re-hosted from durable state on a directory-configured runtime
- [ ] 3.7 Ownership: the creator recorded as the first owner; an owner makes a member an owner; ownership taken only by another owner; owners listed beside the members

## 4. Tests

- [ ] 4.1 Access-control pairs in one place each: a member device served whole beside a ticket holder that is no member refused, and a removed member refused from the next session; a claim from its issuer admitted beside another member's entry under those claims dropped; a read-write document written by another member beside a read-only one refused; a relayed entry admitted on its author's merit while the same peer's own forgery is dropped; an ownership grant by an owner taking effect beside the same act by a plain member refused; a member removed by an owner beside a plain member's removal attempt refused
- [ ] 4.2 Operating conditions: a node hosting a member and a non-member identity side by side; a second device linked before and after the join; a restart with a write made meanwhile; the author offline and the entry reaching a third member through a second; a concurrent add and remove of one member resolving per B3; a member leaving and rejoining; a document's mode flipped read-only to read-write and back; a member made an owner, unmade, and made again
- [ ] 4.3 Three identities with no connections sharing through one cell, and two cells with the same members keeping their entries apart
- [ ] 4.4 Stress pass on join, removal and relay scenarios (`--stress-count`, per the flaky-tests practice); every failure diagnosed in isolation before anything is built on top
- [ ] 4.5 Lints and the full suite (`just precommit-check`)

## 5. Docs and archive

- [ ] 5.1 Sweep the spec tree for text that describes connections as the only sharing path, and multi-identity's "later groups and organizations", and point them at cells
- [ ] 5.2 On archive: place the two new specs and the two deltas at their destinations; `openspec validate --all --strict`
