## ADDED Requirements

### Requirement: The inviting runtime answers what became of a pod invite it minted

The pods service SHALL answer, for a hosted identity and a pod invite, what became of the invite's secret on this runtime: pending while it is unpresented and its lifetime runs; expired once its lifetime ended unpresented; burned once a presentation verified and burned it, until the serving half of that join hands the newcomer both stores' write tickets; used, naming the joiner's `PdnId`, from then on; and unknown for a secret this runtime does not hold for that identity and the pod the invite names — never minted here, minted for another identity of this runtime or into another pod, swept after its lifetime, or minted before the runtime last started. An identity this runtime does not host SHALL be refused as unknown, as every pods operation refuses it. The answer SHALL be read alone: asking writes nothing, and a presentation before or after the question is verified, burned and refused exactly as without it, so a refused presentation leaves a pending invite pending. A presentation by an identity the pod already lists, which writes no joined event and hands both tickets over again, SHALL mark the invite used by that member as a first join does. A serving half cut short once the secret burned — a storage failure, a refused offer, a connection lost before the tickets went out — SHALL leave the invite burned. An invite's state SHALL be kept while its lifetime runs; once it has ended, an invite never presented reads expired, one presented keeps reading burned or used, and the next pod invite this runtime mints sweeps it, after which it reads unknown.

**Example:** Bob's phone b1 mints two invites to "Family" as Bob at 10:00, the first with a 10-minute lifetime, the second with 2 minutes, and asks `invite_state` about them as the day goes on.

| at | what happened | the first invite reads | the second invite reads |
|---|---|---|---|
| 10:01 | nothing yet | pending | pending |
| 10:02 | Carol's phone c1 presented the first; b1 burned it and is writing Carol's joined event | burned | pending |
| 10:02 | b1 handed c1 both stores' write tickets | used by Carol | pending |
| 10:03 | | used by Carol | expired |
| 10:03 | asked as another identity b1 hosts | unknown | unknown |
| 10:04 | b1 restarted | unknown | unknown |

#### Scenario: A served join marks the invite used by the joiner

- **WHEN** a member mints two invites, and a hosted identity on another runtime joins with the first
- **THEN** the first reads pending before the join and used by the joiner's `PdnId` once the join returned, and the second reads pending throughout

#### Scenario: A join cut short after the burn leaves the invite burned

- **WHEN** the inviter's write of the joined event fails once the secret burned
- **THEN** the invite reads burned, and a later invite the newcomer joins with reads used by it

#### Scenario: A refused presentation leaves a pending invite pending

- **WHEN** a dialer presents a secret that was never minted while an invite is pending
- **THEN** the pending invite still reads pending, and the dialer's secret reads unknown

#### Scenario: A member whose join lost the reply is named by the second invite

- **WHEN** the connection drops after the inviter wrote newcomer C's joined event and before its reply reached C, and C then presents a second invite
- **THEN** the first invite reads burned and the second used by C

#### Scenario: Between two identities of one node the invite is answered for its own identity alone

- **WHEN** a hosted identity invites and a co-located identity joins with the invite inside the process
- **THEN** the inviting identity reads the invite used by the co-located one, and the co-located identity asking about the same invite reads unknown

#### Scenario: An invite never presented reads expired after its lifetime

- **WHEN** an invite minted with a lifetime of 1 second is asked about 2 seconds later, and again after a further invite was minted
- **THEN** it reads expired the first time and unknown the second

#### Scenario: A restart forgets every invite's state

- **WHEN** an invite was used, and the inviting runtime stops and starts again on its directory
- **THEN** the invite reads unknown
