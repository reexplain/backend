from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from reexplain_api.api.routes.pdf import MAX_PDF_PAGE_COUNT
from reexplain_api.main import app

client = TestClient(app)


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
