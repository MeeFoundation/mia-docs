# Technical Stack

The technologies each component of the project uses, one section per component. The sections follow [components](../components), and each table lists only the layers that apply to its component. "Not decided" means the component needs the layer and no choice is made.

## mee-pdn

The PDN core.

| Layer | Technology |
| --- | --- |
| **Languages and runtime** | |
| Language and toolchain | Rust |
| Async runtime | tokio |
| **Data and networking** | |
| Peer-to-peer transport | iroh, iroh-gossip, iroh-blobs |
| Sync | `pdn-store` (iroh-docs fork) |
| Storage | redb, iroh-blobs file store |
| Identity and cryptography | Ed25519, BLAKE3, KERI |
| Serialization | serde, postcard, serde_json |
| Errors | thiserror, anyhow |
| Logging | tracing |
| **Build and code quality** | |
| Package manager | Cargo |
| Workspace | Cargo workspace |
| Build | cargo |
| Task runner | just |
| Containers | Docker, Docker Compose |
| Code quality | rustfmt, Clippy, cargo-deny |
| **Testing** | |
| Test runner | cargo-nextest |
| Property-based tests | proptest |
| Container tests | testcontainers |
| Load tests | Python 3 |
| **Environment and delivery** | |
| Developer environment | Devcontainer, VS Code, rust-analyzer |
| CI | GitHub Actions |
| Dependency updates | Dependabot |
| Specs | OpenSpec |
| AI coding agents | Claude Code |

## sdk

The `pdn-mobile` facade and the `pdn-sdk` artifacts that package it. Networking, sync and storage come from `mee-pdn`.

| Layer | Technology |
| --- | --- |
| **Languages and runtime** | |
| Language and toolchain | Rust; generated Swift and Kotlin bindings |
| Async runtime | tokio |
| **Application** | |
| Framework | uniffi |
| **Data and networking** | |
| Serialization | serde_json, base64 |
| Errors | thiserror |
| Logging | tracing |
| **Build and code quality** | |
| Package manager | Cargo |
| Workspace | Cargo workspace |
| Build | cargo |
| Task runner | just |
| Code quality | rustfmt, Clippy, cargo-deny |
| **Testing** | |
| Test runner | cargo-nextest |
| **Environment and delivery** | |
| CI | GitHub Actions |
| Dependency updates | Dependabot |
| Specs | OpenSpec |
| AI coding agents | Claude Code |

## mobile-common

The shared React Native code of the Tellipod app. Networking, sync and storage come from `sdk`.

| Layer | Technology |
| --- | --- |
| **Languages and runtime** | |
| Language and toolchain | TypeScript 7, Node.js 22 |
| **Application** | |
| Framework | React Native, Expo, Expo Router |
| UI and styling | NativeWind, Tailwind design tokens, own UI kit |
| **Build and code quality** | |
| Package manager | pnpm |
| Workspace | pnpm workspaces |
| Build | Expo |
| Task runner | just |
| Code quality | Biome, tsc, knip |
| **Testing** | |
| Component catalog | Storybook |
| **Environment and delivery** | |
| Commit conventions | Conventional Commits, commitlint, Husky |
| Specs | OpenSpec |
| AI coding agents | Claude Code, Cursor |

## ios-app

What the iOS app adds to `mobile-common`.

| Layer | Technology |
| --- | --- |
| Language and toolchain | Native modules, Xcode |
| Device security | Keychain, Secure Enclave, Face ID / Touch ID |
| Build | Xcode, XCFramework |
| Developer environment | Xcode |

## android-app

What the Android app adds to `mobile-common`.

| Layer | Technology |
| --- | --- |
| Language and toolchain | Native modules, Android NDK |
| Device security | Android Keystore (TEE, StrongBox where available), BiometricPrompt |
| Build | Android NDK, Android archive |
| Developer environment | Android NDK |
