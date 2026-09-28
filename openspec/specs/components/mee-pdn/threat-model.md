# Threat model

What the platform defends against and what it leaves undefended: each section names who learns or does what, and where the decision behind it is recorded. A threat missing from this document is not defended against by its absence.

## Network addresses and linkability

The platform provides neither network anonymity nor unlinkability. Every connection runs between two iroh endpoints, and iroh takes a direct path whenever one exists, so a device learns the IP address of every device it connects to: its own identity's siblings, the devices of every identity it holds a [connection](../../architecture/language/connection.md) with, and whoever presents an invite it minted.

**Example:** what each party learns about Alice's phone a1, where the runtime runs as `SpawnOptions::for_product` spawns it, with relays and address lookup bound.

| party | what it learns |
|---|---|
| a device a1 connects to, or that connects to a1 | a1's IP address and port, and with it roughly where Alice is |
| whoever holds an invite a1 minted or a ticket that names a1 | the addresses a1 published when it was minted, a relay URL among them (ADR-0011) |
| whoever runs the relay a1 is homed on | the node ids of a1 and of every device it reaches through that relay, and the IP address a1 connects from |
| anyone who holds a1's node id | whether a1 is up and which relay it is homed on, through address lookup; no withdrawal takes that back |
| Dave, connected to two identities of Alice's that a1 hosts | that the two share a node: both device sets list a1's node id (ADR-0013) |

Two identities hosted on one node share its node id, which the device set of each lists, so a party connected to both sees that they share a device; each identity writes under its own author, so the entries themselves do not link them (ADR-0013). An endpoint per identity, or a device per identity, separates the node ids and leaves the link the network makes: two devices on one home network reach their peers from one public IP address and go online together.

The platform hides no device's address from the parties it syncs with, and it keeps two identities of one person apart by their authors alone; any further separation comes from which devices and networks the person uses, outside the platform. A person whose safety depends on hiding where they are, or on two of their identities staying unlinked, cannot rely on the platform for either.
