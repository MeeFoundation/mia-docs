## Why

This is a throwaway change used to walk through the OpenSpec workflow end-to-end (propose → design → specs → tasks → apply → archive) on an otherwise empty repo. The goal is to exercise the tooling and confirm the artifact pipeline works, not to ship a real capability.

## What Changes

- Introduce a single trivial capability, `hello-page`, that defines one observable behavior: serving a static greeting page at a fixed path.
- Add a placeholder implementation file under the project root so `tasks.md` has something concrete to point at.
- No breaking changes. No migrations. No external dependencies.

## Capabilities

### New Capabilities
- `hello-page`: A single static greeting page reachable at a known URL, used as a smoke test of the docs/serve pipeline.

### Modified Capabilities
<!-- None — this is a greenfield change. -->

## Impact

- New file: `hello.html` (or equivalent) at the project root.
- No code paths, APIs, or dependencies are altered.
- Intended to be archived immediately after `/opsx:apply` to demonstrate the full lifecycle.
