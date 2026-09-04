# Connection establishment

## Purpose

How two identities become [connected](../../../architecture/language/connection.md), realizing ADR-0011 on the runtime: a pairing dialogue — one raw bidirectional exchange on the dedicated pairing ALPN, not a document-sync session — whose handler the runtime registers at spawn through the data-layer assembly slot and whose dial side rides the node's dial handle. The dialogue creates the shared state everything later travels through: mutual connections records in the two identities' [directories](../data-layer/private-metadata-store.md) and the exchanged [connection metadata pair](../data-layer/connection-metadata-store.md). The exchange is bearer-level for now: the KERI proof of control over a presented `PdnId` is a marked step of this dialogue, deferred (ADR-0008's interim posture), and both peers must be online — pending invitations are future work.

## Requirements

### Requirement: An invite is one-time, short-lived, and bearer-free
The connections service SHALL mint an invite for a hosted identity: a fresh random one-time secret (32 bytes from the operating-system generator) with a short lifetime (a default with an invite-time override), held pending on the inviting runtime, and a self-contained invite payload carrying a format version, the inviter's node address, the secret, and the inviting identity's `PdnId`. The payload SHALL carry no ticket and no identity proof. Minting an invite for an identity the runtime does not host SHALL be refused with no pending state created.

Suggestion (non-normative, host-side UX). Because the secret is one-time and short-lived, a consumed or expired invite is recovered only by minting a fresh one — never by re-presenting the same secret, which the inviter burns before replying (see the verify-and-burn requirement below). A host that displays an invite (a QR code, say) is therefore suggested — not required — to rotate the displayed invite to a freshly minted one well before its lifetime elapses (for the 120-second default, on the order of every 60 seconds), and to refresh it once a pairing completes, so a scanner always captures a live, unburned secret. The protocol neither mandates nor observes this rotation.

#### Scenario: The payload carries no bearer material
- **WHEN** an invite is minted for a hosted identity
- **THEN** its payload consists of the format version, the inviter's node address, the one-time secret, and the identity's `PdnId` — no tickets and no identity proof

#### Scenario: Every invite carries a distinct secret
- **WHEN** two invites are minted, whether for one hosted identity or two
- **THEN** their secrets differ, and each is pending independently

#### Scenario: An invite for an unhosted identity is refused
- **WHEN** an invite is requested for an identity the runtime neither created nor linked
- **THEN** the operation fails with an unknown-identity error and no pending invite exists

### Requirement: The dialogue is one raw exchange on the pairing ALPN
Establishment SHALL dial the invite payload's node address under the dedicated pairing ALPN and run one raw bidirectional exchange: the scanner presents the secret, its own `PdnId`, its node address, and a read ticket to its own connection metadata store toward the inviter; the inviter — after the verify-and-burn below — answers with the read ticket to its own store toward the scanner. A payload whose format version the scanner does not speak SHALL be refused before dialing. Establishing on behalf of an identity the scanning runtime does not host SHALL be refused before dialing.

The round-trip SHALL be bounded by a fixed ceiling: `establish` names no budget of its own, so the ceiling is a constant — generous against any live exchange, finite so a dialed inviter that never answers costs the caller the ceiling, surfaced as its own typed outcome distinct from the refusal, and never the transport's idle timeout.

#### Scenario: A hung inviter costs the caller the ceiling and nothing more
- **WHEN** the dialed inviter accepts the pairing dialogue, reads the request, and never answers
- **THEN** `establish` fails within the ceiling with the dialogue-timeout outcome, distinguishable from the refusal without matching on error text

#### Scenario: Establishment completes between two runtimes
- **WHEN** runtime B establishes with a live invite minted on runtime A
- **THEN** the dialogue completes over the pairing ALPN and both sides hold the exchanged read tickets

#### Scenario: An unknown payload version is refused before dialing
- **WHEN** establish is given an invite payload with an unsupported format version
- **THEN** it refuses without opening a connection

#### Scenario: Establishing for an unhosted identity is refused
- **WHEN** establish is invoked for an identity the scanning runtime does not host
- **THEN** the operation fails with an unknown-identity error and no dialogue runs

### Requirement: The secret is verified and burned atomically, before any state
On a presented secret the inviter SHALL atomically check-and-burn against its pending set: present and unexpired → burned and the dialogue proceeds; expired, already burned, or unknown → refused. The check SHALL precede every state change, so a refused attempt leaves no observable state on the inviter: no replica created, no ticket issued, no connections entry, no directory entry. An unpresented secret SHALL expire at the end of its lifetime and thereafter be refused. A refused presentation SHALL NOT burn a live pending invite (a guess cannot extinguish a ceremony in progress), and refusals SHALL be uniform — the dialer cannot distinguish wrong from expired from already burned.

#### Scenario: A second presentation of the same secret is refused
- **WHEN** establishment completed against an invite and a second establish presents the same secret
- **THEN** the second attempt is refused, and the inviter's stores are exactly as the first establishment left them

#### Scenario: An expired secret is refused
- **WHEN** a secret is presented after its lifetime has elapsed
- **THEN** the attempt is refused and no observable state exists on the inviter — no replica, no ticket, no connections entry, no directory entry

#### Scenario: A wrong secret is refused and burns nothing
- **WHEN** a dialer presents a secret that was never minted while an invite is pending
- **THEN** the attempt is refused with no observable state on the inviter, and a subsequent presentation of the pending invite's real secret succeeds

### Requirement: Establishment records the connection for both identities, on all their devices
On a completed dialogue each side SHALL record the counterparty among the connections records of its private-metadata directory, assemble the metadata pair — creating its own store if none exists toward this peer, importing the counterpart's from the received read ticket — and publish the pair's tickets in the same directory. Establishment performed on one device of each identity SHALL thereby reach the identities' other devices: the directory replicates, and a linked device opens the pair from the directory's tickets on demand.

#### Scenario: Both sides list each other
- **WHEN** runtime B establishes with an invite from runtime A
- **THEN** A's identity lists B's among its connections and B's lists A's

#### Scenario: The connection is visible from linked devices
- **WHEN** establishment ran between A's phone and B's phone, and each identity has a laptop linked
- **THEN** each laptop eventually lists the counterparty among its identity's connections and reads the counterpart's metadata store opened from its directory

### Requirement: Re-establishment converges, whichever side invites
A fresh invite between identities that already share establishment state — a completed connection, or the residue of a handshake that failed after the burn — SHALL establish cleanly and converge: each identity's directory holds one connection record per counterparty, each side's own metadata store toward the peer is reused (the directory yields the same replica, so tickets from different attempts address the same namespace), and no duplicate replicas exist — regardless of which side mints the fresh invite.

#### Scenario: Establishing twice yields one connection
- **WHEN** A and B establish, and later establish again from a fresh invite
- **THEN** each lists the other exactly once, and each side's own metadata store is the same replica both times

#### Scenario: The retry may swap directions
- **WHEN** the first establishment ran from A's invite and the second runs from B's invite
- **THEN** the outcome converges identically — one connection, the same metadata pair, no duplicates

### Requirement: A refused establishment is legible to the dialer's caller
Establishment SHALL report a refusal by the inviter to its own caller as a refusal, distinguishable from a failure to reach or complete the dialogue. The refusal SHALL carry no reason: it says that the inviter was reached and said no, and nothing about which of wrong, expired, or already burned applied — the uniformity the dialer's peer sees is unchanged. A caller — a host, a test, or an application — SHALL be able to make the distinction without inspecting human-readable error text.

#### Scenario: A refusal is not a transport failure
- **WHEN** establishment presents a secret that has already been burned, and separately when it dials an address where no inviter answers
- **THEN** the first reports a refusal and the second does not, and the two are distinguishable without matching on error text

#### Scenario: The refusal names no reason
- **WHEN** establishment is refused for a wrong secret, for an expired one, and for an already burned one
- **THEN** all three report the same refusal, carrying nothing that separates the three cases
