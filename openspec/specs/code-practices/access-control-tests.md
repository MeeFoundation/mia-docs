# Access-control tests: pair every allow with a deny

A test that only asserts an authorized party *can* access something verifies nothing about the control — a completely broken control that grants everyone everything passes it. Every test that asserts authorized access MUST, in the same place, assert that the corresponding **unauthorized** party is denied. Pick the tightest negative party for what is under test.

This makes the invariants testable rather than merely asserted (`../components/mee-pdn/invariants.md`): Invariant 1 (an identity's PMS is held by its own devices, and only those) and Invariant 2 (a node acquires a pod's entries only while it is a device of a current member). A positive-only test leaves both unverified.

## Rules

**Read** — two negative parties, a ladder from no access to partial:

1. **Outsider** — holds no ticket and no membership. It receives neither the content nor the fact that the entry exists (the entry never arrives; existence stays hidden). Where the entry's id is content-derived (a BLAKE3 blob hash), the denial MUST also hold for a party that already **knows or can derive the id/hash**: knowing the id yields neither the bytes nor a confirmation that the entry exists. Content-addressing invites a "you have the hash, here are the bytes" path that silently bypasses the read control — this is the case that catches it.
2. **Ticket without membership** — holds the stores' bearer tickets but is no member: a removed member, or an identity handed the tickets. It may connect and dial, yet receives none of the pod's entries. The ticket admits dialing; membership authorizes reading — a session's egress is not bypassed by ticket possession. The outsider of rule 1 never holds a ticket, so only this rule exercises the ticket-without-authorization path.

**Write** —

3. **Lower level** — a plain member against an owner's act, a member writing under another member's name, or an outsider. Its write is refused, and is not accepted by the authorized nodes.

**Example:** the read ladder on "Family", for a claim Bob placed.

| party | holds | receives |
|---|---|---|
| Carol, a current member | membership, both tickets | the claim |
| Dave, removed before the claim | both tickets, no membership | nothing, and nothing says the claim exists |
| Erin, an outsider | nothing | nothing |

## How

- Use real memberships and tickets, not a short-circuit — for example, not a hand-built member set standing in for the membership view.
- Assert on **acquisition, not error text**: that the entry or bytes never arrive and existence is not revealed, not merely that a call returned an error.
