# pdn-node: device linking

The counterpart of the establishment delta in this change: linking refuses uniformly toward the dialed inviter, and that uniformity has swallowed the distinction its own caller needs — refused versus never reached.

## ADDED Requirements

### Requirement: A refused link is legible to the dialer's caller
Linking SHALL report a refusal by the inviting device to its own caller as a refusal, distinguishable from a failure to reach or complete the dialogue and from a failure to catch up after it. The refusal SHALL carry no reason, leaving the uniformity seen by the dialed device unchanged. A caller SHALL be able to make the distinction without inspecting human-readable error text.

#### Scenario: A refusal is not a transport failure
- **WHEN** linking presents a secret that has already been burned, and separately when it dials an address where no inviting device answers
- **THEN** the first reports a refusal and the second does not, and the two are distinguishable without matching on error text

#### Scenario: A refusal is not a catch-up timeout
- **WHEN** linking is refused by the inviting device, and separately when the dialogue succeeds but the imported directory does not catch up within the timeout
- **THEN** the two are distinguishable without matching on error text, and both leave the newcomer with no local residue of the attempt
