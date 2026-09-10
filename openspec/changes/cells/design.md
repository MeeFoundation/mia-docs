# Design: cells

## Context

A PDN node hosts identities. Each identity has a private-metadata directory (its devices, its tickets, its connections records), a data namespace, and, per connection, a directional connection metadata store carrying grants. Sharing means a grant: the claim stays in its issuer's namespace and reaches the audience through capability-filtered reconciliation with the issuer's devices or the audience's own siblings, never through a third party. That model is pairwise by construction.

The product's data model — mia-ontologies, the Cellula app — organizes everything as cells: a folder holding one cell DataBook, a markdown note, files and a chat, nested in a per-user tree. Structured content lives in graphs (`g:SCGraph`), each with a subject and a claimant. A cell has a creator with no privileges, one or more members, a shared name and an origin category; sharing a cell gives every member a complete live copy; the relationship with one other person is a bare two-member cell. The app's authors expect cells to stay "well under 100" members.

This design records the decisions taken for the platform side of cells and the questions left open. It works from the team's working note on cells, from a reading of mia-ontologies on 28 August 2026, from the decisions of 7 September 2026 on roles and document types, and from the decision of 10 September 2026 on the cell's two stores.

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

### D3. One cell is two pdn-store replicas: the membership store and the record store

A cell is served by two replicas, each addressed through the cell id. The **membership store** is the cell's authority: who is a member, with what role, on which devices. It holds, per member, one append-only sequence of **membership events** — join (the join record of D16, binding the member to its announcement key), leave, removal, made-owner, unmade-owner — each an immutable entry under its own key with the sequence number inside the signed bytes, and the member's device-list statements (D16), each version an immutable entry of its own. Nothing in the membership store is overwritten or deleted: a removal is an event, not a deletion, and the store holds no tombstones. The **record store** is what the authority governs: the records — claims and documents (D4). The classifier folds the membership store into the write admission the gate judges both stores by, walking each member's events in sequence order: a join makes it a member and a plain one, made-owner an owner, unmade-owner a plain member again, leave and removal no member, a later join a plain member again — a member that joins again joins as a newcomer does (D11); the author-to-member map comes from the join events and the device statements by highest version. By sequence, never by timestamp, so the order in which the events arrived does not matter. Standing and role are events in one sequence rather than last-writer-wins values because a member is made an owner and unmade repeatedly (D11) and leaves and rejoins (D13), and the flips must order unambiguously against each other and, later, against records (F6), without trusting the timestamp the author sets (D13). A member's sequence is a small key event log of its standing in the cell — the slot KERI fills (C11). Not one replica for all cells, and not one replica per member inside a cell: ADR-0009's case against a shared namespace — a set that is never quiescent, and work spent on entries the filter discards — does not apply, since every member wants every entry and nothing is discarded. Each replica is the authorization unit (who may sync it), the swarm topic and the reconciliation unit, exactly the roles ADR-0009 keeps for a namespace; the two share the audience — every member device — and differ in what they are: the membership store governs, the record store is governed, as the grants in a connection metadata store govern a data store.

Rejected: one replica with the membership material under a key prefix reconciled first. The store orders entries by namespace, author, key, so a key prefix is not a contiguous range but a filter across every author's partition — reconciling it is subset-rbsr, whose fingerprint under a filter (`SessionStore::get_fingerprint` in the fork's `filter.rs`) walks every entry of the replica per round: the cost of converging membership grows with the volume of records, is paid on every session of a store that is never quiescent, and sits on the critical path — before any record is judged. A cached fingerprint tree (D2') does not help a prefix, being built over the store's own order. A separate membership store reconciles by plain reconciliation over a small, almost static set, at a cost independent of the records, and keeps subset-rbsr out of the cell (D7, D19). The price is a second replica per cell — a topic, a ticket, a reconcile pass — a fixed cost per cell, measured with D1'.

Rejected: one role log for the whole cell under a single sequence. It would order role events across members, but the gate judges as of the session from the folded state and needs no such order; the order matters only for historical validity — whether the actor was still an owner at the moment it acted — which is anchoring's question (F6), and which a single sequence answers for the membership store alone, not for the records that would reference it. A concurrent pair of events at one sequence needs a tie-break either way (B10).

### D4. Content is records, of two kinds: claims and documents

A **record** is what a member places into a cell; claims and documents are the two kinds of record. A claim is an assertion by an issuer about a subject — in mia-ontologies a graph with a claimant and a subject, such as a `persona:DriversLicenseDocument`. A document is content — in mia-ontologies the cell's note and its files. The difference between the kinds is in what a record is — an assertion or content — and the difference between a document's two types is in mutability (D17); neither is a difference in payload format: payloads stay opaque below pdn-layer, and a document's type picks how its entries are laid out, not what they contain. Membership material — member records, device records, removal events — is the cell's bookkeeping, not a record in this sense.

### D5. Claims are immutable and, inside a cell, shared with every member

A claim does not change after it is written — a changed assertion is a new claim. Inside a cell there is no narrower audience: a claim placed in a cell is read by every member and written only by its issuer. "Share with Carol and Dave but not Bob" is a different cell (D9).

### D6. Every member reads a document and edits a mergeable-document

A document is read by every member of the cell. A mergeable-document is edited by every member — each operation is an entry signed by the device that wrote it, so who edited what is read from the entries themselves (D15) — and an immutable-document by no one (D17). There is no sharing mode per document: no document is "shared read-only" or "shared read-write", and no act flips such a mode; and ownership (D11) changes nothing about editing — it changes deletion (D12). What takes editing away is removal: the gate serves it as D13 states — the verdict on every honest device is by the entry's author against the member map frozen at session setup, and what was admitted before the removal stays. The rights by role, one table per record kind, are in the pdn-node cells spec.

Rejected: a sharing mode per document, read-only or read-write, flipped over the document's life. It needed an encoding of the mode that survives the flip and a rule for who flips it, and it put a second access structure beside the roles the cell already has. Rejected: editing another member's mergeable-document reserved to owners. It left two plain members unable to write one note together, while the signature on every operation already keeps each edit under its writer's name, and a spoiled document is repaired by an owner's deletion (D12) as any record is.

### D7. Inside a cell, gossip replaces subset-rbsr

No egress filter: both stores are served whole to member devices, the membership store before the record store (D19); the members' devices are the swarm; a write becomes a content-free announcement that neighbours pull through reconciliation and pass on; catch-up after an outage is one session with any neighbour. With 100 members on 2 devices each — 200 nodes — an announcement reaches everyone in 3–4 hops of HyParView's active view, and catch-up costs one reconciliation of the difference rather than a visit to every member. Subset-rbsr keeps its place for connections and personal namespaces.

Rejected: a replica per member inside the cell with the cell as the grant audience. Data would stay with its issuer and grants would stay per claim, but every member's content would be a separate replica the reader reaches separately, grantees stay outside the swarm so a live update needs a grant republish per item, and a stream — a chat — grows the grant record with every message. Kept as an open question for "share without copying" (E3).

### D8. A cell has a human-readable name that is not an identifier

Names repeat, including among one identity's cells. Only the cell id addresses a cell. The name is shared: the cell carries one name every member sees, set at creation and renamed by an owner; there is no per-member name on the platform. The name is a cell-level record (C8).

### D9. Several cells with the same members are ordinary

The member set does not identify a cell.

### D10. The platform knows no ontology

Below pdn-layer a cell entry is a key and opaque bytes. The platform reads from the key what it enforces: the cell, the member under whose name the record sits, the content kind and a document's type. Subject, template, SHACL shapes, categories and the DataBook's fields are the application's, carried inside payloads or derived from them. This is the existing layering — the data layer treats tokens and payloads as opaque, the domain lives in pdn-layer — applied to cells.

### D11. A cell has owners

The creator is the cell's first owner. An owner makes any member an owner, and ownership is taken from a member only by another owner — no other act narrows the owner set. Removing a member from the cell — an owner or a plain member alike — is an owner's act: a member that is no owner removes nobody, so an owner is removed only by another owner. Inviting stays every member's act — a newcomer always joins as a plain member, and only an owner's grant makes it an owner — and leaving stays the member's own (D13). Ownership is a role inside membership: an owner is a member, and losing ownership does not touch membership. Beside the acts on membership, an owner deletes any record (D12); editing is every member's (D6). Members become owners and stop being owners repeatedly over a cell's life — an operating condition, not an edge case. The owner set lives in the membership store as made-owner and unmade-owner events in each member's sequence (D3, D21); the edges of the role are B10.

Rejected: equal-rank membership with no roles at all. It leaves a cell without a repair channel: records nobody may delete and states nobody may fix (D12, D14).

### D12. A member deletes its own records; an owner deletes any member's

A member deletes the records under its own name because they are its own. An owner deletes records of any member — its own, another current member's, a removed member's alike (D13) — because it is an owner. Deletion is the owners' repair power over content, and a deletion followed by a new record is how a claim or an immutable-document is replaced (D18); the mechanics — the tombstone surface — are C7. Neither power writes under another member's name (D15).

### D13. Acting on a record does not depend on its member's standing

The rights to act on a record are the same whether the member that placed it in the cell is a current member or a removed one. Leaving and removal change admission alone — sessions refused, newly authored entries dropped — and change nothing about what is in the cell or what members and owners may do to it: the member's own documents and claims stay, its operations on other members' documents stay, no power over a member's records appears at its removal, and none disappears — the members edit and the owners delete a removed member's records as they do a current member's. A member that joins again writes again — new records, new operations — as any member; whether its earlier operations resolve to it is the implementation's convenience, not a rule. Members leave, rejoin and are removed over a cell's life, and the rules for its records read the same throughout.

### D14. Every reachable state is repairable by owners

No sequence of acts — joins, leaves, removals, ownership changes, edits, deletions — leaves the cell in a state its owners cannot repair from inside. Recreating the cell — a new store, re-invited members, re-uploaded content — is never the only way out. The converse holds too: no operation deletes a cell for every member, owners included — a cell ends by its members leaving, each forgetting its own copy, and a device that holds the store keeps it anyway (Invariant 2). Every rule in this design is measured against this invariant; the act that could strand it — the last owner gone — is the open edge (B10).

### D15. Authorship is forged by no one

A record's authorship is cryptographic — the author signature on its entries — and no role weakens it: a member edits another member's mergeable-document and an owner deletes another member's record, and each such entry carries its actor's own signature, so a document's history reads who wrote what, and every act in a cell reads as the signed act of its actor. Where a record sits — the member under whose name it is placed — and who wrote each entry in it are two different things, and only the second is a statement about authorship. The binding of author keys to members stays what the member publishes (F2); signed claims per the KERI roadmap strengthen the same property (C11).

### D16. A member's devices are announced by the member itself, under its announcement key

Each identity holds a device-announcement key pair. The secret lives in its private metadata store and reaches every new device at linking, beside the store tickets. The cell holds two things about a member's devices: a join-time record binding the member's `PdnId` to its announcement public key — signed by the joining device, carried in the join dialogue, written by the inviter, its root the inviter's word exactly as B7 states — and the member's device-list statements: the member's devices with their author keys, a version counter inside the signed bytes, the whole statement signed by the announcement key.

A statement is self-contained proof, so who writes it into the store does not matter: the gate judges an entry in the membership device area by the embedded signature against the announcement key from the join record, never by the entry's author. A freshly linked device therefore registers itself — it holds the write ticket and the announcement secret, writes the newest statement into its local replica of every cell the identity is a member of, and ordinary sync spreads it through the identity's own devices and through any member, with no waiting on anyone being online. Before syncing a cell replica, each of the identity's devices compares the replica's newest statement version against the private metadata store's and writes the newer one in — the sweep that heals an interrupted fan-out, a cell joined after a linking, and a device linked before the join.

Resolution is by the statement's version, never by entry timestamp: statements coexist, one entry per version (D21), the classifier builds the author-to-member map from the highest validly signed version, and a device writes only when its version exceeds the replica's — a lagging sibling neither displaces a newer list nor is displaced while it catches up. A statement that never left a dying device dies with the device it described; the converged list is the surviving devices' own. The announcement key with its versioned statements is the slot KERI's key event log fills later: KERI replaces the key, not the scheme (C11, F2).

Rejected: a per-identity metadata store polled by acquaintances — every member tracking a replica per acquaintance restores the topology D2 rejects (a member's data served only by its own devices) and the cost ADR-0009 counts (a reconcile pass per tracked store), and its read tickets, once handed out, leak the device list to removed members forever. Rejected: a private-store contact book as the gate's authority — a binding asserted in one cell would judge entries in another, carrying the inviter's word beyond the cell where it was spoken. Rejected: announcements that must be handed to a live member device — in a two-member cell the other member sleeps for weeks, and an announcement waiting for delivery survives nowhere.

### D17. A document is a mergeable-document or an immutable-document

A document has one of two types, chosen when it is placed. A **mergeable-document** is content whose concurrent edits are meant to be kept — a markdown note, a rich text as a JSON tree of text nodes: every edit is an operation, each operation an immutable entry under its own key signed by its writer, and the operations are merged by a CRDT above the data layer. An **immutable-document** is content placed once — a PDF file uploaded into the cell: one entry under one key, written by the member under whose name it sits and updated afterwards by no one, that member included; a changed file is a new record (D18). On the platform an immutable-document has the shape of a claim (D5) — placed once, deleted (D12), replaced by a new record — and differs from it in what it is to the product: content rather than an assertion. Below pdn-layer the type decides the key layout — one key, or one key per operation — and the admission rule: an immutable-document from the member under whose name it sits, a mergeable-document's operation from any member (D6); the merge algorithm and the payload encoding live above (D10).

Rejected: a document type overwritten in place by the last writer. Whole-value replacement under last-writer-wins loses the edits of a note two people write at once, and an in-place overwrite by an owner leaves the member's name on content the owner wrote; deleting and placing anew keeps every record under the name of the member that placed it.

### D18. Replacing a claim or an immutable-document is deleting it and placing a new one

A claim (D5) and an immutable-document (D17) are updated in place by no one. A member replaces its own record because it is its own; an owner replaces any member's record because it is an owner (D12): the old record is deleted, and the new one is placed under the replacer's name — a new record with a new id, its issuer or placing member the replacer, so a member's record replaced by an owner becomes the owner's. References to the old record — links inside notes — stay on the old record and do not follow the new one. That such references break is accepted: a record's id names the member under whose name it sits (C10), so a record replaced under another name is another id. A mergeable-document is edited in place (D6) and its id stays.

### D19. The membership store is reconciled before the record store, and no filter runs inside a cell

A session between two member devices reconciles the membership store to convergence first, folds it into the write admission, and only then reconciles the record store under it; both by plain, unfiltered reconciliation — no capability filter (subset-rbsr) runs on either store, whatever the session peer. The order makes the common case exact: a newcomer's first records and a removed member's later ones are judged, in the session that brings them, under the membership that same session brought. The order does not remove the residue — membership still spreads through the swarm, so a record may reach a device before the membership event authorizing its author — and the residue heals as before: the entry is dropped and offered again by a later session. The gate stays synchronous and reads no replica: everything it needs is in the write admission folded at session setup.

Rejected: no order between the stores — a record judged under stale membership is dropped and re-offered, a session of latency per newcomer write. Rejected: a filter on the record store per session peer — the audience of a cell is every member device, so a filter has nothing to remove and only costs the linear fingerprint (D3).

### D20. Every member device holds the write ticket of both stores

Every member device holds both stores whole and holds their write tickets; write authority inside a cell is the gate's, judged per entry (D6, D12, D17), never the ticket's mode. Any member edits other members' mergeable-documents (D6), an owner deletes other members' records (D12), and every member relays what it holds (D7) — none of which a read-only ticket allows, and a ticket per role would have to be re-cut at every role change (D11). A removed member keeps the write tickets it held: honest devices refuse its sessions and drop its entries from the removal onward (D13), which is the whole of removal under bearer tickets; UWill takes write authority out of the ticket (F1, F3).

### D21. The key layout of both stores

The membership store: `member/<pdnid>/<seq>` — the member's membership events (D3): join, leave, removal, made-owner, unmade-owner; `member/<pdnid>/devices/<version>` — the device-list statements (D16), one entry per version, resolved by the highest validly signed version. Every membership-store entry is written once: an entry at a key the write admission already shows held by the same author is dropped — the whole store is in the write admission, so the check costs nothing — and two authors' events at one sequence both stand until B10's tie-break. The membership store holds no tombstones. The record store: `by/<pdnid>/claim/<id>` — a claim; `by/<pdnid>/doc/immutable/<id>` — an immutable-document, one entry; `by/<pdnid>/doc/mergeable/<id>/<op>` — one entry per operation of a mergeable-document, where `<op>` is the writer's author key followed by the writer's own sequence, so two writers' operations never share a key and one writer's never collide. `<pdnid>` is the member under whose name the record sits — the identity, not a device, so the key outlives the devices that write under it. The gate reads from the key what it enforces (D10): the member, the kind, a document's type; it reads from the entry only its author and whether it is empty — a tombstone (C7) is the store's empty entry at a record's key, at a mergeable-document's key above its operations. Everything else — a document's title, a replacement's reference to what it replaced — is payload.

Rejected: the writer's author key as the key prefix. Devices come and go while the member stays; a record keyed by a device would move with every linking, and the author-to-member map already bridges the two.

## Risks / Trade-offs

- [Every member holds the whole cell in plaintext] → accepted by definition; content encryption is a separate layer; the trust boundary is the member set (F1).
- [A removed member keeps both stores' write tickets and topic ids] → honest devices refuse its sessions and drop its authored entries from the removal onward; it retains what it received and still sees content-free announcements; real expulsion under bearer tickets is a new cell. UWill takes write authority out of the ticket (D13, F1, F3).
- [Membership is a multi-writer set] → its records order by per-member sequence numbers, never by timestamp (D3, D21); a concurrent add and remove, or grant and revoke, at one sequence needs a tie-break (B10); a member-signed founding chain gives membership a root but no total order.
- [Authorship is a transport-level binding] → author keys are node-local; the binding of an author key to a member is what the member publishes under its announcement key (D16), verifiable by anyone holding the join record; an honest gate enforces it; a modified member device can forge locally but cannot pass honest gates. Signed claims come with KERI (C11, F2).
- [Range fingerprints are linear scans] → a record store with 100 writers is never quiescent, so every catch-up session scans it per round; a cached fingerprint tree in pdn-store is the fix (D2'), and the membership store's convergence does not wait for it (D3).
- [The membership store only grows] → events are never deleted; a member's sequence is a handful of events over a cell's life, and the store stays tiny beside the records (D3).
- [Storage per device grows with every cell] → records replicate everywhere; payloads can follow a download policy (D5').
- [Reachability] → the stack is relay-free; in a 100-member cell most device pairs sit behind NATs; the swarm needs one reachable neighbour per device (D3').
- [Concurrent editing of one document loses edits] → a mergeable-document keeps every operation under its own key and merges them above the data layer (D17); an immutable-document is never edited, and two members replacing one at once leave two new records under two names, visible to everyone and resolved by people (D18).
- [The join is bearer-level] → the invitation carries no bearer material and the secret burns, but the newcomer's identity is asserted, not proven; KERI's proof step slots into the same dialogue (B7).
- [An owner deletes another member's records] → accepted as the repair channel (D12, D14); the deletion is the owner's own signed act and forges nothing (D15), and a hostile owner sits inside the trust boundary already (F1).
- [Any member edits any mergeable-document] → accepted: every member is trusted with the whole cell already (F1), each operation carries its writer's signature (D15), and a spoiled document is repaired by further operations or by an owner's deletion (D12).
- [A replaced record breaks references to the old one] → accepted (D18); the deletion and the new record are two signed acts of the replacer (D15).

## Migration Plan

Additive: no existing store, ticket, grant or record changes shape, and a runtime without cells behaves as before. Rollback is forgetting cell stores; nothing else depends on them.

## Open Questions

Grouped; each names its options and, where the team leans somewhere, the leaning — none is decided; a question answered since its posing says so and points at the decision. The ones marked **blocking** are answered before implementation starts (tasks 0.x).

### A. The cell id

- A1 (**blocking**). Form: 32 random bytes, as `PdnId` is minted today, or the hash of a founding record — self-addressing, still keyless — that names the founder and the first members. mia-ontologies asks for a random UUID v4 with no embedded metadata; a hash embeds nothing either, but gives membership a root. Leaning: random, on the app's own reasoning.
- A2. Size and form at the boundary: the app links cells by id inside notes (`[[<id>|text]]`) and expects a UUID; the platform id is 32 bytes. Who converts. And the id is public-safe — it travels in notes to other cells' members — so it is never the replica's namespace id, which is the read capability (Invariant 3).

### B. Membership

- B4 (**blocking**). Join path: a one-time-secret dialogue on a dedicated ALPN, linking-shaped (ADR-0012), carried as a QR code or an invite link; or an invite record carried over an existing channel with the newcomer — a connection or a common cell — where the stores' tickets travel inside an Invariant-3 store as data tickets do; or both. An invite link for someone without the app.
- B5. A member's other devices: the cell's tickets and the announcement secret in the member's directory under a cell kind, opened on demand as connection-metadata pairs are; the opened device registers itself per D16. Open: the shape of that directory kind.
- B6. Organizations as members: an identity hosted on an organization's node — anything the platform treats differently.
- B7. Proof at join: the newcomer's `PdnId` is the inviter's word. KERI's proof step — challenge-response, exchange of key event logs — is the same slot as in pairing and linking.
- B8. A cell with 0 members: representable at all — a store nobody holds — or is the minimum 1.
- B9. Whether joining requires a claim by the newcomer about itself, as mia-ontologies' `c:members` baseline does (one graph per member), or that is the app's business.
- B10. Ownership at the edges: an owner leaving — the one act that ends an ownership without another owner's hand, the last owner's leaving included; whether the rule set keeps at least one owner, so that D14's repairability never loses its subject; a concurrent grant and revoke of one member's ownership, and a concurrent add and remove of one member — two events at one sequence number, which the per-member sequence (D3) does not order.
- B11. Answered by D14: no operation deletes a cell for every member; a cell ends by its members leaving.

### C. Content

- C1. Vocabulary: the platform's claim is mia-ontologies' graph (`g:SCGraph` — subject, claimant, template, triples); mia-ontologies' "claim" is a triple inside one. Fix the mapping in the glossary; decide whether the spec tree keeps "claim" for the graph.
- C2 (**blocking**). Immutable claims and editable graphs: mia-ontologies' graphs are edited by their claimant — Bob updates his contact card. Either a claim is one version of a graph — a new claim per edit, with a head the app follows — or claims are immutable and graphs are documents. If versions: history retained (the version in the key, append-only) or head only (one key, last-writer-wins among the claimant's own writes).
- C3. Chat: a third kind — an append-only stream of immutable messages, each written only by its author, which the gate treats as claims — or a document.
- C5. Answered by D17: a mergeable-document keeps its operations, an immutable-document is never edited. Open above the platform: which CRDT serves markdown and which the rich-text JSON tree, whether pdn-layer or the application runs the merge, and the operation encoding. To confirm: that a document never changes type — a file does not become a merged text, and a payload that changes representation is a new record; and that a member replacing its own record gets a new id rather than reusing the old path, since a reused path would keep the id and make the replacement an update in all but name.
- C6. Files: attachments as blobs; lazy payloads through the fork's download policy; size limits; a rename or move as a new key plus a tombstone.
- C7 (**blocking**). Deletion: the data layer offers no delete on data replicas, and a cell needs one — unsharing a claim, removing a file, deleting a document — and every replacement (D18) is a deletion first, so a cell without deletion has no replacement either. Tombstones as the directory uses them, exposed for cell stores.
- C8. The cell DataBook as a view: which fields are cell-level records — `title`, `origin`, `creator`, `shape`, rarely written, last-writer-wins acceptable — and which are derived at read time — `members`, `memberCount`. A single record written by every member loses additions under last-writer-wins.
- C9. Identifiers inside shared content: `:Self` never enters the store — mia-ontologies keeps it local; members are named by `PdnId`; a non-member — a parent without the app, a pet, a doctor — needs a cell-scoped id every member agrees on, minted by whoever introduces it and mapped to local names on each device.
- C10. Record identity: derived from the cell id, the member under whose name the record sits and the path inside the cell — the form D18 assumes, a record replaced under another name being another id — or from the replica and the key as in data stores. It matters if a one-member cell is ever promoted from a personal namespace (D1').
- C11. Signed claims: `PdnIdentityProof` on a claim by its issuer — KERI.
- C12. The claimant field inside a graph's metadata is never trusted on its own; the author member comes from the key and the gate.

### D. Sync and scale

- D1'. One-member cells: a pair of replicas from birth — D3 read literally, hundreds of pairs per device for a full personal tree, each replica its own swarm and its own reconcile pass — or key prefixes in the identity's own namespace promoted to a replica at the second member, which is a data move and raises C10. Leaning: from birth; measure.
- D2'. The linear-scan range fingerprint in the fork: when to replace it with a cached fingerprint tree; with two stores per cell the tree serves each store over its own order (D3).
- D3'. Reachability: iroh relays or hole punching; always-on member devices as de-facto hubs.
- D4'. Swarm and cadence parameters for 200 nodes: active and passive view sizes, the reconcile interval, churn of mobile devices.
- D5'. The download policy default for record stores: records everywhere, payloads on demand.
- D6'. Clocks: chat ordering by writer timestamps under the fork's 10-minute future window.
- D7'. Storage: a quota per cell on a device; a disk that fills mid-sync.

### E. Relation to what exists

- E1 (**blocking** for the product, not for the platform). Connections: they stay, they become two-member cells — mia-ontologies models the relationship with one person as a bare two-member cell — or both coexist. A two-member cell and a connection differ: a copy into a common space versus a grant on one's own data.
- E2. Grants, subset-rbsr and per-issuer namespaces are not used by a product that keeps everything in cells and shares by copying — mia-ontologies: "the app copies from the Dr. Jane Starostina cell". Kept for other consumers — organization nodes, the SDK — or not.
- E3. The cell as an audience of grants on personal namespaces — "share without copying" — if ever needed.
- E4. Tree position: personal state — in the directory or in the identity's data namespace; `origin` as the filing hint on receipt.
- E5. Answered by D8: one shared name, renamed by owners, and no per-member name on the platform. Open for the product: a bare two-member cell is shown under the other person's name in mia-ontologies — that label is the application's own, derived from membership, not a name the cell carries.
- E6. Source of truth for the app: the record store, with the filesystem materialized from it, or the filesystem with a watcher.

### F. Security

- F1. The trust model stated: every member is trusted with the whole cell; the gate protects honest members from a dishonest member's forgeries, not from its leaks.
- F2. The author-key-to-member binding: published by the member itself (D16); what a device does when two members claim one author key, or when two validly signed statements of one member conflict at one version.
- F3. Each store's topic id equals its namespace id, known to removed members forever: content-free announcements leak activity; a cell that must shed a member entirely moves to a new store.
- F4. Equivocation among members: with n parties the pairwise "first seen wins" of the KERI roadmap is not enough; duplicity detection moves earlier in that roadmap.
- F5. Linkability: one `PdnId` across cells; per-cell pairwise identities (the KERI roadmap's later step).
- F6. A former member's content and a fresh device. An entry a member authored while a member is legitimate cell history, but the author-based gate — the one ground for dropping is that the author resolves to no current member as of the session (D13) — drops it on any device that catches up after the author left or was removed. So a device linked or joined later, a current member's new phone included, converges on the content of current members only, and every departed member's contribution is missing from it; this is the dual of D13, which keeps a departed member's new writes out. The gate cannot tell a departed member's old legitimate entry from a new one, because the author sets the timestamp (D13). Options: (a) accept it — acquisition is per device (Invariant 2), and a cell's full history is promised to no device that was not there; (b) admit in full between an identity's own devices, as data replicas do (capability-gated-ingest), so a new phone at least converges with its siblings — a forgery still cannot escape to another member, whose gate runs, and a late joiner still gets no departed member's history; (c) witnessing — a current member signs a snapshot of accepted entry hashes, and an entry a current member has witnessed is admitted whatever its author, carrying history under a current member's authority, at the cost of the snapshots; (d) membership epochs — a record-store entry names the membership-store sequence it was authored under (each member's event sequence of D3 is that log), checked against the folded history: a step toward anchored signatures, with no blockchain and no total order, and one the self-asserted timestamp cannot stand in for (D13). The clean resolution is capability-bound writes (UWill/KERI, F1, F3): once a removed member's write fails a capability check on its own merit, its device identity may stay in the map and all its validly signed entries be admitted, old and new alike, because it can no longer make an admissible new one — options (b)–(d) then fall away. Leaning: (b) for the new-phone case now, the rest with UWill.

### G. Operations

- G1. Restart: cells re-derived from each hosted identity's directory, or recorded beside the hosted identities.
- G2. Observability: metrics for cell sessions, drops at the gate, swarm size.
- G3. The HTTP host and the container stand: which cell operations the demo surface exposes.
