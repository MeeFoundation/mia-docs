# Pod store

## MODIFIED Requirements

### Requirement: The membership store is reconciled before the record store

A session between two member devices SHALL reconcile the membership store to convergence, build its membership view, and only then reconcile the record store; both stores SHALL be reconciled whole, with no filter on either. The record store's session SHALL be served by the membership view built after the membership store's session, so that a newcomer whose joined event that session brings is served and a member whose departure it brings is refused; a session that would refuse its caller SHALL first wait, for a few seconds at most, for the payloads the caller's own chain and statements still lack, since a joined event counts only once its join statement has arrived. A record SHALL be held whatever it arrives ahead of, and SHALL read once the membership its entries name has arrived.

**Example:** Alice's laptop a2 holds neither Dave's joined event nor Dave's first claim, and sessions with Carol's phone c1, which holds both; `<dave>`: 64 lowercase hex chars of Dave's `PdnId`; `<id>`: the id `put_record` minted.

| step of the session | a2 |
|---|---|
| 1. the membership store reconciled to convergence | takes Dave's joined event, its join statement naming his phone d1 |
| 2. the membership view built | Dave a member at his sequence 1, writing on d1 |
| 3. the record store reconciled | takes `by/<dave>/claim/<id>/1` from d1's author, which the record view reads at Dave's sequence 1 at once |

#### Scenario: A newcomer's first record reads once the session brings its membership

- **WHEN** newcomer D's joined event and D's first claim are both unknown to a device of B, and B's device sessions with a device holding both
- **THEN** B's device reads D's claim at the end of that session

#### Scenario: A refused membership dial keeps the record store's dial held
- **WHEN** a member device's dial of a pod's membership store to another member device is refused as already syncing, because that device's own exchange of the membership store with it is running
- **THEN** the record store's dial held behind it stays held until that exchange ends, and the record store's session is then served by the membership view that exchange brought; a dial refused on every redial until its redials are exhausted releases the held dial, an exchange a resync is queued behind leaves the held dial to the resync, which dials the same pair, and an in-process dial the co-located channel dropped releases the dials held behind it itself

## ADDED Requirements

### Requirement: A join after a departure starts the record store once the membership view shows the join

On a device that holds the pod's tombstone, a join SHALL start the membership store's sync first and SHALL start the record store's sync only once the device's membership view lists its identity as a member again, or once 5 seconds have passed since the membership store's start, whichever comes first; while that join is in flight, the dials the membership store's watcher makes on a session it saw SHALL leave the record store out. The joined event and its join statement come by the membership store's session with the inviter, the payload after the session; a record store started while the view still shows the departure has its first session judged by the departure, takes nothing on it, and the join's catch-up would count that session as the record store's.

**Example:** Carol left "Family" on her phone c1, Alice placed a claim afterwards, then invited Carol again, and c1 joins.

| on c1 | the record store |
|---|---|
| the membership store's session with a1 brings Carol's new joined event; its join statement is still on its way | not started: the view shows Carol's leave |
| the join statement lands 300 ms later; the view lists Carol as a member | started: its first session with a1 is served whole and brings the entry of Alice's claim, and `join` returns with that entry held; the claim reads once its payload lands |
| a1 unreachable after the membership store's session | started 5 seconds after the membership store's; the join's catch-up then waits for its session as for any join |

#### Scenario: A join after a leave answers with the entries of the records placed meanwhile

- **WHEN** a member left on its device, an owner placed a record afterwards and invites the member again, and the device joins while the join statement's payload lands a second after the session that brought the joined event
- **THEN** the join answers with that record's entry held on the device, the record reads once its payload lands, and the record store had no session before the join statement landed

### Requirement: A pod's stores are first started by the start that registers them

While a pod's start is in flight on a device — from its registration in `create_pod`, an import or the opening of its tombstone's record store until both stores' sync is started — the periodic pass, the dials of the identity's own devices and the membership store's watcher SHALL leave that pod's stores alone, and a start that fails SHALL end the hold, so the next run of the pass reaches the pod as before. Each store's sync is then first started by the start alone: a subscription the start attaches sees the store's first session whole, and the record store's dial queues behind the membership store's.

**Example:** Bob's laptop imports "Family" with its pod interval at 1 second, and the pass runs 5 milliseconds into the import.

| the pass | the import |
|---|---|
| finds the pod starting and skips it | starts the membership store with its ordered subscription attached, then the record store; the first session's 1,000 inserts are all in the subscription |
| its next run, after the import returned | reconciles both stores as any pod's |

#### Scenario: A pass during a pod's start draws nothing for it

- **WHEN** a pod's observed import is paused between its registration and the start of its stores' sync while the pod stores' pass runs
- **THEN** that run draws nothing for the pod, the next run after the import draws for it, and the subscription the import opened holds every insert of the record store's first session
