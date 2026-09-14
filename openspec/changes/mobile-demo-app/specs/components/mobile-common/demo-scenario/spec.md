# mobile-common: demonstration scenario

The demonstration is what a person witnesses, so it is specified rather than left to a script written on the day. Each act below is one the runtime's own scenario tests cover, save the one named where it appears, and each is required to appear beside the refusal that gives it meaning: an act shown only in its allowed direction demonstrates nothing about a product whose whole subject is the boundary.

The demonstration follows one person, Alice, across 2 devices of one identity, and one peer, Bob, on a node of his own. Alice starts on a node running on a laptop, joins her phone to that identity through the linking ceremony, and only then does Bob's node establish a connection with her. The order is part of the subject rather than a convenience of the staging: the phone joins an identity that already holds entries, and the connection Bob makes afterwards reaches Alice's laptop node, where nobody performs an act.

The audience decides whether this is worth building. That fixes two things about the form. Nothing is shown that a person cannot see happening. And nothing is claimed that the code does not do, because a demonstration that oversells is discovered later by the same audience.

One physical phone is a limit of this staging, and it is stated rather than worked around. Alice's phone is the only node a person taps acts into by hand; Bob's node, Alice's own laptop node, and the outsider's are processes on the presenter's machine, each acted on by the run-through's script against its debug surface and watched through a browser page pointed at the same surface, running the same screens the phone runs. Every act whose subject is what a person sees is therefore watched on a screen — the phone or that browser page — and never narrated from a terminal instead; both directions of granting are watched for that reason, each on the screen of the identity doing the granting.

## ADDED Requirements

### Requirement: The demonstration runs on nodes that can reach each other, and the path is named
The demonstration SHALL be staged on one physical phone together with the further nodes of the staging. The phone SHALL be a physical device: the application SHALL NOT be staged on an Android emulator, and SHALL NOT be staged on an iOS simulator. The reason is the demonstration's subject rather than reachability — the claim being made is about a phone in a hand, and a window on a laptop is not one. Development against a simulator is unaffected; the audience is what needs a physical device.

The narration SHALL name what carries the traffic, because every node of the staging is spawned with the widest connectivity the runtime offers and that is a choice with parties in it. The node publishes its addresses under its node id to n0's public name servers and resolves its peers through them, and a session that finds no direct path is carried by n0's relay servers. Those servers therefore see a node id, the addresses it publishes, and the times and sizes of traffic between 2 node ids. They see none of the content, which is encrypted between the 2 endpoints, and they hold nothing that names a person: an identity carries no key material and never leaves the nodes that host it.

The narration SHALL also state what the choice gives away, which is availability rather than content: a published node id resolves globally, so anyone holding one can ask whether that device is up and which relay it is homed on, and no withdrawal takes that back. The staging pays it because a phone that moves between networks is unreachable without it, and the demonstration says so rather than letting the audience assume the narrower posture the runtime also offers.

Whether a given session is direct or relayed is not something the screens report, so the demonstration SHALL NOT claim either. What it claims is the narrower and true statement: no account, and no party that knows who the 2 people are.

The network is part of the staging. A network that forbids traffic between its clients pushes every session onto the relay path rather than breaking it, which is worth knowing before the day but is not a reason to change the staging.

#### Scenario: The phone and a node on the presenter's machine establish a connection
- **WHEN** the phone consumes a payload minted by a node on the presenter's machine
- **THEN** the connection is established over the runtime's own protocols, with no account and no party that knows who either person is

#### Scenario: The servers in the path are named
- **WHEN** the first connection of the demonstration is established
- **THEN** the narration states that the node publishes its addresses to n0's name servers and that a session may travel through n0's relay, states that a published node id answers globally whether the device is up, and claims neither that the path is direct nor that those servers see the content

### Requirement: The staging names its nodes, and 4 of them are needed
The demonstration SHALL name each node it uses, the person it stands for, its platform, and whether it is a phone. Exactly one node SHALL be a phone running the application, and it SHALL be the device that joins Alice's identity through the linking ceremony. A node that is not a phone SHALL be identified as such in the narration at the moment it first appears, together with how its payload reaches the phone: a machine has no camera, so it mints the payload and renders it as a code on its own screen, and the phone is the side that reads.

4 nodes are needed, and each for a reason. Alice's laptop node is where her identity is created and her first entries are written. Alice's phone joins that identity, and it is needed twice over: once as the device that comes up caught up, and once as a device of an identity whose other device goes away. Bob's node holds an identity of his own and is the party a grant names. A fourth node is required because the outsider must hold no connection to Alice, and the other 3 all do.

The fourth cannot be saved by hosting a second identity on Bob's node. The data service is keyed by the issuer whose namespace is read, not by the identity a screen believes it is acting under, so once that node has bound Alice's replica it answers the read whichever identity is selected. The outsider is a node or it is nothing.

#### Scenario: Every node that is not a phone is introduced as one
- **WHEN** a node that is not a phone takes part for the first time
- **THEN** the narration says it is not a phone and says how its payload reached it

### Requirement: Every act is the product's own act
Each act SHALL be performed through the host surface as an application performs it. No namespace ticket is handed over, no reconciliation is forced, no state is reset between acts, and waiting for a value is repeating the read.

A demonstration arranged any other way shows the value arriving while the mechanism that should have carried it goes unexercised, and the arrangement is invisible afterwards because the value on the screen is the same value either way ([product-path-arrangement](../../../code-practices/product-path-arrangement.md)).

A node that is not a phone is driven over the runtime's own debug surface, which exposes the runtime's operations and nothing beside them — no ticket, no import, no forced reconciliation. Driving it is therefore the counterparty's own act rather than a shortcut around the product.

#### Scenario: Nothing in the staging bypasses the product
- **WHEN** the whole demonstration is run end to end
- **THEN** every act corresponds to an exported call of the host surface or to the same runtime call on a node driven from a terminal or from a browser page pointed at its debug surface, and no act reaches a store, a ticket, or a reconciliation directly

#### Scenario: No act is preceded by a reset
- **WHEN** the acts are performed in order
- **THEN** each begins from the state the previous one left, and no node is restarted or cleared between them

### Requirement: Waiting is shown as waiting
Where a value crosses between nodes, the demonstration SHALL show the waiting rather than cut around it: the screen says it is waiting, and it arrives while the audience watches. The configured reconcile interval SHALL be short enough that a first appearance is a pause and not an interruption.

Convergence is the product's honest behaviour and hiding it would misrepresent the thing being sold. Which wait the cadence governs differs by act: a grantee reading a granted claim nudges its own reconciliation, so that read converges largely on its own, while a grant record reaching a peer, a connection record reaching Alice's other device, a write reaching a sibling device, and a linking catch-up all wait on the periodic pass. The acts of the second kind are the ones a long interval makes unwatchable, which is why the host configures a shorter one and states the number as its own configuration.

#### Scenario: A value arrives while the audience watches
- **WHEN** a value is written on one node and awaited on another
- **THEN** the awaiting screen shows that it is waiting, and the value appears without the narration moving on to something else in the meantime

### Requirement: A device joins an identity that already holds entries
The demonstration SHALL show Alice's phone joining her existing identity through the linking ceremony, coming up already carrying the entries written on the laptop before it joined, with no further act required of the person.

The phone SHALL host nothing at the moment it joins: the node is brought up and no identity is created on it, so the first identity it ever holds is one it received rather than one it made. An identity created on the phone beforehand would leave the audience unable to tell the two apart, and the claim being made is that an identity exists before the device and outlives it.

It SHALL show that the joining device hosts the identity it joined and no other identity of the same person, so that a device is seen belonging to an identity rather than to a person. Alice's laptop node therefore holds a second identity of hers at the moment the linking payload is minted, so that what the phone does not receive is real.

#### Scenario: A joining device comes up caught up
- **WHEN** a phone hosting no identity at all consumes a linking payload for an identity that already holds entries
- **THEN** the first identity it lists as hosted is that one, and it reads the entries written before it joined, with no further act of the person

#### Scenario: A device that joined one identity hosts that one only
- **WHEN** the laptop node hosts 2 identities of Alice and mints a linking payload for one of them
- **THEN** the phone hosts that identity alone, and nothing on it names the other

### Requirement: One application holds several identities, kept apart
The demonstration SHALL show the phone hosting more than one identity — the one it joined and one it creates itself afterwards, in that order — each with a data namespace of its own and a connection list of its own. The order is what keeps the 2 acts distinct: an identity made on the phone before the join would be indistinguishable, on the screen, from the one that arrived. The same entry path under both identities SHALL be shown holding different values, and the connection established under one SHALL be shown absent from the other's list.

This is the act the product's privacy claim rests on: 2 lives on one device that are not 2 accounts and share nothing by default.

#### Scenario: 2 identities on one device stay disjoint
- **WHEN** one identity holds a connection and an entry is written at the same path under both identities
- **THEN** the connection appears under that identity alone, and each identity reads its own value at the shared path

#### Scenario: A peer of one identity learns nothing of the other
- **WHEN** Bob reads what he has been granted
- **THEN** nothing he can read or list names the other identity or anything inside it

### Requirement: A connection is made by 2 people, and the code burns
The demonstration SHALL show an invite payload minted by Bob's node, rendered as a code on that machine's screen, and read by the phone's camera, ending in a connection that both sides list. No account and no party that knows who the 2 people are SHALL take part; the servers that carry the traffic are named where the staging names them, and none of them holds anything that identifies a person.

The connection SHALL then be shown on Alice's laptop node, which took no part in the ceremony and where nobody performs an act, because an identity holds its connections and a device of that identity comes to hold them too.

This is the one act no runtime test asserts directly. `sibling_serving.rs` and the linking scenarios hold the neighbouring properties for the same order — a device linked before the establishment receives the pair and the grant record and serves by them — and the connection list reads the same replicated directory those cross. The run-through verifies this act first, before anything is built on it.

The same code SHALL then be presented a second time and be refused, with no second connection recorded on the inviting side. The refusal SHALL be shown as a refusal on the screen, not as a silent absence of effect.

#### Scenario: A scanned code connects; the same code again is refused
- **WHEN** the phone scans the code and afterwards scans the same code again
- **THEN** the first scan establishes the connection and the second is refused, and Bob's node lists exactly one connection to that peer

#### Scenario: The connection is listed by both sides
- **WHEN** the establishment completes
- **THEN** each side lists the other's identity among the connections of the identity that took part

#### Scenario: The connection reaches Alice's other device on its own
- **WHEN** the ceremony completes on the phone
- **THEN** Alice's laptop node lists Bob among that identity's connections, with no act performed on it

### Requirement: Both directions of granting are watched, each on the screen of its issuer
The demonstration SHALL show Alice granting Bob a claim and Bob granting Alice claims of his own, over the same connection, each watched on the screen of the identity doing the granting.

The 2 directions carry different halves of the subject. With Alice as the issuer, what the audience sees on her phone is choosing a claim, publishing the grant, withdrawing it and granting it again, and what Bob obtains as grantee is read on the browser screen driving his node. With Bob as the issuer, the run-through's script performs the same 4 acts against his node's debug surface, and their effect is watched on that browser screen rather than read off the script's terminal output; what Alice obtains as grantee — a granted claim arriving, a writable claim accepting an edit, a read-only claim refusing one, and a withdrawn claim leaving the screen as no longer shared rather than as a fault — is shown on her phone.

#### Scenario: Each direction is watched where its screen is
- **WHEN** the granting acts are performed
- **THEN** the acts of an issuer are watched on that identity's own screen — Alice's phone, tapped by a person, or the browser screen driving Bob's node, showing what his script did — and the acts of its grantee are shown on the other party's own screen, and no act whose subject is what a person sees is narrated from a terminal instead

### Requirement: A grant reaches every device of the identity it names
Bob's grant is read first on whichever of Alice's devices happens to check first — her phone, in the demonstration's order. The demonstration SHALL show Alice's laptop node, which read no part of that grant before, reading the same claims afterwards, and reading a later change Bob makes to one of them, with no act performed on the laptop.

The property is the one act 3 already showed for a connection, now shown for what a grant carries: an identity holds the grant, not the device that first read it, so every device of that identity reads what was granted to it.

#### Scenario: A device that read no part of the grant reads it anyway
- **WHEN** Alice's laptop node reads the claims Bob granted her identity, having taken no part in reading that grant before
- **THEN** it reads exactly those claims, and a later change Bob makes to one of them arrives there with no act performed on it

### Requirement: A grant names claims, and the rest is absent rather than hidden
The demonstration SHALL show a grant naming particular claims of the granting identity's data, after which the grantee reads exactly those claims. The granting identity SHALL hold further claims at the time of the grant, so that what is withheld is real.

Claims the grant does not name SHALL be absent from what the grantee can read and from what it can list — not present and marked withheld, not shown as a count. The narration SHALL make this distinction explicitly, because the difference between hidden and absent is the product.

#### Scenario: Exactly the named claims arrive
- **WHEN** Alice holds several claims and grants one of them to Bob
- **THEN** Bob reads that claim and its later updates, and listing yields nothing about the others — neither their content, nor their paths, nor their number

#### Scenario: The grantee's screen shows a shared field, not a redacted record
- **WHEN** Bob has granted Alice a claim and she opens what this peer granted her
- **THEN** the screen shows the granted claims and no placeholder standing for anything else

### Requirement: A granted claim may be writable, and read-only refuses at the screen
The demonstration SHALL show 2 claims of Bob's granted to Alice over one connection, one read-only and one writable. Alice's edit of the writable claim SHALL be shown reaching Bob's node. Her edit of the read-only claim SHALL be refused, with the refusal shown as what was refused and the previous value still in place.

The refused edit is the moment the boundary becomes visible on a device rather than in an argument: the phone in the grantee's hand declines.

#### Scenario: Read-only refuses the write beside read-write accepting it
- **WHEN** Alice edits both claims on the phone
- **THEN** the edit of the writable claim reaches Bob's node, and the edit of the read-only claim is refused with the previous value unchanged

### Requirement: A device stands in for the one that granted
Alice's phone establishes the connection with Bob and publishes the grant. The demonstration SHALL then put the phone in airplane mode and show Alice's laptop node carrying a fresh value of that granted claim to Bob.

Availability is thereby seen not to depend on the device that issued the grant. The gesture is airplane mode with the application still in view rather than a lock, because on one of the 2 platforms a lock ends the process and measures something else.

#### Scenario: The remaining device serves the granted peer
- **WHEN** the phone that established the connection and published the grant goes to airplane mode, and Alice's laptop node writes a new value for the granted claim
- **THEN** Bob reads the new value, obtained from the remaining device of the issuer

### Requirement: A withdrawal closes what the grant opened
The demonstration SHALL show Alice withdrawing on her phone the grant she published there, after which Bob no longer reads the claim, while Alice still reads her own entry. The withdrawal SHALL be performed as one act naming the peer and the issuer.

What the grantee's node does is stronger than emptying the claim: withdrawal unbinds the namespace, so the node stops knowing that issuer and every later read of it is refused rather than answered empty. The demonstration SHALL show that as the access closing and not as a fault, which is a requirement on the screen as much as on the narration — and the screen it is shown on is Alice's, when Bob withdraws the grant he gave her.

The demonstration SHALL also show the grant given again, over the same claim, and the access reopening. That is the path worth showing rather than the first grant: nothing that remembers a withdrawal may block what follows it ([operating-conditions](../../../code-practices/operating-conditions.md)), and a demonstration that ends on a closed door leaves the audience unable to tell a boundary from a dead end.

#### Scenario: Access ends with the grant
- **WHEN** Alice withdraws her grant on the phone
- **THEN** Bob's node stops answering for that issuer altogether, and Alice's own read of the same entry is unaffected

#### Scenario: The grantee's screen says no longer shared, not broken
- **WHEN** Bob withdraws the grant he gave Alice and she opens the screen that showed the claim
- **THEN** the screen says the peer no longer shares it, rather than showing it greyed, or showing the refusal the node now answers with as a fault

#### Scenario: The same claim is granted again and the access reopens
- **WHEN** Alice publishes a grant over the same claim after the withdrawal
- **THEN** Bob reads that claim again, with nothing left from the withdrawal blocking it

### Requirement: The operating conditions the demonstration covers are named, and so are the rest
The demonstration SHALL state which of the platform's operating conditions it exercises and which it does not ([operating-conditions](../../../code-practices/operating-conditions.md)).

Exercised: several identities on one node; one identity across 2 devices; a device joining an identity that already holds entries and before any connection exists; a connection established on one device reaching the other; a grant reaching a device other than the one that first read it; a device leaving while a peer still needs its data; a capability granted, withdrawn, and granted again over the same claim.

Not exercised, and named as such: a device that restarts and returns with its state, which the runtime does and no act here provokes; a disk that fills, which the runtime reports rather than swallows and no act here fills; a connection that degrades rather than ends; a capability narrowed and widened rather than closed and reopened; a process killed for memory, which a phone does and a container never did; a device joining an identity after a connection already exists, and one joining while a ceremony is in flight — the linking condition names 3 arrivals and the staging puts the earliest of them on stage; a withdrawal performed on a device other than the one that published the grant; and every act of a counterparty as the mobile application would show it, since Bob and the outsider run `pdn-node-http` processes rather than that application, watched through a browser's version of the same screens.

#### Scenario: The uncovered conditions are named rather than implied
- **WHEN** the demonstration is delivered
- **THEN** the conditions it does not cover are stated, and no act implies coverage of one of them

### Requirement: The narration states what is not shown
The demonstration SHALL state, rather than leave to inference: that what the screens show lives in this device's storage, which holds the only copy of it; that an identity carries no key material, so nothing here proves who a peer is; that the reconcile cadence is a configured number rather than a property of the network; which nodes in the staging are not phones, and that their side of every act runs through the run-through's script rather than a person's tap, watched on a browser's screen rather than the mobile application's; and that withdrawing a grant closes further delivery without recalling what was already delivered.

A demonstration silent on these invites the opposite assumption on each, and the assumption is what the audience carries away. The last is the one the demonstration would otherwise oversell hardest: a field vanishing from a phone looks like deletion, and the platform promises that access is gated before delivery rather than that delivered data can be retracted ([invariants](../../mee-pdn/invariants.md), Invariant 2).

#### Scenario: The absences are named
- **WHEN** the demonstration is delivered
- **THEN** each of the 5 absences is stated, and no act of the demonstration implies its opposite

#### Scenario: The withdrawal is not narrated as deletion
- **WHEN** the withdrawal act is shown and the claim disappears from the grantee's screen
- **THEN** the narration says that further delivery is closed and that what the grantee already received is not recalled

### Requirement: A party holding nothing is shown obtaining nothing
The demonstration SHALL include a node — not a second identity co-hosted with a party that already has access — holding no connection to Alice and no grant from her, shown obtaining nothing of her data: neither the granted claim nor any other, neither content nor the knowledge that any exists.

This is the tightest denial of the claim the demonstration is delivered to make, and without it every positive act is shown only in its allowed direction ([access-control-tests](../../../code-practices/access-control-tests.md)). The remaining acts pair a connected party against claims outside its own grant, which is a narrower statement: it shows that a grant bounds a peer, not that the platform bounds a stranger.

The second read negative that rule names — a party holding the replica's ticket but no capability — cannot be staged here at all, because no ticket crosses the host surface and the application offers no way to hold one. It stays with the runtime's own scenarios, which hold it against a hand-made ticket, and it is named here as deliberately out of scope rather than left unmentioned.

The refusal SHALL be shown on the browser screen driving the outsider's node, not narrated from a terminal, so the audience sees the denial on a screen rather than reads it off text.

#### Scenario: An unconnected node obtains nothing
- **WHEN** a node with no connection to Alice attempts to read or list her data, while Bob demonstrably reads the granted claim
- **THEN** it obtains nothing and is refused as addressing an issuer it holds nothing of, shown on the browser screen driving that node, and Bob's reading is shown the same way on his own screen so the contrast is visible
