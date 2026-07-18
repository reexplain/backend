from typing import Annotated

from fastapi import APIRouter, Depends

from reexplain_api.models import (
    EmbeddingRequest,
    EmbeddingResponse,
    LearningTurnRequest,
    LearningTurnResult,
)
from reexplain_api.services.openai import OpenAIService, get_openai_service

router = APIRouter()


@router.post("/turn", response_model=LearningTurnResult)
async def generate_turn(
    request: LearningTurnRequest,
    service: Annotated[OpenAIService, Depends(get_openai_service)],
) -> LearningTurnResult:
    return await service.generate_learning_turn(request)


@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(
    request: EmbeddingRequest,
    service: Annotated[OpenAIService, Depends(get_openai_service)],
) -> EmbeddingResponse:
    return await service.create_embeddings(request.inputs)