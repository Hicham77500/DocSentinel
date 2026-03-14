from __future__ import annotations

import os

from fastapi import HTTPException, status
import clamd


def scan_file(file_bytes: bytes) -> None:
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    host = os.getenv("CLAMD_HOST", "127.0.0.1")
    port = int(os.getenv("CLAMD_PORT", "3310"))

    try:
        client = clamd.ClamdNetworkSocket(host=host, port=port)
        client.ping()
        result = client.instream(file_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Antivirus service unavailable: {exc}",
        ) from exc

    status_value = None
    signature = None
    if isinstance(result, dict):
        payload = result.get("stream")
        if isinstance(payload, tuple) and len(payload) >= 2:
            status_value, signature = payload[0], payload[1]

    if status_value == "FOUND":
        detail = "Malware detected."
        if signature:
            detail = f"Malware detected: {signature}"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

    if status_value not in {"OK", None}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Antivirus scan failed.",
        )
