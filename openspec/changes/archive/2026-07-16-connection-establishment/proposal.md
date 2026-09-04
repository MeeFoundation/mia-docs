# Proposal: connection-establishment

## Why

Two identities that have never met cannot become connected today: the runtime records a connection assertion locally (one-sided, no counterparty involved), but nothing creates the mutual state a connection actually is — each side knowing the other, and each side holding the channel through which every later grant, ticket, and revocation travels. ADR-0011 fixed the dialogue (pairing over a raw iroh connection on a dedicated application-layer protocol negotiation identifier) and defers the store-level realization to "the connection metadata store proposal" — this is that proposal. The assembly surface the dialogue plugs into (sync-node-extra-protocols) is landed and waiting; this change builds the protocol and the store it exchanges tickets to.

## What Changes

- **`data-layer` gains the connection metadata store.** Two replicas per connection, one per direction. The replica issued by identity A toward its connected counterparty B is written only by A's devices and read, whole, by B's devices — a new invariant (Invariant 3). In code the pair is `ConnectionMetadata { own, peer }`: `own` is the replica this side issues (created by it, write ticket in its directory), `peer` is the counterpart's (imported from the read ticket received at establishment) — the same replica is `own` at its issuer and `peer` at the counterparty. Same mechanism as the other device stores: a dedicated pdn-store replica plus ticket possession, no new sync machinery. Grants ride inside: entries keyed by data-store issuer carrying, for now, the interim whole-store ticket; the capability payload slot is reserved for the read-capability mechanism (subset-rbsr, then ADR-0007).
- **`pdn-node` gains the pairing protocol (ADR-0011).** Invite mints a one-time random secret with a short lifetime and a self-contained payload (format version, inviter node address, secret, inviter PdnId — no tickets, no identity proof); the scanner dials the pairing ALPN and the two sides run the raw bidirectional exchange: secret + PdnId + node address + read ticket one way, read ticket back. The inviter atomically verifies-and-burns the secret before creating or writing any state, so a refused attempt leaves nothing observable. The handler registers at `Runtime::spawn` through the data-layer assembly slot — the parameter addition sync-node-extra-protocols deferred to exactly this change.
- **Establishment is idempotent; re-establishment is clean.** A handshake that dies after the burn is retried with a fresh invite: each side's own metadata replica per counterparty is created once and reused (looked up through the directory), connections entries are keyed by peer, and importing the same replica twice converges — no duplicate connection, no duplicate replicas, invite direction irrelevant.
- **BREAKING: the connections service drops manual recording.** `invite` / `establish` / `list` plus the grant surface (publish a grant toward a peer, read the grants a peer published) replace `record`: establishment is the producer of connections, and a one-sided record contradicts the connection model (mutual knowledge plus exchanged metadata replicas; see the glossary rewrite below). pdn-node is pre-release; affected tests are rewritten onto establishment.
- **The private-metadata directory carries the pair's tickets; routing stays separate from grants.** The own write ticket and the counterpart read ticket are published under per-connection kinds, so linked devices open the pair on demand — establishment done on the phones is visible from the laptops. Tickets to another identity's data stores are never copied into the directory: they live only inside connection metadata stores, so a revoked grant never survives in a stale copy.
- **Invariant 3 is appended** to the invariants list: written only by the issuing identity's devices; read only by those and the connection counterparty's devices; to everyone else the replica does not observably exist. Invariants 1 and 2 do not cover this store — Invariant 1's audience is own-devices-only, Invariant 2 governs claims under read capabilities, and the metadata store is deliberately read by the counterparty under a ticket alone.
- **Glossary and ADR-0011 maintenance.** `architecture/language/connection.md` still describes the pre-pivot model (a User↔Relying-Party relationship mediated by an Identity Agent) and is rewritten to the accepted one: a connection is between two identities, owned by neither, and being connected grants no data access by itself. ADR-0011 gains the re-establishment case in Validation (claimed in its Consequences, absent from Validation) and its forward reference to this proposal is resolved.

## Out of Scope (deferred)

- **KERI proof of control over the presented PdnId** — remains a marked step of the dialogue; the exchange stays bearer-level, consistent with ADR-0008's interim posture.
- **Pending / offline invitations** — both peers online, per ADR-0011.
- **The reactive bootstrap cascade** — watching the directory and metadata stores and auto-importing whatever grants point at. This change opens the metadata pair on demand (at establishment on the pairing devices; from directory tickets on the others) and reads grants when asked; the subscription-driven orchestration is its own change.
- **Read capabilities and filtered reconciliation** — subset-rbsr. Grant entries carry the interim whole-store ticket; the capability slot stays reserved.
- **Data-service cleanup** — the out-of-band whole-store share/import surface (pdn-node-runtime design D4) stays until subset-rbsr rewrites data sharing onto capability-scoped grants; this change merely makes the metadata store the honest transport for the same interim ticket.
- **Device linking over the pairing dialogue** — re-basing `link_device` onto the same ceremony is a separate, later change.
- **QR encoding and rendering** — the invite payload is a versioned value; its string/QR form is a host concern for the demo stand.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive each spec lands in the component tree.

| Capability (delta)                     | Archive destination                                              |
| -------------------------------------- | ---------------------------------------------------------------- |
| `data-layer-connection-metadata-store` | `openspec/specs/components/mee-pdn/data-layer/connection-metadata-store.md` |
| `pdn-node-connection-establishment`    | `openspec/specs/components/mee-pdn/pdn-node/connection-establishment.md` |
| `pdn-node-core`                        | `openspec/specs/components/mee-pdn/pdn-node/core.md`                     |
| `data-layer-private-metadata-store`    | `openspec/specs/components/mee-pdn/data-layer/private-metadata-store.md` |

### New Capabilities

- `data-layer-connection-metadata-store`: the store — one replica per direction of a connection, own/peer assembly from exchanged tickets, issuer-writes / counterparty-reads access (Invariant 3), grants keyed by data-store issuer with the interim whole-store-ticket payload, replication across both identities' devices, last-writer-wins, payload-waiting grant reads.
- `pdn-node-connection-establishment`: the procedure — invite payload and one-time secret, the raw dialogue on the pairing ALPN, atomic verify-and-burn before any state, the establishment outcome across both identities' devices, idempotent re-establishment, refusals that leave no observable state.

### Modified Capabilities

- `pdn-node-core`: the connections-service requirement — establishment (invite / establish) replaces manual recording as the producer; the service carries the grant surface over the metadata pair; listing and unknown-identity refusals stay.
- `data-layer-private-metadata-store`: the typed-tickets requirement gains the per-connection kinds for the metadata pair; a new requirement pins the routing/grants boundary (no tickets to another identity's data stores in the directory).

### Non-capability spec edits (tasks, not deltas)

- `components/mee-pdn/invariants.md`: append Invariant 3 (append-only list; referenced by number).
- `architecture/language/connection.md`: rewrite to the accepted model; link the term's first use in ADR-0011 and the two new specs; re-check the entries that link it (`relying-party.md`, ADR-0007).
- `architecture/adr/0011-pairing-over-raw-iroh.md`: append the re-establishment Validation case; point the forward reference at the connection-metadata-store spec; strike the open questions this change resolves (secret entropy and lifetime, mid-dialogue failure handling, the handler's home). Status stays the maintainer's call.

## Impact

- **`crates/data-layer`**: new `connection_metadata.rs` (store, pair type, grants surface); no changes to existing stores or the assembly (the extra-protocols slot is consumed, not modified); store-level scenario tests with paired denials per the access-control-tests practice.
- **`crates/pdn-node`**: new pairing module (secret, invite payload, wire messages, protocol handler plus dial side); `Runtime::spawn` threads the handler through `spawn_with_protocols` with late-bound shared state; connections service reshaped (**BREAKING** trait change); existing connections tests rewritten onto establishment; new establishment scenario tests.
- **`crates/pdn-node-http`**: compile-level fallout only where its demo scaffolding referenced the removed operation — adjusted as scaffolding, not specced.
- **Dependencies**: `postcard` (wire messages) becomes a direct `pdn-node` dependency, together with `serde` (derive) that its message types require; `rand` (the secret) already is one. `postcard` (1.1.3) is already in the tree transitively via pdn-store and is added per-crate — only the iroh stack is workspace-pinned.
- **pdn-store fork**: planned untouched; implementation surfaced an inherited upstream liveness gap the new scenario tests exposed, fixed in the fork (see the design's discovered-during-implementation notes): content whose record traveled ahead of its bytes was re-requested only by one best-effort gossip broadcast — now every successful sync also retries the namespace's parked content against the just-synced peer. Upstream PR to iroh-docs to follow.
- **Docs**: Invariant 3, the glossary rewrite, ADR-0011 Validation / More Information edits; a sweep of the spec tree and the active changes (subset-rbsr, reconcile-trigger) for statements this change invalidates — e.g. "recording is the current producer" in `mee-pdn/pdn-node/core.md` and in the code docs.
- **Tests / stress**: the change touches sync and node wiring — it ends with a counted stress pass over the new and adjacent scenario tests per the flaky-tests practice.
