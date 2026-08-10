## ADDED Requirements

### Requirement: Cancellation cleanup precedes retry
The runtime SHALL keep an identity reserved after a linking caller cancels until every local effect of that attempt is rolled back. Cleanup from an older attempt SHALL NOT remove, unhost, or forget state owned by a later attempt, and runtime shutdown SHALL wait within a named budget for supervised cleanup rather than relying on detached destructor tasks.

#### Scenario: Immediate retry survives older cleanup
- **WHEN** a linking attempt is cancelled after importing its replicas and the same runtime immediately retries the identity
- **THEN** the retry waits until the older rollback completes, then succeeds, and the identity remains hosted and usable after all cleanup tasks finish

#### Scenario: Shutdown completes cancellation cleanup
- **WHEN** runtime shutdown begins while a cancelled linking attempt has rollback work pending
- **THEN** shutdown waits within its cleanup budget and leaves no reservation, hosted identity, or imported replica from the cancelled attempt

### Requirement: Post-verification local failures are observable
The inviter SHALL preserve uniform remote refusal after a linking secret is verified, but SHALL record every storage or ticket-minting failure that occurs after the secret burns as a typed local diagnostic. A local failure SHALL NOT be reported to the operator only as a peer refusal.

#### Scenario: Pending registration fails after burn
- **WHEN** durable storage refuses the pending-device write after a valid linking secret is verified and burned
- **THEN** the peer receives the uniform refusal and the inviter records the storage failure locally

### Requirement: Pending-device state is bounded
Every pending-device registration SHALL carry durable creation time and SHALL expire after 24 hours unless the device confirms first. Expiry SHALL confer no access, SHALL survive process restart, and SHALL tombstone abandoned records so they stop replicating as live state.

#### Scenario: Abandoned registrations expire across restart
- **WHEN** several distinct devices leave pending registrations, the inviter restarts, and 24 hours pass without confirmation
- **THEN** cleanup removes every expired pending registration and no device enters the confirmed set

#### Scenario: Confirmation wins before expiry
- **WHEN** a pending device confirms before 24 hours pass
- **THEN** it enters the confirmed device set exactly once and its pending record is removed

### Requirement: Lost-reply retry uses the product path
A fresh invite after a lost reply SHALL converge through the public linking service, including reservation, replica import, catch-up, confirmation, hosted-state insertion, and rollback ownership.

#### Scenario: Fresh invite completes after a lost reply
- **WHEN** a device loses the first linking reply after pending registration and retries immediately through the public linking service with a fresh invite
- **THEN** the second link completes, the identity remains hosted, the device is confirmed exactly once, and no pending registration remains
