# Access-control tests: pair every allow with a deny

A test that only asserts an authorized party *can* access something verifies nothing about the control — a completely broken control that grants everyone everything passes it. Every test that asserts authorized access MUST, in the same place, assert that the corresponding **unauthorized** party is denied. Pick the tightest negative party for what is under test.

This makes the invariants testable rather than merely asserted (`../components/pdn-node/invariants.md`): Invariant 1 (a store is held by its own identity's devices, and only those) and Invariant 2 (a node acquires a claim only if it holds a read capability for it). A positive-only test leaves both unverified.

## Rules

**Read** — two negative parties, a ladder from no access to partial:

1. **Outsider** — holds no ticket and no capability. It receives neither the content nor the fact that the entry exists (the entry never arrives; existence stays hidden). Where the entry's id is content-derived (a BLAKE3 blob hash, or a content-addressed `ClaimId`), the denial MUST also hold for a party that already **knows or can derive the id/hash**: knowing the id yields neither the bytes nor a confirmation that the entry exists. Content-addressing invites a "you have the hash, here are the bytes" path that silently bypasses the read control — this is the case that catches it.
2. **Ticket without capability** — holds the store's bearer ticket but no read capability. It may connect and reconcile, yet receives none of the capability-gated claims. The ticket admits syncing; the capability authorizes reading — the egress filter (subset-rbsr) is not bypassed by ticket possession. The outsider of rule 1 never holds a ticket, so only this rule exercises the ticket-without-authorization path.

**Write** —

3. **Lower level** — holds read but not write (for example, a peer with a read-only ticket to another identity's metadata store), or is an outsider. Its write is rejected, and is not accepted by the authorized nodes.

## How

- Use real capabilities and tickets, not a short-circuit — for example, not the naive `Connections` set standing in for read capabilities.
- Assert on **acquisition, not error text**: that the entry or bytes never arrive and existence is not revealed, not merely that a call returned an error.
