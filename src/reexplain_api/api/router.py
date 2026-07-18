from fastapi import APIRouter, Depends

from reexplain_api.api.routes.learning import router as learning_router
from reexplain_api.api.routes.pdf import router as pdf_router
from reexplain_api.security import require_service_key

api_router = APIRouter(dependencies=[Depends(require_service_key)])


@api_router.get("/health", tags=["health"])
async def authenticated_health() -> dict[str, str]:
	return {"status": "ok"}


api_router.include_router(pdf_router, prefix="/pdf", tags=["pdf"])
api_router.include_router(learning_router, prefix="/learning", tags=["learning"])
