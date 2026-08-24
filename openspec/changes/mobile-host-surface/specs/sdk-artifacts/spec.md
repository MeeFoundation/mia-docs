# sdk: artifacts

The `pdn-sdk` repository packages the mobile facade for the platforms that install it: it generates the Swift and the Kotlin from the facade's crate, archives each with the library the platform links, and publishes releases an application names. The crate itself belongs to the `mee-pdn` workspace and is covered by that workspace's gates; what is specified here is the packaging, because an artifact is the only form in which the facade reaches a device, and a phone shows the consequences of a bad one as behaviour of the runtime.

The reason the packaging sits in a repository of its own is that producing an artifact needs Xcode and the Android NDK, which the workspace's inner loop neither has nor should acquire, and an application needs a released version it can name rather than a build tree it reaches into.

One word is used with a single meaning throughout. A *release* is a published pair of artifacts — one for Apple platforms, one for Android — together with the record of what they were built from. An artifact produced on someone's machine and handed over is not a release, and nothing below applies to it.

## ADDED Requirements

### Requirement: A release is built from one commit of the facade's crate and names it
The packaging SHALL read the facade's crate from a single commit of `mee-pdn`, SHALL build both halves of a release from that one commit, and SHALL record the commit in the release itself.

The record is what makes one class of failure diagnosable. An application built against artifacts older than the runtime it is used against calls something the facade does not export, or meets a refusal the two sides no longer mean the same thing by; the facade reports that refusal as a refusal, faithfully ([host-surface](../mobile-common/host-surface.md)), and it is the one refusal whose reason lies outside everything the person holding the phone can see. Reading the commit from the release answers it in a minute; reconstructing it from the build logs of two platforms does not.

#### Scenario: The commit is readable from the release alone
- **WHEN** a device's behaviour is questioned and the application names the release it was built against
- **THEN** that release identifies the commit of `mee-pdn` its artifacts were built from, without a build log being consulted

#### Scenario: The two halves of a release agree
- **WHEN** the Apple artifact and the Android artifact of one release are examined
- **THEN** both were built from the same commit, so a phone of one platform cannot hold a facade the phone of the other does not

### Requirement: The packaging adds nothing to the facade's surface
The packaging SHALL consist of generation and archiving alone. It SHALL NOT add an exported call, a default argument, a retry, an error translation, or a convenience wrapper of its own, and SHALL NOT carry a hand-written Swift or Kotlin source at all.

An application needing something the facade does not export is a change to [host-surface](../mobile-common/host-surface.md): the crate exports it, a release carries it, and the application names that release. A wrapper added in the packaging instead would be a host surface nobody specified, tested by neither the workspace's suites nor the application's, and drifting from the runtime it claims to speak for — the same substitution the facade itself is forbidden from making, one layer further out.

#### Scenario: A release exports what the crate exports
- **WHEN** the calls a release makes available to an application are enumerated beside the crate's exported surface
- **THEN** the two sets are the same, and no call of the packaging's own devising is among them

#### Scenario: The repository holds no source of its own
- **WHEN** the files this repository tracks are enumerated
- **THEN** they are recipes, configuration and documentation, and no Swift or Kotlin source is among them — the thin module between the bindings and the screens belongs to the application, which owns the platform shells

### Requirement: Generated bindings are build outputs and are committed nowhere
The Swift and the Kotlin the binding generator produces SHALL be produced by a recipe at build time and SHALL NOT be committed, in this repository or in the application's.

A generated file kept in a tree is a file somebody edits, and an edit there is invisible: it survives every regeneration until the day it does not, and the resulting difference between what the crate exports and what a screen calls is discovered on a device.

#### Scenario: A clean checkout carries no bindings
- **WHEN** the repository is checked out fresh
- **THEN** it holds no generated binding, and running the recipe produces them from the named commit of the crate

### Requirement: A release is built in the configuration a device installs
The packaging SHALL build the crate for a release in the product configuration [host-surface](../mobile-common/host-surface.md) requires — the runtime's test-only feature disabled — and SHALL cover every processor architecture the devices the release targets need.

The packaging SHALL fail and publish nothing rather than emit a release missing an architecture or built in another configuration. Both faults present on a device as an application that will not start or a call that is not there, at the point where the least is known about why.

#### Scenario: A missing architecture stops the release
- **WHEN** one of the targeted architectures fails to build
- **THEN** the packaging fails and no release is published, rather than one being published without that architecture

#### Scenario: What a device installs has the test-only surface absent
- **WHEN** the artifacts of a release are examined for the runtime's test-only operations
- **THEN** a forced write and an observation of a replica's contact set are absent from them, not merely unexported

### Requirement: An application consumes a release by naming it
A release SHALL be consumable by an application that names a version: linking it SHALL NOT require the crate's sources, a Rust toolchain, or a checkout of `mee-pdn`.

This is what the split of the artifacts is for. An application that had to build the crate would carry the workspace's toolchains into its own build, and the version its screens were tested against would be whatever its build tree happened to hold.

#### Scenario: A build of the application needs no Rust
- **WHEN** the application is built on a machine with the platform's own toolchain and no Rust toolchain and no `mee-pdn` checkout
- **THEN** the build succeeds against the named release, and the artifacts it links are that release's
