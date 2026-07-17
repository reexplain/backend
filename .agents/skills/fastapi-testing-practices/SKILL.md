---
name: fastapi-testing-practices
description: "Use when: writing or reviewing pytest coverage for FastAPI routes, dependency overrides, uploads, authentication, database boundaries, and API error responses."
---

# FastAPI Testing Practices

## Test Through the Contract

- Exercise routes through `TestClient` for synchronous tests or `httpx.AsyncClient` with ASGI transport for async tests.
- Assert status code and the smallest stable response body that proves behavior. Avoid snapshots of unrelated headers or generated OpenAPI details.
- Build valid binary fixtures with the format's real library instead of hard-coded pseudo-files.
- Cover accepted input, each meaningful validation boundary, malformed content, and upstream error mapping.

## Isolate Boundaries

- Override FastAPI dependencies for authentication, database sessions, clocks, and external services; clear overrides after each test.
- Mock at the network or repository boundary, not inside the behavior under test.
- Use temporary directories and transaction rollback for filesystem and database isolation.
- Keep unit tests deterministic: no real network, shared mutable state, or dependence on execution order.

## Async and Lifespan

- Use async tests when behavior depends on cancellation, concurrency, streaming, or async clients.
- Run application lifespan in tests when startup-created resources are part of the route contract.
- Test cleanup and failure paths for uploaded files, streams, transactions, and background work.

## Verification

- Run the narrow route test first, then the full suite and Ruff.
- Treat warnings from application code as failures to investigate; do not silence them globally without a documented reason.
- Keep fixtures close to the tests that own them until reuse is demonstrated.
