# Threat model

What the platform defends against and what it leaves undefended: each section names who learns or does what, and where the decision behind it is recorded. A threat missing from this document is not defended against by its absence.

## Network addresses and linkability

The platform provides neither network anonymity nor unlinkability. Every connection runs between two iroh endpoints, and iroh takes a direct path whenever one exists, so a device learns the IP address of every device it connects to: its own identity's siblings, the devices of every member of every [pod](../../architecture/language/pod.md) its identities hold, and whoever presents an invite it minted.

**Example:** what each party learns about Alice's phone a1, where the runtime runs as `SpawnOptions::for_product` spawns it, with relays and address lookup bound.

| party | what it learns |
|---|---|
| a device a1 connects to, or that connects to a1 | a1's IP address and port, and with it roughly where Alice is |
| whoever holds an invite a1 minted or a ticket that names a1 | the addresses a1 published when it was minted, a relay URL among them (ADR-0012, ADR-0015) |
| whoever runs the relay a1 is homed on | the node ids of a1 and of every device it reaches through that relay, and the IP address a1 connects from |
| anyone who holds a1's node id | whether a1 is up and which relay it is homed on, through address lookup; no withdrawal takes that back |
| Dave, in a pod with each of two identities of Alice's that a1 hosts | that the two share a node: both device sets list a1's node id (ADR-0013) |
| Dave, holding the tickets to "Family"'s stores and no membership | that a1 writes or pulls in Family, and as which member: each announcement in the stores' swarms names the identity whose replica sends it |

Two identities hosted on one node share its node id, which the device set of each lists, so a party sharing a pod with both sees that they share a device; each identity writes under its own author, so the entries themselves do not link them (ADR-0013). An endpoint per identity, or a device per identity, separates the node ids and leaves the link the network makes: two devices on one home network reach their peers from one public IP address and go online together.

A replica's announcements in its swarm carry the `PdnId` of the identity whose replica sends them, so a pull it triggers addresses that identity. Whoever sits in a swarm learns which identities' replicas write there and when: for a PMS that identity is its own, whom the holder of the namespace id knows already, while in a pod's swarm a holder of its tickets that is no member — a removed member above all — learns which members write, though every session refuses it.

The platform hides no device's address from the parties it syncs with, and it keeps two identities of one person apart by their authors alone; any further separation comes from which devices and networks the person uses, outside the platform. A person whose safety depends on hiding where they are, or on two of their identities staying unlinked, cannot rely on the platform for either.

## Identities hosted on one node

A node acts as every identity it hosts, and nothing in the platform defends one of those identities against the node. Its process holds the material of each — the identity's private metadata store (PMS), with every ticket and key it keeps, and the author the identity writes with — so it can write an entry under any hosted identity's author and open a session naming any of them. Every other device takes the result as that identity's act: a node's claim to act as an identity is checked against the device set the identity publishes, never proven, and every node the identity is linked into is in that set (ADR-0013).

What the platform separates is how an honest node keeps its identities: each holds replicas of its own, writes with an author of its own and takes part in sessions of its own, so an honest node never answers one identity's caller from another identity's stores, and honest devices attribute each entry to the identity that wrote it. That is attribution among honest devices, never a defence against the node that hosts both.

**Example:** what Alice's tablet a3, which hosts Alice-work and Alice-leisure, does with them.

| a3 runs | what it does | what every other device concludes |
|---|---|---|
| an honest runtime | writes Alice-work's entries under a3's author for Alice-work, and serves Alice-leisure's replicas only to the callers Alice-leisure's own records place | each entry is the act of the identity that wrote it |
| a modified runtime, or one whose process is taken over | writes an entry under a3's author for Alice-leisure while Alice acts as Alice-work, and opens a session naming Alice-leisure to read the pods she is a member of | the entry is Alice-leisure's act, and the session is served as hers |

The arrangement is sized for the identities of one person on that person's own devices. On a node shared by different people, whoever controls the node controls every identity on it; ADR-0013 does not answer that arrangement, and the platform gives the people behind those identities no protection from one another.

## Payload bytes by hash

A node serves a payload to any caller that asks for its hash, whatever pods that caller belongs to. Blob transfer is mounted with no gate, and the blob store is one per node, under the replicas of every identity the node hosts, so the isolation between identities on one node and the membership a [pod](../../architecture/language/pod.md)'s stores are served by cover entries and not payload bytes (ADR-0013). A payload is withheld only as far as its hash is: a party that learns a hash outside the platform fetches the bytes, and a party that holds the hash of a known file learns whether the node keeps it. A pod's member device announces the hash of each payload it finishes downloading to the record store's swarm, so a removed member's device that does not leave that swarm learns every new hash and fetches what is placed after the removal.

**Example:** requests to Bob's phone b1, where Bob shares "Family" with Alice-leisure, keeps a pod of one for himself, and Dave's phone d1 shares no pod with anybody.

| caller | asks b1 for | gets |
|---|---|---|
| Alice's tablet a3 | the payload of a diary record in Bob's pod of one, whose hash it learned outside the platform | the diary, a record of a pod neither identity on a3 is a member of |
| d1 | the hash of a public tax form Bob keeps in his pod of one | the form, and with it the fact that Bob keeps it |
