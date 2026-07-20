from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from reexplain_api.models import (
    EmbeddingRequest,
    EmbeddingResponse,
    LearningTurnRequest,
    LearningTurnResult,
    TranscriptionResponse,
)
from reexplain_api.services.openai import OpenAIService, get_openai_service

router = APIRouter()

MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024
MAX_AUDIO_DURATION_SECONDS = 180
READ_CHUNK_SIZE = 1024 * 1024
SUPPORTED_AUDIO_TYPES = {
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "audio/x-m4a",
}


async def read_bounded_audio(file: UploadFile) -> bytes:
    content_type = (file.content_type or "").split(";", maxsplit=1)[0]
    if content_type not in SUPPORTED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The recording format is not supported.",
        )

    chunks: list[bytes] = []
    total_size = 0
    while chunk := await file.read(READ_CHUNK_SIZE):
        total_size += len(chunk)
        if total_size > MAX_AUDIO_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Voice recordings must be 10 MB or smaller.",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The voice recording is empty.",
        )
    return content


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


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: Annotated[UploadFile, File()],
    duration_seconds: Annotated[float, Form(gt=0, le=MAX_AUDIO_DURATION_SECONDS)],
    service: Annotated[OpenAIService, Depends(get_openai_service)],
) -> TranscriptionResponse:
    del duration_seconds
    content = await read_bounded_audio(file)
    return await service.transcribe_audio(
        file.filename or "recording.webm",
        content,
        (file.content_type or "audio/webm").split(";", maxsplit=1)[0],
    )