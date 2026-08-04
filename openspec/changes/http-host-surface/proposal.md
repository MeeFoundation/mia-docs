# Proposal: http-host-surface

**Depends on `product-path-gaps`, which lands first.** That change closes the two product gaps this one would otherwise trip over — a granted replica reaching only the device that published the grant, and a ceremony refusal indistinguishable from an unreachable peer — and rewrites the scenario tests onto the product path. This change assumes both are done: the two marker errors exist to be mapped, and a granted namespace converges from any reachable device of its issuer.

## Why

The runtime's service surface is complete and proven in-process — identity, connections and grants, data, sync — but nothing outside the process can reach it: the HTTP host serves `/live` and a one-line status page. The container harness planned next has therefore nothing to drive: an image built today proves that the binary starts, not that two nodes pair, grant, and replicate. This change gives the host a debug surface wide enough to run the whole scenario from outside the process, so the harness can be written against it.

## What Changes

- **The debug surface covers the embedded runtime's operations.** Behind the existing `PDN_DEBUG=1` gate, the host exposes what the runtime's four services already offer: create an identity, mint and consume a linking payload, mint and consume an invite payload, list connections, publish and read and withdraw grants, write and read and list entries, report the node id and hosted identities. No operation the runtime does not already offer is invented here.
- **And stops there — deliberately, including where it would be convenient.** The out-of-band namespace ticket handover stays off the surface, and nothing forces reconciliation, resets state, or reaches a store directly. A harness that arranged a namespace by importing a ticket would pass with the grant binder broken; a harness that forced a sync would pass with convergence broken. Both would test the route instead of the product, and the arrange and act steps are exactly where that substitution is invisible afterwards.
- **The nodes still talk only iroh; HTTP never travels between them.** Every route acts on the runtime embedded in the host that serves it, and no host addresses another host — the establishment and linking dialogues and the replication between containers run over the runtime's own protocols, exactly as they do for an embedder without any host. The container scenario therefore exercises the product's inter-node path, with HTTP standing in for the in-process method call and for nothing else.
- **And the host itself stays off the product path.** It exists for the container stand: a product host — mobile, desktop — embeds the runtime core in-process, the runtime carries no HTTP dependency, and no product path includes an HTTP endpoint. The spec now states both halves instead of leaving them to the crate layout.
- **A refusal arrives as a refusal.** The host maps a runtime error to a client-error status distinguishable from a host or transport failure, and never reports a refused operation as success. Without this, a container-level deny test — required for every positive access test by [access-control-tests](../../specs/code-practices/access-control-tests.md) — asserts nothing: an authorization failure and a typo in the path would both read as "not the value I expected".
- **The surface carries live ceremony secrets, and says so.** Invite and linking payloads cross it in the clear, each carrying its one-time secret — bearer-free in the ceremony specs' sense, since nothing in a payload grants durable access, yet live until burnt or expired, so a captured payload lets its holder consume the invitation. No namespace ticket crosses the surface at all. The host therefore keeps its default bind on loopback and the surface behind the flag, and the spec states the exposure instead of leaving it implied.
- **Encoding is boring on purpose.** Structured values travel as JSON built from the types the runtime already serializes; entry payloads travel as raw request and response bodies, so no encoding sits between a written byte string and a read one.
- **No authorization of the host's own.** The host authorizes nothing and adds no identity: every operation is the runtime's, refused by the runtime on the runtime's terms. Reaching the surface is reaching the node.

## Out of Scope (deferred)

- **The container harness itself** — Dockerfile, testcontainers, compose and the justfile recipes are the next change; this one only makes them possible.
- **On-disk persistence** — the runtime is still in-memory, and the node's secret key is still fresh per start. Persistence is its own change and depends on containers to be verifiable at all.
- **Retraction verdict subscription** — the runtime exposes retraction verdicts as a stream, which needs a streaming shape (server-sent events or polling with a cursor) and a decision about buffering. The write-retraction scenarios stay in-process until it lands. One consequence the surface states in its own docs: a successful write into a granted namespace says the write was admitted locally, against the grant record this node has read, and the issuer's ingest gate decides afterwards — a claim its own record does not cover is refused there and the entry is retracted here, and no answer on this surface carries that verdict.
- **The out-of-band ticket handover** — `share` and `import` exist on the data service for a ticket obtained outside any grant. They stay off the surface: between connected identities the sanctioned path is the grant, and the runtime binds what a grant names by itself, so nothing in the stand needs them. If a later fixture genuinely does, it arrives with its own justification.
- **A platform HTTP API** — this surface is scaffolding for the stand. Route names stay unpinned, and nothing here is a contract for a product client.
- **Host authentication and transport security** — no tokens, no TLS. The flag and the loopback default are the whole posture.

## Capabilities

Capability ids are component-prefixed (the delta layout is flat: `specs/<capability>/spec.md`); on archive the spec lands in the component tree.

| Capability (delta)   | Archive destination                               |
| -------------------- | ------------------------------------------------- |
| `pdn-node-http-host` | `openspec/specs/components/pdn-node/http-host.md` |

### New Capabilities

None — the host capability already exists.

### Modified Capabilities

- `pdn-node-http-host`: the debug surface gains requirements where it had none. Today the spec says only that `/debug/` is absent without the flag and that its shape is unspecified; that stays true of route names, but six properties become required — the surface covers the embedded runtime's operations, it offers no path the runtime's own callers lack, a refusal is reported as a refusal and never as success, it exposes live ceremony secrets and so stays gated with a loopback default bind, inter-node traffic stays on the runtime's own protocols with no HTTP between nodes, and the host itself stays off the product path: product hosts embed the runtime core, which carries no HTTP dependency.

## Impact

- **`crates/pdn-node-http`**: the router grows the debug routes and their handlers; a small host-side error mapping and the request and response shapes live here. New dependencies: `serde` and `serde_json` (axum's `json` feature); no new dependency on `data-layer`.
- **`crates/pdn-node`**: untouched. Every handler delegates to a service method that exists once `product-path-gaps` has landed — including the two marker errors the error mapping downcasts. If a handler turns out to need something the services still do not offer, that is a finding to raise, not a runtime addition to slip in here.
- **`crates/data-layer`, `crates/pdn-layer`, pdn-store fork**: untouched.
- **Tests**: the host's smoke test grows into a scenario test driving two in-process runtimes through their HTTP surfaces — establishment, grant, replication — plus the paired denials (an unhosted identity, a burnt invite secret, a write outside the grant's write set) asserted as refusals, with the gate itself still asserted absent without the flag. The `pdn-node` scenario suites are not touched here — `product-path-gaps` has already put them on the product path.
- **The stand**: after this change the container harness can be written; nothing about the stand's orchestration is decided here.
