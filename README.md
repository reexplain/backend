# ReExplain API

The private FastAPI service for ReExplain. It validates and extracts PDF text, creates embeddings, and generates structured active-learning questions with OpenAI.

The browser does not call this service directly. Next.js authenticates the user and calls `/api/v1` with a shared service key.

## Stack

- FastAPI and Python 3.12
- pypdf for PDF extraction
- OpenAI for questions and embeddings
- Pydantic Settings for environment configuration

The default models are `gpt-5.4` for learning questions and `text-embedding-3-small` for 1536-dimensional embeddings.

## Setup

Install dependencies and create the environment file:

```bash
uv sync
cp .env.example .env.local
```

Fill in `.env.local`. Important values are:

- `OPENAI_API_KEY`
- `REEXPLAIN_API_SERVICE_KEY`: generate with `openssl rand -hex 32`
- `REEXPLAIN_ALLOWED_ORIGINS`: comma-separated web origins
- `REEXPLAIN_ALLOWED_HOSTS`: comma-separated trusted hosts

Use the same `REEXPLAIN_API_SERVICE_KEY` value in the web app.

## Development

```bash
uv run uvicorn reexplain_api.main:app --app-dir src --reload
```

The API is available at `http://127.0.0.1:8000`. Health is at `/health` and OpenAPI docs are at `/docs`.

## API

```text
POST /api/v1/pdf/extract          Validate and extract a PDF
POST /api/v1/learning/embeddings  Create document embeddings
POST /api/v1/learning/turn        Generate the next learning turn
GET  /api/v1/health               Check service-key authentication
GET  /health                      Check service health
```

PDF uploads are limited to 20 MiB and 25 pages. Learning payloads and model output are validated and bounded.

Verify the service key locally without uploading a PDF:

```bash
curl -H "X-ReExplain-Service-Key: $REEXPLAIN_API_SERVICE_KEY" \
	http://127.0.0.1:8000/api/v1/health
```

## Structure

```text
src/reexplain_api/
	api/         API routers and endpoints
	services/    OpenAI integration
	config.py    Typed environment settings
	models.py    Request and response models
	security.py  Service-key authentication
	main.py      FastAPI app and middleware
tests/         API and security tests
```

## Checks

```bash
uv run ruff check src tests
uv run pytest
```

## Docker

Build and run the same container used by Cloud Run:

```bash
docker build -t reexplain-api .
docker run --rm -p 8080:8080 \
	--env-file .env.local \
	-e REEXPLAIN_ALLOWED_HOSTS=localhost,127.0.0.1 \
	reexplain-api
curl http://localhost:8080/health
```

The image runs as a non-root user, installs only locked production dependencies, and listens on Cloud Run's `PORT` environment variable. Local environment files are excluded from the build context.

## Google Cloud Run

From the `backend` directory, deploy directly from the Dockerfile:

```bash
gcloud run deploy reexplain-api \
	--source . \
	--region us-central1 \
	--allow-unauthenticated \
	--set-env-vars 'REEXPLAIN_ALLOWED_HOSTS=*.run.app' \
	--set-env-vars 'REEXPLAIN_ALLOWED_ORIGINS=https://YOUR_WEB_APP_DOMAIN' \
	--set-env-vars 'REEXPLAIN_QUESTION_MODEL=gpt-5.4,REEXPLAIN_EMBEDDING_MODEL=text-embedding-3-small' \
	--set-secrets 'OPENAI_API_KEY=OPENAI_API_KEY:latest,REEXPLAIN_API_SERVICE_KEY=REEXPLAIN_API_SERVICE_KEY:latest'
```

Create the two Secret Manager secrets before deploying, and grant the Cloud Run runtime service account `Secret Manager Secret Accessor`. Keep `--allow-unauthenticated` because application requests are authenticated with `X-ReExplain-Service-Key`; the health endpoint remains available for platform probes.

After deployment, set the web app's `REEXPLAIN_API_URL` to the Cloud Run service URL and keep its `REEXPLAIN_API_SERVICE_KEY` synchronized with the Secret Manager value.
