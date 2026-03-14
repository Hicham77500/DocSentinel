from __future__ import annotations

import hashlib


def compute_sha256(file_bytes: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(memoryview(file_bytes))
    return hasher.hexdigest()
