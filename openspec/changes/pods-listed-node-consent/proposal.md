# Proposal: pods-listed-node-consent

## Why

A member's device statement lists, for each of the member's devices, the node id it is dialed by and the author the member writes with there, and counts on the signature of the member's identity key alone ([pod stores](../../specs/components/mee-pdn/data-layer/pod-store/spec.md)); every member device dials the listed nodes as that member's contacts on every reconcile pass. A member's modified device can therefore list the node id of a node outside the pod. Every member device then dials that node as the member, the node refuses each session as one for a store it does not host, and the dials go on; with address lookup bound, a node id reaches any node on the network. The node dialed is outside the pod and trusted with nothing, so this is a modified node reaching a denial of service against an honest node, which obliges a fix; pods accept it while they serve load testing.

**Example:** Bob's modified phone b1 lists, in Bob's device statement, the node id of a server outside "Family", whose 100 members hold 2 devices each.

| on the members' devices | the server |
|---|---|
| Bob's statement counts: Bob's identity key signed it | dialed as Bob by 200 member devices on every reconcile pass, 10 s apart by default |
| each session is refused | dialed for good: a member's device list only grows |

## What Changes

Nothing is decided. The change settles how a listed node consents to its listing, and then specifies and builds the answer.

## Open Questions

### How a listed node consents to its listing

- The listed device countersigns its listing with its node key: each device in a statement carries a signature by the node it names, over a fixed prefix, the pod id, the member's `PdnId` and the author it writes with there, made by the device that adds itself and copied into every later version, and the membership view counts no listing whose countersignature fails. A member then lists no node it does not run, at the cost of 64 bytes per listed device in every version and one verification per listing.
- A backoff on refused contacts: a member device dials a listed node that refused a session for the pod less and less often, up to a bound. Nothing changes in the statement, and the node outside the pod is still dialed by every member device at the bound's interval, for good.

**Example:** Bob's modified phone b1 lists the server as above.

| option | the server |
|---|---|
| the listed device countersigns | never dialed: the listing counts for nothing on every member device |
| a backoff on refused contacts | dialed by 200 member devices at the bound's interval, for good |

## Operating conditions

Several identities on one node: a node listed under two members carries a countersignature per member, each over that member's `PdnId` and author. A device linking: the linked device writes its own listing and is the one device holding its node key, so it countersigns as it adds itself. A restart changes nothing: the countersignature sits in the statement. The reach of the dials grows with address lookup, which the product binds.

## Capabilities

None is settled. Countersigning touches `components/mee-pdn/data-layer/pod-store`, for the statement's shape and the membership view's count of it, and `components/mee-pdn/pdn-node/pods`, for the device that adds itself; a backoff touches `components/mee-pdn/data-layer/pod-store`, for the dialing of a pod's contacts.

## Impact

- **`crates/data-layer`**: the device statement and the membership view's count of it, or the dialing of a pod's contacts.
- **`crates/pdn-node`**: the device that adds itself to its member's statement.
