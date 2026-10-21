## ADDED Requirements

### Requirement: Payload downloads toward one provider are bounded

A payload's provider is a node registered as holding it: the sender of the entry that names it, when the sender holds it, the peer of a session that ends while it is wanted, or a gossip neighbor that announces it. A node's engine for an identity SHALL have at most 100 payload downloads in flight toward one provider, the number of bidirectional streams the node's endpoint grants a connection, and SHALL hold every other payload its replicas want as an entry of a queue rather than as a running download. A payload is wanted while an entry of one of the engine's replicas names it and the blob store does not hold it whole. A waiting payload SHALL be fetched from a provider registered as holding it that has room, and a provider registered while the payload waits, by a session that ends or by an announcement, SHALL be one it can be fetched from. The limit SHALL NOT be a parameter of the node's host and SHALL NOT change while the node runs. A provider grants a connection no more streams than that, so a download beyond the limit would only wait inside the transport, holding the memory of a running download.

**Example:** Alice's tablet a3 joins "Family", a pod of 20,000 records whose payloads Alice's laptop a1 holds; Bob's phone b1, which holds them too, finishes a session with a3 midway.

| moment | downloads toward a1 | downloads toward b1 | payloads waiting on a3 |
|---|---|---|---|
| the session with a1 has brought every entry | 100 | 0 | 19,900 |
| a1 has answered one more request | 100 | 0 | 19,899 |
| b1's session with a3 has ended | 100 | 100 | 19,699 |

#### Scenario: A catch-up keeps the limit toward its provider

- **WHEN** a replica joins a namespace of 20,000 entries whose payloads one provider holds
- **THEN** the provider never has more of the replica's blob requests open at once than the limit, and every payload arrives

#### Scenario: A provider registered during a catch-up takes waiting payloads

- **WHEN** a second provider of the same payloads finishes a session with the replica while payloads wait
- **THEN** waiting payloads are fetched from both providers, at most the limit toward each, and every payload arrives

### Requirement: A download that makes no progress is handed on

A payload download that receives nothing from its provider for 10 seconds SHALL be dropped, its stream with it, and the payload SHALL be fetched from another provider registered as holding it. The provider SHALL then pause: no download SHALL go to it for 1 second, each further pause twice the one before up to 16 seconds, for at most 2 minutes after the first; after each pause one download SHALL probe it, and a download from it that succeeds SHALL end the pauses and give it its limit back. A payload whose only provider stalled SHALL stay queued for that provider and SHALL be fetched from it again after its pause, with no session needed. A provider whose 2 minutes ran out SHALL be asked for nothing until a session with it ends, and a payload no other provider holds SHALL wait for that session. A download that fails on the node's own blob store SHALL pause no provider. Without the bound, a provider that accepts a request and sends nothing holds the download for as long as its connection stays open, and the transport keeps a quiet connection open with a keep-alive every 5 seconds.

**Example:** Bob's phone b1 is the only provider of a payload P that Alice's tablet a3 wants, and b1 answers nothing for its first 25 seconds.

| t | a3 |
|---|---|
| 0 s | asks b1 for P |
| 10 s | drops the request; b1 pauses for 1 s |
| 11 s | probes b1 with P |
| 21 s | drops the probe; b1 pauses for 2 s |
| 23 s | probes b1 with P; b1 starts answering at 25 s |
| 25 s | P arrives; b1 may have 100 downloads in flight again |

#### Scenario: A silent provider's payloads come from another provider

- **WHEN** a provider accepts every blob request of a replica and answers none, while a second provider holds the same payloads
- **THEN** every payload arrives from the second provider, those first asked of the silent one after their requests were dropped

#### Scenario: The only provider, silent for a while, is asked again

- **WHEN** the only provider of a replica's payloads answers nothing for 15 seconds and then serves
- **THEN** every payload arrives once it serves, with no session between

#### Scenario: A provider silent for 2 minutes waits for a session

- **WHEN** a provider answers no request of a replica for 2 minutes
- **THEN** no download goes to it until a session with it ends, and its payloads are asked for again after that session

#### Scenario: A failure on the node's own blob store pauses no provider

- **WHEN** a download fails because the node's blob store cannot write the payload
- **THEN** the payload waits as one still wanted, and its provider keeps its limit
