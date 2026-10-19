# Proposal: wire-format-versioning

## Why

A node speaks four formats a peer has to parse exactly: the sync protocol's messages under the ALPN `/iroh-sync/1`, which pdn-store keeps under upstream's name; the announcements in a replica's gossip topic, pdn-store's `Op` under iroh-gossip's ALPN; the linking and pod join dialogues under `/pdn/linking/0` and `/pdn/pod-join/0`; and the document ticket the dialogues carry, encoded as the one variant `Variant0` of `TicketWireFormat`. Only the payloads a person carries from one device to another — the linking payload and the pod invite — carry a format version and refuse another one by name (`UnsupportedLinkingVersion`, `UnsupportedPodInviteVersion`). Nothing else names its version.

The formats change while their names stay. The identity-scoped-replicas change made the first message of a sync session name two identities, and gave the ticket an identity field inside the unchanged `Variant0`; every ALPN stayed as it was. Before that, a message part carrying a rejection had diverged from upstream under the same sync ALPN, and it later left the messages again under the same name, as the linking reply went from two tickets to one under its own. The pods change then added the identity a sync report names to the gossip announcement under the same gossip ALPN: a node of the new build drops the old 75-byte report as an invalid message, logged at debug level, while the old build reads the new 107-byte one and ignores its tail.

A dependency changes a format as well, under an ALPN the platform does not own. The workspace takes iroh-gossip from upstream's main branch past its 0.101.0 release, and that revision writes the header of its own stream as the topic followed by a byte of flags, where 0.101.0 wrote the topic alone, under the same gossip ALPN. A node on 0.101.0 reads the new header and ignores the byte; only upstream's own test, `stream_header_works_across_versions`, checks that, and no test of the workspace puts the two builds side by side. A version the platform moves for its own formats does not mark such a change, since the format belongs to iroh-gossip, so whatever rule this change settles has to say whether a bump of a dependency that alters its own framing counts as a change to a format.

A mismatch between two builds is silent. The encoding carries no description of itself, so a node reading the other shape fails to decode it, or decodes nonsense identities that are then refused as not hosted. On the sync ALPN the accepting side drops the connection without a terminal frame — the one refusal in pdn-store that sends none — so the initiator sees a stream cut short, exactly as a broken network cuts it; iroh logs one warning that names neither a version nor an incompatibility, and the pair retries at every reconcile pass and exchanges nothing. In the linking dialogue an old device and a new inviter part worst: the new inviter burns the secret, registers the old device as pending and answers with one ticket, the old device expects two, fails to decode the reply and rolls back, and the pending record stays on the inviter until it expires. The other way round the link goes through in silence: a new device scanning an old inviter's payload passes both version checks, since the payload's version did not move with the reply, the old inviter answers with two tickets, postcard's `from_bytes` reads the first and leaves the second unread, and the new device joins an identity whose other devices expect of it a store it never imported.

**Example:** old: a build before identity-scoped-replicas; new: a build after it. `/iroh-sync/1`, `/pdn/linking/0` and the ticket's `Variant0` are the same in both.

| what crosses | new sends, old reads | old sends, new reads |
|---|---|---|
| a ticket | decodes: postcard's `from_bytes` leaves the trailing 32-byte identity unread | fails: the bytes end where identity begins (`DeserializeUnexpectedEnd`) |
| the `Init` of a sync session | reads the two identities as the start of its first round: fails to decode, or decodes a round nobody sent | reads 64 bytes of the old first round as identity and caller: fails to decode, or refuses both as not hosted |
| the linking reply, two tickets in both builds | the old device reads the first ticket's 32-byte identity as the start of the second: fails to decode, or decodes a second ticket nobody sent | the new device takes the second ticket's first 32 bytes as the first one's identity: fails to decode the second, or decodes one nobody sent; on a failure it rolls back, the inviter having registered it as pending |
| Which way an `Init` goes depends on the bytes that land in the other shape's fields. A decode failure on `/iroh-sync/1` closes the connection with no terminal frame, and the pair retries at every reconcile pass, every 10 s by default for a PMS and every 5 minutes for a pod's stores. | | |

Under [defect-reachability](../../specs/code-practices/defect-reachability.md), what a node owes a peer that speaks an older format is decided by the change that alters the format, and the identity-scoped-replicas design records that nothing deployed speaks the old one: no user, no data, no compatibility window. That answer holds only until the first deployment that holds data. From then on every change to a format meets devices still on the previous build, because a person's devices update at different times and a phone updates when its owner lets it. The formats keep changing in the meantime, so the rule has to exist before that deployment rather than after its first silent failure.

## What Changes

Nothing is decided. The change settles how a change to a format is marked and what a node does when its peer speaks another format, for the four formats together, and then specifies and applies the answer before the first deployment that holds data. The options are listed under Open Questions, and none of them is chosen.

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
| the refusal at the dial alone | nothing, as today: no frame, the connection closes; with the ALPN moved, no such message arrives | a failed sync, as a broken network gives, retried at every reconcile pass; with the ALPN moved, a failed dial instead |

The first two questions are independent, and the third combines with either answer to them.

## Operating conditions

One device or several is the condition this change exists for: the devices of one identity update at different times, so for a while two builds serve one identity's replicas. A device that restarts after an update comes back to peers still on the previous build. An unstable connection is what a silent mismatch is mistaken for today, which is why the shape of a refusal is its own question. Several identities on one node share one build and are not affected.

## Out of Scope

- The layout of the storage directory. Each change that alters it states its own migration in its design; identity-scoped-replicas states none, since nothing deployed holds data.
- The linking payload and the pod invite themselves. Both already carry a format version and refuse another by name; the dialogues they open are in scope, since a change to a dialogue's messages leaves the payload's version where it was.

## Capabilities

None is settled. The answer touches `components/mee-pdn/data-layer/node-assembly`, where the first message of a sync session is read; `components/mee-pdn/pdn-node/device-linking` and `components/mee-pdn/pdn-node/pods` for the dialogues; and the spec that states the ticket's form. Moving the sync ALPN also touches `crates/pdn-store/CLAUDE.md`.

## Impact

- **`crates/pdn-store`**: the sync ALPN in `net.rs`, the ticket's wire variant in `ticket.rs`, and the read of the first message in `net/codec.rs`.
- **`crates/pdn-node`**: the linking and pod join ALPNs and their dialogues.
- **`crates/pdn-store/CLAUDE.md`**: if the sync ALPN leaves upstream's name.
