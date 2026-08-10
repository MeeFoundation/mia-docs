## ADDED Requirements

### Requirement: Internal failures stay server-side
The host SHALL log the full internal cause chain for an unrecognized failure and SHALL return a stable generic body for HTTP 500. Client-error responses SHALL expose only allow-listed messages belonging to the typed refusal or malformed request.

#### Scenario: Internal cause is not disclosed
- **WHEN** a handler returns an error with nested internal context that maps to HTTP 500
- **THEN** the client receives `internal server error` and the server log retains the complete cause chain

### Requirement: Aggregate request resources are bounded
The host SHALL limit an entry request body to 16 MiB and SHALL admit at most 16 requests concurrently across the router. A request above its body limit SHALL receive HTTP 413, and a request rejected by aggregate admission control SHALL receive HTTP 503 without entering its handler.

#### Scenario: Oversized entry is refused
- **WHEN** a caller sends an entry body larger than 16 MiB
- **THEN** the host answers HTTP 413 without invoking the data service

#### Scenario: Concurrent overload is shed
- **WHEN** 16 admitted requests remain in flight and another request arrives
- **THEN** the additional request receives HTTP 503 within a short margin and aggregate buffered work remains bounded

### Requirement: Liveness is not readiness
`GET /live` SHALL report success while the process and embedded runtime exist, without waiting for the runtime's coarse state lock. `GET /ready` SHALL perform the bounded coarse-lock check and SHALL report non-success when that check exceeds its named budget.

#### Scenario: Long operation does not fail liveness
- **WHEN** an ordinary runtime operation holds the coarse state lock beyond the readiness budget
- **THEN** `GET /live` remains successful and `GET /ready` reports non-success within the budget plus a small margin

#### Scenario: Healthy runtime is live and ready
- **WHEN** the runtime's coarse state lock is available
- **THEN** both `GET /live` and `GET /ready` return success promptly
