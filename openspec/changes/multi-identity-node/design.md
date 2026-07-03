# Design: multi-identity-node

## Context

The codebase is already multi-identity in shape: the registry keys data docs by issuer `PdnId`, store bindings are parameterized by identity, and `read`/`write`/`share_ticket` take the issuer as an argument. The single place that pins a node to one identity is the ingest gate: `SyncNode::spawn(policy)` installs one `IngestPolicy`, and the shipped policy (`SelfOwned { me }`) admits only replicas bound to `me`. A second identity's private metadata or connections store would be dropped at ingest on any node spawned for the first identity. The team decision is to remove the gate now, run on ticket possession until subset-rbsr (Invariant 2, egress filtering) and UWill (ADR-0007) restore enforcement, and let a node host several identities — for example Alice-at-work and Alice-at-leisure — each added to a device explicitly.

## Goals / Non-Goals

**Goals:**

- One `SyncNode` hosts any number of identities, each with its own private metadata store, connections store, and data namespace, addressed independently.
- Adding an identity to a device is an explicit per-identity act: `link_device` once per identity with that identity's seed.
- The ingest gate and everything that exists only to feed it are removed from `data-layer`; the fork's `validate_entry` seam stays, uninstalled.
- Specs tell the truth afterwards: Invariant 1's enforcement section and the affected data-layer capabilities are corrected in this change.

**Non-Goals:**

- Group mechanics (membership, roles, invitations, cascading bootstrap) — a group is conceptually an identity, but nothing group-specific is designed here.
- Automation of adding identities to a device: no cascade during linking, no live propagation to already-linked devices, no UX prompting. These come later as automation over the explicit acts defined here.
- Replacement enforcement (ingest or egress) — that is subset-rbsr and UWill, not this change.
- Persistence, key management, or any identity-layer concern: an identity here is still just a `PdnId` value.

## Decisions

### D1. An identity is an addressing key, not a node resource

The node keeps no list of "identities it hosts". Store handles stay with the caller (today the tests, later the pdn-node runtime), and the registry remains what it already is for data namespaces — a map from issuer to backing doc. Hosting a second identity is nothing more than creating or importing further stores keyed by another `PdnId`. Alternative — an explicit identity registry on the node — rejected: nothing consumes it at this stage, and inventing a resource with no consumer is speculative surface.

### D2. Delete the gate machinery, do not neuter it

`gate.rs` is removed whole: `SelfOwned`, `ConnectionsPolicy`, `Connections`, `AnyOf`, `IngestPolicy`, `IngestCtx`, `Admission`, and the `capability_validator` bridge. `SyncNode::spawn()` takes no policy and installs no validator into the fork. Alternatives rejected: an accept-all policy would keep a dead interface warm, and the interface itself ("decide from the resolved binding, reading nothing") is a one-identity-world shape — the future UWill-era policies need different context (peer, capability material), so there is nothing worth preserving; a `SelfOwned` generalized to a set of identities would need runtime-mutable identity state inside the gate, which is exactly the coupling being removed. The ADR-0008 seam is the fork's `validate_entry` hook, and it survives untouched in pdn-store.

### D3. The registry shrinks to doc addressing

`Binding` and `BindingIndex` exist to translate an incoming entry's iroh namespace into domain terms for the gate; with the gate gone they go too. `Registry` keeps only the issuer-to-doc map that `read`/`write`/`share_ticket` resolve through. The connections and private metadata docs continue to live inside their store handles; the `bind_*` registration steps disappear, while doc creation and import stay. If subset-rbsr later needs a namespace-to-domain resolution for its egress filter, it will be per-peer and capability-driven — a different shape, written fresh, with this one in git history.

### D4. Interim admission is ticket possession, stated as behavior

With no validator installed, whatever a replica syncs from a peer holding its ticket is persisted. This is the interim security stance: a replica's ticket is handed only to the devices (and, later, parties) that should hold that replica, and nothing else filters. Invariant 1 keeps its ticket mechanism and loses its code mechanism; Invariant 2 remains unenforced until subset-rbsr. The window is accepted for the experiment stage and recorded in the invariants spec rather than hidden.

### D5. Linking stays single-seed per identity, repeated per identity

`link_device(node, identity, seed, timeout)` keeps its signature and behavior; a device that should host N identities runs it N times with N seeds obtained out of band (N QR codes). No discovery of one identity through another, no reactive import when a new identity appears elsewhere. This keeps every addition of an identity to a device an observable, user-initiated act — the property the team explicitly wants at this stage.

## Risks / Trade-offs

- **[No ingest control at all in the window]** Any holder of a write ticket can write arbitrary entries into that replica; nothing structural stops junk or cross-identity garbage inside one replica. → Tickets are handed only to own devices at linking; experiment stage, no production data; subset-rbsr then UWill restore enforcement on the proper side (egress, then capabilities). The window is stated in Invariant 1's text.
- **[Losing the cross-identity test scenario]** Deleting `sync_two_nodes` removes the only two-identity, two-node scenario. → The new multi-identity test keeps two identities alive on shared infrastructure, and subset-rbsr's planned read-restriction scenario reintroduces cross-identity sync with actual enforcement; its design gets a note that it now starts from an ungated baseline (and that its "Unaffected: ingest gate" line and D4 "same-identity peer" wording predate multi-identity nodes).
- **[Deleted code that later work half-needs]** subset-rbsr or UWill may want pieces of the binding resolution. → Git history preserves it; the future shape differs enough (per-peer, capability-carrying) that resurrection would mislead more than help.

## Migration Plan

Specs first (they define the target), then code: delete `gate.rs` and the registry's binding side, change `spawn()`, update stores and linking call sites, rewrite tests, then edit `invariants.md` and the subset-rbsr note in `mia-docs`. Single change, no deployment concerns; rollback is `git revert`.
