from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class LearningMaterialAssessment(BaseModel):
    is_learning_material: bool
    confidence: int = Field(ge=0, le=100)
    reason: str = Field(min_length=1, max_length=300)


class LearningHistoryTurn(BaseModel):
    role: Literal["learner", "assistant"]
    content: str = Field(min_length=1, max_length=10_000)


class LearningTurnRequest(BaseModel):
    document_chunks: list[str] = Field(min_length=1, max_length=100)
    history: list[LearningHistoryTurn] = Field(default_factory=list, max_length=40)
    learner_response: str | None = Field(default=None, max_length=4_000)
    safety_identifier: str = Field(min_length=16, max_length=64, pattern=r"^[a-f0-9]+$")

    @field_validator("document_chunks")
    @classmethod
    def validate_chunks(cls, chunks: list[str]) -> list[str]:
        cleaned = [chunk.strip() for chunk in chunks if chunk.strip()]
        if not cleaned or sum(len(chunk) for chunk in cleaned) > 80_000:
            raise ValueError("Document context must contain between 1 and 80,000 characters.")
        return cleaned

    @model_validator(mode="after")
    def validate_history_size(self) -> "LearningTurnRequest":
        if sum(len(turn.content) for turn in self.history) > 60_000:
            raise ValueError("Session history is too large.")
        return self


class ConceptAssessment(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    state: Literal["unexplored", "developing", "demonstrated"]
    score: int = Field(ge=0, le=100)


class EvidenceAssessment(BaseModel):
    concept_name: str = Field(min_length=1, max_length=120)
    kind: Literal["supports", "contradicts", "uncertain"]
    claim: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=500)
    strength: int = Field(ge=0, le=100)


class OpenQuestionAssessment(BaseModel):
    concept_name: str | None = Field(default=None, max_length=120)
    text: str = Field(min_length=1, max_length=500)
    priority: int = Field(ge=0, le=100)


class LearningTurnResult(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=4_000,
        description=(
            "A natural 1-2 sentence reply from an attentive AI learner that briefly reflects "
            "what it understood and asks one concrete, curious question."
        ),
    )
    interaction_type: Literal["explain", "probe", "why", "connect", "apply", "challenge"] = (
        Field(description="The diagnostic mode used internally; not a quiz instruction.")
    )
    active_concept: str = Field(min_length=1, max_length=120)
    concepts: list[ConceptAssessment] = Field(min_length=1, max_length=12)
    evidence: list[EvidenceAssessment] = Field(default_factory=list, max_length=20)
    open_questions: list[OpenQuestionAssessment] = Field(default_factory=list, max_length=10)
    understanding_score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1, max_length=1_500)


class EmbeddingRequest(BaseModel):
    inputs: list[str] = Field(min_length=1, max_length=100)

    @field_validator("inputs")
    @classmethod
    def validate_inputs(cls, inputs: list[str]) -> list[str]:
        cleaned = [value.strip() for value in inputs]
        if any(not value or len(value) > 32_000 for value in cleaned):
            raise ValueError("Embedding inputs must contain between 1 and 32,000 characters.")
        if sum(len(value) for value in cleaned) > 200_000:
            raise ValueError("Embedding batch is too large.")
        return cleaned


class EmbeddingResponse(BaseModel):
    model: str
    embeddings: list[list[float]]


class TranscriptionResponse(BaseModel):
    text: str = Field(min_length=1, max_length=4_000)
    truncated: bool = False
