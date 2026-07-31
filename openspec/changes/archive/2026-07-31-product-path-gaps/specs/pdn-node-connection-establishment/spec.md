# pdn-node: connection establishment

Uniform refusal is a property toward the dialed peer, not toward the dialer's own caller. Today a caller of `establish` cannot tell "the inviter refused me" from "I never reached anyone", because both arrive as the same untyped error — so a host cannot report the refusal faithfully, and a test above the host cannot assert it. This delta requires the distinction while keeping the refusal reasonless.

## ADDED Requirements

### Requirement: A refused establishment is legible to the dialer's caller
Establishment SHALL report a refusal by the inviter to its own caller as a refusal, distinguishable from a failure to reach or complete the dialogue. The refusal SHALL carry no reason: it says that the inviter was reached and said no, and nothing about which of wrong, expired, or already burned applied — the uniformity the dialer's peer sees is unchanged. A caller — a host, a test, or an application — SHALL be able to make the distinction without inspecting human-readable error text.

#### Scenario: A refusal is not a transport failure
- **WHEN** establishment presents a secret that has already been burned, and separately when it dials an address where no inviter answers
- **THEN** the first reports a refusal and the second does not, and the two are distinguishable without matching on error text

#### Scenario: The refusal names no reason
- **WHEN** establishment is refused for a wrong secret, for an expired one, and for an already burned one
- **THEN** all three report the same refusal, carrying nothing that separates the three cases
