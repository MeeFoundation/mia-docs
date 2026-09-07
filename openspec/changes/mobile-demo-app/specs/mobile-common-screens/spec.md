# mobile-common: screens

The screens are shared by both platforms and hold no logic of the protocol. They show what the node holds, they perform acts by calling the host surface, and they report what came back. Everything the surface itself exposes and withholds belongs to [host-surface](host-surface.md); what the demonstration shows belongs to [demo-scenario](demo-scenario.md).

The screens carry the weight of one property the runtime cannot enforce from below: an application can be honest or dishonest about the same node. A grant cached locally, a refusal swallowed into a spinner, or an absent value drawn as a fact would each turn a truthful surface into a misleading screen.

## ADDED Requirements

### Requirement: 5 screens cover the demonstration and nothing else
The application SHALL provide: a screen of the identities this node hosts, with the act of creating one and the choice of which identity the other screens act under; a screen of the acting identity's own entries, with reading and writing them; a screen of that identity's connections; a screen of one connection, showing what this peer granted and what was granted to it, with publishing and withdrawing a grant; and a code reader.

No further screen SHALL be added for the demonstration's sake. A screen with no act behind it on the host surface has nothing to show.

#### Scenario: Every act of the demonstration has a screen
- **WHEN** the demonstration's acts are walked in order
- **THEN** each is performed on one of these screens, and none requires a step outside the application

### Requirement: A granted claim is named on screen by joining, never by guessing
A grant names claim identities derived one-way from the issuer and an entry path, so nothing recovers a path from a grant read. A screen that shows which fields are shared SHALL derive the identities of paths it knows or has listed and join them against what the read reports, and SHALL NOT invent a name for a claim identity it cannot account for.

The two sides do this from different material. The issuer knows its own paths, so its join is exact. The grantee lists the namespace it received, which under a scoped grant contains exactly the claims it was granted, and joins that.

A claim identity the screen cannot account for SHALL be shown as a claim it cannot name rather than omitted, because omitting it would under-report what is shared.

#### Scenario: The issuer's screen names what it shares
- **WHEN** the identity has published a grant over 2 of its paths and opens the connection screen
- **THEN** both paths are shown as shared, each with its write right, joined from the identity's own paths rather than read out of the grant

#### Scenario: The grantee's screen names what it received
- **WHEN** the grantee has been granted one claim and opens the connection screen
- **THEN** that claim is shown by the path the granted namespace lists, and no other path appears

### Requirement: What I share is read from the node, on every device
The connection screen SHALL obtain both halves — what this peer granted, and what this identity granted this peer — by reading the node, and SHALL NOT assemble the second half from what the application remembers publishing.

The peer's half is a list, one capability per issuer the peer grants on behalf of, and the screen SHALL show every one of them. A screen drawing only the first would under-report what is shared with the person, which is the same failure as omitting a claim it cannot name.

A grant published on one device reaches the identity's other devices by replication, so the screen on a device that did not publish it reads nothing until the record and its payload arrive. It SHALL show that as waiting, in the same way it does for a claim, rather than as sharing nothing. An application answering from memory would contradict a sibling device that had already withdrawn the grant, and would show nothing at all on a device that had joined afterwards.

#### Scenario: A device that did not publish the grant still shows it
- **WHEN** a grant is published on one device of an identity and the connection screen is opened on another device of the same identity
- **THEN** the screen shows that it is waiting until the record arrives, and shows the same capability afterwards

#### Scenario: A withdrawal on one device empties the screen on the other
- **WHEN** the grant is withdrawn on one device of the identity
- **THEN** the other device's connection screen stops showing it once the withdrawal has replicated, with nothing left from what it displayed before

### Requirement: The person chooses the act before reading a code, and no payload is inspected
The application SHALL ask the person which act a code is being read for — accepting an invitation to connect, or joining a device to an identity — before the code is read, and SHALL pass the value straight to the corresponding call.

The application SHALL NOT inspect a payload, parse it, or wrap it in a format of its own to decide what it is. A payload is opaque above the host surface, and an application that learned to read one would have to be changed whenever the runtime's payload changed, for no gain: the person knows which act they are performing, and asking is one tap.

#### Scenario: A code read for the wrong act is refused by the runtime
- **WHEN** a linking payload is read while the act chosen is accepting an invitation
- **THEN** the call is refused and the refusal is shown, with the application having made no attempt to recognize the payload itself

### Requirement: A code on screen is an exposure with a lifetime, and the screen says so
While a code is displayed, the screen SHALL state that whoever photographs it can use it until it is used or until the lifetime the screen asked for at the mint runs out. It SHALL show that lifetime running down, SHALL stop displaying the code when it reaches its end, and SHALL be dismissable by the person at once.

The payload carries a live one-time secret. Nothing in it grants durable access, which is exactly why it is safe to show to a camera and unsafe to leave on a table.

The screen SHALL NOT claim the code has been used. The facade exports no way to ask whether a minted payload has been consumed, so from the displaying side a code taken by the other device is indistinguishable from one still waiting, and a screen saying otherwise would be inventing knowledge it does not have. What it says instead is what it knows: the lifetime it chose has run out.

#### Scenario: The screen shows the lifetime it asked for, and stops at its end
- **WHEN** a code is displayed and its lifetime runs out
- **THEN** the code is no longer drawn, the screen says the lifetime has run out, and it does not say whether the other device used it in time

### Requirement: The screen stays awake while a code is shown or a value awaited
The application SHALL prevent the display from sleeping while a code is on screen and while a read is being repeated for a value that has not arrived.

A screen that dims mid-ceremony ends the ceremony from the person's side, and a demonstration interrupted by a lock screen is an interruption the audience attributes to the product.

#### Scenario: A ceremony is not interrupted by the display
- **WHEN** a code is displayed for longer than the platform's idle interval
- **THEN** the display stays on until the code is dismissed or consumed

### Requirement: Waiting is a state with a cause
A screen reading a value that has not arrived SHALL show that it is waiting and SHALL keep reading, and SHALL say what it is waiting for. It SHALL NOT present an absent value as an established fact, and SHALL NOT stop at the first empty read.

A read reports no value both when nothing was ever written and when a record has arrived while its payload has not. The two are indistinguishable on the surface, so a screen that concluded from one empty read would announce that a peer shared nothing at the moment the peer's value was on its way.

#### Scenario: An empty read continues into waiting
- **WHEN** a granted claim reads empty on the first attempt
- **THEN** the screen shows that it is waiting for the value and reads again, rather than showing the claim as having none

#### Scenario: Waiting has an end the person can see
- **WHEN** waiting continues beyond what the configured cadence explains
- **THEN** the screen says so, so an unreachable peer is distinguishable from a slow one

### Requirement: A namespace that stopped being shared is shown as that, not as a fault
When a grant is withdrawn, the grantee's node unbinds the namespace and stops knowing that issuer, so every later read or listing of it is refused rather than answered empty. A screen that previously showed those claims SHALL render that refusal as the peer no longer sharing them, and SHALL NOT render it as an error, a defect, or a network problem.

This is the one place where an honest refusal and an honest screen pull in opposite directions. The rule that a refusal is shown as what was refused is what keeps the rest of the application truthful; here the thing refused *is* the access ending, and showing a fault banner at the moment a person exercised their own control would misdescribe the product exactly where it works best.

#### Scenario: A withdrawn grant reads as no longer shared
- **WHEN** the issuer withdraws the grant and the grantee's screen for that connection is redrawn
- **THEN** the screen says the peer no longer shares those claims, and shows no error

#### Scenario: An issuer this node never held is still a refusal
- **WHEN** a screen addresses an issuer the node has never held anything of
- **THEN** the refusal is shown as a refusal, because nothing was ever shared for it to have stopped

### Requirement: A refusal is shown as what was refused
A refused act SHALL be reported on the screen naming what was refused, and SHALL NOT be presented as done, as pending, or as an unspecified error. A refusal of an unpermitted write SHALL leave the previous value on screen.

An unrecognized failure SHALL be shown with a stable message and SHALL NOT display an internal cause chain, which goes to the platform log instead.

#### Scenario: The refused edit shows the boundary
- **WHEN** the person edits a claim granted read-only
- **THEN** the screen says the write was not granted and shows the value unchanged

#### Scenario: A defect is not dressed as a refusal
- **WHEN** an unrecognized failure occurs
- **THEN** the screen shows the stable message for it, distinct from anything the runtime refused

### Requirement: The interface offers no ticket, no import and no reset
No screen SHALL offer to hand over or accept a namespace ticket, to import or share a namespace outside a grant, to force a synchronization, or to clear the node's state. None of these exists on the host surface, and a screen that offered one would be describing a product that does not exist.

#### Scenario: The interface has no such control
- **WHEN** every screen is walked
- **THEN** no control offers a ticket, an import, a share, a forced synchronization, or a reset

### Requirement: The interface answers while a call is outstanding
No screen SHALL block on a call to the host surface. A ceremony, a read waiting on a payload, and a listing of a replicated namespace all take time no interface can be held for, and a screen frozen on a ceremony is indistinguishable from a node that died.

The surface owes asynchronous calls; keeping the interface responsive with them is the application's, which is why the requirement lives here.

#### Scenario: A ceremony runs while the interface answers
- **WHEN** a ceremony call is outstanding
- **THEN** the interface continues to draw and accept input, and the result arrives without the application having blocked for it

### Requirement: The screens hold no protocol logic
The screens SHALL call the host surface and render what it returns. They SHALL NOT cache a grant, a connection list or an entry beyond what a redraw needs, SHALL NOT retry a ceremony on their own, and SHALL NOT hold any rule about what a peer may read or write.

The node is the single answer to every one of those questions. A screen holding a second answer would be right until the node changed, and the disagreement would surface as an interface contradicting itself.

#### Scenario: A withdrawn grant disappears without the application being told twice
- **WHEN** a grant is withdrawn by the issuer and the grantee's connection screen is redrawn
- **THEN** the screen reflects what the node now reads, with nothing left from what it displayed before

### Requirement: An identifier is shown for comparing, never as a name or a proof
Where an identity or a node is shown, it SHALL be rendered so two people can compare it by eye, and SHALL NOT be labelled as a verified name, an account, or a proof of who anyone is. A name the person types for a peer SHALL be presented as their own note, held on their own device.

An identity is an opaque value the runtime mints, with no key material behind it. A screen calling it verified would be the one place in the product claiming something the platform does not do.

#### Scenario: A peer is labelled by a note, not by a claim about them
- **WHEN** the person names a connection and looks at it later
- **THEN** the name is shown as their own note beside the peer's identifier, and nothing presents it as the peer's verified name

### Requirement: The interface states that this device holds the only copy
Where a person would otherwise assume a copy is kept somewhere else, the interface SHALL state that identities, connections and entries live in this device's storage and that nothing behind the screens keeps another copy.

The identities screen is where the assumption forms, since it is the screen that looks like an account list, and an account list implies a service holding the account. Leaving the assumption to form and then be broken by a lost phone is worse than the sentence that prevents it.

#### Scenario: The identities screen says where what it lists lives
- **WHEN** the identities screen is shown
- **THEN** it states that what it lists lives on this device and that no copy of it is kept elsewhere

### Requirement: The screens are composed from one vocabulary of elements
The screens SHALL be composed from a single set of elements — a scrolling screen, a card, a title, a note, a typography element every string passes through, a button carrying the variants primary, secondary, danger and link, an identifier, a refusal banner and a waiting banner — and SHALL NOT introduce a second way of saying what one of them already says.

Every honesty property this capability requires is carried by one element, so it is met once rather than on each screen: a refusal is the refusal banner wherever it appears, a wait is the waiting banner that names its cause, and an identifier is grouped for comparing by eye. A screen drawing its own refusal text would be the place the closed table stopped being closed.

A note SHALL carry the sentences the person needs in the interface's own voice. A value the node reported SHALL NOT be drawn as a note, because the two would then be indistinguishable.

A button whose act cannot be undone SHALL be marked apart from the others.

#### Scenario: A refusal looks the same on every screen
- **WHEN** a refusal is shown on any screen
- **THEN** it is the refusal banner, naming the kind, the sentence of the closed table, and whether the refusal came from this application or from the node

#### Scenario: No screen invents an element
- **WHEN** the screens are read
- **THEN** every element on them belongs to this vocabulary, and nothing the node did not report is drawn as though it had

### Requirement: The look and the libraries are the organization's, not this application's
The palette, the typography and the component vocabulary SHALL be those of the organization's other mobile products, so that a person meeting 2 of them meets one organization. The application SHALL NOT invent a palette of its own, and no screen SHALL carry a color literal.

What is taken is the look and the public libraries, not another product's architecture. A layered source arrangement and a shared translation catalogue answer problems this application does not have: it is bounded at 5 screens by the requirement above, and its copy is largely platform terms and sentences these requirements fix word for word, which a translation would split and collapse.

#### Scenario: A color reaches a screen from the shared palette
- **WHEN** any screen or element is read
- **THEN** every color it draws comes from the shared palette by name, and none is written as a literal in a screen

#### Scenario: The interface does not suspend while a call is outstanding
- **WHEN** a value the screen shows is still being read
- **THEN** the screen keeps drawing and accepting input and shows the waiting banner that names what it waits for, rather than replacing the subtree with a fallback that names nothing

### Requirement: The identities screen opens on the node's own state
The identities screen SHALL show, before anything else, whether a node is up, with the act of bringing it up and the act of stopping it, and the node id while it is up.

It SHALL then list the identities this node hosts, with the act of creating one and the choice of which identity the other screens act under, and SHALL show which identity is chosen on the row itself rather than elsewhere.

It SHALL carry the act of minting a code that joins another device to the chosen identity. This is the screen the act belongs to because an identity is what the code names, and the reader consumes such a code without any screen offering to mint one.

No other screen SHALL offer bringing the node up. A screen acting under an identity has nowhere to act until a node is up, and it says so rather than offering the act again.

#### Scenario: Nothing acts before a node is up
- **WHEN** no node is up and any screen other than this one is opened
- **THEN** it states that the node is down, offers no act of its own, and does not offer bringing the node up

#### Scenario: A device is joined to the identity from the screen that names it
- **WHEN** an identity is chosen and a second device is to join it
- **THEN** the code that joins it is minted on this screen, shown as a displayed code, and consumed by the other device through the reader

#### Scenario: The chosen identity is visible where it is chosen
- **WHEN** an identity is chosen
- **THEN** its row says that the other screens act as it, and the rows of the others say they can be chosen

### Requirement: The entries screen writes a path and a value, and lists without fetching
The entries screen SHALL show the identity it acts as, an act of writing that takes an entry path and a value, and the listing of that identity's own entries.

Each row of the listing SHALL be the entry path and the length of its payload, with the act of reading that one entry. The listing reports what the node holds now without fetching payloads, so a length is what it can show and a value costs an act of its own — which the screen SHALL state where the listing is empty, rather than leaving an empty listing to be read as an identity with no data.

A value read SHALL be shown beside the path it was read from, and SHALL NOT replace the listing.

#### Scenario: A listing costs no payloads
- **WHEN** the entries screen is opened
- **THEN** it shows each entry path with the length of its payload, and no payload has been fetched

#### Scenario: A written entry appears in the listing
- **WHEN** an entry is written
- **THEN** the listing is read again and the entry appears in it, at the path that was written

### Requirement: The connections screen offers 2 ways into a connection and no third
The connections screen SHALL offer showing an invite code and reading a code, and SHALL state that both devices have to be on one local network because a peer is reached at an address it publishes about itself with no relay behind it.

It SHALL list this identity's connections, each row carrying the peer's identifier and the sentence that running the ceremony proves both devices held the same one-time secret and nothing about who the person is. A row SHALL open the connection screen for that peer.

#### Scenario: A connection is reached only through its row
- **WHEN** the connections screen is read
- **THEN** the only way to a peer's connection screen is that peer's row, and no control offers a peer the node does not hold a connection to

### Requirement: The connection screen is 4 cards in one order
The connection screen SHALL be, in this order: the peer, what this peer shares with me, what I share with this peer, and the act of sharing claims with this peer.

The order is what the person came for. They arrive to read what is shared before they change it, so the act that changes it sits below both halves and is reached after both have been read.

**The peer** SHALL be the peer's identifier shown for comparing by eye against what the other person sees on their own screen, with the sentence that it is an opaque value with no key behind it and that any name given to it is the person's own note held on this device.

**What this peer shares with me** SHALL carry one row per claim of the capability the peer granted: the entry path joined against the listing of the namespace received, whether the claim is writable, and either the value or a waiting banner naming the value it waits for. A claim the screen cannot name SHALL be shown as a claim it cannot name rather than omitted. A writable claim SHALL carry the act of writing a new value, with the sentence that the write is admitted against the grant record this node has read and that the issuer's own gate decides afterwards without its verdict reaching this screen. A peer that has withdrawn SHALL render as that peer no longer sharing, per the requirement on a namespace that stopped being shared.

**What I share with this peer** SHALL carry one row per claim of the capability read from the node, each with its write right, and one act withdrawing the whole grant, marked as an act that cannot be undone. Below it SHALL stand the sentence that withdrawing closes further delivery and does not recall what this peer already received.

**Sharing claims with this peer** SHALL offer this identity's own entry paths as a choice of several, a field for a path the listing does not carry, and 2 acts — granting read-only and granting with the right to write — with the sentence that publishing again replaces the whole grant toward this peer rather than adding to it.

Neither half SHALL be drawn from what this device remembers doing, per the requirement that what I share is read from the node.

#### Scenario: The halves are read before the act that changes them
- **WHEN** the connection screen is opened
- **THEN** what the peer shares and what is shared with the peer are both above the act of sharing, and neither is below it

#### Scenario: A read-only claim offers no write
- **WHEN** a claim the peer granted is not writable
- **THEN** the row shows it as read-only and carries no field for writing a value

#### Scenario: Publishing again replaces rather than adds
- **WHEN** a grant is published over one path and then published over another
- **THEN** the screen says beforehand that the whole grant toward this peer is replaced, and afterwards shows only the second path as shared

### Requirement: The reader asks for the act before the camera opens
The code reader SHALL ask which act the code is being read for — accepting an invitation to connect, or joining this device to an identity — and SHALL open the camera only after the act is chosen.

A refused camera consent SHALL be reported on this screen, with the way to grant it, rather than as an empty view.

#### Scenario: The camera does not open before the act is known
- **WHEN** the reader is opened
- **THEN** the choice of act is shown first, and no camera is running until one is chosen

### Requirement: A displayed code is a modal that dismisses at once
A code SHALL be shown as a modal carrying: the code itself, the sentence that whoever photographs it can use it in place of the device it was meant for until it is used or until its lifetime runs out, the first characters of the payload as an identifier for comparing by eye, and the act of dismissing it.

The modal SHALL keep the display awake while it stands, SHALL report the code as spent once it has been used or has expired, and SHALL offer nothing but dismissal in that state.

#### Scenario: A spent code says so rather than staying drawable
- **WHEN** a displayed code is consumed by the other device
- **THEN** the modal replaces it with the statement that it is spent and no longer works, and the code itself is gone from the screen
