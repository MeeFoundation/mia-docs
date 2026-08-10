# HTTP host

## Purpose

The HTTP host for the demo stand: a thin binary embedding the [runtime core](core.md) and serving it over HTTP. One process, one embedded runtime. The HTTP surface is a host over the core, not the platform API — other hosts (mobile, wasm) embed the same core later.

## Requirements

### Requirement: The host serves liveness unconditionally
The host SHALL expose `GET /live` returning success while the embedded runtime is running, with no flag or configuration required. Container harnesses and the demo stand probe it.

#### Scenario: Liveness while running
- **WHEN** the host process is up with its embedded runtime
- **THEN** `GET /live` returns HTTP 200

### Requirement: Readiness is bounded separately
The host SHALL expose `GET /ready` as a bounded check of the runtime's coarse state lock. `GET /live` SHALL NOT wait for that lock.

#### Scenario: Lock contention affects readiness only
- **WHEN** the coarse state lock remains held beyond 2 seconds
- **THEN** `/live` returns HTTP 200 and `/ready` returns non-success within its budget

### Requirement: Debug requests have aggregate bounds
The host SHALL accept at most 16 concurrent requests and at most 16 MiB per entry body. It SHALL return HTTP 503 when concurrency admission is full and HTTP 413 for an oversized body. HTTP 500 responses SHALL use stable generic public text while retaining the full cause chain only in server logs.

#### Scenario: Overload is shed
- **WHEN** 16 requests are already admitted
- **THEN** an additional request receives HTTP 503 without entering its handler

### Requirement: The debug surface is absent by default
Debug endpoints are demo scaffolding, not platform API. The host SHALL NOT serve any route under `/debug/` unless `PDN_DEBUG=1` is set at startup; when enabled, their shape is deliberately unspecified and may change without a spec change.

#### Scenario: Debug routes off without the flag
- **WHEN** the host starts without `PDN_DEBUG` set
- **THEN** requests under `/debug/` return HTTP 404
