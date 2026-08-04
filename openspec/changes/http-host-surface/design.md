## Context

The runtime core is complete enough to run the whole stand scenario: pairing, device linking, capability-scoped grants, scoped reads and writes are all in-process green. The HTTP host has not kept up — it embeds a runtime and serves `GET /live` plus a one-line status page. Everything the stand needs to demonstrate is therefore reachable only from inside the process, which is exactly what a container harness cannot do.

This change is second of two: `product-path-gaps` lands first and closes what the harness would otherwise have to work around — an audience reaching only the device that published a grant, and a ceremony refusal indistinguishable from an unreachable peer. Everything below assumes those are in place.

The constraint that shapes this design: the harness is a test, and a test is worth what its assertions are worth. Over HTTP an assertion sees a status code and a body, so the surface has to preserve two distinctions the in-process tests get for free — a refusal is not a failure, and a value read back is the value written, not an encoding of it. Everything else about the surface is scaffolding and may change freely.

## Goals / Non-Goals

**Goals:**

- The runtime's service operations reachable over HTTP, one route to one service call.
- Refusals legible: an authorization refusal is distinguishable from an unreachable peer, a wrong route, and a host bug.
- Byte-exact round trip for entry payloads, so a replication assertion tests replication and not base64.
- A surface with no shortcut around the mechanisms the stand exists to demonstrate, so a green container run means the product works and not that the harness was helped.
- The product-path boundary explicit: HTTP reaches a node from outside its process, nodes reach each other only over the runtime's iroh protocols, and the product ships no HTTP endpoint at all.
- Small enough to read in one sitting: the host stays glue, with no state and no orchestration of its own.

**Non-Goals:**

- A product API. Route names, paths, and body shapes are unpinned scaffolding.
- Authentication, authorization, or transport security in the host.
- Streaming: the retraction verdict subscription needs a shape decision and stays in-process for now.
- The container harness, the Dockerfile, and persistence — separate changes that build on this one.

## Decisions

### D1. Routes are identity-first, and their names are the host's own business

Every runtime operation but node status is scoped by a hosted identity or a data issuer, so the identity rides in the path: `/debug/identities`, `/debug/identities/{identity}/invite`, `/debug/identities/{identity}/connections`, `/debug/identities/{identity}/grants/{peer}`, `/debug/data/{issuer}/{path}`. `PdnId` is hex `Display` and `FromStr` already, so the path segment parses without a helper.

Alternative — identity in the request body for every call — was rejected because it hides the most common denial: an operation addressing an identity this runtime does not host. In the path it is one uniform parse-then-refuse for every route; in the body it is a field each handler must remember to read.

### D2. Structured values travel as JSON; entry payloads travel as raw bodies

A write puts the request body's bytes into the entry; a read returns the entry's bytes as the response body. No base64, no JSON string escaping, no encoding to agree on. Alternative — base64 inside a JSON envelope, uniform with everything else — was rejected because it inserts a transformation between the bytes written and the bytes read, and a replication test that fails then fails ambiguously: the transform is as likely a suspect as the sync.

Listings, grants, and the identity list are JSON, built from types that already derive serde (`EntryInfo`, `GrantedClaim`, `ReadGrant`); the ceremony payloads are JSON too, but pass through as opaque values (D3).

### D3. Ceremony payloads cross the surface as opaque tokens

`invite` returns the payload and `establish` takes it back, but the host does not read inside it: the payload is serialized once by the runtime's own serde form and travels as a value the host passes through untouched. The product form is a QR the human moves from one screen to the other, and this is that move — the harness copies a token between containers exactly as a person copies the code, and neither the host nor the test comes to depend on which fields the payload has. Alternative — a typed body mirroring `InvitePayload` field by field — was rejected for pinning an internal shape into a test's arrange step, where a later field change would break the harness for no reason the harness cares about.

### D4. A grant read returns the capability, and no ticket crosses the surface at all

`read_grants` yields the capability and the replica's ticket together. The surface returns the capability — issuer, claims, commands — and drops the ticket, and the out-of-band `share` and `import` stay off the surface entirely (proposal, out of scope).

The reason is not primarily that a ticket is bearer material, though it is. It is that the runtime binds a granted namespace by itself as the grant record replicates — the core spec's requirement that grants bind and unbind with their record — so a harness never needs a ticket to make a grant work. Offering one anyway would let the harness arrange the granted namespace by importing it, and a scenario arranged that way keeps passing after the binder breaks: the read returns the right value, obtained by a path the product does not use. Withholding the ticket is what makes the container scenario a test of the grant path rather than of the import route.

### D5. The surface has no convenience the product lacks

The same argument generalizes, and it generalizes to the place where it will actually be tempting: the first time a container test goes red waiting for convergence, the cheap fix is a route that forces a reconciliation. It must not exist. The product converges on its own — a nudge before access and the periodic pass — and a forced sync in the act step would make the test prove something the stand does not do. The same goes for resetting state, writing into a store directly, or fabricating a device record: none exist for an embedder of the runtime, so none exist here.

What remains for waiting is repeating the read, which is honest: it is what an application does, and when it never converges the test fails for the true reason.

### D6. Refusal legibility is inherited, not built here

The error table below rests on two typed markers — `EstablishmentRefused` and `LinkingRefused` — that `product-path-gaps` adds to `pdn-node`. Before them, a refused ceremony and an unreachable peer arrive as the same untyped error, and neither mapping choice is acceptable: map every ceremony error to a client error and a dead peer container reads as a refusal, so the deny test passes for the wrong reason; map them all to a server error and the deny test cannot assert anything at all.

Their contract, which this design relies on and does not restate: reasonless, downcastable from the service call's `anyhow::Error`, meaning "the dialogue reached the point of the answer and none came". What they deliberately do not separate — a genuine refusal from a connection that died mid-dialogue — is argued in that change; here it matters only that the deny tests' negative case is a deliberate replay against a live peer, which lands squarely on the refusal.

### D7. Ceremony calls block their request; `link`'s wait is a query parameter

`establish` and `link` run a network dialogue that takes seconds, and `link` additionally waits for catch-up under a caller-supplied timeout. The handlers await them and answer when they are done; `link` takes the timeout as a query parameter with a default. Alternative — accept, return 202, poll a job id — was rejected: it invents host state and a job lifecycle for a stand whose callers are a test and a shell script, both of which are happy to wait.

### D8. Nothing waits for replication on the server side

Reading a peer's grants or a replicated entry can legitimately return "not yet": the record is there and the payload is still arriving, or the reconciliation has not run. The surface reports what the runtime reports right now — empty list, or 404 for an absent entry — and the caller polls. Long-polling would mean the host inventing a waiting semantic the runtime does not have, and would hide the difference between "slow" and "never" precisely where the harness needs to see it.

### D9. The error table is closed and its default is 500

Handlers downcast the `anyhow::Error` against a fixed list and map each to a status with the error's own text:

| Error                                                                       | Status | Reading                                          |
| --------------------------------------------------------------------------- | ------ | ------------------------------------------------ |
| `EstablishmentRefused`, `LinkingRefused`, `WriteNotGranted`, `DelegationUnsupported` | 403    | the runtime's rules said no                      |
| `UnknownIdentity`, `data_layer::UnknownIssuer`                              | 409    | the runtime does not host what you addressed     |
| `UnsupportedInviteVersion`, `UnsupportedLinkingVersion`, a malformed body or path | 400    | the request itself is wrong                      |
| an unknown query parameter, an empty entry payload                          | 400    | the request itself is wrong, decided by the host |
| an absent entry                                                             | 404    | nothing is there                                 |
| anything unrecognized                                                       | 500    | the host does not know what happened             |

An unhosted identity is 409 rather than the more natural 404 for one reason: route names are unpinned, so a test asserting 404 for an unhosted identity would keep passing after a route was renamed out from under it. Separating "the runtime refused you" from "this host serves no such route" costs one status code and buys a deny test that cannot pass by accident.

Two statuses the host decides without a downcast are worth naming, because both would otherwise land on the 500 default and read as a host bug. An empty entry payload is one: the engine keeps no zero-length entry, so the write fails with an error the table cannot name, and the request that caused it is simply wrong. An unknown query parameter is the other, and it is refused rather than ignored for the reason the bind resolution fails on an unparseable value — a mistyped `lifetime_secs` that fell back to the default would mint an invite with a lifetime nobody asked for, and a mistyped listing prefix would widen a listing back to the whole namespace, with nothing in either answer saying so.

The 500 default is deliberately the pessimistic one: an unmapped error is a host that does not understand what happened, and reporting that as a clean refusal is the laundering this whole design exists to prevent. The unreachable-peer case rides that default — it needs no type of its own, because 500 against 403 is already the distinction the deny test rests on.

### D10. `/live` and `/debug/status` stay as they are

`/live` is unchanged. `/debug/status` is subsumed by the sync routes but stays: it is the one human-readable probe, and the demo script leans on it.

### D11. The product-path boundary is stated, not left to the crate layout

Two properties of the stand are true by construction but, before this change, stated nowhere normative. First: the surface is a control plane over one node — every route acts on the embedded runtime of its own host, no handler addresses another host, and everything between nodes (the ceremony dialogues, reconciliation, gossip) travels the runtime's own protocols over its iroh connections. Second: the host is not on the product path — a product host embeds the runtime core in-process, the runtime carries no HTTP dependency, and no product deployment serves HTTP at all.

The spec now states both as requirements, because the container harness is exactly where an implicit boundary erodes: the first convenient handler that dials the other container would quietly turn a product-path scenario into an HTTP relay test, and nothing downstream would reveal it — the assertions would still read the right values. Stating the boundary where the assertions rest keeps a green container run meaning what it claims: the product's own inter-node path, driven from outside the process.

## Risks / Trade-offs

- **The surface is unauthenticated remote control of the node** → it stays behind `PDN_DEBUG=1`, the host keeps its loopback default bind, and the spec states the exposure rather than leaving it to be discovered. A container that opens it wider does so explicitly.
- **The harness depends on unpinned route names** → the harness lives in this repo and moves with the routes; nothing outside the repo may depend on them, which the spec says in as many words.
- **A closed error table drifts as the runtime grows new typed errors** → the drift is visible: a new typed refusal that nobody mapped shows up as 500 in a deny test, which fails loudly rather than passing quietly.
- **Blocking handlers hold a connection for the length of a dialogue** → acceptable at stand scale; `link`'s timeout bounds the longest of them, and the runtime lock is never held across a network round trip, so a slow dialogue does not freeze the other routes.
- **The surface is built on a change that has not landed yet** → the dependency is one-way and narrow: two marker errors to downcast, and a granted namespace that converges from any reachable device of its issuer. If `product-path-gaps` lands differently, what breaks here is the error table, loudly, in its own unit test.
- **Removing `share` and `import` from the surface may block a fixture nobody has written yet** — the scale measurements will want to plant a large namespace cheaply → they are absent, not deleted: the service keeps them, and a fixture that needs them argues for its route then, on its own terms.

## Migration Plan

Additive and gated: the new routes exist only under `PDN_DEBUG=1`, `/live` is untouched, and no persisted state or wire format changes. Rollback is deleting the routes.

## Open Questions

- **Retraction verdicts over HTTP** — server-sent events, or polling with a cursor and a bounded buffer? Deferred with the subscription itself; the write-retraction scenarios stay in-process until then.
- **Whether the harness wants a status route richer than `/debug/status`** — node id and hosted identities are enough to tell containers apart, and anything more (per-replica sync state, peer lists) is introspection nobody has needed yet. Left out until a failing container run asks for it by name.
