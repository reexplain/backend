from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from pypdf import PdfReader
from pypdf.errors import PdfReadError

router = APIRouter()

PDF_CONTENT_TYPE = "application/pdf"
MAX_PDF_SIZE_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGE_COUNT = 25
READ_CHUNK_SIZE = 1024 * 1024


class ExtractedPage(BaseModel):
    page_number: int
    text: str


class ExtractedPdf(BaseModel):
    filename: str
    page_count: int
    text: str
    pages: list[ExtractedPage]


async def read_bounded_pdf(file: UploadFile) -> bytes:
    if file.content_type != PDF_CONTENT_TYPE:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported.",
        )

    chunks: list[bytes] = []
    total_size = 0

    while chunk := await file.read(READ_CHUNK_SIZE):
        total_size += len(chunk)
        if total_size > MAX_PDF_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="PDF files must be 20 MB or smaller.",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid PDF.",
        )

    return content


@router.post("/extract", response_model=ExtractedPdf)
async def extract_pdf(file: Annotated[UploadFile, File()]) -> ExtractedPdf:
    content = await read_bounded_pdf(file)

    try:
        reader = PdfReader(BytesIO(content), strict=False)
        if len(reader.pages) > MAX_PDF_PAGE_COUNT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"PDF files must contain {MAX_PDF_PAGE_COUNT} pages or fewer.",
            )
        pages = [
            ExtractedPage(page_number=index, text=(page.extract_text() or "").strip())
            for index, page in enumerate(reader.pages, start=1)
        ]
    except (PdfReadError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF could not be read.",
        ) from error

    return ExtractedPdf(
        filename=file.filename or "document.pdf",
        page_count=len(reader.pages),
        text="\n\n".join(page.text for page in pages).strip(),
        pages=pages,
    )
