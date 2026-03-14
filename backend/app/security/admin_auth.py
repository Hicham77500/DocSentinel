from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status


def require_admin_token(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    expected_token = os.getenv("DOCSENTINEL_ADMIN_TOKEN", "")
    if not expected_token or not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    if not hmac.compare_digest(x_admin_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
