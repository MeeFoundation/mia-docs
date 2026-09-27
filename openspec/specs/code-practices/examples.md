# Examples: render every rule into a case

A spec and the code state rules. Explaining how something works, render the rule into one concrete example: with attention running low, an example is understood faster than a rule. The example comes with the rule, never instead of it.

## Where

- A decision in `design.md`: after its text, before its rejected alternatives. It shows the chosen option alone.
- A requirement in a spec: after its text, before the first scenario.
- A finding of a deep review: right after how it shows up.
- An explanation in chat the user asked for.

An example that would be contrived is left out: a ranking of values, a checklist, a rule that something never happens. A rule about every possible case gets a counterexample, when one is known.

## What makes it an example

One case, a few rows, the outcome stated. Real values as the code has them — `grants/<issuer-hex>`, 8,192 bytes, HTTP 409 — and people with their roles, Alice (issuer) and Bob (read grant); never `id1` or `foo`. Checked against the code as a scenario is, because the example is the part that gets read.

The shape is whatever puts this case in front of the reader fastest, chosen fresh each time. Shapes that have worked, as hints rather than a menu: a table of operations against participants for access; an annotated listing of paths or keys, before and after a write; a message with its bytes; a timeline with a column per device, session or task; a table of states or causes against what each side observes; a table of states against events; numbered steps with what survives a failure or a kill after each; the values at a limit and just past it; a request with its response; one case run under each option; the mechanism broken against a test that stays green or turns red. A column for what the spec promises turns any of them into the statement of a defect.

Three of them, for the level of detail:

| operation | Alice (issuer) | Bob (read grant) | Dave (ticket, no capability) | Carol (outsider) |
|---|---|---|---|---|
| read | allowed | allowed | denied | denied |
| write | allowed | denied | denied | denied |

```
message:       Message::Abort { reason: AbortReason::AlreadySyncing }
encoded as:    00 00 00 02 02 01
encodes:       frame length 2 (u32 big-endian), Message variant 2 = Abort, AbortReason variant 1 = AlreadySyncing
```

```
email, phone: the claims contact/email and contact/phone
t    Bob (issuer)                     session S1, b1 → a1              session S2, b1 → a1
t0                                    set up: Alice reads email, phone
t1   narrows Alice's grant to email   still serves email and phone
t2                                    ends; a1 keeps phone
t3                                                                     set up: email only
```
