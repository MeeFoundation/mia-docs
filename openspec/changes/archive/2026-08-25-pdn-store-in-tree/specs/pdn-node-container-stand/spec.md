# pdn-node: container stand

The store is a crate of the workspace, so the image build has no fork to resolve from a checkout beside the workspace and no cargo configuration to carry for it. The build's inputs are the workspace's manifests, its lock file, and its crates; nothing else reaches the image, and nothing outside version control can change what it runs.

## MODIFIED Requirements

### Requirement: The image carries the workspace as it resolves
The image SHALL be built from the workspace alone — its manifests, its lock file, and its crates, the store among them — and no input outside version control SHALL reach the build: a cargo configuration file beside the workspace is not carried, and no stage of the build reaches for a checkout beside it.

#### Scenario: A store edit reaches the image
- **WHEN** a source file under `crates/pdn-store` is edited and the image is rebuilt
- **THEN** the containers run that edit, and no step of the build refuses the resolution or reaches outside the build context

#### Scenario: A cargo configuration beside the workspace stays out
- **WHEN** a `.cargo/config.toml` exists beside the workspace and the build context is listed
- **THEN** the listing carries no `.cargo` entry
