# pdn-node: device linking — delta for identity-scoped-replicas

## MODIFIED Requirements

### Requirement: Link returns caught up, and failure leaves no local residue
`link` SHALL NOT report success until the imported directory has completed one successful sync exchange that started after the import — one bounded wait against the peer that just answered the dialogue, not a retry loop; a directory that cannot catch up within the caller's timeout SHALL surface as an error, not a hang. The property waited on is a completed session, not arrived content: a runtime that never synced and one that synced and found nothing new must not be confused, so polling the directory's contents does not discharge this requirement.

The caller's timeout SHALL bound the whole act, the dialogue included: the dialogue spends from the budget first and the catch-up gets what remains, so a dialed inviter that never answers costs the caller its budget — surfaced as its own typed outcome — and never the transport's idle timeout. Without this bound the budget would govern only the last third of the act, and a hung inviter would hold the caller for as long as the transport tolerates a silent connection, however small a budget the caller named.

The dialing runtime SHALL arm the identity for session classification the moment its directory is imported, before the data namespace is imported — so at no instant does the data binding exist ahead of the book that judges its sessions. A data replica no records can judge refuses every session ([multi-identity](../../data-layer/multi-identity/spec.md)), so the other order opens no serving window either; what it costs is the data namespace's first sessions, refused while nothing judges them and retried by nothing before the node's next reconcile pass. The cost of arming early is bounded and fail-closed: while the directory is still converging, callers it cannot yet resolve are refused, and a refused device is served once its record replicates in — the node's periodic reconcile pass is the retry cadence.

On any failure after import, the dialing runtime SHALL undo what this linking did, in reverse order — the data-namespace import, the arming, the directory — so a failed link leaves no local residue and the identity is unknown to the runtime again. The link brings up stores of its own for the identity it joins, so the undo drops what it brought up and reaches nothing else: a namespace of that same issuer which another identity of this node holds under a grant is held for that identity and is untouched by this rollback. The emptied store the undo leaves, and the subdirectory holding it, MAY remain; a start SHALL host nothing from a subdirectory the runtime's record of hosted identities does not name. A device record already committed on the inviter side may remain, per the lost-reply posture above.

#### Scenario: Success implies the directory is caught up
- **WHEN** `link` returns success
- **THEN** the newcomer's directory replica has completed a successful sync exchange started after the import, and the device set it reads locally includes the identity's existing devices

#### Scenario: No serving window opens while the link catches up
- **WHEN** the data namespace of a linking identity receives a session from a caller the still-converging directory cannot resolve, before `link` has returned
- **THEN** the session is refused — the identity was armed before the data namespace was imported, so no session reaches the namespace ahead of the book that judges it

#### Scenario: A timed-out link leaves nothing behind on the dialing node
- **WHEN** the directory cannot complete a first sync within the timeout
- **THEN** `link` fails, the identity is absent from the runtime's hosted identities and disarmed for classification, and operations addressed to it are refused as unknown — as they were before the attempt, not as storage errors against a dropped replica

#### Scenario: A failed link leaves a granted namespace of the same issuer intact
- **WHEN** a runtime reached an issuer's namespace through a peer's grant, then links into that same issuer and the link fails
- **THEN** the grant still reads that namespace's entries afterwards, and the identity is still not hosted — the two replicas are held for two identities, and the rollback reaches only the one the link brought up

#### Scenario: A start hosts nothing from what a failed link left
- **WHEN** a link fails after its import and the runtime is restarted on the same directory
- **THEN** the identity is not hosted, nothing of it is readable, and the subdirectory the failed link created carries no identity into the hosted set
