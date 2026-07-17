## REMOVED Requirements

### Requirement: An identity is provisioned on its first device
**Reason**: Provisioning is respecified in `pdn-node-device-linking` ("An identity is provisioned with its full store set on its first device"): the connections store no longer exists to be created, the data namespace joins provisioning, and the procedure lives in pdn-node with the rest of the ceremony.
**Migration**: See `pdn-node/device-linking.md`; the seed-sufficiency clause is superseded by the linking dialogue.

#### Scenario: Superseded by the pdn-node ceremony
- **WHEN** an identity is provisioned after this change
- **THEN** the governing requirements are `pdn-node-device-linking`'s

### Requirement: Linking into further identities is independent and repeatable
**Reason**: Per-identity isolation of linking is already required by `data-layer-multi-identity` ("An identity is added to a device explicitly"), which this change rewords for the invite-based act; the ceremony side lives in `pdn-node-device-linking`.
**Migration**: See `data-layer/multi-identity.md` and `pdn-node/device-linking.md`.

#### Scenario: Carried by multi-identity
- **WHEN** a device links into several identities after this change
- **THEN** the isolation guarantees are `data-layer-multi-identity`'s

### Requirement: A device links from a single seed
**Reason**: The seed — a bearer write ticket carried in a QR — is gone: linking starts from a bearer-free payload, and the bootstrap tickets ride the dialogue's reply (`pdn-node-device-linking`). Discovery through the directory is no longer part of the linking critical path; nothing remains for it to discover.
**Migration**: The linking payload replaces the seed; the reply's directory and data tickets replace ticket discovery.

#### Scenario: Superseded by the dialogue
- **WHEN** a device links after this change
- **THEN** it dials the payload's address and receives the bootstrap tickets in the reply

### Requirement: A linked device registers itself
**Reason**: Registration inverted: the inviter writes the newcomer's device record into its own replica before replying (`pdn-node-device-linking`, "The inviter registers the newcomer before replying"), so the delivery-confirmation machinery this requirement mandated (`confirm_registration`, the re-request driver) is removed rather than reimplemented.
**Migration**: The registration exists on an existing device from the start; no push, no confirmation wait.

#### Scenario: Superseded by inviter-side registration
- **WHEN** a device links after this change
- **THEN** its device record is written by the inviter as part of the dialogue

### Requirement: The device set is bidirectional
**Reason**: Carried by `pdn-node-device-linking`'s scenarios (the newcomer is registered on the inviting device; success implies the caught-up newcomer reads the existing devices) together with the directory's replication requirement — no separate requirement needed.
**Migration**: No behavior change.

#### Scenario: Carried by the ceremony and directory specs
- **WHEN** a device links after this change
- **THEN** both directions of device-set visibility follow from the ceremony and directory requirements

### Requirement: Bootstrap is directory-first
**Reason**: The premise dissolved: the directory is no longer the discovery channel for the linking critical path (the reply hands the bootstrap tickets over directly), and the connections store this requirement ordered against no longer exists. The directory remains the durable record (`tickets/data`, per-connection kinds) consumed outside the ceremony.
**Migration**: See `pdn-node-device-linking` ("The reply hands over the bootstrap tickets") and the directory's typed-tickets requirement.

#### Scenario: Superseded by tickets-in-reply
- **WHEN** a device links after this change
- **THEN** the stores it comes up with arrive from the reply, not from directory discovery
