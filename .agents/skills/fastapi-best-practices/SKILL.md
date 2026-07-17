---
name: fastapi-best-practices
description: "Use when: creating, reviewing, or refactoring FastAPI applications, routers, dependencies, request validation, response models, configuration, and error handling in Python APIs."
---

# FastAPI Best Practices

## Structure

- Keep `main.py` limited to application construction, middleware, lifespan, and router registration.
- Group routes by domain under `api/routes`; move reusable business logic out of route functions once it has more than one caller or becomes difficult to test through HTTP.
- Use versioned API prefixes for public contracts and keep operational endpoints such as health checks outside that prefix.
- Prefer explicit absolute imports from the application package.

## Contracts

- Define Pydantic request and response models for structured bodies. Set `response_model` so OpenAPI and runtime serialization share the same contract.
- Use precise HTTP status codes and stable, user-safe error details. Do not expose tracebacks, filesystem paths, credentials, or upstream internals.
- Validate uploads by declared type, content signature, and bounded size. Treat filenames and MIME types as untrusted metadata.
- Keep async route functions non-blocking. Run unavoidable CPU-bound or blocking work in a worker/thread when it becomes large enough to affect request concurrency.

## Dependencies and Configuration

- Use FastAPI dependencies for request-scoped concerns such as authentication, database sessions, and shared validation.
- Read environment configuration through a typed settings object when configuration grows beyond a few process-level values.
- Pin compatible dependency ranges in `pyproject.toml` and commit the generated lockfile.
- Initialize shared clients during application lifespan and close them on shutdown.

## Quality

- Format and lint with Ruff; test the HTTP contract with pytest and `TestClient` or `httpx.AsyncClient`.
- Test success, validation boundaries, authorization, and mapped upstream failures.
- Keep OpenAPI enabled in development; make production exposure an explicit deployment decision.
- Add abstractions only after a concrete second use or a clear testing boundary appears.
