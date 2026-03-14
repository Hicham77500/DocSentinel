from __future__ import annotations

import hashlib
import secrets


def generate_api_key() -> str:
    return secrets.token_urlsafe(48)


def hash_api_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
