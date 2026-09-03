# Proposal: cells

## Why

Sharing on PDN is pairwise: a connection between two identities, and per-claim grants over it, each claim staying in its issuer's namespace and reaching the audience through filtered reconciliation from the issuer's own devices. The product's data model ([mia-ontologies](https://github.com/MeeFoundation/mia-ontologies)) is built on **cells** — private collaboration spaces of 0..n members whose content stays alive for every member, with the relationship between two people modelled as a cell of two — and a group has nothing to stand on today: a newcomer cannot get in without pairing with every member, nobody relays an author's content while the author is offline, and there is no space several people write into. This change adds the cell as a platform primitive. It records the decisions the team has taken and lists, deliberately and at length, the questions still open, so that the product's data model and the platform meet on one definition before either side builds on the other.

## What Changes

- **A new primitive, the cell.** A space shared by 0..n members, identified by a cell id that carries no key material — a cell signs nothing, issues nothing and proves nothing; every act inside it is a member's act. One cell is one pdn-store replica, the **cell store**, held whole by every device of every member.
- **No connection between members.** Membership rests on the cell alone: a member joins on the invitation of one member and sees everyone; connections between members are neither required nor created.
- **Records, of two kinds.** A cell's content is **records**. A **claim** — an assertion by an issuer about a subject: a driver's license, a parent's statement of a child's blood type — is a record that is immutable and, inside a cell, readable by every member and written only by its issuer. A **document** — content that is edited: a jointly written markdown note — is a record shared with the whole cell read-only or read-write, and a document's mode flips over its life. There is no narrower audience inside a cell.
- **Whole-replica sync among members.** Member devices form the cell store's swarm and replicate it whole: capability-filtered reconciliation (subset-rbsr) does not run inside a cell, and any member device catches up from any other. The ingest gate judges a cell-store entry by its author, not by the session peer, because members relay each other's entries.
- **Membership with owners.** Any member invites; any member removes a member that is no owner, itself included; an owner is removed only by another owner. A cell has owners: the creator is the first owner, an owner makes any member an owner, and only another owner takes ownership from a member. Owners are the cell's repair channel — an owner deletes any member's record. Joining follows the shape of the linking ceremony (ADR-0012): a one-time secret verified and burned before any state changes, and no bearer material in the invitation.
- **Three standing invariants.** What may be done to a record does not depend on whether the member that placed it is a current member or a removed one. Every state a cell can reach is repairable by its owners, so no situation forces recreating the cell — a new store, re-invited members, re-uploaded content. And authorship is forged by no one: no power, ownership included, writes content under another member's name.
- **A human-readable name that is not an address.** A cell carries a name — a string that can repeat, including among one identity's cells; several cells with the same members are ordinary.
- **Nothing existing changes.** Connections, grants, per-issuer namespaces and their egress filter keep their requirements. How they relate to cells — whether a connection is a cell of two, whether grants gain the cell as an audience — is an open question this change names and does not answer.
- **Open questions are recorded, not resolved.** The design lists them, grouped and with their options; the ones that block implementation are the first task group, and implementation does not start before they are answered.

## Capabilities

| Capability (delta) | Archive destination |
| --- | --- |
| `data-layer-cell-store` | `openspec/specs/components/data-layer/cell-store.md` |
| `pdn-node-cells` | `openspec/specs/components/pdn-node/cells.md` |
| `data-layer-capability-gated-ingest` | `openspec/specs/components/data-layer/capability-gated-ingest.md` |
| `data-layer-subset-reconciliation` | `openspec/specs/components/data-layer/subset-reconciliation.md` |

### New Capabilities

- `data-layer-cell-store`: the cell's replica — one per cell, identified by a keyless cell id, replicated whole among the devices of its members and served to member devices only, its entries admitted by authorship (a claim from its issuer, a document per its mode), its swarm the members' devices.
- `pdn-node-cells`: the cells service — creating a cell for a hosted identity, inviting and joining under a one-time secret, ownership (the creator the first owner, owners making and unmaking owners), reaching a member's other devices through the identity's directory, removing and leaving, writing records — claims and documents — and recovering hosted cells across a restart.

### Modified Capabilities

- `data-layer-capability-gated-ingest`: the gate arms on cell stores too, judging by the entry's author resolved to a member rather than by the session peer.
- `data-layer-subset-reconciliation`: the unfiltered-session rule and the swarm-composition rule extend to the member devices of a cell store; the import refusal for tracked non-data replicas names cell stores.

## Impact

- **`crates/pdn-types`**: a `CellId` byte identifier.
- **`crates/data-layer`**: the cell store as a replica kind beside the directory, the data store and the connection metadata store — creation, import from a ticket, forgetting; classification of member devices; the authorship policy in the ingest gate; swarm membership on import; contact derivation from member device records; a download policy for payloads.
- **`crates/pdn-node`**: the cells service; the join dialogue on its own ALPN; the ownership surface; the directory kinds that carry a cell to a member's other devices; restart recovery of hosted cells; the join and removal paths under the flaky-test discipline.
- **`crates/pdn-layer`**: the vocabulary — the record and its two kinds, claim and document, their envelope, the mapping onto mia-ontologies' graphs and cell DataBooks.
- **`crates/pdn-store`**: no change — the swarm, the content-free topic and the ingest hook are used as they are. The linear-scan range fingerprint (`get_fingerprint` in `store/fs.rs`) is a cost the cell store makes visible; it is among the open questions, not in this change.
- **Specs**: a glossary entry `architecture/language/cell.md`; the terms claim and document reconciled with mia-ontologies' graph and DataBook; a sweep of specs that describe connections as the only sharing path.
- **Depends on**: ADR-0011 and ADR-0012 for the shape of the join dialogue; multi-identity hosting; the classifier's device resolution. Nothing pending.
