# pdn-node: HTTP host

The debug surface stops being an unexamined hole in the host spec: its route names stay unpinned, but what it must cover, how it must report a refusal, what it exposes, and which side of the product path it stands on become requirements — because the container harness asserts against it, and an assertion is only worth what the surface underneath it guarantees.

## MODIFIED Requirements

### Requirement: The debug surface is absent by default
Debug endpoints are demo scaffolding, not platform API. The host SHALL NOT serve any route under `/debug/` unless `PDN_DEBUG=1` is set at startup. When enabled, route names, paths, and payload shapes are deliberately unspecified and may change without a spec change; the properties required of the surface as a whole are the requirements below.

#### Scenario: Debug routes off without the flag
- **WHEN** the host starts without `PDN_DEBUG` set
- **THEN** requests under `/debug/` return HTTP 404

## ADDED Requirements

### Requirement: The debug surface covers the embedded runtime's operations
When enabled, the debug surface SHALL make the embedded runtime's service operations reachable over HTTP: creating an identity, minting and consuming a device-linking payload, minting and consuming an invite payload, listing an identity's connections, publishing and reading and withdrawing grants, writing and reading and listing entries of an issuer's data namespace, and reporting the node id and the hosted identities. The surface SHALL introduce no operation the runtime does not offer: each route delegates to one service call and adds no orchestration of its own.

#### Scenario: A whole scenario runs over HTTP alone
- **WHEN** two hosts run with the flag set and a caller drives them only over HTTP — creating an identity on each, minting an invite on one, establishing from the other, publishing a grant, writing an entry, and reading it back through the grantee
- **THEN** every step is reachable over the surface, and the grantee reads the granted entry without any in-process call into either runtime

#### Scenario: A device joins over HTTP
- **WHEN** a caller mints a linking payload on the host of an identity's first device and consumes it on a second host
- **THEN** the second host reports the same identity among its hosted identities, and reads the entries written before the link

### Requirement: The surface offers no path the runtime's own callers lack
The surface SHALL NOT expose the out-of-band namespace ticket handover, SHALL NOT offer any means of forcing reconciliation, resetting state, or reaching a store other than through a service operation, and SHALL NOT hand a namespace ticket to a caller as part of reading a grant. What a caller can do over HTTP is what an embedder of the runtime can do, and no more.

The reason is what a test built on this surface proves. A harness that arranged a granted namespace by importing its ticket would keep passing after the grant binding broke; one that forced a reconciliation would keep passing after convergence broke. Both substitutions sit in the arrange and act steps, where nothing downstream reveals them — the assertions still read the right value, obtained the wrong way.

#### Scenario: A granted namespace arrives with no ticket crossing the surface
- **WHEN** a connected peer publishes a grant toward a hosted identity and a caller then reads the granted entry over the surface
- **THEN** the entry eventually reads back, and no route was available that would have handed over or accepted a namespace ticket

#### Scenario: Convergence is waited for, not forced
- **WHEN** a caller waits over the surface for a value written on another node
- **THEN** repeating the read is the only means available, and no route exists that triggers reconciliation

### Requirement: The container scenario runs on the product path
The surface is a control plane over the one node serving it: every route SHALL act on the embedded runtime of its own host, and the host SHALL NOT address another host over HTTP — the host carries no HTTP client at all. Everything that travels between nodes — the establishment and linking dialogues, reconciliation, gossip — SHALL travel the runtime's own protocols over its iroh connections, exactly as it does for an embedder running without any host. A ceremony payload moves between containers through the caller, as the product's payload moves between devices through a human. A scenario driven over the surface therefore exercises the product's inter-node path, with HTTP standing in for the in-process method call and for nothing else.

#### Scenario: Nodes exchange no HTTP
- **WHEN** a caller drives two hosts through establishment, a grant, and replication using only their debug surfaces
- **THEN** each request acts on the runtime of the host that serves it, the hosts exchange no HTTP requests between themselves, and the inter-node dialogue and synchronization run over the runtime's iroh connections

### Requirement: A refused operation is reported as a refusal
The host SHALL report an operation the runtime refused with a client-error status and the runtime's error text, and SHALL NOT report it as success. A refusal SHALL be distinguishable from an absent route and from a host or transport failure. Container-level deny tests rest on this: a surface that answers alike for "the runtime refused you" and "you asked wrong" makes every paired denial vacuous ([access-control-tests](../../code-practices/access-control-tests.md)).

#### Scenario: An unhosted identity is refused, not absent
- **WHEN** a debug request addresses an identity the runtime neither created nor linked
- **THEN** the response carries a client-error status other than 404 and names the unknown-identity or unknown-issuer refusal, and 404 remains reserved for a route the host does not serve or for an absent entry

#### Scenario: An absent entry is reported as absent, not as a refusal
- **WHEN** a debug request reads a path no entry exists at, under an identity or issuer the runtime does host
- **THEN** the response is 404

#### Scenario: A write outside the grant's write set is refused
- **WHEN** a caller writes, over the surface, a claim of a granted namespace that the local grant record covers read-only
- **THEN** the response is a client error and reading that claim back yields the value that was there before

#### Scenario: A burnt invite secret is refused
- **WHEN** an invite payload that has already been consumed is presented again
- **THEN** the response is a client error and the inviting host records no second connection

### Requirement: The debug surface exposes live ceremony secrets and stays bound accordingly
Invite and linking payloads cross the debug surface in the clear, each carrying its live one-time secret. The payloads are bearer-free as the ceremony specs require ([connection-establishment](connection-establishment.md), [device-linking](device-linking.md)) — no ticket and no identity proof, nothing that grants durable access — but until the secret is burnt or expired, whoever captures the payload can consume the invitation in the intended recipient's place. No namespace ticket crosses the surface at all. The surface carries no authentication of its own: reaching the surface is reaching the node. The host SHALL bind loopback unless a wider bind is configured explicitly, so exposing the surface beyond the local host is a deliberate act — the container harness's act, not a default.

#### Scenario: Default bind is loopback
- **WHEN** the host starts with no bind address configured
- **THEN** it listens on a loopback address only

#### Scenario: A wider bind is explicit
- **WHEN** the host starts with a bind address configured
- **THEN** it listens on exactly that address

### Requirement: The host stays off the product path
The host exists so a test can reach a node from outside its process — the container stand and the demo are its only intended deployments. A product host — mobile, desktop — embeds the runtime core in-process and reaches other nodes only over the runtime's own protocols; no product path includes an HTTP endpoint. The runtime crate SHALL declare no HTTP server or client of its own: the host depends on the runtime, never the reverse. What iroh's relay client speaks to reach a relay server is transport underneath the runtime, not a surface of it, and no requirement here reaches into the transitive dependency tree. Nothing outside this repository may depend on this surface or its routes.

#### Scenario: The runtime serves no HTTP of its own
- **WHEN** the runtime crate is built on its own, with no host around it
- **THEN** it names no HTTP server or client among its own dependencies, it opens no HTTP listener, and no crate in the workspace besides the host depends on the host
