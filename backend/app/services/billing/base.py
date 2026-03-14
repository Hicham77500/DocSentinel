from __future__ import annotations

from abc import ABC, abstractmethod


class BillingProvider(ABC):
    @abstractmethod
    def create_checkout_session(
        self,
        tenant_id: str,
        plan_code: str,
        success_url: str,
        cancel_url: str,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def create_customer_portal_session(self, tenant_id: str, return_url: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def handle_webhook(self, payload: bytes, signature: str | None) -> dict:
        raise NotImplementedError
