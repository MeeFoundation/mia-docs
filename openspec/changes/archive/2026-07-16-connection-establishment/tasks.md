# Tasks: connection-establishment

## 1. The connection metadata store (`data-layer`)

- [x] 1.1 `connection_metadata.rs`: `ConnectionMetadataStore` mirroring the other device stores — `create` / `import` / `share_ticket`, no domain `NamespaceId` — plus the pair type `ConnectionMetadata { own, peer }` (D1, D2)
- [x] 1.2 Grants surface on the store: publish a grant (`grants/<issuer-hex>/ticket`, the `/cap` slot reserved and unwritten), read one (payload-waiting, mirroring the directory's ticket reads), list, withdraw (tombstone); capability payloads opaque at this layer (D7)
- [x] 1.3 Store-level scenario tests: dedicated replicas (creation, the two directions distinct, per-connection isolation), the own→peer flip, import-binds-before-content, grant round-trip, a grant published after establishment with no new pairing, a withdrawn grant reading absent, payload-waiting reads, replication across both identities' devices (issuer's phone → issuer's laptop and both counterparty devices), last-writer-wins convergence
- [x] 1.4 Access pairs per the access-control-tests practice: the issuer's second device writes via the directory's write ticket ⟷ the counterparty holding only the read ticket cannot write; the counterparty reads the whole store ⟷ a third identity (itself sharing state with the issuer) holds no replica of the pair, no ticket, and nothing revealing its existence

## 2. The pairing protocol (`pdn-node`)

- [x] 2.1 Pairing module: the 32-byte secret (operating-system generator), the pending-invite set keyed by secret bytes and bound to the inviting identity, lazy expiry (checked at presentation, swept at the next invite), default lifetime 120 s with an invite-time override (D4)
- [x] 2.2 The invite payload (format version, inviter node address, secret, inviter `PdnId` — no tickets, no identity proof) and the two length-prefixed postcard wire messages; the scanner refuses an unknown payload version before dialing (D5)
- [x] 2.3 Accept side (the protocol handler): read the request → atomic verify-and-burn under the runtime lock *before any state* → create-or-reuse `own` via the directory lookup → import the scanner's ticket as `peer` (the scanner's node address supplements the first-sync contacts) → connections entry + directory kinds → respond with the own read ticket; refusals uniform (close without a distinguishing answer); a wrong secret burns nothing (D3, D4)
- [x] 2.4 Dial side (`establish`): version check → dial through the data-layer dial handle on the pairing ALPN → send the request, receive the response → the same state assembly as 2.3's, mirrored
- [x] 2.5 `Runtime::spawn` threads the handler through `SyncNode::spawn_with_protocols` with a late-bound state slot (a dial before the slot is filled is refused; unreachable in the honest flow); pdn-node stays free of a direct iroh dependency via the data-layer re-exports (D6)
- [x] 2.6 Dependencies: `postcard` as a direct pdn-node dependency (per-crate, matching the in-tree 1.1.3 from pdn-store; only the iroh stack is workspace-pinned); `rand` is already a direct dep

## 3. The service surface (`pdn-node`, BREAKING)

- [x] 3.1 `ConnectionsService` reshaped: `invite` / `establish` / `list` plus the grant surface (publish a grant of a hosted issuer's namespace toward a peer; read a peer's grants), `record` removed; the metadata pair opens on demand from directory tickets and is cached per (identity, peer) (D3, D8)
- [x] 3.2 Existing pdn-node tests that drove `record` rewritten onto establishment (two in-process runtimes, the invite payload passed as a value)
- [x] 3.3 `pdn-node-http`: demo scaffolding referencing the removed operation adjusted (scaffolding, unpinned by spec); the specced surface (`/live`, env) untouched
- [x] 3.4 Code docs updated: the connections-service docs (establishment is the producer now), the runtime docs (the pairing handler threads at spawn — the anticipated slot is consumed)

## 4. Establishment scenario tests (`pdn-node`)

- [x] 4.1 Full establishment between two runtimes (scenarios "Establishment completes between two runtimes", "Both sides list each other", "The payload carries no bearer material", "Every invite carries a distinct secret"), then the grant flow end to end (core scenario "A grant crosses to the peer with no new pairing"): publish a grant, read it on the peer, import through the data service, read the entries
- [x] 4.2 Device visibility (scenario "The connection is visible from linked devices"): two identities × two devices — pairing on the phones, both laptops list the counterparty and read the counterpart's store from the directory-opened pair
- [x] 4.3 Re-establishment (scenarios "Establishing twice yields one connection", "The retry may swap directions"): a second establishment from a fresh invite, once direction-swapped — one connections entry per side, the own store is the same replica both times, no duplicate replicas
- [x] 4.4 Refusal pairs (scenarios of the verify-and-burn requirement, per the access-control-tests practice): a replayed secret; an expired secret (tiny invite-time lifetime); a wrong secret that burns nothing (the real secret still establishes afterwards); each refusal probed for no observable state on the inviter (connections list, directory kinds, hosted replicas unchanged); an unknown payload version refused before dialing; unknown-identity refusals for invite and establish

## 5. Spec-tree and ADR edits (manual, not deltas)

- [x] 5.1 `components/pdn-node/invariants.md`: append Invariant 3 — the store is written only by the issuing identity's devices, read only by those and the connection counterparty's devices, and to every other party it does not observably exist; mechanism paragraph (ticket routing through the two directories and the establishment dialogue; the namespace identifier travels nowhere else; the bearer caveat as in Invariant 1)
- [x] 5.2 `architecture/language/connection.md` rewritten to the accepted model: a connection is between two identities, owned by neither — mutual connections-store records plus the exchanged metadata pair; being connected grants no data access (capabilities do, per record); link the term's first use in ADR-0011 and in both new specs to the glossary; re-check the entries and ADRs that link `connection.md` (`relying-party.md`, ADR-0007) still read true against the new text
- [x] 5.3 ADR-0011: append the re-establishment case to Validation (fresh invite after a post-burn failure converges with no duplicates — the property its Consequences claim); point the forward reference "the connection metadata store proposal" at the archived spec; strike the open questions this change resolves (secret entropy and lifetime → D4; mid-dialogue failure handling → D3 and re-establishment; where the handler lives and the data-layer API → landed); status already flipped to `accepted` (2026-07-15)
- [x] 5.4 Sweep the spec tree and the active changes (subset-rbsr, reconcile-trigger) for statements this change invalidates: "recording is the current producer / establishment becomes a producer in a later change" anywhere outside the delta, phrasing that treats the extra-protocols slot as unconsumed, and subset-rbsr's swarm language (the metadata-store counterparty is a whole-store reader and a legitimate swarm member — its D4/D5 must stay consistent with the new spec)
- [x] 5.5 CLAUDE.md crate rows: `data-layer` gains the connection metadata store (and the pairing slot reads as consumed), `pdn-node` gains establishment (invite / establish / grants in place of record)

## 6. Wrap-up

- [x] 6.1 `just precommit-check` green across the workspace
- [x] 6.2 Flaky-test stress pass per the flaky-tests practice (`just stress`, loopback-bound): `connection_metadata` — the binary that exposed the parked-content race — in a counted loop (×300), then every other scenario binary together (×100); any failure is a defect of this change, diagnosed in isolation before anything is built on top. (First sizing — establishment+metadata ×300, adjacent ×20 — ran pre-fix to 303 ok / 1 FAIL, the parked-content reproduction.)
- [x] 6.3 `openspec validate --all --strict` passes for the change
