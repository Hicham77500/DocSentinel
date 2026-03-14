from __future__ import annotations

import json
import logging
import mimetypes
from pathlib import Path
import urllib.error
import urllib.request
import uuid


logger = logging.getLogger(__name__)
OCR_SANDBOX_URL = "http://ocr-sandbox:8080/ocr"
OCR_TIMEOUT_SECONDS = 10.0


def _guess_content_type(file_path: Path) -> str:
    guessed, _ = mimetypes.guess_type(file_path.name)
    if guessed:
        return guessed
    return "application/octet-stream"


def _build_multipart_payload(
    file_name: str,
    content_type: str,
    file_bytes: bytes,
    boundary: str,
) -> bytes:
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    footer = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return header + file_bytes + footer


def _extract_from_sandbox(file_path: Path, file_bytes: bytes) -> str:
    boundary = f"docsentinel-{uuid.uuid4().hex}"
    content_type = _guess_content_type(file_path)
    payload = _build_multipart_payload(
        file_name=file_path.name,
        content_type=content_type,
        file_bytes=file_bytes,
        boundary=boundary,
    )

    request = urllib.request.Request(
        OCR_SANDBOX_URL,
        data=payload,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=OCR_TIMEOUT_SECONDS) as response:
        response_body = response.read()

    parsed = json.loads(response_body.decode("utf-8"))
    text = parsed.get("text", "")
    if isinstance(text, str):
        return text
    return ""


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        logger.error("OCR input path does not exist or is not a file: %s", file_path)
        return ""

    try:
        file_bytes = path.read_bytes()
        extracted = _extract_from_sandbox(path, file_bytes)
        return extracted.encode("utf-8", errors="ignore").decode("utf-8")
    except urllib.error.HTTPError:
        logger.exception("OCR sandbox returned an HTTP error for file: %s", file_path)
        return ""
    except urllib.error.URLError:
        logger.exception("Failed to reach OCR sandbox for file: %s", file_path)
        return ""
    except TimeoutError:
        logger.exception("Timeout while calling OCR sandbox for file: %s", file_path)
        return ""
    except json.JSONDecodeError:
        logger.exception("Invalid OCR sandbox response for file: %s", file_path)
        return ""
    except Exception:
        logger.exception("Unexpected OCR error for file: %s", file_path)
        return ""
