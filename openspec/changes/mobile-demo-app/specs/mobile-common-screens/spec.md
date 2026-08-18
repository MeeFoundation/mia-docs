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
While a code is displayed, the screen SHALL state that whoever photographs it can use it until it is used or expires, and SHALL show that the code stops working after either. A displayed code SHALL be dismissable by the person at once.

The payload carries a live one-time secret. Nothing in it grants durable access, which is exactly why it is safe to show to a camera and unsafe to leave on a table.

#### Scenario: The code stops working once consumed
- **WHEN** the code has been consumed by the intended device
- **THEN** the displaying screen shows it as spent, and presenting it again is refused

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

### Requirement: The interface states that state does not survive the process
Where a person would otherwise assume their data is kept, the interface SHALL state that identities, connections and entries live only while the application runs.

The identities screen is where the assumption forms, since it is the screen that looks like an account list. Leaving the assumption to form and then be broken is worse than the sentence that prevents it.

#### Scenario: The identities screen says what it is
- **WHEN** the identities screen is shown
- **THEN** it states that what it lists is lost when the application stops
