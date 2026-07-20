## MODIFIED Requirements

### Requirement: Link returns caught up, and failure leaves no local residue
`link` SHALL NOT report success until the imported directory has completed one successful sync exchange that started after the import — one bounded wait against the peer that just answered the dialogue, not a retry loop; a directory that cannot catch up within the caller's timeout SHALL surface as an error, not a hang. The property waited on is a completed session, not arrived content: a runtime that never synced and one that synced and found nothing new must not be confused, so polling the directory's contents does not discharge this requirement.

The dialing runtime SHALL arm the identity for session classification the moment its directory is imported, before the data namespace is imported — so at no instant does the data binding exist ahead of the book that judges its sessions. The other order would serve the data namespace ticket-bounded (full view to any caller) for the whole catch-up wait, on a long-lived namespace id already known to every past grantee and every holder of a leaked ticket. The cost of arming early is bounded and fail-closed: while the directory is still converging, callers it cannot yet resolve are refused, and a refused device is served once its record replicates in — the node's periodic reconcile pass is the retry cadence.

On any failure after import, the dialing runtime SHALL undo what this linking did, in reverse order — the data-namespace import, the arming, the directory — so a failed link leaves no local residue and the identity is unknown to the runtime again. Undoing SHALL restore what the import displaced rather than delete it: an issuer can already be bound when the link runs, because a namespace reached through a peer's grant binds the same issuer without making the identity hosted, and the pre-dial refusal cannot see it. A rollback that forgot the issuer outright would destroy a replica this linking never imported, permanently — so the data namespace is unbound only when the link's import was what bound it, and the replica it brought up is dropped only when it is not the replica the restored binding names. A device record already committed on the inviter side may remain, per the lost-reply posture above.

#### Scenario: Success implies the directory is caught up
- **WHEN** `link` returns success
- **THEN** the newcomer's directory replica has completed a successful sync exchange started after the import, and the device set it reads locally includes the identity's existing devices

#### Scenario: No serving window opens while the link catches up
- **WHEN** the data namespace of a linking identity receives a session from a caller the still-converging directory cannot resolve, before `link` has returned
- **THEN** the session is refused — the identity was armed before the data namespace was imported, so the namespace is never served ticket-bounded during the wait

#### Scenario: A timed-out link leaves nothing behind on the dialing node
- **WHEN** the directory cannot complete a first sync within the timeout
- **THEN** `link` fails, the identity is absent from the runtime's hosted identities and disarmed for classification, and operations addressed to it are refused as unknown — as they were before the attempt, not as storage errors against a dropped replica

#### Scenario: A failed link leaves a granted namespace of the same issuer intact
- **WHEN** a runtime reached an issuer's namespace through a peer's grant, then links into that same issuer and the link fails
- **THEN** the grant still reads that namespace's entries afterwards, and the identity is still not hosted — the rollback restored the binding it displaced instead of forgetting the issuer
