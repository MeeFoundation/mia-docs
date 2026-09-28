# Proposal: cells

## Why

Several people need one space they all write into: its content stays with every member whether or not its author is online, and a newcomer enters it on one member's invitation. This change adds that space as a platform primitive — the **cell**, a private space of 0..n members, the relationship between two people being a cell of two — and records the decisions the team has taken.

**Example:** Alice, Bob and Carol keep one shopping list; Alice writes it on her phone a1 and a1 goes offline, and Dave then joins on Bob's invitation. Bob's phone is b1.

| | connections and grants | a cell |
|---|---|---|
| where the list sits | Alice's namespace, under a grant to Bob and one to Carol, each on a connection of its own | the cell's record store, under Alice's name, held whole by every member device |
| Carol, who last synced before the write, catches up while every device of Alice is offline | from nobody: b1 holds the list under Alice's grant and serves it to Bob's own devices alone | from b1, which serves every member device |
| Dave joins | pairs with Alice and waits for her grant on the list, neither possible until a1 is back online | presents Bob's invite once, and his first session, with b1, brings the list with the rest of the cell |

## What Changes

- **A new primitive, the cell.** A space shared by 0..n members, identified by a cell id that carries no key material: the id is derived from its creator's announcement key and a random nonce, so every device checks the root of membership against the id it holds. A cell signs nothing, issues nothing and proves nothing; every act inside it is a member's act. One cell is two stores — the **membership store**, holding who is a member, with what role, on which devices, and the **record store**, holding the records — each held whole, as a replica of its own, by every member identity on every device that hosts it: a node hosting two members holds the cell twice (ADR-0013).
- **No connection between members.** Membership rests on the cell alone: a member joins on the invitation of one member and sees everyone; connections between members are neither required nor created.
- **Records, of three kinds.** A cell's content is **records**, each readable by every member; there is no narrower audience inside a cell and no sharing mode per record, neither "shared read-only" nor "shared read-write". A **claim** — an assertion by an issuer about a subject: a driver's license, a parent's statement of a child's blood type — is immutable and written only by its issuer. A **mergeable-document** — a markdown note — is edited: its edits are operations, appended by any member under the writer's own signature; this change stores, admits and reconciles the operations and hands them back with their writers, and merging them into one document is outside it. An **immutable-document** — a file — is placed once and updated by no one.
- **Whole-replica sync among members, membership first.** Member devices form both stores' swarms, replicate them whole and hold the write ticket of each: capability-filtered reconciliation (subset-rbsr) never runs inside a cell, a session reconciles the membership store to convergence before the record store, and any member device catches up from any other. A session names the member whose replica it addresses and the member its caller acts as; a sibling device is looked up in its identity's own directory, another member's device in that member's device statements, and two members hosted on one node sync inside the process. Write authority is the ingest gate's, judged per entry by its author's membership state at the membership sequence the entry names — the same verdict on every device whenever the entry arrives — not by the session peer, because members relay each other's entries, and not by the ticket.
- **Membership with owners.** Any member invites, and a newcomer joins as a plain member; an owner kicks any other member, an owner or not, and leaving stays every member's own. A cell has two roles, owner and member: the creator is the first owner, an owner promotes any member to owner, and only another owner demotes an owner. A member that joins again is a plain member until an owner promotes it anew. A plain member reads everything and edits every mergeable-document; an owner's powers are the acts on membership and the cell's name. Joining follows the shape of the linking ceremony (ADR-0012): a one-time secret verified and burned before any state changes, and no bearer material in the invitation; between two identities of one node it runs inside the process.
- **Three invariants.** What may be done to a record does not depend on whether the member that placed it is a current member or one that left or was kicked. Every membership state a cell can reach is repairable by its owners, so no situation of membership forces recreating the cell — a new store, re-invited members, re-uploaded content. And authorship is forged by no one: every entry carries its writer's signature, so an edit of another member's mergeable-document reads as the editor's act, never as the member's.
- **A member's own history is taken on its word.** Cells are needed early, for load testing, and the defence against a member's device that contradicts its own member's history — a demoted owner acting under the point it held as an owner, a departed member writing under its old sequence, a rewrite of its own entries, two events of its own at one point — rests on anchored signatures over the platform's key event logs, which this change does without. Honest devices take such entries as they come, no test covers these paths, and the fix they oblige is deferred and recorded in the design; what no state of the member's own ever allowed — a record under another member's name, an act naming a point at which its actor lacks the state the act needs — stays refused. The deferral ends before connections go.
- **A record placed stays.** No member and no owner deletes or replaces a record: content placed by mistake, a member's junk and a departed member's records stay for every member, and a corrected claim sits beside the old one. The store beneath stays as it is.
- **A human-readable name that is not an address.** A cell carries a name — a string that can repeat, including among one identity's cells; an owner renames it. Several cells with the same members are ordinary.
- **Nothing existing changes its behaviour.** Connections, grants, per-issuer namespaces and their egress filter keep their requirements. Cells stand beside them and rest on none of them: no grant names a cell, and cell content never flows through a grant. Once cells prove themselves in practice, the mobile application's integration included, connections go entirely, with the machinery that serves only them.
- **Chat is a later change.** A cell will carry a chat; this change does not build it, and it is not expected to sit on the store's reconciliation — a stream of messages is a sync shape of its own.

## Capabilities

| Capability (delta)                                      | Archive destination                                                            |
| ------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `components/mee-pdn/data-layer/cell-store`              | `openspec/specs/components/mee-pdn/data-layer/cell-store/spec.md`              |
| `components/mee-pdn/pdn-node/cells`                     | `openspec/specs/components/mee-pdn/pdn-node/cells/spec.md`                     |
| `components/mee-pdn/data-layer/capability-gated-ingest` | `openspec/specs/components/mee-pdn/data-layer/capability-gated-ingest/spec.md` |
| `components/mee-pdn/data-layer/subset-reconciliation`   | `openspec/specs/components/mee-pdn/data-layer/subset-reconciliation/spec.md`   |
| `components/mee-pdn/data-layer/private-metadata-store`  | `openspec/specs/components/mee-pdn/data-layer/private-metadata-store/spec.md`  |
| `components/mee-pdn/pdn-node-http/host`                 | `openspec/specs/components/mee-pdn/pdn-node-http/host/spec.md`                 |
| `components/mee-pdn/pdn-node-http/container-stand`      | `openspec/specs/components/mee-pdn/pdn-node-http/container-stand/spec.md`      |

### New Capabilities

- `components/mee-pdn/data-layer/cell-store`: the cell's two stores — the membership store and the record store, identified by a keyless cell id, held as replicas of their own by every member identity and replicated whole among the devices of its members, the membership store first, served to member devices only by the member a session names, their write tickets held by every member device, the record store's entries admitted by authorship (a claim or an immutable-document from the member under whose name it sits, a mergeable-document's operation from any member), its swarm the members' devices.
- `components/mee-pdn/pdn-node/cells`: the cells service — creating a cell for a hosted identity, inviting and joining under a one-time secret, ownership (the creator the first owner, owners promoting members and demoting other owners), reaching a member's other devices through the identity's directory, kicking and leaving, writing records — claims, mergeable-documents and immutable-documents — and recovering hosted cells across a restart.

### Modified Capabilities

- `components/mee-pdn/data-layer/capability-gated-ingest`: the gate arms on a cell's two stores too, judging by the entry's author resolved to a member rather than by the session peer.
- `components/mee-pdn/data-layer/subset-reconciliation`: the unfiltered-session rule and the swarm-composition rule extend to the member devices of a cell's stores; the import refusal for tracked non-data replicas names them.
- `components/mee-pdn/data-layer/private-metadata-store`: the directory publishes a cell's two write tickets under per-cell kinds, keeps a record per cell and membership event of the identity, keyed by its sequence, that a leave tombstones, and holds the identity's announcement key pair at a fixed path, minted with the identity.
- `components/mee-pdn/pdn-node-http/host`: the debug surface covers the cells service, one route per operation, with its refusals reported as refusals.
- `components/mee-pdn/pdn-node-http/container-stand`: the stand runs a cell across three containers with its paired denials, a kick and a restart.

## Impact

- **`crates/pdn-types`**: a `CellId` byte identifier.
- **`crates/data-layer`**: the membership store and the record store as replica kinds beside the directory, the data store and the connection metadata store — creation, import from their tickets and forgetting, each for a named hosted identity, the session order between them; classification of a caller by the member it names — a sibling in the identity's own directory, another member in its device statements (D32); the authorship policy in the ingest gate; swarm membership on import; contact derivation from member device records; payloads fetched with their entries, as the store fetches them by default; entries outside the key layout kept, used by nothing and listed (D27).
- **`crates/pdn-node`**: the cells service; the join dialogue on its own ALPN, generic over its streams and run inside the process between two identities of one node; the ownership surface; the directory kinds that carry a cell to a member's other devices; restart recovery of hosted cells; the join and kick paths under the flaky-test discipline.
- **`crates/pdn-layer`**: the vocabulary — the record and its three kinds, claim, mergeable-document and immutable-document and their envelope.
- **`crates/pdn-node-http`**: debug routes for every operation of the cells service (D31); the stand's three-container cell scenario.
- **`crates/pdn-store`**: no change; the swarm, the content-free topic and the ingest hook are used as they are. The linear-scan range fingerprint (`get_fingerprint` in `store/fs.rs`) is a cost the record store makes visible, which load tests measure.
- **Specs**: a glossary entry `architecture/language/cell.md`; a sweep of specs that describe connections as the only sharing path.
- **Depends on**: ADR-0011 and ADR-0012 for the shape of the join dialogue; multi-identity hosting; ADR-0013 and the identity-scoped replicas it specifies — a replica, an author and sessions per hosted identity, the identities named on every session, the in-process path between two identities of one node. Nothing pending.

