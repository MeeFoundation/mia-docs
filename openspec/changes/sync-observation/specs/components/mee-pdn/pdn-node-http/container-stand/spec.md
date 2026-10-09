# Container stand

## MODIFIED Requirements

### Requirement: Convergence is waited for at the runtime's own cadence
A scenario SHALL wait for convergence by repeating a read, bounded by a budget above the runtime's periodic reconciliation interval. No route, environment variable, or harness call SHALL force a reconciliation, and no scenario SHALL shorten the runtime's cadence, through the host's pod interval setting or otherwise.

**Example:** Bob waits to read `contact/email` under Alice; `<alice>` and `<bob>` are their identities in hex.

| part | what it does |
|---|---|
| the runtime reconciles | every 10 s, its default, which nothing on the stand shortens; each pod store every 300 s, with `PDN_POD_RECONCILE_INTERVAL_SECS` unset on every container |
| the scenario reads | every 100 ms: 409 until the namespace is bound, 404 until the entry arrives, then 200 |
| its budget | 2 min, 12 reconciliation intervals |
| on expiry | `"contact/email under <alice> never read back as expected for <bob>"`, the last answer, the node's log tail |

#### Scenario: A wait ends when the value arrives
- **WHEN** a scenario waits for a value written on another container
- **THEN** it repeats the read until the value appears or its budget expires, and a failed wait names what it waited for

## ADDED Requirements

### Requirement: The stand's image carries no observation surface, and a second image does
The stand's image SHALL be built without the host's observation feature, and the image build SHALL take the features to enable as a build argument that is empty by default. The container suite SHALL build a second image with the observation feature, in the release profile as the stand's image is, and SHALL run against it only the scenarios of the observation routes, beside a scenario asserting that the stand's image serves none of them.

**Example:**

| image | built with | used by |
|---|---|---|
| the stand's image | no feature | every scenario of the stand, the live demos, and the observation routes' absence |
| the observation image | `FEATURES=observation` | the observation routes' scenarios |

#### Scenario: The stand's image has no observation routes
- **WHEN** a container starts from the stand's image with the debug surface enabled
- **THEN** requests to the observation routes return HTTP 404, and its status states `observation off`

#### Scenario: The observation image serves them
- **WHEN** a container starts from the observation image with the debug surface enabled
- **THEN** the observation routes answer, its status states `profile release` and `observation on`, and every other route answers as on the stand's image
