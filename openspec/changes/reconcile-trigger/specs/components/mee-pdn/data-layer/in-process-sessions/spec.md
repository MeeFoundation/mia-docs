# data-layer: in-process sessions — delta for reconcile-trigger

## MODIFIED Requirements

### Requirement: A write reaches the co-located identities that hold its namespace

A write SHALL announce to the identities of its own node that hold the same namespace and may read the written entry — on a data namespace the issuer and the identities whose grant covers the written claim, on a directory or a connection metadata store every identity that holds it — which SHALL then reconcile over the in-process path. An identity of the node that holds the namespace but may not read the entry SHALL take no session on the announcement. The announcement SHALL carry no entry content, so what the receiving identity obtains comes through the session and its filter. A write SHALL reach a co-located identity on the announcement, without waiting for the periodic pass, also when it lands while the pair's previous session is being set up or is running: the pair then keeps the announcement pending and reconciles again once that session ends, as a reconcile trigger does ([reconcile trigger](../reconcile-trigger/spec.md)).

**Example:** Alice-work writes `contact/email`, then `notes/diary`, on node a1; Alice-leisure, on a1 too, holds her namespace under a grant of `contact/email`.

| step | what reaches Alice-leisure |
|---|---|
| 1 `contact/email`: Alice-work's engine sends `CoLocatedRequest::Announce { namespace, writer: Alice-work }` | a namespace and an identity: no key, no payload |
| 2 the node opens `sync_in_process` from Alice-work to Alice-leisure | at once, not at the next pass, 10 s apart by default |
| 3 the session runs through Alice-work's egress filter | `contact/email` |
| 4 `notes/diary`: Alice-work's engine announces it; the grant does not cover it | nothing: the node opens no session with Alice-leisure, and `notes/diary` stays out, existence included |

#### Scenario: A co-located identity sees a write without the periodic pass

- **WHEN** an identity writes an entry a co-located identity is granted, within one reconcile interval
- **THEN** the co-located identity reads that entry before the interval elapses

#### Scenario: The announcement carries nothing by itself

- **WHEN** a write a co-located identity's grant covers and a write it withholds land together
- **THEN** the session the announcement opens carries the covered entry alone, and the withheld claim stays absent from that identity's replica

#### Scenario: An identity the write does not cover takes no session on it

- **WHEN** an identity writes a claim that a co-located identity holding its namespace is not granted, within one reconcile interval
- **THEN** no in-process session opens between the two before the interval elapses

#### Scenario: A write during a co-located session is not left to the pass

- **WHEN** an identity writes a claim a co-located identity is granted while the session announced for its previous write to that identity is still being set up or is running
- **THEN** the co-located identity receives the later claim before the next periodic pass
