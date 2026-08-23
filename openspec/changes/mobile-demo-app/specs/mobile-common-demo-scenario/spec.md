# mobile-common: demonstration scenario

The demonstration is what a person witnesses, so it is specified rather than left to a script written on the day. Each act below is one the runtime's own scenario tests already cover, and each is required to appear beside the refusal that gives it meaning: an act shown only in its allowed direction demonstrates nothing about a product whose whole subject is the boundary.

The audience decides whether this is worth building. That fixes two things about the form. Nothing is shown that a person cannot see happening — no output read aloud from a terminal standing in for a screen. And nothing is claimed that the code does not do, because a demonstration that oversells is discovered later by the same audience.

## ADDED Requirements

### Requirement: The demonstration runs on devices that can reach each other
The demonstration SHALL be staged on physical devices sharing one local network, together with any further node in that same network. It SHALL NOT be staged on 2 Android emulators, and SHALL NOT be staged on iOS simulators.

The 2 exclusions have different reasons and are not one rule. The runtime binds its endpoint with no relay and no discovery configured, so a peer is reached only at an address the endpoint publishes about itself; every Android emulator holds the same address on its own virtual router, so a payload minted in one directs the other at itself, and no setting inside the application changes that. An iOS simulator is not an emulator — it runs as a process on the host machine's own network stack, so 2 of them reach each other and pairing between them works. What rules the simulator out is the demonstration's subject: the claim being made is about a phone in a hand, and a window on a laptop is not one.

Development against a single device or a simulator is unaffected; the ceremonies are what needs 2 devices, and the audience is what needs them physical.

The network is part of the staging, not a detail of the venue. A network that forbids traffic between its clients breaks every act below and reports nothing worth reading, and a device on a mobile connection has no direct path at all.

#### Scenario: 2 Android emulators cannot pair
- **WHEN** an invite payload is minted in one Android emulator and consumed in a second
- **THEN** establishment fails to reach the inviter, and the failure is a property of the environment rather than a defect of the application

#### Scenario: 2 devices in one network pair
- **WHEN** 2 physical devices share a local network that permits traffic between its clients, and one consumes the other's invite payload
- **THEN** the connection is established over the runtime's own protocols, with no relay and no third party involved

### Requirement: The staging names its nodes, and 4 of them are needed
The demonstration SHALL name each node it uses, the person or persona it stands for, its platform, and whether it is a phone. At least 2 nodes SHALL be phones running the application. A node that is not a phone SHALL be identified as such in the narration at the moment it first appears.

4 nodes are needed, and each for a reason. The granting identity's first device and the grantee are 2. A third is required because 2 acts need a node that stays up while another goes away — the granting identity's second device joining, and that device serving the grantee after the first is gone. A fourth is required because the outsider must hold no connection to the granting identity, and the other three all do.

The fourth cannot be saved by hosting a second identity on the grantee's phone. The data service is keyed by the issuer whose namespace is read, not by the identity a screen believes it is acting under, so once that phone has bound the granting identity's replica it answers the read whichever identity is selected. The outsider is a node or it is nothing.

Where a node is a process on the presenter's machine rather than a phone, the narration says so, and says that its payload is carried by hand because a machine does not read a code off a screen.

#### Scenario: The third node is introduced as what it is
- **WHEN** the third node takes part for the first time
- **THEN** the narration says it is not a phone and says how its payload reached it

### Requirement: Every act is the product's own act
Each act SHALL be performed through the host surface as an application performs it. No namespace ticket is handed over, no reconciliation is forced, no state is reset between acts, and waiting for a value is repeating the read.

A demonstration arranged any other way shows the value arriving while the mechanism that should have carried it goes unexercised, and the arrangement is invisible afterwards because the value on the screen is the same value either way ([product-path-arrangement](../../code-practices/product-path-arrangement.md)).

#### Scenario: Nothing in the staging bypasses the product
- **WHEN** the whole demonstration is run end to end
- **THEN** every act corresponds to an exported call of the host surface, and no act reaches a store, a ticket, or a reconciliation directly

#### Scenario: No act is preceded by a reset
- **WHEN** the acts are performed in order
- **THEN** each begins from the state the previous one left, and no node is restarted or cleared between them

### Requirement: Waiting is shown as waiting
Where a value crosses between nodes, the demonstration SHALL show the waiting rather than cut around it: the screen says it is waiting, and it arrives while the audience watches. The configured reconcile interval SHALL be short enough that a first appearance is a pause and not an interruption.

Convergence is the product's honest behaviour and hiding it would misrepresent the thing being sold. Which wait the cadence governs differs by act: a grantee reading a granted claim nudges its own reconciliation, so that read converges largely on its own, while a grant record reaching a peer, a write reaching a sibling device, and a linking catch-up all wait on the periodic pass. The acts of the second kind are the ones a long interval makes unwatchable, which is why the host configures a shorter one and states the number as its own configuration.

#### Scenario: A value arrives while the audience watches
- **WHEN** a value is written on one device and awaited on another
- **THEN** the awaiting screen shows that it is waiting, and the value appears without the narration moving on to something else in the meantime

### Requirement: One application holds several identities, kept apart
The demonstration SHALL show one device hosting more than one identity, each with a data namespace of its own and a connection list of its own. The same entry path under 2 identities SHALL be shown holding different values, and a connection established by one SHALL be shown absent from the other's list.

This is the act the product's privacy claim rests on: 2 lives on one device that are not 2 accounts and share nothing by default.

#### Scenario: 2 identities on one device stay disjoint
- **WHEN** one identity establishes a connection and an entry is written at the same path under both identities
- **THEN** the connection appears under that identity alone, and each identity reads its own value at the shared path

#### Scenario: A peer of one identity learns nothing of the other
- **WHEN** a peer connected to one identity reads what it has been granted
- **THEN** nothing it can read or list names the other identity or anything inside it

### Requirement: A connection is made by 2 people, and the code burns
The demonstration SHALL show an invite payload rendered as a code on one device's screen and read by the other device's camera, ending in a connection that both sides list. No account, no directory, and no third party SHALL take part.

The same code SHALL then be presented a second time and be refused, with no second connection recorded on the inviting side. The refusal SHALL be shown as a refusal on the screen, not as a silent absence of effect.

#### Scenario: A scanned code connects; the same code again is refused
- **WHEN** the second device scans the code and afterwards scans the same code again
- **THEN** the first scan establishes the connection and the second is refused, and the inviting device lists exactly one connection to that peer

#### Scenario: The connection is listed by both sides
- **WHEN** the establishment completes
- **THEN** each device lists the other's identity among the connections of the identity that took part

### Requirement: A grant names claims, and the rest is absent rather than hidden
The demonstration SHALL show a grant naming particular claims of the granting identity's data, after which the grantee reads exactly those claims. The granting identity SHALL hold further claims at the time of the grant, so that what is withheld is real.

Claims the grant does not name SHALL be absent from what the grantee can read and from what it can list — not present and marked withheld, not shown as a count. The narration SHALL make this distinction explicitly, because the difference between hidden and absent is the product.

#### Scenario: Exactly the named claims arrive
- **WHEN** the granting identity holds several claims and grants one of them
- **THEN** the grantee reads that claim and its later updates, and listing yields nothing about the others — neither their content, nor their paths, nor their number

#### Scenario: The grantee's screen shows a shared field, not a redacted record
- **WHEN** the grantee opens what this peer granted it
- **THEN** the screen shows the granted claims and no placeholder standing for anything else

### Requirement: A granted claim may be writable, and read-only refuses at the screen
The demonstration SHALL show 2 claims granted over one connection, one read-only and one writable. The grantee's edit of the writable claim SHALL be shown reaching the granting identity's own device. The grantee's edit of the read-only claim SHALL be refused, with the refusal shown as what was refused and the previous value still in place.

The refused edit is the moment the boundary becomes visible on a device rather than in an argument: the phone in the grantee's hand declines.

#### Scenario: Read-only refuses the write beside read-write accepting it
- **WHEN** the grantee edits both claims
- **THEN** the edit of the writable claim reaches the granting identity, and the edit of the read-only claim is refused with the previous value unchanged

### Requirement: A second device joins an identity and can stand in for the first
The demonstration SHALL show a second device joining an existing identity through the linking ceremony, coming up already carrying that identity's connections and the entries written before it joined, with no further act required of the person.

It SHALL show that the joining device hosts the identity it joined and no other identity of the same person, so that a device is seen belonging to an identity rather than to a person.

With the first device gone, the second SHALL be shown carrying a fresh value to a granted peer, so that availability is seen not to depend on the device that issued the grant.

#### Scenario: A joining device comes up caught up
- **WHEN** a device consumes a linking payload for an identity that already holds a connection and an entry
- **THEN** it lists that identity as hosted, lists the connection, and reads the entry written before it joined

#### Scenario: A device that joined one identity hosts that one only
- **WHEN** the inviting device hosts 2 identities and mints a linking payload for one of them
- **THEN** the joining device hosts that identity alone, and nothing on it names the other

#### Scenario: The remaining device serves the granted peer
- **WHEN** the device that published the grant is taken off the network and the joined device writes a new value for a granted claim
- **THEN** the granted peer reads the new value, obtained from the remaining device of the issuer

### Requirement: A withdrawal closes what the grant opened
The demonstration SHALL show the granting identity withdrawing the grant, after which the grantee no longer reads the claim, while the granting identity still reads its own entry. The withdrawal SHALL be performed as one act naming the peer and the issuer.

What the grantee's node does is stronger than emptying the claim: withdrawal unbinds the namespace, so the node stops knowing that issuer and every later read of it is refused rather than answered empty. The demonstration SHALL show that as the access closing and not as a fault, which is a requirement on the screen as much as on the narration.

The demonstration SHALL also show the grant given again, over the same claim, and the access reopening. That is the path worth showing rather than the first grant: nothing that remembers a withdrawal may block what follows it ([operating-conditions](../../code-practices/operating-conditions.md)), and a demonstration that ends on a closed door leaves the audience unable to tell a boundary from a dead end.

#### Scenario: Access ends with the grant
- **WHEN** the grant is withdrawn
- **THEN** the grantee's node stops answering for that issuer altogether, and the issuer's own read of the same entry is unaffected

#### Scenario: The grantee's screen says no longer shared, not broken
- **WHEN** the withdrawal has taken effect and the grantee opens the screen that showed the claim
- **THEN** the screen says the peer no longer shares it, rather than showing it greyed, or showing the refusal the node now answers with as a fault

#### Scenario: The same claim is granted again and the access reopens
- **WHEN** the granting identity publishes a grant over the same claim after the withdrawal
- **THEN** the grantee reads that claim again, with nothing left from the withdrawal blocking it

### Requirement: The operating conditions the demonstration covers are named, and so are the rest
The demonstration SHALL state which of the platform's operating conditions it exercises and which it does not ([operating-conditions](../../code-practices/operating-conditions.md)).

Exercised: several identities on one node; one identity across several devices; a device joining after connections and entries already exist; a device leaving while a peer still needs its data; a capability granted, withdrawn, and granted again over the same claim.

Not exercised, and named as such: a device that restarts and returns with its state, since state does not survive a process at all; a disk that fills, since nothing is written to one; a connection that degrades rather than ends; a capability narrowed and widened rather than closed and reopened; and a process killed for memory, which a phone does and a container never did.

#### Scenario: The uncovered conditions are named rather than implied
- **WHEN** the demonstration is delivered
- **THEN** the conditions it does not cover are stated, and no act implies coverage of one of them

### Requirement: The narration states what is not shown
The demonstration SHALL state, rather than leave to inference: that state is held in memory and does not survive the process; that an identity carries no key material, so nothing here proves who a peer is; that the reconcile cadence is a configured number rather than a property of the network; which nodes in the staging are not phones; and that withdrawing a grant closes further delivery without recalling what was already delivered.

A demonstration silent on these invites the opposite assumption on each, and the assumption is what the audience carries away. The last is the one the demonstration would otherwise oversell hardest: a field vanishing from a phone looks like deletion, and the platform promises that access is gated before delivery rather than that delivered data can be retracted ([invariants](../pdn-node/invariants.md), Invariant 2).

#### Scenario: The absences are named
- **WHEN** the demonstration is delivered
- **THEN** each of the 5 absences is stated, and no act of the demonstration implies its opposite

#### Scenario: The withdrawal is not narrated as deletion
- **WHEN** the withdrawal act is shown and the claim disappears from the grantee's screen
- **THEN** the narration says that further delivery is closed and that what the grantee already received is not recalled

### Requirement: A party holding nothing is shown obtaining nothing
The demonstration SHALL include a node — not a second identity co-hosted with a party that already has access — holding no connection to the granting identity and no grant from it, shown obtaining nothing of that identity's data: neither the granted claim nor any other, neither content nor the knowledge that any exists.

This is the tightest denial of the claim the demonstration is delivered to make, and without it every positive act is shown only in its allowed direction ([access-control-tests](../../code-practices/access-control-tests.md)). The remaining acts pair a connected party against claims outside its own grant, which is a narrower statement: it shows that a grant bounds a peer, not that the platform bounds a stranger.

The second read negative that rule names — a party holding the replica's ticket but no capability — cannot be staged here at all, because no ticket crosses the host surface and the application offers no way to hold one. It stays with the runtime's own scenarios, which hold it against a hand-made ticket, and it is named here as deliberately out of scope rather than left unmentioned.

#### Scenario: An unconnected node obtains nothing
- **WHEN** a node with no connection to the granting identity attempts to read or list that identity's data, while a granted peer demonstrably reads the granted claim
- **THEN** it obtains nothing and is refused as addressing an issuer it holds nothing of, and the granted peer's reading is shown in the same place so the contrast is visible
