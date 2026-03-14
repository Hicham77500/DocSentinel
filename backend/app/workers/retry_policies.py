from __future__ import annotations


MAX_RETRIES = 5
INITIAL_BACKOFF = 2
MAX_BACKOFF = 60


def compute_backoff(retries: int) -> int:
    if retries < 0:
        retries = 0
    delay = INITIAL_BACKOFF ** retries
    return min(delay, MAX_BACKOFF)
