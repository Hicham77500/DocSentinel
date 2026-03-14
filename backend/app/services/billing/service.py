from __future__ import annotations

from fastapi import HTTPException, status

from app.config.settings import settings
from app.services.billing.base import BillingProvider
from app.services.billing.stripe_provider import StripeBillingProvider


def get_billing_provider() -> BillingProvider:
    provider = settings.BILLING_PROVIDER.strip().lower()
    if provider == "stripe":
        return StripeBillingProvider()

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Billing provider is not available.",
    )
