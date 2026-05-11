## Context

The repository is empty apart from the `openspec/` directory; this change exists solely to walk through the OpenSpec lifecycle. There is no existing serving infrastructure, no framework, and no deployment pipeline to integrate with.

## Goals / Non-Goals

**Goals:**
- Exercise the full propose → apply → archive pipeline with one concrete artifact per stage.
- Produce a file on disk that can be opened in a browser and visibly satisfies the spec scenarios.

**Non-Goals:**
- A real web server, build system, or CI integration.
- Styling, accessibility, internationalization, or any concern beyond a single greeting string.
- Long-term maintenance — this change is expected to be archived immediately after apply.

## Decisions

- **Plain static HTML file at the project root.** A single `hello.html` is the smallest artifact that satisfies the spec. Alternatives considered: a markdown file (rejected — not directly browser-renderable without tooling), a templated page (rejected — adds dependencies for no benefit on a throwaway change).
- **No build step.** The file is hand-authored and committed as-is. A build step would obscure the OpenSpec demonstration with unrelated tooling decisions.
- **Canonical path = `/hello.html` relative to the project root.** Defined here so the spec scenarios have a concrete referent.

## Risks / Trade-offs

- [Demo artifact may be mistaken for real code] → Proposal and design both call out the throwaway intent; archive removes the change from active state once exercised.
- [Plain HTML offers no test harness] → Acceptable; the spec scenarios are observable by opening the file and visually confirming content.
