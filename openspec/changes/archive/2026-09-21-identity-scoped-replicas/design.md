# Design

## Context

See [proposal.md](proposal.md) for motivation, and ADR-0013 for the level of isolation this change implements. A node today runs one iroh endpoint, one gossip instance, one blob store and one docs engine, and that engine holds one replica per namespace in one replica store with one persisted author. Everything a session is judged by is derived from the caller's authenticated node id: the access book resolves it through the device sets published by each hosted identity, and where that resolution answers with several identities the rights are their union. The runtime's registry maps an issuer to one replica, and refuses to register a second identity onto a replica another one holds, because the reverse lookup would otherwise pick between them.

Three properties of the surrounding libraries shape what is possible without forking them. iroh refuses a connection whose target is the endpoint's own id, before any address or transport is considered, so two identities on one endpoint cannot reach each other over the network at all. iroh-gossip delivers a broadcast to the swarm and never to the broadcasting node's own subscribers, and it marks the message as received, so a co-located subscriber does not see it even echoed back by a neighbour; the same library does support any number of subscribers to one topic, so several identities on one endpoint can share the swarm. iroh-blobs takes an event sender that can refuse a request, so a gate over payload bytes is reachable later without a fork.

Three properties of pdn-store shape the rest. The sync codec runs over any pair of asynchronous streams — its own tests drive it over an in-memory pair — so a session without a network costs no second implementation. The store, the sync actor and the range reconciler know a replica only by its namespace, so keeping the fork's divergence away from them decides where the holder is allowed to appear; the sync actor does carry the session's egress filter through to the ingest gate, and a second session-scoped value rides that same path without reaching the tables or the reconciler. And a store's actor is one thread: it runs a current-thread runtime and does there everything the store does — the signature check on every entry it ingests, the range fingerprints a session computes, its inserts and its commits — while the database underneath admits one writer at a time.

The pairing and linking dialogues in the runtime are written against iroh's stream types directly, which is the one place where the in-process path needs the code to become generic.

The count this is sized for is 1 to 10 identities on a node, all of one person. That is what makes a fixed cost per identity affordable and a notification that reaches every co-located holder of a namespace cheap enough to be the whole mechanism.

## Goals / Non-Goals

**Goals:**

- Isolation that follows from where the bytes live: what one hosted identity acquires is stored, written and served separately from what another acquires, on the same node.
- One place where a caller's claim to act as an identity is checked, with the same answer for a session arriving over the network and for one running inside the process.
- Everything two identities on separate nodes can do, two identities on one node can do too: establish a connection, grant each other, and converge a namespace they both hold.
- A divergence from upstream iroh-docs that stays at the protocol boundary but for the cache bound a store is opened with and the session's ingest verdict riding the session path to the gate, so the replica store's tables, the open-replica map, the live state and the range reconciler keep tracking upstream.
- A hosted identity as the whole unit a session names, so nothing above it depends on how many endpoints the node binds.
- Nothing a node holds sits outside an identity, and nothing is served on a ticket alone: every replica is held for some identity, and every session carries a verdict.

**Non-Goals:**

- Hiding that two identities share a node. One endpoint publishes one node id into every device set, and a counterparty of both reads the same node id in both places.
- Scoping payload bytes. The blob store stays one, and its egress stays as it is.
- Proving in a session that the caller acts as an identity. Identities hold no key material, and a device that hosts two of them holds the material of both either way.
- Changing what a swarm carries, when a peer reconciles, or how a grant is recorded.
- Carrying over a directory written under the previous layout.
- A node shared by different people. One process holds the namespace secrets of every identity it hosts, so a node for several people is a question of process boundaries rather than of how one node divides itself, and the counts a server carries would also multiply the sessions a namespace held by many co-located identities costs.

## Decisions

### D1. A hosted identity owns an engine, a replica store and an author

A hosted identity holds its own half of the node: its own docs engine with its own replica store, its own persisted author, its own registry of bound namespaces and its own access book. The node keeps one endpoint, one gossip instance and one blob store under all of them. Two identities granted by one issuer therefore hold two replicas of that issuer's namespace, each reconciled on its own and each serving what its own grant covers, and a cell that two identities of one person are members of is held twice on that node. Each hosted identity's store work runs on that identity's own actor thread and against its own database, so identities busy at the same time occupy several cores, and the two halves of a session between two co-located identities run on two threads.

**Rejected alternatives:**

- Key the replica store by identity and namespace, keeping one engine.
  - **Pros:** one store, one actor thread and one file per node; one cache for the node rather than a share per hosted identity; no dispatch on the accept path.
  - **Cons:** one actor thread and one writer for every identity the node hosts, so signature checks, range fingerprints and commits queue behind one another however many cores the device has — the two halves of a session between two co-located identities included; the identity reaches the tables, the open-replica map, the live state and the range reconciler, which is where the fork tracks upstream — the one place this change keeps it out of; forgetting an identity becomes a range delete inside a live file whose pages a compaction returns, rather than the removal of a subtree.
- One replica per namespace with the acting identity filtering every local read.
  - **Pros:** no protocol change, no second engine, no in-process path.
  - **Cons:** the bytes of two identities stay together, so isolation holds only where a filter was remembered; a grant withdrawn toward one audience leaves its entries readable through the other; a removed member of a cell keeps receiving what the co-located member receives.
- An endpoint per identity.
  - **Pros:** the node id, the swarm membership and the transport separate too, which is what unlinkability needs.
  - **Cons:** a socket, a relay connection, address discovery and a probing schedule per identity, on a phone as well; identity creation waits for an endpoint to bind; a device in a device set becomes one identity's endpoint, so one physical device leaving means as many withdrawals as it hosts identities.

### D2. On the wire a hosted identity is a holder: 32 opaque bytes

pdn-store calls the party a replica is held for, and the party a caller acts for, the **holder**: 32 opaque bytes it compares and never interprets. `data-layer` fills a holder with the hosted identity's `PdnId`, so the store stays free of the platform's identity vocabulary, as it is free of it today.

### D3. The protocol's first message names both holders

The first message of a sync session carries the holder whose replica is addressed and the holder the caller acts for, beside the namespace it already carries. The dialing side knows both: the contact it dials was derived from a device set or a member statement, which names the identity it belongs to, and the identity it acts as is the identity the session was started for.

A peer the engine recorded as useful carries a node id and nothing else, so a replica also states whom such a peer is dialed as: the issuer for a data namespace, the identity for a store its own devices share. Without that statement a recorded peer would be dialed as the dialing side's own holder, which is right for a sibling and wrong for every other case — a granted replica's peers are the issuer's devices, and naming the wrong holder is refused as not hosted.

**Rejected alternatives:**

- Name only the caller's holder and let the serving side pick a replica.
  - **Cons:** a node can hold the same namespace in several hosted identities with equal claim to it — an issuer and an audience it granted, or two members of one cell — so the pick is ambiguous exactly where hosted identities must not be confused.

### D4. A caller acts as an identity whose device set lists its node id

The serving side admits the caller's named identity when the records it can read of that identity list the caller's node id as one of its devices, and refuses the session as not hosted otherwise. Which records those are follows from who is serving: a device of the identity resolves it in that identity's own directory, and a hosted issuer serving a counterparty resolves it in the device set that counterparty published into their connection's metadata store, which is the resolution each side already uses for read rights. This is the resolution the node id already carried; naming an identity selects among the identities a node is genuinely a device of, and a node that is a device of none of them selects nothing.

A device the serving side has not yet seen published is refused until its record reaches it, and no longer: the records that admit a caller travel over a directory and a connection metadata store, whose bound is their ticket rather than the device set they carry (D17), so a device that joined while the counterparty was away carries its own record there and the next session admits it.

**Rejected alternatives:**

- A key per device and identity, published in the device set, signing the session's keying material.
  - **Pros:** the claim becomes a proof rather than an assertion.
  - **Cons:** a node that hosts two identities holds both keys, so the proof says exactly what the device set already says; new key material has to be minted, published, carried to a linked device and rotated.

### D5. Rights, write admission and contacts belong to the named identity

Session rights are computed from the named identity alone: for a hosted issuer, whether the caller is one of its devices and otherwise what that connection's grant record carries; for a replica held under a grant, the grant record of the identity that holds it. Write admission is recorded per hosted identity, replica and caller, and a granted replica's contacts are addresses paired with the identity each is dialed as, derived from the one connection that bound that replica.

The write set travels with the session it was decided for, the way the egress filter already does, rather than being deposited under the pair it was decided for. A deposit outlives its session: two sessions of one node acting as two identities overwrite each other's, and a session that resolves to a closed egress still ingests — under whatever a withdrawn grant left behind. Both are how a peer comes to write past a right it no longer has, or to draw a refusal for an entry it was entitled to write, which it acts on by retracting an entry it holds legitimately.

### D6. An accepted connection is dispatched by its first message

The docs protocol handler reads the first message of an accepted connection, resolves the holder it names, and hands the streams and that message to the engine of that hosted identity; a message naming a holder the node does not host is refused as not hosted, in the same shape as a replica that is not here. Reading that first message belongs to the handler and never to an engine: an engine is only ever handed a session whose first message is already read, so no accept path waits on the wire inside an engine's own loop, where it would stop every other thing that loop does. A node hosting one identity takes the same contract with a resolver of one holder, so the two assemblies differ in the resolver alone.

### D7. Two identities of one node sync over in-process streams

A dial whose target address carries this node's own endpoint id runs the session over an in-memory pair of streams: the same codec, the same session setup on both sides, the same access provider call, the same ingest gate and the same egress filter, with the peer node id supplied as this node's own. The rule is a property of the address, so it also covers a contact list or a ticket that names this node after a restart, and no caller chooses between transports.

**Rejected alternatives:**

- Copy entries between the two replicas directly.
  - **Pros:** no session, no codec, no snapshot.
  - **Cons:** the gate and the filter are the isolation, and a path that skips them is a path where co-located identities are not isolated at all.
- A loopback address or a second endpoint bound to the same key.
  - **Cons:** iroh refuses by comparing endpoint ids, before the address is looked at, and two endpoints on one key are one id.

### D8. The pairing dialogue between two identities of one node runs the same way

Establishment between two identities of one node runs the pairing dialogue over an in-memory pair of streams, with the one-time secret verified and burned as it is over the network, and the stores assembled by the same steps. The dialogue's message exchange becomes generic over its streams so that one implementation serves both transports.

### D9. A write announces to the identities of its own node directly

A write broadcasts to the swarm as it does now, and in the same step notifies the co-located identities that hold the same namespace, which then reconcile over the in-process path. An announcement names the holder of the replica that wrote it, so a receiving node knows which replica to address when it pulls.

**Rejected alternatives:**

- Rely on the swarm to carry a co-located identity's write.
  - **Cons:** iroh-gossip does not deliver a broadcast to the broadcasting node's own subscribers and marks it received, so it never arrives, with or without a neighbour.
- Leave co-located identities to the periodic reconcile pass.
  - **Cons:** a write by one identity would reach the other on the interval while reaching another node at once.

### D10. Each hosted identity writes with its own author

Every hosted identity holds one author, persisted with its replicas and stable across restarts, and every write it performs is signed by that author. A write into a replica the identity holds under a grant therefore carries the author of the identity that was granted, and what a cell or a counterparty binds to a member is the author of that member on that device. The runtime's provisional-write tracker judges an entry by the author of the identity whose replica holds it, and a retraction verdict is recorded in that identity's directory, which the verdict's author names.

### D11. An import names the identity the replica is held for

Importing a ticket names the identity the replica is held for, and the import lands in that identity. The runtime imports a ticket that arrived inside a connection's grant record into the identity of the identity the grant is addressed to, and refuses to import it into another; the check lives where the grant is known, since a ticket handed over out of band carries no record of where it came from.

### D12. The storage directory holds a subdirectory per hosted identity

A node's directory keeps its endpoint key and its lock where they are, and holds one subdirectory per hosted identity with that identity's replica store and author. The blob store stays one directory for the node. Those subdirectories are also what a store's share of the cache budget is counted from (D14), so the layout is read as well as written.

### D13. Every create and every import names its identity

Creating or importing a replica names the identity it is held for, the private metadata directory and the connection metadata stores included. An assembly hosts the identity whose replicas it holds, as the product does, so the records that judge a session are there wherever a replica is.

**Rejected alternatives:**

- A default hosted identity that a create or an import without a named hosted identity lands in.
  - **Pros:** the suites that assemble the data layer directly keep their arrange steps unchanged.
  - **Cons:** the default carries the most permissive posture on the node, so a call site that names no hosted identity fails open into it silently — the class of mistake this change exists to remove.
- A hosted identity required in the runtime and optional in `data-layer`.
  - **Cons:** the permissive bucket stays in the library, and what keeps the runtime out of it is discipline rather than the shape of the call.

### D17. No replica is served without an owner and a verdict

Every replica sits in the identity of an identity the node hosts, and a data replica's session is judged by that identity's records; a session the records cannot judge is refused. The store takes a session access provider as a requirement of assembling it, so a consumer states what judges its sessions before it can serve one. A directory and a connection metadata store keep the ticket bound Invariants 1 and 3 give them, because a directory carries the records every other verdict reads and judging it by its own unconverged device set would close the bootstrap that delivers them.

**Rejected alternatives:**

- Keep the store's provider optional, with an unset provider serving every session whole.
  - **Pros:** the fork's constructor and its upstream-derived suites stay as upstream wrote them.
  - **Cons:** the permissive posture is what a consumer gets by forgetting, on a fork whose reason to exist is the gate.
- Keep the library's ticket-bounded replica for assemblies that host no identity.
  - **Pros:** the suites that reconcile a replica between two bare nodes keep their arrange steps.
  - **Cons:** those steps are a ticket handed over by hand, which the product path practice admits only as a test's subject or its negative control, and the state they arrange — data under no identity — is one the product never reaches.

### D14. A replica store's cache is a share of a node budget, cut as the store opens

A node is spawned with the memory its replica stores may hold together, and the share one hosted identity takes is that memory divided by the identities its storage directory holds once that identity has a subdirectory of its own there (D12), cut as that identity's store opens. A device carrying one identity therefore gives it the whole budget, the second identity of a directory takes half, and the tenth a tenth. The bound cannot be changed on an open store, so a store keeps what it opened at: an identity created or linked while the node runs takes a share cut from the set that now includes it, every other hosted identity keeps running untouched, and the bounds handed out together pass the budget until the next start cuts every share from the whole set. A session that grows from one identity to ten hands out under three budgets in all, and the node reports that it stands above its budget, because it is the only place that is visible. The workspace states one default in a single place that the hosts and the suites take: 1 GiB for a node's replica stores, which is the whole budget for a device carrying one identity. A host on a phone states that one number once at that application's first start, from the memory that device can spare, and keeps it with its own settings; this change states that expectation and writes no mobile code. The bound caps resident memory rather than reserving it — pages enter a cache as they are read and leave it at the cap — and the store reports what it uses and how often it evicts, so both numbers are answered by measurement.

**Rejected alternatives:**

- A count of identities stated by the host at spawn.
  - **Pros:** one share for the whole start, cut before any store opens; a host that knows it will carry five says so before it carries them.
  - **Cons:** no platform answers that count, so a host either guesses or copies the default — and a host that states one identity while carrying ten multiplies the bound by the nine it left out, while a host that states ten on a device carrying one cuts a single heavy store to a tenth of the budget it could have had. The node cannot tell either case from a correct statement, so neither is reported.
- Leave the cache at the storage library's own default.
  - **Cons:** the cap is per database and there is one database per hosted identity, so the caps multiply with the identities a node hosts, and each evicts knowing nothing of the others.
- One budget shared by every hosted identity's cache.
  - **Cons:** the bound cannot be changed on an open store, so an identity created while the node runs would mean reopening every other hosted identity's store and cutting the sessions it is in.
- Recut the share among the identities the node holds whenever that set changes.
  - **Pros:** the bounds handed out always sum to the budget, with no overshoot to report.
  - **Cons:** same reopening, and a share that moves under a running store is a bound the store cannot take.

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
| imports a ticket into another identity | refused (D11) |
| asks for payload bytes by hash | served, as it is today |

### D16. A grant binds and unbinds for the identity it addresses

The namespace a grant names is imported into the identity of the identity the grant is addressed to, and a withdrawal takes that replica out of that identity. One pair binds one issuer there — a grant names its own identity as the data issuer, and an identity holds one connection per counterparty — so the binder decides from the pair it swept and the registry that identity holds.

**Rejected alternatives:**

- The count of bound pairs, narrowed from the node to the identity.
  - **Pros:** the decision stays exact under a delegated grant naming another identity's data, the one arrangement that puts two pairs of one hosted identity on one issuer.
  - **Cons:** a mechanism and a spec paragraph that decide nothing under the arrangements the platform has, and a scenario that can be arranged only by clearing the binder's bookkeeping by hand.

## Operating conditions

Walked against [operating-conditions](../../specs/code-practices/operating-conditions.md), with the ones that change the outcome named.

- **Several identities on one node** is what the change is about: it moves from a classification that can resolve to several identities to a session that names exactly one, and every decision above is a consequence (D1, D3, D4, D5).
- **One device or several** changes the outcome twice: an identity's replicas reconcile with that identity's other devices as they do now, and a co-located identity reaches them only through the in-process path (D7).
- **A device that restarts** changes the outcome: each hosted identity comes back with its own store and author, and contacts that name this node's own address route to the in-process path rather than failing to dial (D7, D10, D12).
- **A device linking before, during or after a process** keeps its shape, because linking is one identity's act and stays within that identity's own stores.
- **Capabilities granted, narrowed, widened, revoked and granted again** change the outcome: a withdrawal toward one identity now unbinds that identity's replica and leaves the other's untouched, which is the property four of the reachability scenarios currently assert in the opposite direction.
- **An unstable connection** is unchanged for network sessions and absent for in-process ones, which fail only as a local error.
- **A disk that fills** is affected in degree: a namespace held by two identities of one node is stored twice, and the storage a node needs grows with the identities it hosts, not with the namespaces alone.

## Measurement

What the decisions above leave to measurement, taken against a store of 100,000 entries — a 64 MiB replica store file, the size a personal store of a few years of claims and connection metadata reaches. The figures come from a release build on one machine, over loopback, with the blob store in memory, one namespace, payloads of one small size, and nothing else touching either store while they run; they are stable across runs to a tenth of a percent, and they are orders of magnitude rather than budgets to hold anyone to.

**A catch-up is the receiving identity's actor thread, almost entirely (D1).** Reconciling those 100,000 entries into an empty replica takes 6.0 seconds of wall clock, of which 5.6 seconds — 93% — is spent inside the receiving store's actor thread and 0.11 seconds — under 2% — inside the serving one's. The receiving side pays per entry (the insert, the ingest verdict, the index write); the serving side only reads ranges. So a store per hosted identity buys close to the whole parallelism it looks like it should: two identities catching up on one actor thread would serialise, and on two threads they do not. It also answers the second question in the negative for this case — the serving side's 2% is all a cached fingerprint tree could cut, and the cost is not there.

**A pass over a converged pair is fingerprint work, and it is not free (D1).** The same pair reconciled again with nothing to carry takes 39 milliseconds, of which 19 milliseconds is each side's actor thread: 97% of the exchange is the two stores walking their ranges to agree that they match. The figure is for a store of this size and grows with it, so the standing cost is the pairs a node holds times that walk divided by the reconcile interval: at tens of seconds and a handful of pairs it is a fraction of a percent of a core, and a store of a million entries across ten pairs at a thirty-second interval is over a tenth of one. This change raises that cost by design, because a namespace two co-located identities hold is two replicas and so two pairs where it used to be one. A cached fingerprint tree is what would remove it, and these are the numbers that make the case for building one; nothing in this change needs it.

**What a catch-up spends is the insert path, not the protocol (D1).** Receiving an entry costs 60 microseconds against 24 for writing one straight into a store and 66 for writing one through the API, so a reconciled entry costs about what a local write costs and the wire and the range exchange are not where the time goes. A catch-up that has to be faster is made faster by batching inserts inside the actor, not by changing the protocol.

**The cache a store uses is its working set, not its file (D14).** Filling those 100,000 entries and then scanning them whole leaves 36 MiB resident, and the same 36 MiB at every share above it: 1 GiB, 256 MiB and 102 MiB all held 36 MiB with no eviction at all. At a 32 MiB share — a 1 GiB budget cut 32 ways — the cache held its cap and evicted 1,044 times during the fill and 3,016 times by the end of the scan. So the default of 1 GiB for one identity is far above what one store of this size wants, the breach point for a store like this sits near 36 MiB, and a 1 GiB budget stays comfortable divided up to about 28 ways. A host on a phone that states a smaller budget should read that figure as "36 MiB per identity carrying a store of this size", and a share below it costs evictions rather than correctness.

## Risks / Trade-offs

- [Two identities on one node stay linkable] → accepted; one endpoint publishes one node id into both device sets, and a counterparty of both sees it; separating the node ids is what an endpoint per identity would take, and this arrangement stays open without moving what sits above it (D1).
- [The blob store is shared and serves any hash to any caller] → entries belong to an identity, payload bytes do not; a caller that learns a hash gets the bytes and can probe whether this node holds content it already has; the gate arrives with the identity-bound authorization work, and iroh-blobs already offers the hook it needs.
- [A node that hosts two identities is one trust domain] → it holds the secrets of both, so acting as either identity is free to it; the checks bound it to the identities it is a device of, and the separation it gains is of honest storage and authorship, not of a compromised process (D4, D15).
- [A second transport is a second place to be wrong] → the in-process path runs the same codec, the same session setup and the same gates, and every scenario that crosses it is paired with the check that a deliberately broken gate fails it (D7, D8).
- [A namespace held by two identities of one node is stored and synced twice] → accepted as the price of separation; the in-process path keeps the second copy cheap in bandwidth, not in disk, and the second pair costs a fingerprint walk on every pass whether anything changed or not (D1, D7, Measurement).
- [A thread and a replica store per hosted identity] → the cost is linear in identities, paid at each one's creation, and affordable at the count this is sized for; what one thread buys and what one store's cache uses are measured above.
- [Replica store caches multiply] → the cache cap is per database and one database per node made it invisible; with a store per identity the size becomes configuration with one stated default, and the value a phone passes is that application's own decision (D14).
- [The protocol's first message changes shape] → nothing deployed speaks it, and the changes that build on it — the trigger transport of reconcile-trigger, the mobile facade, cells — are named in the proposal's Impact.
- [Four scenarios that rest on one replica shared by two audiences are rewritten or removed] → they defend a property the change removes on purpose; three are restated as the separated expectation and keep their paired denial, and the one that pins the count of bound grants goes with the count (D16).

## Migration Plan

Nothing deployed holds data, so there is no format migration and no compatibility window: a node starting on a directory written under the previous layout finds no hosted identity subdirectory and holds no identity from it, and nothing inspects or reports what the previous layout left there.

The order of landing follows the dependencies. The protocol's hosted identity fields and the dispatcher come first, carrying one hosted identity per node so the workspace stays green while nothing above names a second one. The identity per hosted identity follows in `data-layer`, then the acting identity through `pdn-node` and its host, then the in-process path for sessions and for pairing. The stand's assertion of read isolation between two identities on one node closes the change, because it is the first place the property is observed from outside the process.
