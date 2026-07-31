## Context

Both fixes here were found the same way: by asking, of four scenario tests, why they hand a namespace over by ticket when a recorded grant already covers it. Two of the answers were "no reason, it predates the grant binder". The other two were the product missing a piece, with the instrument quietly standing in.

The pieces are unrelated to each other and both small. What binds them into one change is what they unblock: the tests that rest on them, and the container stand that would otherwise meet the same two walls with a harness in the way, where they are far harder to see.

## Goals / Non-Goals

**Goals:**

- A granted replica converges from any device of its issuer that is reachable, not only from the device that published the grant.
- A caller of the two ceremonies can tell a refusal from a failure to reach, without reading error text and without learning why it was refused.
- Every scenario test arranges through the path the product uses, or says in its own words why it cannot.
- The rule written down, so the next test does not reintroduce the shortcut.

**Non-Goals:**

- Any HTTP surface. That change sits on top of this one.
- Discovery, relays, or hole punching — a contact is dialed where a path is known, and widening that is a transport question, not this one.
- Delegated grants, where the issuer is not the counterparty and the counterparty's device set is not the issuer's.
- Making the refusal distinguish a genuine "no" from a connection that died mid-dialogue. That would mean a wire-level refusal message and a revision of ADR-0011's dialogue.

## Decisions

### D1. The issuer's devices come from the connection metadata store, re-derived per sweep

The grant sweep already opens the counterparty's replica and reads its published device set for the retraction tracker ([connections.rs:411](../../../../crates/pdn-node/src/connections.rs#L411)); the contact refresh sits seven lines below it. The devices go in there, next to the audience siblings, and the set is re-derived on every sweep rather than stored — the same argument the sibling contacts already make: the published records are the durable truth and they replicate, so a list kept beside them would be a second source for one fact, and the stale one.

Tombstones fall out for free: the published-device read takes the latest entry per key without empty ones, so a withdrawn device simply stops appearing and the next sweep drops it.

Alternative — carry every device's address in the grant's ticket at publish time — was rejected twice over: the publishing device does not know its siblings' current addresses, and the ticket is a snapshot where the device set is a moving thing.

As implemented, "drops it" forced one surface change the Impact section did not predict: the tracked-contact list in data-layer was add-only, and a list that only grows can never let a withdrawn device leave, so `add_namespace_contacts` became `set_namespace_contacts` and the sweep derives the entire list every time — the grant ticket's addressing for devices the issuer still publishes, the issuer's published devices, and the siblings of every hosted audience bound to this issuer (the several-identities condition: two audiences of one issuer share one replica, so a per-identity list would flap). The engine keeps its own short record of once-useful peers and may redial a withdrawn device until that record ages out; the guarantee is therefore "leaves the derived contact set", and the delta says so.

### D2. Contacts stay endpoint ids, and that is the assumption to check first

The existing contact refresh adds an endpoint id with no addresses, on the argument that the endpoint resolves paths it has spoken to. That holds for the audience's own siblings, which sync with each other constantly. It is an assumption for the issuer's siblings, and the whole fix rests on it.

The check comes first in the tasks, not after: stand up an audience and a two-device issuer, publish from one device, take it offline, and see whether the other is dialed at all. If it is, the fix is what D1 describes. If it is not, the branch is D4.

### D3. The marker errors attach where the refusal is already recognized

`establish` and `link` each have exactly one place where a missing answer is turned into an error with a context string ([pairing.rs:366](../../../../crates/pdn-node/src/pairing.rs#L366), [linking.rs:381](../../../../crates/pdn-node/src/linking.rs#L381)). The distinction the caller needs is therefore already computed — attaching a typed value where a string is attached today is the whole change.

The markers carry no reason. Uniformity is owed to the dialed peer and stays exactly as it is; what changes is that the dialer's own caller stops having to match English to tell a refusal from an unreachable address. Alternative — matching the context string in each host — was rejected as brittle by construction and as a hole that would reopen for every further host.

What the marker does not separate: a genuine refusal, a connection that died mid-dialogue, and a handler that failed internally all surface as the missing answer, exactly as they do in the string today. Narrow enough for the deny tests that need it — their negative case is a deliberate replay against a live peer, and a peer that is simply down fails at the dial instead.

### D4. If an endpoint id does not resolve, the device record must carry addresses — as its own change

The fallback, should D2's check fail: the published device record grows an address hint, or the pair republishes reachability. Both touch a store format read by the counterparty, which is a heavier change than this one and deserves its own argument. It is named here so the check has a defined outcome either way, and so a negative result ends in a decision rather than in improvisation.

### D5. Tests arrange through the product path; instruments are admitted, not hidden

An arrange or act step reaches a namespace the way the product reaches it. A hand-made ticket handover is admissible in exactly two places: where the out-of-band path is the subject of the test, and where it is the negative control the access-control practice requires — the outsider holding a ticket and no grant. Anywhere else it is a shortcut to a state the product would have produced, and a test arranged that way keeps passing after the mechanism it stands in for breaks.

The rewrites are checked against a deliberately broken mechanism, because that is the only thing that distinguishes a rewrite from a rearrangement: if the assertions still pass with the binder disabled, they were never testing it.

## Operating conditions walked

Per `code-practices/operating-conditions.md`, the conditions that change this change's outcome, each backed by a delta scenario and a test: several identities on one node (two audiences of one issuer bind one replica — the contact set unions their siblings), one device or several with no founder assumption (the grant published from the linked device converges past it), a device linking before or after the grant (the late-linked device is dialed without a re-import), and capabilities moving (a re-grant after withdrawal rebuilds the contacts). The unstable connection is D3's whole subject — refused versus never-reached. Left out deliberately: the filling disk (no new storage path is introduced here) and linking mid-ceremony (the ceremonies stay as ADR-0011 and ADR-0012 define them; nothing here changes their dialogue windows).

## Risks / Trade-offs

- **D2's assumption fails and the fix does not work at all** → the check is the first task and its negative outcome has a named branch (D4). Nothing else in the change depends on it: the refusal markers and three of the four rewrites stand on their own.
- **A granted replica now dials more peers, and a stale device set means dialing the departed** → the set is re-derived per sweep and excludes tombstones, so a withdrawn device drops out at the next sweep; the cost of a dial to an unreachable id is a failed attempt the reconcile pass already tolerates.
- **The union of contacts grows on a well-connected node** → contacts are per replica, and a replica's issuer has as many devices as a person has; the scale question is the number of replicas, which is measured separately.
- **Rewriting four tests could lose a regression the hand-made version caught** → each rewrite must fail against a broken mechanism before it is accepted.
- **The two markers become public API of `pdn-node`** → additive and reasonless, so they neither weaken the ceremonies' uniformity nor constrain a future KERI-backed identity service.

## Migration Plan

Additive throughout: no store format changes, no wire format changes, no persisted state. The contact set is derived at runtime, so nothing carries over between runs and rollback is removing the derivation.

## Open Questions

- **Whether the sibling-serving test's variant in the linking suite can drop its instrument entirely** — with the issuer's devices reachable it should isolate the serving device by taking the other offline, as the sibling-serving test does. If something else pins it to a hand-made ticket, that is a further gap and is worth naming rather than absorbing. *Resolved: it can — the grantee rides its binder-imported grant and the phone shuts down for isolation. The one instrument left is the outsider control's laptop-minted ticket, which needs addressing to the serving device and has no grant to carry it; the test's docs name it.*
- **How wide the new practice is drawn** — the rule is about arranging through the product path, which reaches past tickets. Written narrow first, against the case in hand. *Resolved: written against the granted-namespace case, with the two admissible instruments (subject, negative control) and the broken-mechanism check as the acceptance bar (`code-practices/product-path-arrangement.md`).*
