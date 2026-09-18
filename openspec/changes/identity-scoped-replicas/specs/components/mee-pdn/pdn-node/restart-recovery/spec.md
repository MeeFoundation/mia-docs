# pdn-node: restart recovery — delta for identity-scoped-replicas

## MODIFIED Requirements

### Requirement: A restarted runtime recovers each hosted identity along the product path
At spawn, a runtime SHALL host every identity its record names whose directory replica its store holds, each in its own scope, by opening that identity's private metadata directory from the replica that scope already holds and performing the same registration a newly created identity performs: the directory arms session classification, the identity enters the hosted set, and its connection sweep begins. Everything else SHALL be re-derived from the directory rather than recorded: the identity's data namespace from its published `data` ticket, its connections from its connection records, each connection's metadata pair from that pair's two published tickets, and the granted namespaces from the counterparty's grant records, all imported into that identity's scope. A contact re-derived this way that names this node's own address SHALL be reached inside the process. Recovery SHALL require no peer, no ceremony, and no network.

#### Scenario: An identity comes back hosted
- **WHEN** a runtime restarts on a directory whose record names one identity
- **THEN** that identity is reported as hosted, its own entries are readable, and no ceremony was performed to get there

#### Scenario: A connection and its grant come back
- **WHEN** a runtime that holds an established connection and an imported grant restarts
- **THEN** the connection is listed, the grant is readable from the pair, and the granted namespace's entries are readable again once the pair's first sweep completes

#### Scenario: Several identities on one node each come back
- **WHEN** a runtime hosting two identities, each with a connection of its own, restarts
- **THEN** both are hosted, and each lists its own connections and no other identity's

#### Scenario: Two identities granted by one issuer come back apart
- **WHEN** a runtime hosting two identities granted different claims of one issuer restarts
- **THEN** each identity reads the claim its own grant names and neither reads the other's

#### Scenario: A device that linked before the restart is still a device
- **WHEN** a device that joined an identity before a restart is read out of that identity's device set afterwards
- **THEN** it is present, and it is the same node id it registered under
