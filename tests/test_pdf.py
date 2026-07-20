from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

import reexplain_api.api.routes.pdf as pdf_route
from reexplain_api.api.routes.pdf import MAX_PDF_PAGE_COUNT, PDF_PREVIEW_PAGE_COUNT
from reexplain_api.main import app
from reexplain_api.models import LearningMaterialAssessment
from reexplain_api.security import require_service_key
from reexplain_api.services.openai import get_openai_service

client = TestClient(app, base_url="http://localhost")


@pytest.fixture(autouse=True)
def bypass_service_authentication():
    service = FakeOpenAIService()
    app.dependency_overrides[require_service_key] = lambda: None
    app.dependency_overrides[get_openai_service] = lambda: service
    yield service
    app.dependency_overrides.pop(require_service_key, None)
    app.dependency_overrides.pop(get_openai_service, None)


class FakeOpenAIService:
    def __init__(self) -> None:
        self.assessment = LearningMaterialAssessment(
            is_learning_material=True,
            confidence=92,
            reason="The preview explains a subject in an instructional way.",
        )
        self.previews: list[str] = []

    async def assess_learning_material(self, preview: str) -> LearningMaterialAssessment:
        self.previews.append(preview)
        return self.assessment


def make_pdf(
    page_count: int = 1,
    text: str = "Photosynthesis explains energy conversion.",
) -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    for page_number in range(page_count):
        page = writer.add_blank_page(width=612, height=792)
        if page_number == 0 and text:
            font = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                }
            )
            page[NameObject("/Resources")] = DictionaryObject(
                {
                    NameObject("/Font"): DictionaryObject(
                        {NameObject("/F1"): writer._add_object(font)}
                    )
                }
            )
            stream = DecodedStreamObject()
            stream.set_data(
                f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
            )
            page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(output)
    return output.getvalue()


def test_extract_pdf(bypass_service_authentication: FakeOpenAIService) -> None:
    response = client.post(
        "/api/v1/pdf/extract",
        files={"file": ("notes.pdf", make_pdf(), "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "filename": "notes.pdf",
        "page_count": 1,
        "learning_content_confidence": 92,
        "text": "Photosynthesis explains energy conversion.",
        "pages": [{"page_number": 1, "text": "Photosynthesis explains energy conversion."}],
    }
    assert bypass_service_authentication.previews == [
        "Photosynthesis explains energy conversion."
    ]


def test_rejects_non_pdf_content_type() -> None:
    response = client.post(
        "/api/v1/pdf/extract",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 415


def test_rejects_malformed_pdf() -> None:
    response = client.post(
        "/api/v1/pdf/extract",
        files={"file": ("notes.pdf", b"%PDF-not-really", "application/pdf")},
    )

    assert response.status_code == 400


def test_accepts_pdf_at_page_limit() -> None:
    response = client.post(
        "/api/v1/pdf/extract",
        files={
            "file": (
                "notes.pdf",
                make_pdf(page_count=MAX_PDF_PAGE_COUNT),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["page_count"] == MAX_PDF_PAGE_COUNT
    assert response.json()["pages"][-1]["page_number"] == MAX_PDF_PAGE_COUNT


def test_rejects_pdf_over_page_limit() -> None:
    response = client.post(
        "/api/v1/pdf/extract",
        files={
            "file": (
                "notes.pdf",
                make_pdf(page_count=MAX_PDF_PAGE_COUNT + 1),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": f"PDF files must contain {MAX_PDF_PAGE_COUNT} pages or fewer."
    }


def test_rejects_non_learning_material_before_full_extraction(
    monkeypatch: pytest.MonkeyPatch,
    bypass_service_authentication: FakeOpenAIService,
) -> None:
    class FakePage:
        def __init__(self, text: str) -> None:
            self.text = text
            self.extraction_count = 0

        def extract_text(self) -> str:
            self.extraction_count += 1
            return self.text

    class FakeReader:
        def __init__(self) -> None:
            self.pages = [FakePage("Invoice total due: $42.00.") for _ in range(4)]

    reader = FakeReader()
    monkeypatch.setattr(pdf_route, "PdfReader", lambda *_args, **_kwargs: reader)
    bypass_service_authentication.assessment = LearningMaterialAssessment(
        is_learning_material=False,
        confidence=18,
        reason="The preview is an invoice rather than instructional content.",
    )

    response = client.post(
        "/api/v1/pdf/extract",
        files={"file": ("invoice.pdf", b"%PDF-fake", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "This PDF does not seem to contain learning material suitable for a learning "
            "session (confidence: 18%). The preview is an invoice rather than instructional "
            "content."
        )
    }
    assert [page.extraction_count for page in reader.pages] == [1, 1, 1, 0]
    assert len(bypass_service_authentication.previews) == 1
    assert PDF_PREVIEW_PAGE_COUNT == 3


def test_rejects_textless_pdf_without_calling_ai(
    bypass_service_authentication: FakeOpenAIService,
) -> None:
    response = client.post(
        "/api/v1/pdf/extract",
        files={"file": ("scan.pdf", make_pdf(text=""), "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "The PDF does not contain extractable text to assess as learning material."
    }
    assert bypass_service_authentication.previews == []
