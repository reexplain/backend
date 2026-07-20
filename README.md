# ReExplain - Backend

ReExplain is an AI-powered teach-back learning app built around a simple question: what do you actually understand after studying something? Instead of summarising a PDF or presenting a fixed quiz, it asks the learner to explain concepts in their own words. The AI takes the role of a curious learner, reflecting what it understood, pointing out what remains unclear, and asking the learner to take the explanation further.

This private FastAPI service powers that learning loop. It handles PDF extraction, learning-material checks, voice transcription, structured GPT-5.6 learning turns, and embeddings. The browser never calls it directly; the Next.js app authenticates the learner first and sends requests with a shared service key.

> **Judge highlight:** This service turns GPT-5.6 output into safe, typed learning data. Codex accelerated the prompt, contract, and test work described in [How Codex accelerated development](#how-codex-accelerated-development).

## Why this service exists

Keeping file and AI work in a small backend service gives the product a clear security boundary:

- The browser never receives the OpenAI key or the backend service key.
- PDF and audio validation happens before expensive model calls.
- Model responses are checked against Pydantic schemas before they reach the web app.
- The web app can focus on the learning experience while this service owns extraction and AI integration.

## What it does

| Capability | What happens |
| --- | --- |
| PDF extraction | Validates the file, limits size and pages, extracts text with `pypdf`, and checks whether the material is suitable for learning. |
| Learning turn generation | Uses GPT-5.6 to return a typed AI-learner reply, concepts, evidence, gaps, score, and summary. |
| Embeddings | Produces 1536-dimensional embeddings for discussed concepts so the web app can merge related mastery concepts and draw graph edges. |
| Voice transcription | Validates a recorded response and transcribes it before the learner reviews and submits the text. |

## GPT-5.6 learning contract

The default learning model is configured by `REEXPLAIN_QUESTION_MODEL` (`gpt-5.6-luna` in local development). It is prompted to be a curious learner, not a conventional quiz engine.

For each turn, the model must return structured data that the web app can save safely:

- a concise 2–4 sentence response that reflects what it understood;
- a small set of distinct concepts and one active concept;
- evidence marked as support, contradiction, or uncertainty;
- open questions that guide a future explanation;
- a score and a plain factual summary for resuming the session.

The prompt explicitly rejects document-structure labels such as chapter, section, exercise, figure, page, and numbered problem names. Concept descriptions are limited to short, stand-alone statements so the dashboard can generate crisp practice activities from the learner's discussion.

## Key design decisions

| Decision | Reason |
| --- | --- |
| FastAPI + Pydantic models | Requests and AI responses have explicit, testable contracts. |
| Private versioned routes | The Next.js server is the application boundary; the browser does not call the service directly. |
| GPT-5.6 structured output | The UI can render evidence and mastery information without brittle text parsing. |
| Embeddings in a separate endpoint | The same compact API can support both document and concept similarity work. |
| Bounded uploads and payloads | Resource limits protect the service from oversized files and prompts. |
| Typed upstream error mapping | Clients receive stable, safe messages rather than provider internals. |

## How Codex accelerated development

Codex was used as an implementation and testing partner for the service and its integration points. It accelerated:

- shaping the typed FastAPI request and response contracts;
- refining the GPT-5.6 teach-back prompt so concepts are general, concise, and suitable for practice;
- adding prompt-focused and HTTP-contract tests;
- checking upload, transcription, model-output, and service-key boundaries;
- keeping the FastAPI code aligned with the Next.js session and mastery workflows.

The product decisions were intentional: use a learner-led teaching flow, keep AI calls private, validate every boundary, and return structured data that can improve practice and mastery over time.

## Technology

- Python 3.12
- FastAPI and Uvicorn
- Pydantic and Pydantic Settings
- `pypdf` for PDF parsing
- OpenAI APIs
- `uv` for dependency and environment management
- Pytest and Ruff

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- An OpenAI API key

## Local setup

Install the locked dependencies and create a local environment file:

```bash
uv sync
cp .env.example .env.local
```

Configure `.env.local`:

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI credential. Keep it server-only. |
| `REEXPLAIN_API_SERVICE_KEY` | Shared secret expected from Next.js in `X-ReExplain-Service-Key`. Generate with `openssl rand -hex 32`. |
| `REEXPLAIN_ALLOWED_ORIGINS` | Comma-separated web origins, for example `http://localhost:3000`. |
| `REEXPLAIN_ALLOWED_HOSTS` | Comma-separated hosts trusted by the service. |
| `REEXPLAIN_QUESTION_MODEL` | Learning-turn model; defaults to `gpt-5.6-luna`. |
| `REEXPLAIN_EMBEDDING_MODEL` | Embedding model; defaults to `text-embedding-3-small`. |
| `REEXPLAIN_TRANSCRIPTION_MODEL` | Transcription model; defaults to `gpt-4o-mini-transcribe`. |

Set the same service-key value in `web/.env.local` as `REEXPLAIN_API_SERVICE_KEY`.

## Run locally

```bash
uv run uvicorn reexplain_api.main:app --app-dir src --reload
```

The service runs at [http://127.0.0.1:8000](http://127.0.0.1:8000).

- Health probe: `GET /health`
- Authenticated health check: `GET /api/v1/health`
- Interactive API docs in development: `/docs`

## API reference

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/pdf/extract` | Validate and extract an uploaded PDF. |
| `POST` | `/api/v1/learning/turn` | Generate the next structured teach-back turn. |
| `POST` | `/api/v1/learning/embeddings` | Create embeddings for concepts or text. |
| `POST` | `/api/v1/learning/transcribe` | Transcribe a recorded response. |
| `GET` | `/api/v1/health` | Verify service-key authentication. |
| `GET` | `/health` | Public process health probe. |

All `/api/v1` routes require `X-ReExplain-Service-Key`, except browser access is normally prevented by the web app architecture. The web app makes these requests server-to-server.

## Limits and safeguards

- PDFs: PDF content type, PDF signature, 20 MiB maximum, and 25 pages maximum.
- Learning context: bounded document chunks, conversation history, and learner input.
- Voice files: supported audio types, 10 MiB maximum, and bounded duration validation.
- Embedding input: bounded item count, item length, and total batch size.
- Model responses: parsed into Pydantic models; invalid output is rejected instead of being passed to the UI.
- Upstream failures: mapped to stable HTTP errors without exposing provider details or secrets.

Test the configured service key without uploading a file:

```bash
curl -H "X-ReExplain-Service-Key: $REEXPLAIN_API_SERVICE_KEY" \
  http://127.0.0.1:8000/api/v1/health
```

## Project structure

```text
src/reexplain_api/
  api/         Versioned routes and health endpoints
  services/    OpenAI and PDF-related business logic
  config.py    Typed settings and environment loading
  models.py    Pydantic request and response contracts
  security.py  Service-key authentication
  main.py      App creation, middleware, and router registration
tests/         API, prompt, and security tests
```

## Quality checks

```bash
uv run ruff check src tests
uv run pytest
```

## Docker

Build and run the same container layout used by Cloud Run:

```bash
docker build -t reexplain-api .
docker run --rm -p 8080:8080 \
  --env-file .env.local \
  -e REEXPLAIN_ALLOWED_HOSTS=localhost,127.0.0.1 \
  reexplain-api
curl http://localhost:8080/health
```

The image runs as a non-root user, installs locked production dependencies, and listens on Cloud Run's `PORT` environment variable. Local environment files are excluded from the build context.

## Google Cloud Run

From the `backend` directory, deploy from the Dockerfile:

```bash
gcloud run deploy reexplain-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars 'REEXPLAIN_ALLOWED_HOSTS=*.run.app' \
  --set-env-vars 'REEXPLAIN_ALLOWED_ORIGINS=https://YOUR_WEB_APP_DOMAIN' \
  --set-env-vars 'REEXPLAIN_QUESTION_MODEL=gpt-5.6-luna,REEXPLAIN_EMBEDDING_MODEL=text-embedding-3-small' \
  --set-secrets 'OPENAI_API_KEY=OPENAI_API_KEY:latest,REEXPLAIN_API_SERVICE_KEY=REEXPLAIN_API_SERVICE_KEY:latest'
```

Create the two Secret Manager secrets first and grant the Cloud Run runtime service account `Secret Manager Secret Accessor`. `--allow-unauthenticated` is used for platform health probes; application routes still require `X-ReExplain-Service-Key`.

After deployment, set `REEXPLAIN_API_URL` in the web app to the Cloud Run URL and keep `REEXPLAIN_API_SERVICE_KEY` synchronized with Secret Manager.
