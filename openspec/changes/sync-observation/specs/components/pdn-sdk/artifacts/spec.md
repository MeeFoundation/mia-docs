# sdk: artifacts

## ADDED Requirements

### Requirement: A test build is packaged apart from every release
The packaging SHALL build, on request, artifacts of the facade with its observation feature enabled, for the sync tests, in the same release configuration a release is built in. Such an artifact SHALL be named as a test build together with the commit it packages, SHALL NOT be published as a release, and SHALL NOT be named by the application's release build. A release SHALL stay built as the requirement on the configuration a device installs states.

**Example:**

| artifact | observation | configuration | recorded under `build/release/` | named by |
|---|---|---|---|---|
| a release `V`, from `just release V` | off | release | yes, `build/release/V/release.json` | the application's release build |
| a test build of the checked-out commit | on | release | no | the application's test build, on the tester's machine |

#### Scenario: A test build is never a release
- **WHEN** a test build is produced
- **THEN** it carries the observation calls, it is built in the release configuration, its name says it is a test build, and no release lists it

#### Scenario: A release is unchanged by the test build's existence
- **WHEN** a release is built after a test build of the same commit
- **THEN** the release's artifacts carry no observation call
