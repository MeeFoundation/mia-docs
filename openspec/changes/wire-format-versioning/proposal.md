# Proposal: wire-format-versioning

## Why

A node speaks three formats a peer has to parse exactly: the sync protocol's messages under the ALPN `/iroh-sync/1`, which pdn-store keeps under upstream's name; the pairing and linking dialogues under `/pdn/pairing/0` and `/pdn/linking/0`; and the document ticket both of them carry, encoded as the one variant `Variant0` of `TicketWireFormat`. Only the payloads a person carries from one device to another — the invite and the linking payload — carry a format version and refuse another one by name (`UnsupportedInviteVersion`, `UnsupportedLinkingVersion`). Nothing else names its version.

The formats change while their names stay. The identity-scoped-replicas change made the first message of a sync session name two identities, and gave the ticket an identity field inside the unchanged `Variant0`; every ALPN stayed as it was. Before that, the message part that carries a rejection had already diverged from upstream under the same sync ALPN.

A mismatch between two builds is silent. The encoding carries no description of itself, so a node reading the other shape fails to decode it, or decodes nonsense identities that are then refused as not hosted. On the sync ALPN the accepting side drops the connection without a terminal frame — the one refusal in pdn-store that sends none — so the initiator sees a stream cut short, exactly as a broken network cuts it; iroh logs one warning that names neither a version nor an incompatibility, and the pair retries every reconcile interval and exchanges nothing. In the pairing dialogue a new scanner and an old inviter part worst: the old inviter parses the request and commits its half of the connection, the new scanner cannot parse the reply and rolls back, and the old side goes on dialing a connection nobody holds.

**Example:** old: a build before identity-scoped-replicas; new: a build after it. `/iroh-sync/1`, `/pdn/pairing/0` and the ticket's `Variant0` are the same in both.

| what crosses | new sends, old reads | old sends, new reads |
|---|---|---|
| a ticket | decodes: postcard's `from_bytes` leaves the trailing 32-byte identity unread | fails: the bytes end where identity begins (`DeserializeUnexpectedEnd`) |
| the `Init` of a sync session | reads the two identities as the start of its first round: fails to decode, or decodes a round nobody sent | reads 64 bytes of the old first round as identity and caller: fails to decode, or refuses both as not hosted |
| the pairing request, then its reply | the old inviter decodes the request, dropping the identity at the end of the scanner's ticket, and commits its half | the new scanner fails at the reply's ticket, which ends where identity begins, and rolls back |
| Which way an `Init` goes depends on the bytes that land in the other shape's fields. A decode failure on `/iroh-sync/1` closes the connection with no terminal frame, and the pair retries every reconcile interval, 10 s by default. | | |

Under [defect-reachability](../../specs/code-practices/defect-reachability.md), what a node owes a peer that speaks an older format is decided by the change that alters the format, and the identity-scoped-replicas design records that nothing deployed speaks the old one: no user, no data, no compatibility window. That answer holds only until the first deployment that holds data. From then on every change to a format meets devices still on the previous build, because a person's devices update at different times and a phone updates when its owner lets it. The formats keep changing in the meantime, so the rule has to exist before that deployment rather than after its first silent failure.

## What Changes

Nothing is decided. The change settles how a change to a format is marked and what a node does when its peer speaks another format, for the three formats together, and then specifies and applies the answer before the first deployment that holds data. The options are listed under Open Questions, and none of them is chosen.

## Open Questions

### How a change to a format is marked

- The ALPN or the format version moves with every change to what it carries, and the ticket's variant moves from `Variant0` to the next one whenever the ticket changes. A node of another build then fails at the dial, which names the ALPN it does not support, instead of after it. The sync ALPN leaves upstream's name, which pdn-store's `CLAUDE.md` states it keeps.
- A format version negotiated inside the first message, with the ALPN kept for the protocol's whole life. The ALPN keeps upstream's name, and every session pays one more step before its first round.

**Example:** Alice's phone a2 runs a build whose `Init` has gained a field; her laptop a1 still runs the build before it; a2 dials a1 to sync.

| option | where the mismatch shows | what a2 reports |
|---|---|---|
| the ALPN moves with the change | in the handshake: a1 offers no such ALPN | the dial fails with the TLS alert `no_application_protocol` |
| a format version in the first message | on `/iroh-sync/1`, when a1 reads the version, one step before the first round | a1's answer to the version |

### What a node does with a peer that speaks another format

- It refuses the peer by name, and the two stay apart until both run one build. This is the simpler rule, and a person's devices on two builds stop exchanging until the one behind updates.
- It keeps serving the previous format beside the new one for a window — two ALPNs or two versions at once — so a staged update keeps working. This costs a second path through the code for the length of the window, and a rule for when the previous format goes.

**Example:** Alice's phone a2 updates on Monday, her laptop a1 on Thursday; on Tuesday Alice writes `contact/email` on a2.

| option | a1 receives `contact/email` |
|---|---|
| refuse the other format by name | on Thursday, once a1 has updated; until then each side reports a refusal naming the other's format, and the two exchange nothing |
| serve the previous format for a window | on Tuesday, at the two devices' next reconciliation, in the previous format |

### What a refusal looks like on the wire

- A node answers a first message it cannot decode with a terminal frame, as every other refusal in pdn-store already does, so the initiator reports a refusal instead of a cut stream. This holds whatever the two questions above settle.
- The refusal comes at the dial alone, which a moved ALPN already gives, and nothing is added to the first message's read path.

**Example:** a2 dials a1 on `/iroh-sync/1` with a first message a1's build cannot decode.

| option | what a1 sends | what a2 reports |
|---|---|---|
| a terminal frame for an undecodable first message | an `Abort` frame, as `refuse_session` sends for an identity it does not host | a refusal: `ConnectError::RemoteAbort` |
| the refusal at the dial alone | nothing, as today: no frame, the connection closes; with the ALPN moved, no such message arrives | a failed sync, as a broken network gives, retried every reconcile interval; with the ALPN moved, a failed dial instead |

The first two questions are independent, and the third combines with either answer to them.

## Operating conditions

One device or several is the condition this change exists for: the devices of one identity update at different times, so for a while two builds serve one identity's replicas. A device that restarts after an update comes back to peers still on the previous build. An unstable connection is what a silent mismatch is mistaken for today, which is why the shape of a refusal is its own question. Several identities on one node share one build and are not affected.

## Out of Scope

- The layout of the storage directory. Each change that alters it states its own migration in its design; identity-scoped-replicas states none, since nothing deployed holds data.
- The invite and the linking payload. Both already carry a format version and refuse another by name.

## Capabilities

None is settled. The answer touches `components/mee-pdn/data-layer/node-assembly`, where the first message of a sync session is read; `components/mee-pdn/pdn-node/connection-establishment` and `components/mee-pdn/pdn-node/device-linking` for the dialogues; and the spec that states the ticket's form. Moving the sync ALPN also touches `crates/pdn-store/CLAUDE.md`.

## Impact

- **`crates/pdn-store`**: the sync ALPN in `net.rs`, the ticket's wire variant in `ticket.rs`, and the read of the first message in `net/codec.rs`.
- **`crates/pdn-node`**: the pairing and linking ALPNs and their dialogues.
- **`crates/pdn-store/CLAUDE.md`**: if the sync ALPN leaves upstream's name.
