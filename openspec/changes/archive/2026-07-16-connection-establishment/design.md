# Design: connection-establishment

## Context

What exists. `data-layer` runs the device-internal half of an identity's world: the connections store and the private-metadata directory (Invariant 1), provisioning and single-seed device linking, and — since sync-node-extra-protocols — a spawn-time slot for externally supplied protocols on the node's one endpoint plus a narrow `DialHandle` for the dial side and the node's own address. `pdn-node` owns node assembly in one place (`Runtime::spawn`, its design D5) behind one coarse state lock, and its connections service today only records a connection assertion locally. ADR-0011 fixed the establishment dialogue — a raw bidirectional exchange on a dedicated application-layer protocol negotiation (ALPN) identifier, with a one-time secret verified and burned atomically — and deferred the store-level realization to this proposal.

Constraints carried in from ADR-0011 and the platform posture: nothing bearer-grade in the invite payload (it is semi-public, and the counterparty is unknown when it is minted); an atomic verify-and-burn with one authoritative side, before any state change; the road to capability-first authorization stays open — being connected must not mean seeing data, so what the connection carries is a channel for grants, not access itself.

A pdn-store fact the access story rests on: a replica's namespace identifier is itself the read capability (whoever knows it can sync the replica), and the namespace secret key is the write capability; tickets bundle a capability with node addresses. Hiding a replica's existence therefore means its identifier travels only where intended — in this design: inside the pairing dialogue and the two identities' directories, nowhere else. This is the same bearer-token caveat Invariant 1 already states; identity-bound access lands with UWill.

## Goals / Non-Goals

**Goals:**

- The connection metadata store: one dedicated replica per direction of a connection, written only by the issuing identity's devices, read whole by the counterparty's devices (Invariant 3), carrying grants that outlive the pairing moment — publish more, or withdraw, with no new pairing.
- The establishment dialogue end to end on the runtime, per ADR-0011: invite, dial, atomic verify-and-burn, ticket exchange, and the recorded outcome on both sides — with refused attempts leaving no observable state on the inviter.
- Establishment made on one device of each identity visible from all their devices, through the directory.
- Clean re-establishment: a handshake that dies after the burn is retried with a fresh invite and converges — no duplicate connection entries, no duplicate replicas, whichever side invites.
- Access tests paired with their tightest denials (access-control-tests practice); a counted stress pass at the end (flaky-tests practice).

**Non-Goals:**

- The KERI proof of control over a presented PdnId (a marked step of the dialogue, deferred; the exchange is bearer-level, ADR-0008's interim posture).
- Pending or offline invitations — both peers online.
- The reactive bootstrap cascade (watching the directory and the metadata stores, auto-importing granted data stores); this change opens stores on demand.
- Read capabilities, filtered reconciliation, and the data-service rewrite onto capability-scoped sharing — subset-rbsr.
- Re-basing device linking onto the pairing dialogue.
- QR string encoding and rendering (host concern; in-process the invite payload is passed as a value).

## Decisions

### D1. Two replicas per connection, one per direction

The store issued by A toward B is a different replica from the one issued by B toward A; at each side the pair is held as `ConnectionMetadata { own, peer }` — `own` the replica this side issues and writes, `peer` the counterpart's, imported read-only. The alternative — one shared replica with both parties writing, roles distinguished by an access-level marker — is rejected by the ADR-0009 argument in miniature: a shared store with two writers forces per-entry write authorization and per-entry read discipline out of the structure and into code, while per-direction replicas encode "one side writes, the other reads" in the replica boundary itself; the third party is cut off by ticket possession either way, so the shared store buys nothing. A consequence worth naming: the counterparty is the audience of the *whole* replica, so no per-entry filtering is ever needed inside a connection metadata store — it is buildable on today's stack, and consistent with subset-rbsr's swarm rule (the counterparty is a legitimate whole-store reader; capability-scoped readers exist only for data stores).

### D2. The pair assembles during the dialogue; content converges after

Each side creates its `own` replica and hands the counterpart a read ticket inside the dialogue; each imports the received ticket as its `peer`. Import binds the local replica to the issuing namespace immediately — it is not "create empty, attach later" — and starts background sync, so the pair is structurally complete when the dialogue ends even though `peer`'s content arrives asynchronously. Grant reads are therefore payload-waiting and polled, exactly like the directory's ticket reads during linking (`wait_for_ticket` precedent). The node address the scanner sends in its half (part of ADR-0011's message shape) supplements the ticket's own address list as a first-sync contact.

### D3. Idempotency is keyed through the directory

An identity's `own` replica toward peer `P` is created once per (identity, `P`) and thereafter *looked up*, never re-created; the lookup lives in the private-metadata directory under per-connection kinds — `connection-metadata/<P-hex>/own` (the write ticket: every device of the issuer writes grants) and `connection-metadata/<P-hex>/peer` (the received read ticket). This one decision carries three properties: re-establishment reuses the same replica (tickets handed out on different attempts address the same namespace — no duplicates); the key is the counterparty, not the invite direction, so it converges whichever side invites the retry; and linked devices open the pair from the directory on demand (both entries are imports — the write ticket carries the write capability), which is how establishment made on the phones reaches the laptops. The alternative — an in-memory establishment registry — is rejected: it dies with the process and is not device-replicated, so the laptops could never open the pair. The connections-store half of the outcome is idempotent already (one entry per peer, last-writer-wins), and importing the same namespace twice converges onto one local replica.

### D4. Secret mechanics: burn on match, expire lazily, refuse uniformly

The secret is 32 random bytes from the operating-system generator; the default lifetime is 120 seconds, overridable at invite time (tests, hosts). Pending invites live in runtime memory keyed by secret bytes, each bound to the identity it invites for (a runtime hosts several). Verify-and-burn is a single map operation under the runtime lock: present and unexpired → remove and proceed; expired → remove and refuse; unknown → refuse — and it runs *before* any store is created or any entry written, which is the whole of the no-state-on-refusal property. Expiry is lazy — checked at presentation, swept at the next invite — no background task. A wrong secret does not burn a live invite: guessing must not extinguish a ceremony in progress, and an attacker gets one 256-bit guess per connection with no partial-match oracle, so map lookup is not a usable timing channel. All refusals look identical to the dialer (the connection closes without a distinguishing answer): a prober cannot separate wrong from expired from already-burned. Runtime restart drops pending invites — acceptable: an invite is a live ceremony, and a fresh invite is the recovery path for every failure anyway.

### D5. Wire shape: two postcard messages on one stream

One bidirectional stream per establishment, ALPN `/pdn/pairing/0`; two length-prefixed postcard messages: the scanner's request — format version, the secret, the scanner's PdnId, its node address, the read ticket to its `own` store — and the inviter's response — the read ticket to *its* `own` store. The version rides in the invite payload too, so a scanner refuses a payload it does not speak before dialing. postcard over hand-rolled framing or JSON: it is the compact, already-in-tree choice (pdn-store serializes with it), and the message set is two structs. The KERI proof is a marked slot in both messages' successors, not built.

### D6. The handler is runtime code with late-bound state

pdn-node constructs the pairing handler and threads it through `SyncNode::spawn_with_protocols` inside `Runtime::spawn` — the parameter addition pdn-node-runtime's D5 anticipated and sync-node-extra-protocols deferred to exactly this change. The handler is built before the node exists (extra-protocols D1), so it captures the pending-invite set plus a late-bound slot for the shared runtime state, filled right after spawn; a connection arriving before the slot is filled is refused (unreachable in the honest flow — no invite payload exists before spawn returns). Both the accept side and the dial side take the runtime's one coarse lock for the assembly writes, following the documented precedent (linking holds it for its whole wait); establishment serializes with other services: a deliberate simplification, not a scalability claim, and the writes it holds the lock for are local — the network round-trip runs with the lock released. pdn-node stays free of a direct iroh dependency: the handler and dialer are written against `data-layer`'s re-exported types (`ExtraProtocol`, `DialHandle`, connection and address types).

### D7. Grants are keyed by data-store issuer; the interim payload is the whole-store ticket

Grant entries live under `grants/<issuer-hex>` — the ticket to that issuer's data store at `grants/<issuer-hex>/ticket`, the read capability at `grants/<issuer-hex>/cap`, *reserved* and unwritten until subset-rbsr. Tickets are data-layer vocabulary and are parsed here; capability payloads stay opaque bytes at this layer (their semantics live above — uwill, subset-rbsr). Keying by issuer gives delegated grants (sharing a third party's claims) a home for free later. The alternative — landing the store empty and deferring all grant content to subset-rbsr — is rejected: the routing/grants boundary (D8 of the flat model: no counterparty data tickets in the directory) would be vacuous with nothing riding the store, and data handover would stay on the out-of-band path the flat model exists to remove. This change moves the same interim whole-store ticket into the honest channel; subset-rbsr changes the payload, not the store.

### D8. Service surface: invite / establish / list / grants; manual recording removed

The connections service becomes: `invite` (mint a pending secret and payload for a hosted identity), `establish` (consume a scanned payload: dial and run the dialogue), `list` (unchanged), plus the grant surface — publish a grant of a hosted issuer's namespace toward a connected peer, and read the grants a connected peer has published (opening the pair from directory tickets on demand, per D3). `record` is removed rather than kept alongside: a one-sided record without a metadata pair manufactures exactly the half-connection the accepted model rejects (mutual knowledge plus exchanged replicas), and its only consumers are tests, which migrate to establishment. Reading a grant hands back the ticket; importing it stays an explicit data-service act (the reactive cascade is a later change).

## Risks / Trade-offs

- **[Coarse lock across establishment]** The accept and dial sides hold the runtime lock while creating stores and writing entries, so concurrent service calls wait. → Accepted as a deliberate simplification with documented precedent (linking); the writes under the lock are local — no network wait — and grant *polling* stays outside it, so only assembly writes hold it. Splitting the lock waits on measured contention.
- **[Reply loss after the inviter committed]** The inviter records the connection, the scanner never receives the response → one-sided state until a fresh invite (either direction) converges it. → Accepted, and exactly what D3 makes safe; the re-establishment scenario pins it.
- **[Existence hiding rests on identifier secrecy]** Knowing a namespace identifier is read capability in pdn-store, so "others do not observe the store" holds because the identifier travels only in the dialogue and the two directories. → Stated honestly in Invariant 3 with Invariant 1's bearer caveat; identity-bound access is UWill's.
- **[Directory and replica growth per connection]** Two ticket kinds and three replicas per connection accumulate on well-connected nodes. → Known scale axis, measured by the post-demo thousand-connections check; nothing in this change worsens the per-connection constant.
- **[New direct dependency]** `postcard` in pdn-node (`rand` is already a direct dep). → `postcard` (1.1.3) is already in the tree transitively via pdn-store; it is added as a per-crate direct dep of pdn-node, matching the convention that only the iroh stack is workspace-pinned.

## Migration Plan

1. `data-layer`: `connection_metadata.rs` — store type, pair type, grant surface — plus store-level scenario tests with paired denials. Purely additive.
2. `pdn-node`: the pairing module (secret, invite payload, wire messages, handler and dial side); `Runtime::spawn` threads the handler; the connections service trait reshaped; existing connections tests rewritten onto establishment; `pdn-node-http` demo scaffolding adjusted where it referenced the removed operation.
3. Docs: Invariant 3 appended; the connection glossary entry rewritten and linked; ADR-0011 Validation and More Information edits; sweep of the spec tree and the active changes for invalidated statements.
4. Stress pass over new and adjacent scenario tests; rollback is reverting the change — data-layer additions have no other consumers yet, and the pdn-node trait change is contained in pre-release code.

## Discovered during implementation

Three liveness gaps below this change's own layer surfaced through its scenario tests and were fixed alongside it — none alters the decisions above:

- **Replica starvation after a dead initial exchange (data-layer).** The engine records a peer as useful only after one successful exchange, so a doc whose first import exchange died had no recorded peer and the periodic reconcile pass re-dialed nobody — one transient failure starved the replica permanently. The reconcile pass now re-dials each doc's import-time contacts alongside the engine's recorded-useful peers.
- **Content starvation after a lost gossip broadcast (pdn-store fork; inherited from upstream iroh-docs, upstream PR to follow).** An entry whose record traveled ahead of its content bytes (relayed by a peer that had not fetched them yet) parked its hash, to be retried only when a best-effort `ContentReady` gossip broadcast arrived; a lost broadcast starved the content forever. Reproduced at roughly 0.7% per run by the four-device last-writer-wins scenario (1 failure in 303 runs). The fork now retries a namespace's parked content against every peer a successful sync finishes with, and parks hashes keyed by namespace so the retry and the `PendingContentReady` attribution stay exact.
- **Scenario tests bind loopback (`PDN_BIND_LOOPBACK=1`, set by the just recipes).** The host's filter on this development machine silently drops the first datagrams of every fresh UDP flow to the machine's own LAN address for seconds to minutes, which starves one-shot dials and made every in-process suite run nondeterministic. Bound to loopback the suites are hermetic and roughly an order of magnitude faster; production spawns leave the variable unset and bind all interfaces. Test-side hardening that stays regardless: the poll ceiling at 120 seconds, and success-path establishments retrying with the same live invite (`establish_patiently`) — the recovery ADR-0011 prescribes to the scanner.

## Open Questions

None blocking this change. How a read capability scopes a claim set (entry path versus claim id) and the capability payload format belong to subset-rbsr; the QR string encoding, size budget, and the linkability of the PdnId in the invite payload stay open with ADR-0011 (host and demo concerns this change does not touch).
