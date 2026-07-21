import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from reexplain_api.config import Settings, get_settings
from reexplain_api.main import app
from reexplain_api.models import (
    ConceptAssessment,
    EmbeddingResponse,
    EvidenceAssessment,
    LearningTurnRequest,
    LearningTurnResult,
    TranscriptionResponse,
)
from reexplain_api.security import require_service_key
from reexplain_api.services.openai import (
    LEARNING_INSTRUCTIONS,
    ensure_learner_evidence,
    get_openai_service,
)


class FakeOpenAIService:
    async def generate_learning_turn(self, request):
        return LearningTurnResult(
            content="Why does the author connect these two ideas?",
            interaction_type="why",
            active_concept="Causal connection",
            concepts=[
                ConceptAssessment(
                    name="Causal connection",
                    description="Explains why one claim supports another.",
                    state="developing",
                    score=45,
                )
            ],
            evidence=[],
            open_questions=[],
            understanding_score=45,
            summary="The learner is beginning to identify the causal connection.",
        )

    async def create_embeddings(self, inputs):
        return EmbeddingResponse(
            model="text-embedding-3-small",
            embeddings=[[0.0] * 1536 for _ in inputs],
        )

    async def transcribe_audio(self, filename, content, content_type):
        return TranscriptionResponse(text="Paging maps virtual to physical addresses.")


client = TestClient(app, base_url="http://localhost")


def test_learning_prompt_uses_a_learner_led_teach_back_contract() -> None:
    assert "curious AI learner being taught by the user" in LEARNING_INSTRUCTIONS
    assert "thoughtful peer" in LEARNING_INSTRUCTIONS
    assert "natural, warm, and composed" in LEARNING_INSTRUCTIONS
    assert "clear 1-2 sentence reply of at most 55 words" in LEARNING_INSTRUCTIONS
    assert "ask exactly one concise, curious question" in LEARNING_INSTRUCTIONS
    assert "checks the depth of the user's understanding" in LEARNING_INSTRUCTIONS
    assert "not a hidden exam" in LEARNING_INSTRUCTIONS
    assert "formal assessment phrases" in LEARNING_INSTRUCTIONS
    assert "one brief source-grounded corrective hint" in LEARNING_INSTRUCTIONS
    assert "learner's strengths and next weakness" in LEARNING_INSTRUCTIONS
    assert "choose one specific foundational concept" in LEARNING_INSTRUCTIONS
    assert "ask one concrete question" in LEARNING_INSTRUCTIONS
    assert "Do not ask the user to choose a topic" in LEARNING_INSTRUCTIONS
    assert "whole subject" in LEARNING_INSTRUCTIONS
    assert "no more than 5 primary, generic concepts" in LEARNING_INSTRUCTIONS
    assert "Prefer 4-5 broad, connected ideas" in LEARNING_INSTRUCTIONS
    assert "Concept names must describe general subject matter only" in LEARNING_INSTRUCTIONS
    assert "document-structure labels" in LEARNING_INSTRUCTIONS
    assert "short, crisp noun phrase of 2-6 words" in LEARNING_INSTRUCTIONS
    assert "no more than 48 characters" in LEARNING_INSTRUCTIONS
    assert "Do not use verbs, full sentences" in LEARNING_INSTRUCTIONS
    assert "self-contained subject-matter statements" in LEARNING_INSTRUCTIONS
    assert (
        "Never mention or imply a document, PDF, source, passage, excerpt"
        in LEARNING_INSTRUCTIONS
    )
    assert "Most replies should not be questions" not in LEARNING_INSTRUCTIONS


def test_learning_request_accepts_25_document_chunks() -> None:
    request = LearningTurnRequest(
        document_chunks=[f"Page {page}" for page in range(1, 26)],
        safety_identifier="a" * 32,
    )

    assert len(request.document_chunks) == 25


def test_concept_names_are_bounded_for_concise_session_and_graph_labels() -> None:
    with pytest.raises(ValidationError):
        ConceptAssessment(
            name="x" * 49,
            description="A concise description.",
            state="developing",
            score=50,
        )


def test_learner_response_always_produces_evidence() -> None:
    result = LearningTurnResult(
        content="What part of the definition is still unclear?",
        interaction_type="probe",
        active_concept="Sorting output",
        concepts=[
            ConceptAssessment(
                name="Sorting output",
                description="Defines the required sorted result.",
                state="developing",
                score=35,
            )
        ],
        evidence=[],
        open_questions=[],
        understanding_score=35,
        summary="The learner attempted to describe the output.",
    )

    updated = ensure_learner_evidence(result, "The output is [3, 2, 1].")

    assert updated.evidence == [
        EvidenceAssessment(
            concept_name="Sorting output",
            kind="uncertain",
            claim="The output is [3, 2, 1].",
            rationale=(
                "The response was recorded, but the model did not provide a specific assessment."
            ),
            strength=50,
        )
    ]


def test_versioned_api_requires_service_authentication() -> None:
    response = client.post(
        "/api/v1/learning/embeddings",
        json={"inputs": ["bounded source text"]},
    )

    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_authenticated_health_accepts_configured_service_key() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        reexplain_api_service_key="test-service-key"
    )
    try:
        response = client.get(
            "/api/v1/health",
            headers={"X-ReExplain-Service-Key": "test-service-key"},
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_preflight_allows_configured_origin() -> None:
    response = client.options(
        "/api/v1/learning/embeddings",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-reexplain-service-key",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "x-reexplain-service-key" in response.headers["access-control-allow-headers"].lower()


def test_learning_routes_return_typed_model_results() -> None:
    app.dependency_overrides[require_service_key] = lambda: None
    app.dependency_overrides[get_openai_service] = FakeOpenAIService
    try:
        turn_response = client.post(
            "/api/v1/learning/turn",
            json={
                "document_chunks": ["A cause precedes its effect."],
                "history": [],
                "learner_response": None,
                "safety_identifier": "a" * 32,
            },
        )
        embedding_response = client.post(
            "/api/v1/learning/embeddings",
            json={"inputs": ["A cause precedes its effect."]},
        )
        transcription_response = client.post(
            "/api/v1/learning/transcribe",
            files={"file": ("teaching.webm", b"recorded speech", "audio/webm")},
            data={"duration_seconds": "42"},
        )
    finally:
        app.dependency_overrides.pop(require_service_key, None)
        app.dependency_overrides.pop(get_openai_service, None)

    assert turn_response.status_code == 200
    assert turn_response.json()["interaction_type"] == "why"
    assert embedding_response.status_code == 200
    assert len(embedding_response.json()["embeddings"][0]) == 1536
    assert transcription_response.status_code == 200
    assert transcription_response.json() == {
        "text": "Paging maps virtual to physical addresses.",
        "truncated": False,
    }


def test_transcription_rejects_recordings_over_three_minutes() -> None:
    app.dependency_overrides[require_service_key] = lambda: None
    app.dependency_overrides[get_openai_service] = FakeOpenAIService
    try:
        response = client.post(
            "/api/v1/learning/transcribe",
            files={"file": ("teaching.webm", b"recorded speech", "audio/webm")},
            data={"duration_seconds": "181"},
        )
    finally:
        app.dependency_overrides.pop(require_service_key, None)
        app.dependency_overrides.pop(get_openai_service, None)

    assert response.status_code == 422
