# Design

## Context

See [proposal.md](proposal.md) for motivation, and ADR-0013 for the level of isolation this change implements. A node today runs one iroh endpoint, one gossip instance, one blob store and one docs engine, and that engine holds one replica per namespace in one replica store with one persisted author. Everything a session is judged by is derived from the caller's authenticated node id: the access book resolves it through the device sets published by each hosted identity, and where that resolution answers with several identities the rights are their union. The runtime's registry maps an issuer to one replica, and refuses to register a second identity onto a replica another one holds, because the reverse lookup would otherwise pick between them.

Three properties of the surrounding libraries shape what is possible without forking them. iroh refuses a connection whose target is the endpoint's own id, before any address or transport is considered, so two identities on one endpoint cannot reach each other over the network at all. iroh-gossip delivers a broadcast to the swarm and never to the broadcasting node's own subscribers, and it marks the message as received, so a co-located subscriber does not see it even echoed back by a neighbour; the same library does support any number of subscribers to one topic, so several scopes on one endpoint can share the swarm. iroh-blobs takes an event sender that can refuse a request, so a gate over payload bytes is reachable later without a fork.

Three properties of pdn-store shape the rest. The sync codec runs over any pair of asynchronous streams — its own tests drive it over an in-memory pair — so a session without a network costs no second implementation. The store, the sync actor and the range reconciler know a replica only by its namespace, so keeping the fork's divergence away from them decides where the scope is allowed to appear. And a store's actor is one thread: it runs a current-thread runtime and does there everything the store does — the signature check on every entry it ingests, the range fingerprints a session computes, its inserts and its commits — while the database underneath admits one writer at a time.

The pairing and linking dialogues in the runtime are written against iroh's stream types directly, which is the one place where the in-process path needs the code to become generic.

The count this is sized for is 1 to 10 identities on a node, all of one person. That is what makes a fixed cost per identity affordable and a notification that reaches every co-located holder of a namespace cheap enough to be the whole mechanism.

## Goals / Non-Goals

**Goals:**

- Isolation that follows from where the bytes live: what one hosted identity acquires is stored, written and served separately from what another acquires, on the same node.
- One place where a caller's claim to act as an identity is checked, with the same answer for a session arriving over the network and for one running inside the process.
- Everything two identities on separate nodes can do, two identities on one node can do too: establish a connection, grant each other, and converge a namespace they both hold.
- A divergence from upstream iroh-docs that stays at the protocol boundary, so the replica store, the sync actor and the range reconciler keep tracking upstream.
- A scope that is the whole unit a session names, so nothing above it depends on how many endpoints the node binds.
- An assembly that hosts no identity — every `data-layer` suite that is not about identities — keeps working unchanged.

**Non-Goals:**

- Hiding that two identities share a node. One endpoint publishes one node id into every device set, and a counterparty of both reads the same node id in both places.
- Scoping payload bytes. The blob store stays one, and its egress stays as it is.
- Proving in a session that the caller acts as an identity. Identities hold no key material, and a device that hosts two of them holds the material of both either way.
- Changing what a swarm carries, when a peer reconciles, or how a grant is recorded.
- Carrying over a directory written under the previous layout.
- A node shared by different people. One process holds the namespace secrets of every identity it hosts, so a node for several people is a question of process boundaries rather than of scopes, and the counts a server carries would also multiply the sessions a namespace held by many co-located scopes costs.

## Decisions

### D1. A hosted identity is a scope, and a scope owns an engine, a replica store and an author

A scope is one hosted identity's half of the node: its own docs engine with its own replica store, its own persisted author, its own registry of bound namespaces and its own access book. The node keeps one endpoint, one gossip instance and one blob store under all of them. Two identities granted by one issuer therefore hold two replicas of that issuer's namespace, each reconciled on its own and each serving what its own grant covers, and a cell that two identities of one person are members of is held twice on that node. Each scope's store work runs on that scope's own actor thread and against its own database, so identities busy at the same time occupy several cores, and the two halves of a session between two co-located scopes run on two threads rather than queueing behind each other.

**Rejected alternatives:**

- Key the replica store by scope and namespace, keeping one engine.
  - **Pros:** one store, one actor thread and one file per node; one cache for the node rather than a share per scope; no dispatch on the accept path.
  - **Cons:** one actor thread and one writer for every identity the node hosts, so signature checks, range fingerprints and commits queue behind one another however many cores the device has — the two halves of a session between two co-located scopes included; the scope reaches the tables, the open-replica map, the live state and the range reconciler, which is where the fork tracks upstream; forgetting an identity becomes a range delete inside a live file whose pages a compaction returns, rather than the removal of a subtree.
- One replica per namespace with the acting identity filtering every local read.
  - **Pros:** no protocol change, no second engine, no in-process path.
  - **Cons:** the bytes of two identities stay together, so isolation holds only where a filter was remembered; a grant withdrawn toward one audience leaves its entries readable through the other; a removed member of a cell keeps receiving what the co-located member receives.
- An endpoint per identity.
  - **Pros:** the node id, the swarm membership and the transport separate too, which is what unlinkability needs.
  - **Cons:** a socket, a relay connection, address discovery and a probing schedule per identity, on a phone as well; identity creation waits for an endpoint to bind; a device in a device set becomes one identity's endpoint, so one physical device leaving means as many withdrawals as it hosts identities.

### D2. A scope is an opaque 32-byte identifier on the wire

pdn-store carries the scope as 32 opaque bytes and compares them; the meaning of those bytes is `data-layer`'s, which passes the hosted identity's `PdnId`. The store stays free of the platform's identity vocabulary, as it is free of it today.

### D3. The protocol's first message names both scopes

The first message of a sync session carries the scope whose replica is addressed and the scope the caller acts as, beside the namespace it already carries. The dialing side knows both: the contact it dials was derived from a device set or a member statement, which names the identity it belongs to, and the scope it acts as is the scope the session was started for.

**Rejected alternatives:**

- Name only the caller's scope and let the serving side pick a replica.
  - **Cons:** a node can hold the same namespace in several scopes with equal claim to it — an issuer and an audience it granted, or two members of one cell — so the pick is ambiguous exactly where scopes must not be confused.

### D4. A caller acts as an identity whose device set lists its node id

The serving side admits the caller's named scope when that identity's own records list the caller's node id as one of its devices, and refuses the session as not hosted otherwise. This is the resolution the node id already carried; naming a scope selects among the identities a node is genuinely a device of, and a node that is a device of none of them selects nothing.

**Rejected alternatives:**

- A key per device and identity, published in the device set, signing the session's keying material.
  - **Pros:** the claim becomes a proof rather than an assertion.
  - **Cons:** a node that hosts two identities holds both keys, so the proof says exactly what the device set already says; new key material has to be minted, published, carried to a linked device and rotated.

### D5. Rights, write admission and contacts belong to the named scope

Session rights are computed from the named scope alone: for a hosted issuer, whether the caller is one of its devices and otherwise what that connection's grant record carries; for a replica held under a grant, the grant record of the scope that holds it. Write admission is recorded per scope, replica and caller, and a granted replica's contacts are addresses paired with the scope each is dialed as, derived from the one connection that bound that replica.

### D6. An accepted connection is dispatched by its first message

The docs protocol handler reads the first message of an accepted connection, resolves the scope it names, and hands the streams and that message to the engine of that scope; a message naming a scope the node does not host is refused as not hosted, in the same shape as a replica that is not here. The engines below the dispatcher keep the accept path they have.

### D7. Two scopes of one node sync over in-process streams

A dial whose target address carries this node's own endpoint id runs the session over an in-memory pair of streams: the same codec, the same session setup on both sides, the same access provider call, the same ingest gate and the same egress filter, with the peer node id supplied as this node's own. The rule is a property of the address, so it also covers a contact list or a ticket that names this node after a restart, and no caller chooses between transports.

**Rejected alternatives:**

- Copy entries between the two replicas directly.
  - **Pros:** no session, no codec, no snapshot.
  - **Cons:** the gate and the filter are the isolation, and a path that skips them is a path where co-located identities are not isolated at all.
- A loopback address or a second endpoint bound to the same key.
  - **Cons:** iroh refuses by comparing endpoint ids, before the address is looked at, and two endpoints on one key are one id.

### D8. The pairing dialogue between two identities of one node runs the same way

Establishment between two identities of one node runs the pairing dialogue over an in-memory pair of streams, with the one-time secret verified and burned as it is over the network, and the stores assembled by the same steps. The dialogue's message exchange becomes generic over its streams so that one implementation serves both transports.

### D9. A write announces to the scopes of its own node directly

A write broadcasts to the swarm as it does now, and in the same step notifies the co-located scopes that hold the same namespace, which then reconcile over the in-process path. An announcement names the scope of the replica that wrote it, so a receiving node knows which replica to address when it pulls.

**Rejected alternatives:**

- Rely on the swarm to carry a co-located scope's write.
  - **Cons:** iroh-gossip does not deliver a broadcast to the broadcasting node's own subscribers and marks it received, so it never arrives, with or without a neighbour.
- Leave co-located scopes to the periodic reconcile pass.
  - **Cons:** a write by one identity would reach the other on the interval while reaching another node at once.

### D10. Each hosted identity writes with its own author

Every scope holds one author, persisted with its replicas and stable across restarts, and every write a scope performs is signed by it. A write into a replica the scope holds under a grant therefore carries the author of the identity that was granted, and what a cell or a counterparty binds to a member is the author of that member on that device. The runtime's provisional-write tracker recognises this node's own writes by the set of its scopes' authors.

### D11. An import names the scope that holds the replica

Importing a ticket names the identity the replica is held for, and the import lands in that scope. A ticket that arrived inside a connection's grant record is imported into the scope of the identity the grant is addressed to, and an import that names another scope is refused.

### D12. The storage directory holds a subdirectory per scope

A node's directory keeps its endpoint key and its lock where they are, and holds one subdirectory per scope with that scope's replica store and author. The blob store stays one directory for the node.

### D13. Every create and every import names its scope

Creating or importing a replica names the scope it lands in, the private metadata directory and the connection metadata stores included, and the scope is the identity the replica is held for. An assembly that hosts no identity names a scope of its own choosing, and a scope the access book holds no records for is served and admitted whole to any holder of the ticket, which is what an unregistered replica means.

**Rejected alternatives:**

- A default scope that a create or an import without a named scope lands in.
  - **Pros:** the suites that assemble the data layer directly keep their arrange steps unchanged.
  - **Cons:** the default carries the most permissive posture on the node, so a call site that names no scope fails open into it silently — the class of mistake this change exists to remove.
- A scope required in the runtime and optional in `data-layer`.
  - **Cons:** the permissive bucket stays in the library, and what keeps the runtime out of it is discipline rather than the shape of the call.

### D14. A scope's replica store cache is a fixed share of a memory budget

The cache size a node is spawned with is the share one scope takes, and a host derives it from the memory it gives the replica stores and the number of identities the device is provisioned for. A store's cache bound is fixed when that store is opened, so an identity created while the node runs opens its store at the same share and every other scope keeps running untouched, and the node's worst case stays the budget the share was cut from. The workspace states one default of 1 GiB per scope in a single place that the desktop host and every test import. A host on a phone computes its own share once at that application's first start, from the memory that device can spare, and keeps it with its own settings; this change states that expectation and writes no mobile code. The bound caps resident memory rather than reserving it, and the store reports what it uses and how often it evicts, so the number is answered by measurement.

**Rejected alternatives:**

- Leave the cache at the storage library's own default.
  - **Cons:** the cap is per database and there is one database per scope, so the caps multiply with the identities a node hosts, and each evicts knowing nothing of the others.
- Divide the budget among the scopes the node currently holds.
  - **Pros:** a node hosting two identities uses the whole budget rather than two shares of it.
  - **Cons:** the bound cannot be changed on an open store, so adding an identity means reopening every other scope's store and cutting the sessions it is in, or leaving the node above its budget until the next start.
- A share chosen without regard to how many identities the device may host.
  - **Cons:** the node's worst case grows with every identity added, which is the multiplication this decision exists to bound.

### D15. The node is the trust boundary, and the checks bound what a device can claim

What a modified node can obtain is bounded by the identities it is genuinely a device of, and what it can produce is bounded by the author keys and namespace keys it holds.

| A modified node | Outcome |
| --- | --- |
| names an identity whose device set does not list it | refused as not hosted (D4) |
| names one of the identities it is a device of | served that identity's rights alone, never a union (D5) |
| opens a session per identity it hosts | obtains what each identity was granted, which its own stores already hold |
| authors an entry as another member | the entry's signature fails; author keys are held by that member's devices |
| places its own entry under another member's name in a cell | dropped by the gate, which resolves the author to a member through that member's statements |
| writes outside the write set of its grant | refused at the issuer's gate and retracted at the writer |
| imports a ticket into another scope | refused (D11) |
| asks for payload bytes by hash | served, as it is today |

## Operating conditions

Walked against [operating-conditions](../../specs/code-practices/operating-conditions.md), with the ones that change the outcome named.

- **Several identities on one node** is what the change is about: it moves from a classification that can resolve to several identities to a scope that is one, and every decision above is a consequence (D1, D3, D4, D5).
- **One device or several** changes the outcome twice: a scope's replicas reconcile with the same identity's other devices as they do now, and a co-located scope of another identity reaches them only through the in-process path (D7).
- **A device that restarts** changes the outcome: each scope comes back with its own store and author, and contacts that name this node's own address route to the in-process path rather than failing to dial (D7, D10, D12).
- **A device linking before, during or after a process** keeps its shape, because linking is one identity's act and happens inside its scope.
- **Capabilities granted, narrowed, widened, revoked and granted again** change the outcome: a withdrawal toward one identity now unbinds that identity's replica and leaves the other's untouched, which is the property three of the reachability scenarios currently assert in the opposite direction.
- **An unstable connection** is unchanged for network sessions and absent for in-process ones, which fail only as a local error.
- **A disk that fills** is affected in degree: a namespace held by two identities of one node is stored twice, and the storage a node needs grows with the identities it hosts, not with the namespaces alone.

## Risks / Trade-offs

- [Two identities on one node stay linkable] → accepted; one endpoint publishes one node id into both device sets, and a counterparty of both sees it; separating the node ids is what an endpoint per identity would take, and the scope admits that arrangement without moving what sits above it (D1).
- [The blob store is shared and serves any hash to any caller] → entries are scoped, payload bytes are not; a caller that learns a hash gets the bytes and can probe whether this node holds content it already has; the gate arrives with the identity-bound authorization work, and iroh-blobs already offers the hook it needs.
- [A node that hosts two identities is one trust domain] → it holds the secrets of both, so choosing either scope is free to it; the checks bound it to the identities it is a device of, and the separation it gains is of honest storage and authorship, not of a compromised process (D4, D15).
- [A second transport is a second place to be wrong] → the in-process path runs the same codec, the same session setup and the same gates, and every scenario that crosses it is paired with the check that a deliberately broken gate fails it (D7, D8).
- [A namespace held by two identities of one node is stored and synced twice] → accepted as the price of separation; the in-process path keeps the second copy cheap in bandwidth, not in disk (D1, D7).
- [A thread and a replica store per hosted identity] → the cost is linear in identities, paid at each one's creation, and affordable at the count this is sized for; the measurement belongs with the tasks.
- [Replica store caches multiply] → the cache cap is per database and one database per node made it invisible; with a store per identity the size becomes configuration with one stated default, and the value a phone passes is that application's own decision (D14).
- [The protocol's first message changes shape] → nothing deployed speaks it, and the changes that build on it — the trigger transport of reconcile-trigger, the mobile facade, cells — are named in the proposal's Impact.
- [Three scenarios that assert one replica shared by two audiences are rewritten] → they defend a property the change removes on purpose; each is restated as the separated expectation and keeps its paired denial.

## Migration Plan

Nothing deployed holds data, so there is no format migration and no compatibility window: a node starting on a directory written under the previous layout finds no scope subdirectory and holds no identity from it, and nothing inspects or reports what the previous layout left there.

The order of landing follows the dependencies. The protocol's scope fields and the dispatcher come first, carrying one scope per node so the workspace stays green while nothing above names a second one. The scope per hosted identity follows in `data-layer`, then the acting identity through `pdn-node` and its host, then the in-process path for sessions and for pairing. The stand's assertion of read isolation between two identities on one node closes the change, because it is the first place the property is observed from outside the process.
