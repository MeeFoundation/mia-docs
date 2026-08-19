## ADDED Requirements

### Requirement: The host reads where its state lives from the environment, and requires it
The host SHALL read the runtime's storage location from `PDN_DATA_DIR` at startup and pass that directory to the runtime it embeds. The host SHALL NOT offer an in-memory mode and SHALL NOT carry a path of its own: unset, the start stops with an error naming the variable, because a host that starts without a directory promises persistence it does not provide. A directory the runtime cannot use — unwritable, or held by another running node — SHALL stop the start with an error naming it, and SHALL NOT be answered by starting in memory instead: a host that silently forgets where its state was is indistinguishable, from outside, from one that lost it.

#### Scenario: The configured directory is used
- **WHEN** the host starts with `PDN_DATA_DIR` set to a writable directory
- **THEN** the runtime stores its state there, and a host started again on the same directory serves the same node id and the same hosted identities

#### Scenario: An unset variable stops the start
- **WHEN** the host starts with `PDN_DATA_DIR` unset
- **THEN** the process exits with an error naming the variable, serving neither liveness nor the debug surface

#### Scenario: An unusable directory stops the start
- **WHEN** the host starts with `PDN_DATA_DIR` naming a directory it cannot use
- **THEN** the process exits with an error naming the directory, serving neither liveness nor the debug surface
