from fastapi import FastAPI

from reexplain_api.api.router import api_router

app = FastAPI(
    title="ReExplain API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
