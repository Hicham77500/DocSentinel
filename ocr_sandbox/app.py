from __future__ import annotations

from io import BytesIO
import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from pdf2image import convert_from_bytes
from PIL import Image, UnidentifiedImageError
import pytesseract


logger = logging.getLogger(__name__)

app = FastAPI(title="DocSentinel OCR Sandbox", version="0.1.0")

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
}


def _extract_from_pdf(file_bytes: bytes) -> str:
    pages = convert_from_bytes(file_bytes)
    chunks: list[str] = []
    for page in pages:
        chunks.append(pytesseract.image_to_string(page))
    return "\n".join(chunks)


def _extract_from_image(file_bytes: bytes) -> str:
    with Image.open(BytesIO(file_bytes)) as image:
        return pytesseract.image_to_string(image)


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)) -> dict[str, str]:
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    filename = file.filename or "document.bin"
    suffix = Path(filename).suffix.lower()
    content_type = file.content_type or ""
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type.",
        )

    try:
        if content_type == "application/pdf" or suffix == ".pdf":
            extracted = _extract_from_pdf(content)
        else:
            extracted = _extract_from_image(content)
    except (UnidentifiedImageError, OSError, ValueError):
        logger.exception("Failed OCR processing for file: %s", filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to process document.",
        ) from None
    except Exception:
        logger.exception("Unexpected OCR sandbox error for file: %s", filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OCR processing error.",
        ) from None

    return {"text": extracted.encode("utf-8", errors="ignore").decode("utf-8")}
