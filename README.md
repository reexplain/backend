# ReExplain API

FastAPI service for document processing.

## Development

```bash
uv sync
uv run uvicorn reexplain_api.main:app --app-dir src --reload
```

The API is available at `http://127.0.0.1:8000`, with OpenAPI docs at `/docs`.

## Checks

```bash
uv run ruff check .
uv run pytest
```
