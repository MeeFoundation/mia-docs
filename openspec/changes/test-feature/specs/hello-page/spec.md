## ADDED Requirements

### Requirement: Static greeting page

The system SHALL provide a static greeting page reachable at a known path that returns a human-readable welcome message.

#### Scenario: Page is served at the canonical path

- **WHEN** a user requests the greeting page at its canonical path
- **THEN** the system returns an HTML document containing the text `Hello, OpenSpec` and a successful response status

#### Scenario: Page content is stable across requests

- **WHEN** the same page is requested twice in succession
- **THEN** the response body is byte-identical between requests
