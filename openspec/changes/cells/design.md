# Design: cells

## Context

A PDN node hosts identities. Each identity has a private-metadata directory (its devices, its tickets, its connections records), a data namespace, and, per connection, a directional connection metadata store carrying grants. Sharing means a grant: the claim stays in its issuer's namespace and reaches the audience through capability-filtered reconciliation with the issuer's devices or the audience's own siblings, never through a third party. That model is pairwise by construction.

The product's data model — mia-ontologies, the Cellula app — organizes everything as cells: a folder holding one cell DataBook, a markdown note, files and a chat, nested in a per-user tree. Structured content lives in graphs (`g:SCGraph`), each with a subject and a claimant. A cell has a creator with no privileges, one or more members, a shared name and an origin category; sharing a cell gives every member a complete live copy; the relationship with one other person is a bare two-member cell. The app's authors expect cells to stay "well under 100" members.

This design records the decisions taken for the platform side of cells and the questions left open. It works from the team's working note on cells and from a reading of mia-ontologies on 28 August 2026.

## Goals / Non-Goals

**Goals:**

- A shared space for 0..n members with one definition on both sides — the platform and the product's data model.
- Everything a member writes reaches every member, from any member, with the author's authorship enforced on every honest device.
- Reuse: the swarm, the content-free topic, the ingest hook, the linking-shaped dialogue, multi-identity hosting, the directory as the carrier to a member's other devices. No change in pdn-store.
- Every unanswered question written down, with its options.

**Non-Goals:**

- Identity proof at join, signed claims, key rotation — the KERI roadmap.
- Identity-bound, revocable access — UWill.
- Content encryption — a separate layer; every member holds the plaintext by definition.
- Recall of delivered content — Invariant 2 governs acquisition, not retention.
- Answering the open questions below.

## Decisions

### D1. A cell has no key pair — only an identifier

The cell id is a 32-byte identifier minted at creation, in the same byte-id family as `PdnId`. A cell signs nothing: no grant is issued by a cell, no claim is issued by a cell, and no dialogue proves "this is cell X". Every act inside a cell is a member's act — signed by that member's device author key, and, with KERI, by the member's identity. Consequence: there is nothing to steal and nothing to rotate — a cell's security is its members' security — and the KERI roadmap needs no group identifier and no multi-signature key set built from members' keys.

Rejected: the cell as an identity with a key set (a multi-signature autonomic identifier). It buys a totally ordered membership log at the price of a group key to manage, a rotation on every membership change, and a second identity kind in the roadmap. Whether a group that speaks in its own name is needed is the separate question of organizations, which are issuers and do need keys.

### D2. No connections "each with each"

Membership rests on the cell: a member joins on one member's invitation and sees everyone. Rejected: a cell as a fan-out of pairwise connections — n×(n−1)/2 pairing ceremonies, adding a member is work for every existing member, and no relay: a member obtains another member's content only from that member's devices, since a grantee never re-serves a third party.

### D3. One cell is one pdn-store replica

The cell store. Not one replica for all cells, and not one replica per member inside a cell. ADR-0009's case against a shared namespace — a set that is never quiescent, and work spent on entries the filter discards — does not apply: every member wants every entry, and nothing is discarded. The replica is the authorization unit (who may sync it), the swarm topic and the reconciliation unit, exactly the roles ADR-0009 keeps for a namespace.

### D4. Content is records, of two kinds: claims and documents

A **record** is what a member places into a cell; claims and documents are the two kinds of record. A claim is an assertion by an issuer about a subject — in mia-ontologies a graph with a claimant and a subject, such as a `persona:DriversLicenseDocument`. A document is content that is edited — in mia-ontologies the cell's note and its files. The difference is in mutability and in who writes (D5, D6), not in payload format: payloads stay opaque below pdn-layer. Membership material — member records, device records, removal records — is the cell's bookkeeping, not a record in this sense.

### D5. Claims are immutable and, inside a cell, shared with every member

A claim does not change after it is written — a changed assertion is a new claim. Inside a cell there is no narrower audience: a claim placed in a cell is read by every member and written only by its issuer. "Share with Carol and Dave but not Bob" is a different cell (D9).

### D6. A document is shared read-only or read-write with the whole cell

The mode is chosen per document and is not fixed for life: a document's mode flips read-only to read-write and back — an operating condition, not an edge case. There is no "only Carol writes". The enforcing mechanism is the ingest gate on every honest member device, judging by the entry's author; the encoding of the mode, which has to survive the flip, and who flips it are open (C4).

### D7. Inside a cell, gossip replaces subset-rbsr

No egress filter: the store is served whole to member devices; the members' devices are the swarm; a write becomes a content-free announcement that neighbours pull through reconciliation and pass on; catch-up after an outage is one session with any neighbour. With 100 members on 2 devices each — 200 nodes — an announcement reaches everyone in 3–4 hops of HyParView's active view, and catch-up costs one reconciliation of the difference rather than a visit to every member. Subset-rbsr keeps its place for connections and personal namespaces.

Rejected: a replica per member inside the cell with the cell as the grant audience. Data would stay with its issuer and grants would stay per claim, but every member's content would be a separate replica the reader reaches separately, grantees stay outside the swarm so a live update needs a grant republish per item, and a stream — a chat — grows the grant record with every message. Kept as an open question for "share without copying" (E3).

### D8. A cell has a human-readable name that is not an identifier

Names repeat, including among one identity's cells. Only the cell id addresses a cell. Whether the name is shared content or per-member is open (E5).

### D9. Several cells with the same members are ordinary

The member set does not identify a cell.

### D10. The platform knows no ontology

Below pdn-layer a cell entry is a key and opaque bytes. The platform reads from the key what it enforces: the cell, the author member, the content kind and a document's mode. Subject, template, SHACL shapes, categories and the DataBook's fields are the application's, carried inside payloads or derived from them. This is the existing layering — the data layer treats tokens and payloads as opaque, the domain lives in pdn-layer — applied to cells.

### D11. A cell has owners

The creator is the cell's first owner. An owner makes any member an owner, and ownership is taken from a member only by another owner — no other act narrows the owner set. Removing a member from the cell — an owner or a plain member alike — is an owner's act: a member that is no owner removes nobody, so an owner is removed only by another owner. Inviting stays every member's act — a newcomer always joins as a plain member, and only an owner's grant makes it an owner — and leaving stays the member's own (B2). Ownership is a role inside membership: an owner is a member, and losing ownership does not touch membership. Members become owners and stop being owners repeatedly over a cell's life — an operating condition, not an edge case. Where the owner set lives follows B1's membership material; the edges of the role are B10.

Rejected: equal-rank membership with no roles at all. It leaves a cell without a repair channel: records nobody may delete and states nobody may fix (D12, D14).

### D12. An owner deletes any member's record

An owner deletes records of any member — its own, another current member's, a removed member's alike (D13). Deletion is the owners' repair power over content; its mechanics — the tombstone surface — are C7. Nothing in this power edits a record in place or writes under another member's name (D15).

### D13. Acting on a record does not depend on its member's standing

The rights to act on a record are the same whether the member that placed it in the cell is a current member or a removed one. Removal changes admission alone — sessions refused, newly authored entries dropped — and changes nothing about what members and owners may do to the records already in the cell: no power over a member's records appears at its removal, and none disappears. Members leave, rejoin and are removed over a cell's life (B2), and the rules for its records read the same throughout.

### D14. Every reachable state is repairable by owners

No sequence of acts — joins, leaves, removals, mode flips, ownership changes, deletions — leaves the cell in a state its owners cannot repair from inside. Recreating the cell — a new store, re-invited members, re-uploaded content — is never the only way out. Every rule in this design is measured against this invariant; the act that could strand it — the last owner gone — is the open edge (B10).

### D15. Authorship is forged by no one

A record's authorship is cryptographic — the author signature on its entries — and no role weakens it: an owner deletes another member's record but writes nothing under that member's name, and every act in a cell reads as the signed act of its actor. The binding of author keys to members stays what the member publishes (F2); signed claims per the KERI roadmap strengthen the same property (C11).

### D16. A member's devices are announced by the member itself, under its announcement key

Each identity holds a device-announcement key pair. The secret lives in its private metadata store and reaches every new device at linking, beside the store tickets. The cell holds two things about a member's devices: a join-time record binding the member's `PdnId` to its announcement public key — signed by the joining device, carried in the join dialogue, written by the inviter, its root the inviter's word exactly as B7 states — and the member's device-list statements: the member's devices with their author keys, a version counter inside the signed bytes, the whole statement signed by the announcement key.

A statement is self-contained proof, so who writes it into the store does not matter: the gate judges an entry in the membership device area by the embedded signature against the announcement key from the join record, never by the entry's author. A freshly linked device therefore registers itself — it holds the write ticket and the announcement secret, writes the newest statement into its local replica of every cell the identity is a member of, and ordinary sync spreads it through the identity's own devices and through any member, with no waiting on anyone being online. Before syncing a cell replica, each of the identity's devices compares the replica's newest statement version against the private metadata store's and writes the newer one in — the sweep that heals an interrupted fan-out, a cell joined after a linking, and a device linked before the join.

Resolution is by the statement's version, never by entry timestamp: statements coexist per author, the classifier builds the author-to-member map from the highest validly signed version, and a device writes only when its version exceeds the replica's — a lagging sibling neither displaces a newer list nor is displaced while it catches up. A statement that never left a dying device dies with the device it described; the converged list is the surviving devices' own. The announcement key with its versioned statements is the slot KERI's key event log fills later: KERI replaces the key, not the scheme (C11, F2).

Rejected: a per-identity metadata store polled by acquaintances — every member tracking a replica per acquaintance restores the topology D2 rejects (a member's data served only by its own devices) and the cost ADR-0009 counts (a reconcile pass per tracked store), and its read tickets, once handed out, leak the device list to removed members forever. Rejected: a private-store contact book as the gate's authority — a binding asserted in one cell would judge entries in another, carrying the inviter's word beyond the cell where it was spoken. Rejected: announcements that must be handed to a live member device — in a two-member cell the other member sleeps for weeks, and an announcement waiting for delivery survives nowhere.

## Risks / Trade-offs

- [Every member holds the whole cell in plaintext] → accepted by definition; content encryption is a separate layer; the trust boundary is the member set (F1).
- [A removed member keeps the store's write ticket and the topic id] → honest devices refuse its sessions and drop its authored entries from the removal onward; it retains what it received and still sees content-free announcements; real expulsion under bearer tickets is a new cell. UWill takes write authority out of the ticket (B3, F1, F3).
- [Membership is a multi-writer set under last-writer-wins] → a concurrent add and remove of one member resolve by rule, not by order; a member-signed founding chain gives membership a root but no total order (B1, B3).
- [Authorship is a transport-level binding] → author keys are node-local; the binding of an author key to a member is what the member publishes under its announcement key (D16), verifiable by anyone holding the join record; an honest gate enforces it; a modified member device can forge locally but cannot pass honest gates. Signed claims come with KERI (C11, F2).
- [Range fingerprints are linear scans] → a cell store with 100 writers is never quiescent, so every catch-up session scans the store per round; a cached fingerprint tree in pdn-store is the fix (D2').
- [Storage per device grows with every cell] → records replicate everywhere; payloads can follow a download policy (D5').
- [Reachability] → the stack is relay-free; in a 100-member cell most device pairs sit behind NATs; the swarm needs one reachable neighbour per device (D3').
- [Concurrent editing of one document under per-key last-writer-wins loses edits] → the document's representation — whole value or an operation log merged above the platform — is open (C5).
- [The join is bearer-level] → the invitation carries no bearer material and the secret burns, but the newcomer's identity is asserted, not proven; KERI's proof step slots into the same dialogue (B7).
- [An owner deletes another member's records] → accepted as the repair channel (D12, D14); the deletion is the owner's own signed act and forges nothing (D15), and a hostile owner sits inside the trust boundary already (F1).

## Migration Plan

Additive: no existing store, ticket, grant or record changes shape, and a runtime without cells behaves as before. Rollback is forgetting cell stores; nothing else depends on them.

## Open Questions

Grouped; each names its options and, where the team leans somewhere, the leaning — none is decided. The ones marked **blocking** are answered before implementation starts (tasks 0.x).

### A. The cell id

- A1 (**blocking**). Form: 32 random bytes, as `PdnId` is minted today, or the hash of a founding record — self-addressing, still keyless — that names the founder and the first members. mia-ontologies asks for a random UUID v4 with no embedded metadata; a hash embeds nothing either, but gives membership a root. Leaning: random, on the app's own reasoning.
- A2. Size and form at the boundary: the app links cells by id inside notes (`[[<id>|text]]`) and expects a UUID; the platform id is 32 bytes. Who converts. And the id is public-safe — it travels in notes to other cells' members — so it is never the replica's namespace id, which is the read capability (Invariant 3).

### B. Membership

- B1 (**blocking**). Where membership lives: records in the cell store itself, inductively from the founding record — leaning confirmed by D16 for the device half: the join record binds the member to its announcement key, and the member's own signed statements carry its devices. Still open: the shape of the member, owner and removal records themselves and who writes them (owner marks per B10).
- B2. Leaving versus removal: leaving is every member's own act while removal is an owner's (D11), so leaving is not a self-removal — whether the two share a record shape is open. Members leave and rejoin, and a removed member is re-added — ordinary conditions, not edge cases; what a rejoin restores — the old member record, the standing of the records under the member's name — is open, bounded by D13.
- B3. Removal semantics under bearer tickets: gate-only — sessions refused and the removed member's authors dropped from the next session. A concurrent add and remove of one member: remove-wins, last-writer-wins, or a threshold of removal records. An entry authored before the removal but arriving after it.
- B4 (**blocking**). Join path: a one-time-secret dialogue on a dedicated ALPN, linking-shaped (ADR-0012), carried as a QR code or an invite link; or an invite record carried over an existing channel with the newcomer — a connection or a common cell — where the store's ticket travels inside an Invariant-3 store as data tickets do; or both. An invite link for someone without the app.
- B5. A member's other devices: the cell's tickets and the announcement secret in the member's directory under a cell kind, opened on demand as connection-metadata pairs are; the opened device registers itself per D16. Open: the shape of that directory kind.
- B6. Organizations as members: an identity hosted on an organization's node — anything the platform treats differently.
- B7. Proof at join: the newcomer's `PdnId` is the inviter's word. KERI's proof step — challenge-response, exchange of key event logs — is the same slot as in pairing and linking.
- B8. A cell with 0 members: representable at all — a store nobody holds — or is the minimum 1.
- B9. Whether joining requires a claim by the newcomer about itself, as mia-ontologies' `c:members` baseline does (one graph per member), or that is the app's business.
- B10. Ownership at the edges: an owner leaving — the one act that ends an ownership without another owner's hand, the last owner's leaving included; whether the rule set keeps at least one owner, so that D14's repairability never loses its subject; a concurrent grant and revoke of one member's ownership; how the owner set is encoded in B1's membership material.

### C. Content

- C1. Vocabulary: the platform's claim is mia-ontologies' graph (`g:SCGraph` — subject, claimant, template, triples); mia-ontologies' "claim" is a triple inside one. Fix the mapping in the glossary; decide whether the spec tree keeps "claim" for the graph.
- C2 (**blocking**). Immutable claims and editable graphs: mia-ontologies' graphs are edited by their claimant — Bob updates his contact card. Either a claim is one version of a graph — a new claim per edit, with a head the app follows — or claims are immutable and graphs are documents. If versions: history retained (the version in the key, append-only) or head only (one key, last-writer-wins among the claimant's own writes).
- C3. Chat: a third kind — an append-only stream of immutable messages, each written only by its author, which the gate treats as claims — or a document.
- C4. Key layout: an author prefix (`by/<member>/…`) so the gate reads the author member from the key. Where the mode lives: a document's mode flips read-only to read-write and back over its life (D6), so an encoding that fixes the mode at creation does not suffice on its own — a record the mode's holder writes (a lookup per entry), or a key encoding paired with a mechanism that survives the flip. Who flips a document's mode — its creator, an owner — is also open.
- C5 (**blocking**). Documents under concurrency: per-key last-writer-wins on the whole value — an edit is lost when two members edit at once — or an operation log, every operation an immutable entry written by its author and merged by a CRDT above the platform. With an operation log the platform has one rule for everything — every entry is written by its author — and read-write means "any member may append operations to this document".
- C6. Files: attachments as blobs; lazy payloads through the fork's download policy; size limits; a rename or move as a new key plus a tombstone.
- C7 (**blocking**). Deletion: the data layer offers no delete on data replicas, and a cell needs one — unsharing a claim, removing a file, deleting a document. Tombstones as the directory uses them, exposed for cell stores.
- C8. The cell DataBook as a view: which fields are cell-level records — `title`, `origin`, `creator`, `shape`, rarely written, last-writer-wins acceptable — and which are derived at read time — `members`, `memberCount`. A single record written by every member loses additions under last-writer-wins.
- C9. Identifiers inside shared content: `:Self` never enters the store — mia-ontologies keeps it local; members are named by `PdnId`; a non-member — a parent without the app, a pet, a doctor — needs a cell-scoped id every member agrees on, minted by whoever introduces it and mapped to local names on each device.
- C10. Claim identity: derived from the cell id and the path inside the cell, or from the replica and the key as in data stores. It matters if a one-member cell is ever promoted from a personal namespace (D1').
- C11. Signed claims: `PdnIdentityProof` on a claim by its issuer — KERI.
- C12. The claimant field inside a graph's metadata is never trusted on its own; the author member comes from the key and the gate.

### D. Sync and scale

- D1'. One-member cells: a replica from birth — D3 read literally, hundreds of replicas per device for a full personal tree, each its own swarm and its own reconcile pass — or key prefixes in the identity's own namespace promoted to a replica at the second member, which is a data move and raises C10. Leaning: from birth; measure.
- D2'. The linear-scan range fingerprint in the fork: when to replace it with a cached fingerprint tree.
- D3'. Reachability: iroh relays or hole punching; always-on member devices as de-facto hubs.
- D4'. Swarm and cadence parameters for 200 nodes: active and passive view sizes, the reconcile interval, churn of mobile devices.
- D5'. The download policy default for cell stores: records everywhere, payloads on demand.
- D6'. Clocks: chat ordering by writer timestamps under the fork's 10-minute future window.
- D7'. Storage: a quota per cell on a device; a disk that fills mid-sync.

### E. Relation to what exists

- E1 (**blocking** for the product, not for the platform). Connections: they stay, they become two-member cells — mia-ontologies models the relationship with one person as a bare two-member cell — or both coexist. A two-member cell and a connection differ: a copy into a common space versus a grant on one's own data.
- E2. Grants, subset-rbsr and per-issuer namespaces are not used by a product that keeps everything in cells and shares by copying — mia-ontologies: "the app copies from the Dr. Jane Starostina cell". Kept for other consumers — organization nodes, the SDK — or not.
- E3. The cell as an audience of grants on personal namespaces — "share without copying" — if ever needed.
- E4. Tree position: personal state — in the directory or in the identity's data namespace; `origin` as the filing hint on receipt.
- E5. The name: shared content, per-member for a bare two-member cell (mia-ontologies' rule), or always per-member.
- E6. Source of truth for the app: the cell store, with the filesystem materialized from it, or the filesystem with a watcher.

### F. Security

- F1. The trust model stated: every member is trusted with the whole cell; the gate protects honest members from a dishonest member's forgeries, not from its leaks.
- F2. The author-key-to-member binding: published by the member itself (D16); what a device does when two members claim one author key, or when two validly signed statements of one member conflict at one version.
- F3. The topic id equals the namespace id, known to removed members forever: content-free announcements leak activity; a cell that must shed a member entirely moves to a new store.
- F4. Equivocation among members: with n parties the pairwise "first seen wins" of the KERI roadmap is not enough; duplicity detection moves earlier in that roadmap.
- F5. Linkability: one `PdnId` across cells; per-cell pairwise identities (the KERI roadmap's later step).

### G. Operations

- G1. Restart: cells re-derived from each hosted identity's directory, or recorded beside the hosted identities.
- G2. Observability: metrics for cell sessions, drops at the gate, swarm size.
- G3. The HTTP host and the container stand: which cell operations the demo surface exposes.
