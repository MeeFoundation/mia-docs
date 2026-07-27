# Tasks: capability-scoped-writes

> The writer-side mechanism is Option A (design D5): the issuer's gate signals a
> capability refusal back in-band, so the writer retracts deterministically in one
> session. The earlier re-offer counting is superseded — its tasks are marked done
> where the code still stands and re-opened where A replaces it (fork observation,
> writer counting, threshold-timed tests). The gate, the physical retract, the
> marker, and the event surface carry over unchanged.

## 1. Grant vocabulary (D1)

- [x] 1.1 `ReadGrant` claims become per-claim pairs (claim id + write flag), read always granted per claim; `covers` splits into read-cover and write-cover; serde round-trip tests updated — an old-shape payload decodes as no grant (fail-closed, asserted)
- [x] 1.2 Access book consumes both sets: `GrantWidth` and `union_claims` carry (read set, write set); the egress filter keeps consuming the read set only
- [x] 1.3 `ConnectionsService::publish_grant` takes per-claim commands (**BREAKING**); ticket mode follows the record as a whole — any write → `ShareMode::Write`, none → `ShareMode::Read`; `PeerGrant` and the grant binder carry the new shape unchanged otherwise
- [x] 1.4 Test helpers (`nominal_claims`, `claims_on`, `granted_patiently`) speak per-claim commands

## 2. Fork surface (pdn-store)

- [x] 2.1 `CapabilityValidator` learns the session origin: the peer already present at the `validate_entry` chokepoint is passed to the injected predicate (local inserts stay ungated); builder wiring unchanged otherwise
- [x] 2.2 In-band rejection (A): the validator distinguishes a capability refusal (`Unauthorized`) from a transient one; on a capability refusal the ranger emits a new `MessagePart::Rejected` carrying the refused entry's identity (author, key, timestamp) on the reply, and the receiving side surfaces incoming `Rejected` parts to an injected `rejection_observer` (peer + entry identity). Only-`Unauthorized`, no new session state. **Remove** the superseded per-session sent-entries observation.
- [x] 2.3 A local physical-retract operation: remove one record (author, key, timestamp-bound) from a replica without inserting anything; the store's existing replacement machinery is the base
- [x] 2.4 A rejection names only an entry the replica would newly store: the ranger tests the incoming entry against the same prefix-dominance rule its insert applies, and refuses an already-held entry silently, so a narrowed grant cannot make the sender destroy data both sides hold
- [ ] 2.5 Full pre-push checklist of `./pdn-store` (fmt, clippy for all three feature sets, docs-rs, deny, tests + doctests, wasm) after the A change, then rev-bump the workspace dependency off the local `[patch]`

## 3. Ingest gate (D2, D3, D4)

- [x] 3.1 The session classifier computes the write set beside the read set and deposits a per-session snapshot keyed by replica and peer, for both session roles, before any entry flows
- [x] 3.2 The validator installed at spawn beside the access provider: hosted-issuer data replicas judge by snapshot (issuer device → all; write set → per claim; else refuse); directories, connection metadata stores, grantee-held and unregistered replicas admit as before
- [x] 3.3 Grantee-side second duty: entries named by a local retraction marker are refused at ingest (the branch exists from the start, empty marker set = no-op)
- [x] 3.4 The gate's verdict is three-valued: only a live capability decision against the session's write set signals the sender; a marker match, an unresolved session, and records the gate cannot read refuse silently, and markers are consulted on data replicas only
- [x] 3.5 Courtesy refusal in the data service: a write at a granted namespace outside the local record's write set fails at the call site before touching the replica (D8)

## 4. Documentation of the accepted windows (D9)

- [x] 4.1 The last-write-wins window (10 minutes, `MAX_TIMESTAMP_FUTURE_SHIFT`) stated in the capability-gated-ingest spec and verified against the fork constant; the tightening knob recorded in design only, off
- [x] 4.2 Per-session write-right freezing stated next to the read side's freezing where the specs describe session rights

## 5. Retraction (D5, D6, D7)

- [x] 5.1 Writer-side consumption of the rejection (A): the runtime installs the `rejection_observer`; a rejection is acted on only when the peer resolves as a device of the issuer (the read side's device-set resolution) and names an own author's entry — then a verdict fires at once, one session. **Remove** the re-offer counting (`RetractionTracker` pending/threshold, the sent-observer wiring, the `retraction_threshold` `SpawnOptions` knob, and the per-device stopgap that stood in for the peer check)
- [x] 5.2 The act: physical removal through the fork operation; verify re-offering stops and the issuer's entry reads back (the set difference is gone)
- [ ] 5.3 Markers in the directory: `retractions/<issuer-hex>/<author-hex>/<path>`, payload carrying bound, node id, content hash, timestamp; written at verdict — plus the drop rule: pruned when the entry can no longer win (superseded by a newer own write, or aged out by a retention window) and in bulk on forget, never on a bare re-grant; the retention window a constant injected like the reconcile interval
- [x] 5.4 Marker consumption on every device of the identity: remove matching local entries, refuse their re-ingest (the 3.3 branch); verified against sibling flap — a sibling still holding the entry does not re-establish it
- [x] 5.5 Surfacing: `tracing` dependency added, warn on verdict; runtime event stream in the existing changes-stream style; pdn-node subscription surface per the core delta
- [x] 5.6 A verdict acts only on a name the local record confirms: before the marker is written, the named author, path, timestamp and content hash are matched against the replica's own record, so a fabricated bound arms nothing and a superseded version is not retracted

## 6. Tests

- [x] 6.1 Flip the pinned gap in `write_grant_round_trips_while_reads_stay_scoped`: the out-of-scope acceptance becomes the write-denial pair — the forced write never reaches the issuer
- [x] 6.2 Data-layer gate scenarios per the capability-gated-ingest delta: granted-claim admission, out-of-scope refusal, read-only refusal, withdrawal refusing the next session, device replication and sibling relay untouched, beyond-window timestamp refusal
- [ ] 6.3 Data-layer retraction scenarios per the write-retraction delta (A): accepted write draws no rejection, a refused write draws a rejection and verdicts in one session, a forged non-issuer rejection is ignored, local view returns to the issuer's value, sibling converges via marker, marker never touches issuer-authored entries, the issuer's later write at a marked path is read, a re-grant does not drop the marker, markers age out / leave on forget
- [x] 6.4 Runtime scenario (pdn-node): one connection, one grant — `contact/email` read-only, `contact/phone` read-write; the phone write round-trips both ways, the email write refuses at the call site, the forced email bypass never reaches the issuer and is retracted at once with the event observed (no threshold knob); read denials stay with the existing scenarios (access-control-tests.md pairing)
- [ ] 6.5 Mutation-verified non-vacuity: suppressing the validator install fails the refusal scenarios; suppressing the rejection emission fails the retraction scenario; suppressing marker consumption fails the sibling-flap scenario
- [x] 6.6 `just check`, full workspace suite, stress pass on the touched scenario binaries per flaky-tests.md before anything builds on top

## 7. Docs sweep

- [x] 7.1 Hand-apply the delta requirements to the main tree (read-capabilities, connection-metadata-store, subset-reconciliation, private-metadata-store, pdn-node core; capability-gated-ingest and write-retraction) — including the A revision (in-band rejection, marker retention window, "silent on the wire" inverted)
- [x] 7.2 `data-store.md` Purpose: the write-authority sentence stops saying unscoped-until-the-hook; `uwill.md` open question on write semantics gains a pointer to the interim answer (per-claim write enforced at ingest by session identity)
- [x] 7.3 Rustdoc under A: the node module doc, `grant.rs` write commentary, the data and connections service docs — describe the gate and the in-band rejection, not re-offer counting
- [x] 7.4 Sweep the spec tree and the active changes (`reconcile-trigger`, `test-feature`) for stale re-offer-counting / "silent on the wire" / single-write-flag phrasing; glossary entry only if the specs adopt a new term (retraction), linked at first use
