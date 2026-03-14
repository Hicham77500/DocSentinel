from dataclasses import dataclass
from functools import lru_cache
import os


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    DATABASE_URL: str
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool
    MINIO_RAW_BUCKET: str
    DOCSENTINEL_API_KEY: str
    BILLING_PROVIDER: str
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    APP_BASE_URL: str
    ALLOWED_CONTENT_TYPES: tuple[str, ...]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Settings(
        DATABASE_URL=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/docsentinel",
        ),
        REDIS_URL=redis_url,
        CELERY_BROKER_URL=os.getenv("CELERY_BROKER_URL", redis_url),
        CELERY_RESULT_BACKEND=os.getenv("CELERY_RESULT_BACKEND", redis_url),
        MINIO_ENDPOINT=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        MINIO_ACCESS_KEY=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        MINIO_SECRET_KEY=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        MINIO_SECURE=_as_bool(os.getenv("MINIO_SECURE"), default=False),
        MINIO_RAW_BUCKET=os.getenv("MINIO_RAW_BUCKET", "raw"),
        DOCSENTINEL_API_KEY=os.getenv("DOCSENTINEL_API_KEY", ""),
        BILLING_PROVIDER=os.getenv("BILLING_PROVIDER", ""),
        STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY", ""),
        STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
        APP_BASE_URL=os.getenv("APP_BASE_URL", "http://localhost:8000"),
        ALLOWED_CONTENT_TYPES=(
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/tiff",
        ),
    )


settings = get_settings()
