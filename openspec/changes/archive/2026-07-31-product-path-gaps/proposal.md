# Proposal: product-path-gaps

## Why

Four scenario tests reach a granted namespace by handing its ticket over by hand, though a grant of that namespace is already recorded and the runtime binds what a grant names unprompted. Each keeps passing if the binding breaks — they read as proof of the grant path and are not. Classifying them turned up why the hand-made setup was there in the first place: two places where the product path is genuinely missing a piece, and the instrument was standing in for it.

An audience has no route to any device of the issuer except the one that published the grant, so a granted replica stops converging when that one device goes offline — although a sibling of it holds the same data and is authorized to serve. And a caller of the two ceremonies cannot tell "the peer refused me" from "I never reached the peer", because uniform refusal — a property owed to the dialed peer — reaches the dialer's own caller as the same untyped error.

Both bite the container stand directly: the first is "stop one of Alice's two containers", the second is what a deny test over HTTP has to distinguish. Closing them, and then rewriting the tests onto the path they now describe, is the work here — before anything is built on top.

## What Changes

- **A granted replica reaches every device of its issuer, not only the publishing one.** The runtime already reads the issuer's published device set from the connection metadata store — for the retraction tracker, two lines above where contacts are refreshed. Those devices become contacts of the granted replica, re-derived per sweep exactly as the audience's own siblings already are, so a device linked later is dialed and a withdrawn one stops being.
- **A refused ceremony is legible to the dialer's caller.** Two reasonless marker errors — `EstablishmentRefused` and `LinkingRefused` — attach where the refusal is already recognized. They carry no reason, so what the dialed peer can distinguish is unchanged; they say only that the dialogue reached the point of the answer and no answer came.
- **The tests that arrange by hand move onto the product path.** Three drop their manual import outright. The fourth — a linked device serving a grant published elsewhere — becomes expressible only because of the reachability fix: with the issuer's siblings reachable, the test isolates the serving device by taking the other one offline, the way the sibling-serving test already isolates its own.
- **The rule behind that becomes a practice.** Arrange and act steps reach a namespace the way the product reaches it; a hand-made handover is admissible only where the out-of-band path is the subject of the test or where it is the negative control the access-control practice requires.

## Out of Scope (deferred)

- **The HTTP surface** — the `http-host-surface` change builds on this one. It needs both fixes and neither of them is about HTTP.
- **Reaching a device the audience has never spoken to** — a contact carries an endpoint id, which resolves where the endpoint knows a path. If the check in tasks finds ids insufficient, carrying addresses in the device record is a follow-up with its own argument, not a silent widening here (design, D4).
- **Discovery, relays, hole punching** — reachability here means "dial a device we have a path to", not "find a device on the open internet".
- **Delegation** — a grant still names the granting identity's own issuer; nothing about the contact set changes that.
- **The metadata pair's own reachability** — a pair store's tracked contacts come from the establishment-time tickets, so they name the establishing devices alone; once those go dark, record replication between the surviving holders rides the gossip overlay with no reconcile-contact backstop. The stress pass surfaced it as a grant record racing its publisher's shutdown; the scenarios pin their arrangement with an explicit record-arrival wait, and widening the pair stores' contact derivation is a follow-up with its own argument, exactly as D4 is.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree.

| Capability (delta)                  | Archive destination                                              |
| ----------------------------------- | ---------------------------------------------------------------- |
| `pdn-node-core`                     | `openspec/specs/components/mee-pdn/pdn-node/core.md`                     |
| `pdn-node-connection-establishment` | `openspec/specs/components/mee-pdn/pdn-node/connection-establishment.md` |
| `pdn-node-device-linking`           | `openspec/specs/components/mee-pdn/pdn-node/device-linking.md`           |
| `data-layer-subset-reconciliation`  | `openspec/specs/components/mee-pdn/data-layer/subset-reconciliation.md`  |

### New Capabilities

None — every capability touched here already exists.

### Modified Capabilities

- `pdn-node-core`: a granted replica gains the issuer's other devices among its contacts, derived from the device set the issuer publishes in the connection metadata store. The sibling-contacts requirement beside it is modified in one clause: two hosted identities granted by the same issuer bind one replica, so the derived set unions every such audience's siblings instead of consulting only one directory.
- `pdn-node-connection-establishment`: a refused establishment becomes legible to the dialer's own caller — distinguishable from never reaching the inviter, while still carrying no reason. Uniformity toward the dialed peer is untouched.
- `pdn-node-device-linking`: the same distinction for `link`, which additionally must not read as a catch-up timeout.
- `data-layer-subset-reconciliation`: the tracked-contact surface is set wholesale per derivation instead of appended to — a list that only ever grows can never let a withdrawn device leave.

## Impact

- **`crates/pdn-node`**: `connections.rs` — the grant sweep derives the granted replica's whole contact set from the device records (issuer's published devices, every bound audience's siblings, the grant ticket's addressing for still-published devices) and sets it wholesale; `pairing.rs` and `linking.rs` — one marker error each, re-exported from the crate root next to `UnknownIdentity`.
- **`crates/data-layer`**: one surface change after all — `add_namespace_contacts` becomes `set_namespace_contacts` (replace), because "a withdrawn device drops out" is not expressible over a list that only grows; plus a `test-util` feature exposing the tracked contact set read-only for scenario assertions. The dialability check itself passed, so nothing here touches addressing (the D4 branch stays dormant).
- **Tests**: four `pdn-node` scenario tests rewritten onto the product path, each verified against a deliberately broken mechanism so the rewrite cannot pass vacuously; seven reachability scenarios — the audience converging from a device that did not publish the grant with the publisher offline, a grant published from a linked device, a late-linked device, a withdrawn device, per-counterparty contact isolation, two co-hosted audiences of one issuer, and a re-grant after withdrawal — and the ceremony refusal scenarios.
- **`code-practices/`**: one new entry, next to the access-control and flaky-test practices.
- **Dependents**: `http-host-surface` sits on top of this and expects both fixes present.
