## MODIFIED Requirements

### Requirement: A granted namespace binds and unbinds for the identity its grant addresses

The runtime SHALL keep the data namespaces behind a connection's live grants imported, without an explicit import act: for every open metadata pair of a hosted identity it SHALL watch the counterparty's replica and, as a grant record becomes readable there, import the namespace the record's ticket names for that identity. A grant whose ticket comes to name a different replica SHALL be re-imported onto it, and the replica it bound before SHALL be forgotten in that import, so a counterparty that keeps moving its grant leaves no replica behind. A grant that disappears from the counterparty's replica SHALL take its binding back out, and the replica it bound SHALL be forgotten with it, so the issuer resolves to nothing for that identity again.

The replica belongs to the identity the grant addresses, and one pair binds one issuer there: a grant names its own identity as the data issuer, and an identity holds one connection per counterparty. A withdrawal therefore decides from the pair it swept alone, and a co-located identity granted by the same issuer holds a replica of its own that the withdrawal leaves untouched.

The import bookkeeping SHALL be an optimization, not the arbiter. An issuer already resolving in that identity to the very namespace a grant names SHALL be adopted into the bookkeeping rather than re-imported: each import holds one more open handle on the replica, and the drop at the end of its life must find exactly one. An issuer resolving to nothing SHALL be re-imported even when the bookkeeping names exactly the namespace the grant carries, so a replica forgotten while the bookkeeping survived comes back on the pair's next sweep instead of being skipped forever.

The runtime SHALL bound this to what it imported itself. A namespace imported by any other route SHALL never be forgotten by this mechanism, and the explicit import operation SHALL remain available for a ticket obtained out of band. Nor SHALL such a namespace be displaced: while an issuer resolves in that identity to a replica an import of another route bound, a grant whose ticket names a different replica waits, and the binding follows the grant only once that import is forgotten or the grant comes to name the replica the issuer already resolves to — re-importing over it would have two owners displace each other on every sweep.

Watching SHALL include the counterparty replica's payload arrivals, not only its entry arrivals: a grant's ticket travels as a payload blob, so a record whose entry has replicated is not yet a ticket that can be acted on.

#### Scenario: A grant binds its namespace with no import act

- **WHEN** a connected peer publishes a grant of its data store toward a hosted identity, and the grant record and its ticket payload replicate to the identity's runtime
- **THEN** the runtime imports the granted namespace for that identity by itself and the granted entries become readable there, with no import operation invoked by the caller

#### Scenario: A linked device binds a grant established elsewhere

- **WHEN** a device is linked into an identity whose connection and grant were established on another of its devices, and the pair and grant records replicate to it
- **THEN** the newly linked device imports the granted namespace by itself, reaching it through the pair its directory carries

#### Scenario: A withdrawn grant unbinds its namespace

- **WHEN** the granting peer withdraws the grant and the tombstone replicates to the grantee's copy of the pair
- **THEN** the grantee forgets the namespace it imported under that grant, and operations addressing that issuer as that identity fail with an unknown-issuer error

#### Scenario: A withdrawal toward one audience spares the co-hosted other

- **WHEN** one node hosts two identities granted by the same issuer, and the issuer withdraws the grant toward one of them
- **THEN** the withdrawn identity's replica is forgotten and its issuer resolves to nothing for it, while the co-located identity goes on reading its own replica and receiving the issuer's fresh writes there

#### Scenario: A forgotten replica re-imports on the next sweep

- **WHEN** a bound replica is forgotten while the binder's bookkeeping still names its import, and the pair's replica changes next
- **THEN** the runtime re-imports the granted namespace and its entries are readable again

#### Scenario: A grant moved onto another replica replaces the one it bound

- **WHEN** the counterparty's grant record comes to carry a ticket of a namespace other than the one it bound, and the record replicates to the grantee's copy of the pair
- **THEN** the grantee imports the namespace the record now names, and the replica the grant bound before is no longer held or reconciled

#### Scenario: A grant waits while an out-of-band import holds its issuer

- **WHEN** a runtime has imported a namespace out of band under an issuer, and that issuer's grant naming a different namespace then becomes readable in the pair
- **THEN** the grant's sweep neither imports the granted namespace nor forgets the one imported out of band

#### Scenario: An out-of-band import is not unbound

- **WHEN** a runtime imports a namespace from a ticket obtained outside any grant, and no grant record for that issuer exists in any of its pairs
- **THEN** the imported namespace stays bound — the binding mechanism forgets only namespaces it imported itself

#### Scenario: A withdrawal leaves an out-of-band import that holds the issuer

- **WHEN** a runtime holding a grant's namespace imports another namespace out of band under that grant's issuer, and the grant is then withdrawn
- **THEN** the namespace imported out of band stays bound and held — the withdrawal forgets only the replica the grant bound, and that one had already been replaced

#### Scenario: A withdrawal over many retraction markers leaves the runtime serving

- **WHEN** an audience holds more of the issuer's retraction markers than a store subscription buffers, and the issuer withdraws the grant
- **THEN** the audience's runtime drops those markers as it forgets the namespace, and every call waiting on the runtime answers afterwards
