## Context

The proposal says why connections go. What shapes how is that pods were built beside connections, and in several places on the same machinery, so the removal is not a matter of deleting files: some of what connections own is what pods stand on.

- **The armer.** `spawn_connection_armer` in `crates/pdn-node/src/connections.rs` sweeps an identity's PMS on every change and every `sweep_interval`. One sweep binds the identity's data namespace, opens connection pairs, starts grant binders, applies retraction markers, confirms this device in the PMS (`ensure_own_device_confirmed`) and calls `crate::pods::arm_pods`, which is how a member's other devices and a restarted runtime open their pods. Linking and `create` start it, and so does restart recovery.
- **The ceremony machinery.** `crates/pdn-node/src/pairing.rs` holds the framing (`read_message`, `write_message`, `MAX_WIRE_MESSAGE_LEN`), the pending-invite set (`PendingInvites`), the state slot (`StateSlot`), `DEFAULT_INVITE_LIFETIME` and `InviterUnreachable`; `linking.rs` and `pods.rs` import all of them from there.
- **The session hooks in pdn-store.** A pod's store runs on the per-session egress predicate and ingest verdict that subset reconciliation added to pdn-store: a former member's device is served its departure's past through an `EntryFilter`, a dial toward a callee it serves nothing has a closed egress, and `WriteAdmission::Signed`, `Past` and `Rests` decide ingest per entry. The accept decision's recheck (`RestsOn`) reads the PMS and the membership store. Only `ValidateOutcome::Reject` — the rejection echoed to a writer so it retracts — and `retract_entry` serve grants alone: the access book returns `Reject` only for `WriteAdmission::Claims`.
- **Tests on the mechanism, through connections.** Many tests of mechanisms pods use reach them through a grant or the data namespace: the frozen session view, the hidden existence of a withheld entry, co-located sessions, persistence, blob collection, identity stacks, the change stream, the stop that waits for a serving half, and the stand's restart, kill and full-disk scenarios.
- **openspec rules.** A MODIFIED requirement may not drop a scenario the main spec holds (`findMissingCurrentScenarios`), so a requirement that loses a scenario is removed and added again under a new name; a capability whose every requirement is removed is retired, and the archive deletes its spec.

## Goals / Non-Goals

**Goals:**

- Every pod scenario behaves as before, proven by the same tests, which stay green at every step of the work.
- No test coverage of a mechanism that stays is lost: what a deleted test proved about a kept mechanism is proven by a rewritten test before the deletion.
- After the change, a grep for connection, grant, pairing, retraction, read capability, data namespace or UWill over the code, the specs, the ADRs and every `CLAUDE.md` finds an iroh connection or a word in its plain sense, and nothing else.

**Non-Goals:**

- No new pod behaviour, and no change to a pod's wire format, keys or membership rules.
- No migration of a state directory a build with connections wrote.
- No defence against a member's own contradicting history, and no gate on payload bytes served by hash.

## Decisions

### D1. Mechanics both kinds of store use move into one new capability; grant semantics retire

Subset reconciliation and capability-gated ingest retire with grants, and what they state about every session moves into one new capability, `components/mee-pdn/data-layer/reconciliation-sessions`, written for the PMS and a pod's stores: the per-session egress predicate and ingest verdict, the hidden existence of a withheld entry, own devices and current members served whole, the access decided at setup, the view frozen at setup, a removal travelling as its artefact, the bound in time, the content-free topic, the swarm as the store's device set, the uniform refusal, an entry affecting only its own key, the key bound and the future-timestamp window. Who a pod's store serves and what its entries count for stay in the pod stores spec, which the new capability points to. Every requirement that moves names its destination in its removal's reason.

**Example:** where three requirements of subset reconciliation go.

| requirement | after this change |
|---|---|
| A session serves a view frozen at session setup | reconciliation sessions, same name, without the rejection check |
| A granted replica serves the audience identity's devices | retired: grants go |
| Same-identity reconciliation is unfiltered | reconciliation sessions, as "An identity's own devices and a pod's current members are served whole" |

**Rejected alternatives:**

- Keep both capabilities, their requirements rewritten for pods
  - **Cons:** two capabilities named for a read capability and a capability gate that no longer exist, each reader astonished by the name before the text
- Fold the mechanics into the pod stores spec
  - **Cons:** the PMS shares every one of them, and the pod stores spec is already 884 lines on what a pod is

### D2. An identity's own data is a record in a pod of one

The identity's data namespace goes with the data service and the `data` ticket kind: an identity's store set is its PMS, and what it keeps for itself is a record in a pod it creates and invites nobody into. A pod of one is held whole by the identity's own devices — every device linked into it reaches it through the armer — and any of them reads and writes it through the pods service.

**Example:** Alice keeps her diary on her phone a1 and her laptop a2.

| step | call | result |
|---|---|---|
| once | `pods().create(alice)` on a1 | the pod "Alice", Alice its one owner and member |
| write | `put_record(alice, pod, MergeableDocument, …)` on a1 | the diary's first operation |
| read | `read_ops(alice, pod, diary)` on a2 | the operation, once the armer opened the pod on a2 and its stores converged |

**Rejected alternatives:**

- Keep the data namespace as an identity's own-devices store
  - **Pros:** a key-value surface by path, which a pod's records do not offer
  - **Cons:** a second store kind, with its own registry role, contacts, session rules and tests, held for a case a pod of one already covers

### D3. pdn-store keeps its session hooks and loses the rejection echo

pdn-store keeps the session access provider, the egress predicate, the ingest verdict, the accept recheck, `Doc::sync_with_peers`, `order_after` and every other divergence pods use. Its ingest verdict becomes two-valued — accept, or drop in silence — and the rejected-entry part of the sync message (`MessagePart::Rejected`, `RejectId`), the rejection sink, the `would_insert` check behind it and `retract_entry` go. The standing validator outside sessions (`CapabilityValidator`, installed by the data layer as `capability_ingest_validator`) goes too: with no data replica left it accepts every entry, which is what the store's own `validate_entry` does without it. The crate's `CLAUDE.md` names the divergence that remains, and the change ends with the pdn-store checks and a stress pass.

**Example:** the verdicts a pod's store returns today and after the change, for an entry a former member's device offers.

| entry offered | today | after |
|---|---|---|
| inside the departure's past | `Accept` | `Accept` |
| outside it | `Drop` | `Drop` |
| any entry, on any store | never `Reject` | `Reject` does not exist |

**Rejected alternatives:**

- Leave the rejection echo in place, unused
  - **Cons:** a divergence from upstream that serves nothing, a wire part no node sends, and tests that keep a dead path alive
- Remove the session hooks with grants
  - **Cons:** breaks a pod's departure past, its closed egress and its admission of signed entries

### D4. The dialogue machinery leaves the pairing module for a module of its own

What linking and a pod's join share moves from `pairing.rs` into `crates/pdn-node/src/ceremony.rs`: `read_message`, `write_message`, `MAX_WIRE_MESSAGE_LEN`, `PendingInvites`, `StateSlot`, `DEFAULT_INVITE_LIFETIME` and `InviterUnreachable`, the last one still public. The pairing handler, its ALPN, its payload, its errors, its in-process path and `pending_invites` go.

**Example:** the imports of `pods.rs` before and after.

```
before:  use crate::pairing::{read_message, write_message, InviterUnreachable, DEFAULT_INVITE_LIFETIME, MAX_WIRE_MESSAGE_LEN};
after:   use crate::ceremony::{read_message, write_message, InviterUnreachable, DEFAULT_INVITE_LIFETIME, MAX_WIRE_MESSAGE_LEN};
```

**Rejected alternatives:**

- Keep `pairing.rs`, emptied of pairing
  - **Cons:** a module named for a ceremony that does not exist, which every reader of linking and pods follows to find their framing
- A copy of the framing in each ceremony
  - **Cons:** two framings that can drift, and the frame ceiling stated twice

### D5. The armer keeps its two pod duties, under a name of its own

The armer stays: one sweep per PMS change and per `sweep_interval`, which confirms this device in the PMS when the confirmed set lacks it and opens every pod whose PMS record its holding here does not match (`arm_pods`). It moves from `connections.rs` to `crates/pdn-node/src/armer.rs` as `spawn_identity_armer`; binding the data namespace, opening pairs, starting grant binders and applying retraction markers go. The specs already call it "the armer".

**Example:** what one sweep of Alice's armer on her laptop a2 does after the change.

| read from Alice's PMS | the sweep |
|---|---|
| `devices/` without a2 | writes `devices/<a2-hex>` |
| `pods/ad58a3faa04cdc5576c8dc5823a347c6/1`, the pod not open on a2 | opens both stores from `tickets/pod/ad58a3faa04cdc5576c8dc5823a347c6/…` |
| nothing else | — |

**Rejected alternatives:**

- Fold the sweep into the pods module
  - **Cons:** the device confirmation is linking's repair, not a pod's, and a pods module that confirms devices is the next wrong home

### D6. `pdn-layer` keeps its domain draft without connections, capabilities, delegation or UWill

`pdn-layer` stays as the domain layer the workspace reserves, and loses what serves connections: `Invite`, `Connection`, `ConnectionId`, `Capability`, `AccessMode`, `DelegatedClaim`, the `uwill` module, the capability field of `Claim`, the connection a `WriteClaim` names, and the connection, delegation and per-issuer sync operations of `PdnOp`. What stays is the identity and device operations, `Claim` with its attribute and the claim operations. `pdn-types` loses the items left without a consumer — `NonEmpty`, `Aid`, `NamespaceRole`, `NodeAddr`, and `EntryPath`, `EntryInfo` and `PathValidationError` once the data service and the data layer's entry operations are gone — and keeps `ClaimId`, `OperationalKey` and `PdnIdentityProof`, which the remaining draft names.

**Example:** `PdnOp` before and after, by section.

| section | before | after |
|---|---|---|
| identity and devices | 5 operations | the same 5 |
| connections | 5 operations | gone |
| claims | 4 operations, `WriteClaim` naming a connection | 4 operations, `WriteClaim` naming none |
| delegation | 3 operations | gone |
| discovery and sync | `SyncOnce { issuer }` | gone |

**Rejected alternatives:**

- Delete the crate
  - **Pros:** nothing consumes it
  - **Cons:** removes the domain layer the workspace's layering names, and its identity and claim draft, which serve no connection

### D7. Six ADRs become obsolete, two new ones carry what pods need of them

ADR-0004, ADR-0007, ADR-0008, ADR-0009, ADR-0010 and ADR-0011 become obsolete stubs: the question each answered — how grants name their audience, what capability format grants grow into, how an ingest gate judges a grant's writer, how an issuer's data is addressed, how a read capability narrows a session, how two identities become connected — goes away with connections. ADR-0014 records the decision pods still need from ADR-0008 and ADR-0010: pdn-store is our variant of iroh-docs whose every session the embedder judges, by an egress predicate and an ingest verdict the store applies without knowing their meaning. ADR-0015 records what pods need from ADR-0011: a pod's join is its own dialogue on its own ALPN, over a raw iroh connection, with a one-time secret verified and burned before any state changes and nothing bearer-grade in the invite. ADR-0002, ADR-0003, ADR-0012 and ADR-0013 keep their decisions and are edited where they name connections, grants, the data namespace or pairing. Every citation of an obsolete ADR in the tree moves to the ADR that answers its question now, or goes.

**Example:** where the citations of ADR-0008 go.

| cited in | after |
|---|---|
| `pdn-store/crate/spec.md`, the store's divergence | ADR-0014 |
| Invariant 2, the read side's counterpart of the ingest gate | ADR-0014 |
| ADR-0012, the bearer posture the KERI step keeps | the sentence states the posture itself |

**Rejected alternatives:**

- Mark the six superseded by the new ADRs
  - **Cons:** a superseded ADR keeps every word, so the tree keeps six records of connection decisions for a reader to discount; and the new ADRs answer different questions, so "superseded" would claim a continuity that is not there
- Edit the six in place to describe pods
  - **Cons:** an ADR is the record of one decision; rewritten to a different decision it keeps its number and loses its meaning

### D8. Invariant 3 goes, Invariant 2 states acquisition by membership

Invariant 3, on connection metadata stores, goes, and its number is not reused. Invariant 2 is rewritten: a node obtains an entry of a pod's store only while it is a device of a current member, except a former member's device, which is served its departure's past; acquisition, not retention, as before, and payload bytes held back only as far as their hash is. Invariant 1 loses the connections records from the PMS's contents and the sentence on UWill. Code that cites "Invariants 1 and 3" cites Invariant 1.

**Example:** the three invariants after the change.

| invariant | states |
|---|---|
| 1 | an identity's PMS is reachable only by its own devices, bounded by its ticket |
| 2 | a node obtains a pod's entry only while it is a device of a current member, a former member's device its departure's past alone |
| 3 | — |

**Rejected alternatives:**

- Renumber the invariants
  - **Cons:** every code comment and spec citing Invariant 2 by number changes for nothing

### D9. The code practices are written on pods

`access-control-tests.md` keeps its ladder on pods: for read, an outsider holding no ticket and no membership, then a holder of the stores' tickets who is no member — a removed member, or an identity handed the tickets — neither receiving an entry or the fact that it exists; for write, a lower level — a plain member against an owner's act, a member under another member's name. `product-path-arrangement.md` arranges on the pod path — invite and join, the armer opening a pod on a sibling — admits a hand-made `import_pod` only where the import is the subject or the ticket holder is the negative control, and names a pods test as its worked example in place of `sibling_serving.rs`. `operating-conditions.md` names membership acts — invited and joined, promoted and demoted, removed, left and joined again — where it named capabilities granted, narrowed, widened, revoked and granted again. The other practices lose their connection examples. The workspace `CLAUDE.md` and the openspec context repeat these summaries and follow them.

**Example:** the read ladder on "Family", for a claim Bob placed.

| party | holds | receives |
|---|---|---|
| Carol, a current member | membership, both tickets | the claim |
| Dave, removed before the claim | both tickets, no membership | nothing, and nothing says the claim exists |
| Erin, an outsider | nothing | nothing |

**Rejected alternatives:**

- Leave the practices on grants until a later pass
  - **Cons:** every review and every change in between is held to rules naming parties that no longer exist

### D10. Tests move onto pods before anything is deleted, then the code goes layer by layer from the top

The work runs in phases, each green under `just check` and `just test`. First every test that reaches a kept mechanism through a connection, a grant or the data namespace is rewritten onto a pod or the PMS while the old path still exists, each rewrite checked to fail with its mechanism broken. Then the code goes from the top down — the HTTP host and the stand, pdn-node, data-layer, pdn-store, pdn-layer and pdn-types — taking with each layer the tests whose subject it removes. The documents follow the code, the sweeps follow the documents, and a stress pass over the affected scenarios ends the change.

**Example:** one test through the phases: `two_identities_of_one_node_write_as_two_authors` in `crates/data-layer/tests/co_located_identities.rs`.

| phase | the test |
|---|---|
| port | rewritten onto two members of one pod on one node; checked to fail with a per-node author forced, then restored |
| data-layer removal | still green; its old grant arrangement is gone with it |
| stress | in the pass over `co_located_identities.rs` |

**Rejected alternatives:**

- Delete first, rewrite what breaks
  - **Cons:** a test deleted with its file takes its property with it unnoticed, and a rewrite after the deletion has no old path to be checked against
- One change per layer
  - **Cons:** the spec tree would say a layer was gone while the code above still used it, or the reverse

### D11. Archived changes about removed mechanisms are deleted; the others are swept

An archived change whose subject this change removes is deleted, git keeping it, as an obsolete ADR's text is kept: `2026-06-17-connections-store-gate-read`, `2026-06-30-per-issuer-namespace`, `2026-07-16-connection-establishment`, `2026-07-20-subset-rbsr`, `2026-07-23-serve-granted-to-audience-devices`, `2026-07-24-capability-scoped-writes`, `2026-07-31-product-path-gaps` and `2026-08-24-own-grant-read`. In every other archived change the decisions and measured claims that describe a removed mechanism as the platform's are rewritten as present state or deleted; a proposal's Why, which records the state its change started from, stays as written, and no archived delta is touched.

**Example:** what happens to three archived changes.

| archived change | after |
|---|---|
| `2026-07-24-capability-scoped-writes` | deleted |
| `2026-10-05-pods` | D30 and D34 no longer make the removal wait for the mobile integration or for anchored history; D30's coexistence becomes the platform with pods alone |
| `2026-08-19-disk-persistence` | its Why keeps "the connections it established"; a decision naming the connection armer names the armer |

**Rejected alternatives:**

- Leave the archive as it is
  - **Cons:** archived prose is kept true by the workspace's rule, and a reader reconstructing a decision would meet grants as the platform's present
- Rewrite every archived change, deleted ones included
  - **Cons:** rewrites the history of mechanisms that no longer exist, for no reader

### D12. Active changes about connections are deleted; the rest are swept

`reconcile-trigger` and `retraction-marker-lifetime`, whose subjects are grants and retraction markers, are deleted, and so are `mobile-host-surface` and `mobile-demo-app`, whose application lives outside this tree. `unclassified-connection-bounds` concerns iroh connections and stays. Every other active change is swept for what it says of connections, grants, the data namespace, pairing or retraction, and rewritten as if this change were merged; the change whose proposal makes the defence of a member's own history land before connections are removed keeps the criterion behind that ordering — before any pod carries data people depend on — and loses the ordering.

**Example:** what the sweep does in three active changes.

| active change | after |
|---|---|
| `reconcile-trigger` | deleted |
| `wire-format-versioning` | the dialogues it lists are linking and the pod join; pairing's ALPN and `UnsupportedInviteVersion` go |
| `blob-egress-gate` | its cases are a removed member's device and an outsider holding a hash; a grant's audience goes |

**Rejected alternatives:**

- Keep `reconcile-trigger` and rewrite it for pods
  - **Cons:** its problem is a grantee outside the swarm, which a pod has no counterpart of: a pod's member devices form its swarm

### D13. A directory a build with connections wrote is not supported

A build of this change opens no state directory an earlier build wrote with connections in it: no migration reads the connections records, the `data` ticket, the retraction markers or the connection metadata replicas, and nothing guarantees such a directory starts. The stand and the demos already start each run on fresh state, and a developer's directory is deleted before the first run of this build.

**Example:** a directory written by a build with connections, started by this build.

| on disk | this build |
|---|---|
| `identities/<alice-hex>/pms` | read, as before |
| `connections/<bob-hex>`, `tickets/data`, `retractions/…` in her PMS | never read |
| the data namespace and the metadata pair in her `docs.redb` | never opened |

**Rejected alternatives:**

- Migrate on start
  - **Cons:** code written to run once, on directories that exist only on developers' machines and the stand, both of which start fresh anyway

### D14. A retired capability's spec is deleted by hand, and where its requirements go is recorded here

openspec retires a capability only when its spec holds requirement statements and scenarios alone, and every one of the eight retired specs carries example tables, which the archive refuses to delete with the file; a REMOVED delta against a spec already deleted is refused in turn. The eight specs are therefore deleted from the main tree in the archive task, with no delta of their own, and this table is the record of where each requirement goes; a trial archive in a scratch copy, with the eight deleted first, applies every other delta and leaves 16 main specs passing `openspec validate --specs --strict`.

**Example:** the destination of every retired requirement.

| retired capability | requirement | after this change |
|---|---|---|
| `data-layer/subset-reconciliation` | Reconciliation reveals only read-authorized claims | reconciliation sessions: "What a session's egress withholds is hidden, not merely undelivered" |
| | Withheld claims are hidden, not merely undelivered | the same |
| | Delivery is gated before transfer | the same |
| | The filter runs in pdn-store on the read side | reconciliation sessions: "A session's egress and ingest are decided above the store, per session" |
| | Same-identity reconciliation is unfiltered | reconciliation sessions: "An identity's own devices and a pod's current members are served whole" |
| | The caller's rights are resolved once, at session setup | reconciliation sessions: "A session's access is decided at setup and holds for the session" |
| | A session serves a view frozen at session setup | reconciliation sessions, same name, without the rejection check |
| | A removal travels as the artefact it leaves | reconciliation sessions, same name, without retraction |
| | A session is bounded in time | reconciliation sessions, unchanged |
| | The gossip topic carries no content | reconciliation sessions, same name |
| | Grantees stay outside the gossip swarm | reconciliation sessions: "A store's swarm is its device set"; the grantee part goes |
| | A granted replica serves the audience identity's devices | goes with grants |
| | A granted replica reconciles with siblings as well as the issuer | goes with grants |
| | Unauthorized callers are refused uniformly | reconciliation sessions, same name |
| `data-layer/capability-gated-ingest` | Ingest into a hosted issuer's replica is capability-gated | goes with grants; the silent drop is in "A session's egress and ingest are decided above the store, per session" |
| | The write set is frozen per session | folded into "A session's access is decided at setup and holds for the session" |
| | Own devices and unarmed replicas are not narrowed | own devices: "An identity's own devices and a pod's current members are served whole"; the pod case is the pod stores spec's |
| | A key longer than the store's bound is refused on every replica | reconciliation sessions, same name |
| | Admitted writes compete by last-write-wins within a stated window | reconciliation sessions: "An entry dated beyond the future window is dropped on every replica" |
| `pdn-node/connection-establishment` | A stop lets the serving half in flight finish | pdn-node core: "A stop lets the serving half of every ceremony in flight finish" |
| | its other 7 requirements | go with connections and pairing |
| `data-layer/connection-metadata-store` | all 8 | go with connections |
| `data-layer/read-capabilities` | all 6 | go with grants |
| `data-layer/write-retraction` | all 5 | go with grants |
| `data-layer/data-store` | A write affects only its own path | reconciliation sessions: "An entry affects only its own key", which carries the refusal of a zero-length write from "Entries are opaque payloads at validated paths" too |
| | its other 8 requirements | go with the data namespace: an identity's own data is a pod of one (D2) |
| `pdn-node/namespace-addressing` | all 4 | go with the data namespace; a record is addressed by pod id and record reference ([pods](../../../specs/components/mee-pdn/pdn-node/pods/spec.md)) |

**Rejected alternatives:**

- REMOVED deltas with `retire_capabilities: true`
  - **Cons:** the archive refuses to delete a spec whose requirements hold tables, and every spec in the tree holds them by the examples rule
- Strip the eight specs' tables first, then retire them by delta
  - **Cons:** edits to files whose only future is deletion, made to satisfy the tool

### D15. Readiness answers for the blob store as well as the replica store

`GET /ready` reads the replica store and looks a hash up in the blob store, and fails when either refuses. On a full state directory a placement into a pod fails at the blob store before the replica store is touched; iroh-blobs' metadata actor then stops, every later payload read fails — sessions are denied, a pod's contacts are not derived — and the replica store still answers its read. The lookup reaches that actor, which the replica store's read never does. The data namespace masked this: a read of it nudged a session, whose snapshot committed the replica store's pending batch onto the full disk and failed the replica store too.

**Example:** Alice's node on a 16 MiB state directory, asked after the fill.

| what refused | the replica store's read | the blob store's lookup | `GET /ready` |
|---|---|---|---|
| nothing: the node is healthy | answers | answers | 200 |
| claim 63's placement, at the blob store | answers | `Sender closed`: the metadata actor stopped | 500 |
| a session's commit, at the replica store | `Previous I/O error` | not asked | 500 |

**Rejected alternatives:**

- Read the replica store alone, and fill the disk the stand's way
  - **Cons:** a node that serves nothing keeps reporting ready, so an orchestrator never restarts it; the stand would prove readiness only where a session happened to commit after the fill

### D16. A dial that cannot reach a gossip neighbor is tried again

When a sync dial fails to connect, or a payload download fails, toward a peer that is a gossip neighbor in some swarm of the engine — a connection with it stands, so it is up — pdn-store's live actor tries it again 1 s later, each further wait twice the one before up to 16 s, for at most 2 minutes after the first failure; an exchange with the pair that finishes, or the download succeeding, ends the series, and so does the peer ceasing to be a neighbor. iroh sends a new connection's handshake on the path it last selected for the peer while any connection to that peer lives, and selects again only when a connection's path opens. A member's device that restarts on a new port connects to the others at once from it, while their dials keep going to its old port until it opens another connection — its gossip does within about a minute. A peer that is no neighbor is not retried this way: its next sync report or pass dials it. What the retry leaves to the pod pass, 300 s, is a record whose announcement reached no neighbor at all, as one placed before the restarted device's swarm formed; the stand's restart scenarios wait for that pass.

**Example:** Alice's tablet a3 is killed and starts again on port 48670, its old one 51650; Bob's phone b1 is the other member of "Family", and a3 is a gossip neighbor of b1 throughout.

| t | a3 | b1 |
|---|---|---|
| 0 s | starts, syncs "Family" with b1 from 48670, places "after" | takes the entry; the payload download goes to 51650 and fails |
| 1 s, 3 s, 7 s, 15 s, 31 s | | the download is tried again: 51650, fails |
| 30 s | | its connections to the old a3 time out; the selected path stays 51650 |
| 44 s | its gossip connects to b1 again, from 48670 | the path is selected again: 48670 |
| 47 s | | the try 16 s after the one at 31 s downloads the payload; "after" reads |

**Rejected alternatives:**

- Patch iroh to select the path again when a connection closes
  - **Pros:** fixes the cause, for every protocol on the endpoint
  - **Cons:** a fork of the transport the whole workspace stands on, for a change upstream has not made; the selection still waits for the old connections' idle timeout, and the pull that failed before it still needs a second try
- Gate the retry on an address iroh reports in active use
  - **Cons:** iroh keeps reporting the address active while the dials themselves use it, so a peer that is down would be retried for the whole two minutes
- Retry every dial that fails to connect
  - **Cons:** a peer that is down is redialed for two minutes by every replica naming it, and every scenario that waits for no dial in flight waits that long
- Shorten the pod reconcile interval
  - **Cons:** every store of every member pays the extra sessions, for the one case a retry covers

## Operating conditions

- **Several identities on one node.** Changes the outcome: co-located sessions, identity stacks and the stand's two personas now hold pods, not grants, and their tests move onto pods (in-process sessions, identity-scoped replicas, container stand).
- **One device or several.** Changes the outcome: a linked device comes up with the PMS alone and reaches its pods through the armer (device linking).
- **A device linking before, during or after a process.** Changes the outcome for a node of an earlier build: the linking reply changes shape under the same ALPN and payload version, so an old device does not link to a new inviter, while a new device links to an old one and drops the data-namespace ticket unread; named out of scope in the proposal.
- **An unstable connection.** No change: no session or ceremony rule changes.
- **A disk that fills.** Changes the outcome of the stand's full-disk scenario, which places records instead of writing entries: a placement fills the blob store first, which readiness now reads (D15; container stand, host).
- **A device that restarts.** Changes the outcome: recovery re-derives pods alone, and a directory written with connections is not supported (D13; restart recovery). A device killed and started on a new port is reached again by the retry of D16, which the data namespace's pass used to stand in for; a record whose announcement reached no neighbor waits for the pod pass, and the stand's restart scenarios wait that long.
- **Clocks that disagree.** No change in behaviour; the future-timestamp window moves into reconciliation sessions.
- **Capabilities granted and narrowed and widened and revoked and granted again.** The condition goes with grants; its pod counterpart, the membership acts, keeps every scenario it has.

## Risks / Trade-offs

- [A deleted test takes a kept property with it] → the port phase runs first; the inventory in tasks names, for every deleted test, either the removed mechanism it proved or the rewritten test that proves its kept property; each rewrite fails with its mechanism broken.
- [The rejection echo's removal disturbs a pod's ingest] → pdn-store keeps every verdict pods return; the change runs `just check-store`, `just test-store` and a stress pass over the pod scenarios in `crates/data-layer/tests` and `crates/pdn-node/tests`.
- [A hidden dependency of pods on connection code] → the armer, the ceremony machinery, the session hooks and the test-only hooks are named above; what the compiler reports beyond them is moved, never deleted, until a test shows it serves nothing.
- [A rewritten spec example states what the code does not] → every example and scenario the deltas rewrite is checked against the code or its test while the task that changes the code runs, and corrected in the delta first.
- [The archive's application refuses a delta] → a trial archive in a scratch copy of `mia-docs` runs before the real one, and `openspec validate --specs --strict` after it.
- [Pods carry data people depend on before the defence of a member's own history] → the criterion stays recorded where the defence is, unchanged; the removal of connections no longer stands in for it.

## Migration Plan

No deployment migrates: state directories start fresh (D13). The order of work is D10's, laid out in tasks; a phase that turns red is fixed inside that phase. Rollback is reverting the change's commits; nothing outside the repositories changes.
