from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from reexplain_api.api.routes.pdf import MAX_PDF_PAGE_COUNT
from reexplain_api.main import app
from reexplain_api.security import require_service_key

client = TestClient(app, base_url="http://localhost")


@pytest.fixture(autouse=True)
def bypass_service_authentication():
    app.dependency_overrides[require_service_key] = lambda: None
    yield
    app.dependency_overrides.pop(require_service_key, None)


def make_pdf(page_count: int = 1) -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


def test_extract_pdf() -> None:
    response = client.post(
        "/api/v1/pdf/extract",
        files={"file": ("notes.pdf", make_pdf(), "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "filename": "notes.pdf",
        "page_count": 1,
        "text": "",
        "pages": [{"page_number": 1, "text": ""}],
    }


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
