# Proposal: ticket-relay-at-start

## Why

A node that runs with relays reaches its home relay some time after its endpoint binds: iroh connects to the relay in the background, and until it has, the address the endpoint reports carries its direct addresses alone. Every payload that hands this node's address to another device takes that address as it stands at the moment it is minted, with no wait: the document tickets the data layer mints for a pod's stores and for an identity's private metadata store (PMS), each built from `AddrInfoOptions::RelayAndAddresses` over the endpoint's address in `crates/data-layer/src/node.rs`, and the inviter's address in a linking payload and in a pod invite, taken from the node's dial handle in `crates/pdn-node/src/identity.rs` and `crates/pdn-node/src/pods.rs`. A payload minted before the home relay is reached therefore names no relay, and a device that receives it can reach this node only at the direct addresses it names.

On the container stand, run with `Connectivity::Relays` against n0's relays, the endpoint logged its home relay about 400 ms after it bound, and an invite minted as soon as the host answered named no relay URL: neither device's paths to the other held a relay until the host was made to wait 3 s after its start before it served requests.

What this costs depends on the connectivity. Under `Connectivity::RelaysAndAddressLookup`, which `SpawnOptions::for_product` sets, a device that holds a node id resolves the node's current home relay through address lookup, so a payload without a relay delays a dial until the node has published one and loses nothing for good. Under `Connectivity::Relays` there is no lookup: a device behind a NAT that holds only such a payload never reaches the node, and a ticket a PMS keeps carries the same address to the identity's other devices for as long as the PMS holds it, since a contact derived from a ticket keeps the addresses the ticket gave its node.

**Example:** Alice starts the app on her phone a1 and invites Bob from the first screen; Bob's phone b1 is behind a NAT, and both nodes run with relays.

| moment | a1's endpoint address | the invite b1 scans | b1 reaching a1, with address lookup | without it |
|---|---|---|---|---|
| 0 ms, a1's endpoint binds | its direct addresses | | | |
| 150 ms, Alice taps "invite" | its direct addresses | no relay URL | once a1 has published its relay | never: no path b1 can open leads to a1 |
| 400 ms, a1 reaches its home relay | its direct addresses and its relay URL | | | |

## What Changes

Nothing is decided. The change settles whether a payload that hands out this node's address waits for the home relay, and how long, or whether one minted before it is ever replaced, and then specifies and builds the answer. The options are listed under Open Questions, and none of them is chosen.

## Open Questions

### Where the wait for the home relay sits, if anywhere

- At the node's start: under a connectivity with relays, `SyncNode::spawn` returns only once iroh's `Endpoint::online` has, bounded by a budget past which the node starts without a relay and says so. Every payload minted afterwards names the relay, at the cost of a slower start, up to the budget, on every start, and of a node offline at start being slower still.
- At each mint: the paths that build a ticket or a ceremony payload await `Endpoint::online`, bounded the same way, before they read the endpoint's address. A start stays as fast as it is, and only a payload minted in the first moments waits.
- Nowhere, with the gap stated: a payload minted before the home relay names none, and a device reaches the node by address lookup alone. This holds under `RelaysAndAddressLookup`, and leaves `Relays` with the failure in the example.

### Whether a ticket a PMS keeps is minted again

- Tickets a PMS keeps for the identity's pods are minted once, when the identity creates or joins a pod, and are read back by the identity's other devices for as long as it holds the pod. A ticket minted before the home relay, or before the node moved to another network and another home relay, keeps the address it had. Minting them again when the node's home relay changes would cover both, at the cost of a PMS write per held pod on every change of relay.
- Leaving them as they are, and letting address lookup or the contacts the membership derives carry a moved node's current address, which they do only under `RelaysAndAddressLookup`.

**Example:** a1 creates "Family" 200 ms after its start and writes the pod's tickets into Alice's PMS; Alice links her laptop a2 the next day.

| option | the tickets a2 reads from the PMS |
|---|---|
| a wait at start or at each mint | name a1's relay |
| no wait, no new mint | name a1's direct addresses of that moment alone |
| a new mint when the home relay changes | name the relay a1 reached 200 ms later |

## Operating conditions

A device that restarts changes the outcome: each start opens the gap again, and a restart is when a person is likeliest to invite or link at once. A device that moves between networks changes it too, through the second question: the home relay it reaches on the new network is not the one its earlier tickets name. An unstable connection lengthens the gap, since the relay takes longer to reach, and decides how long a bounded wait has to be. Several identities on one node share one endpoint, so one wait or one change of relay serves them all. Linking is affected as the invite is: the linking payload carries the inviter's address the same way. A disk that fills, clocks that disagree and a membership that moves leave the outcome as it is.

## Out of Scope

- What a relay learns of the nodes that use it, which `Connectivity` already states.
- The path a node chooses once a relay path exists, which the data layer's path selector settles.

## Capabilities

None is settled. The answer touches `components/mee-pdn/data-layer/node-assembly`, where the endpoint is bound and the node's start is specified; `components/mee-pdn/pdn-node/device-linking` and `components/mee-pdn/pdn-node/pods` for the ceremony payloads; and `components/mee-pdn/data-layer/private-metadata-store` if tickets a PMS keeps are minted again.

## Impact

- **`crates/data-layer`**: `SyncNode::spawn_with` or the ticket paths — `share_pod_tickets` and `own_pod_tickets` in `src/node.rs`, `share_ticket` in `src/private_metadata.rs` — and the PMS's ticket records if they are minted again.
- **`crates/pdn-node`**: the inviter's address in `src/identity.rs` and `src/pods.rs`.
