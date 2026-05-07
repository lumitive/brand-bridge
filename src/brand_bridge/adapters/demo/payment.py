"""Demo PaymentProvider — synthesizes prepay / callback / status / refund."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from brand_bridge.core.providers.payment import (
    CallbackResult,
    PaymentProvider,
    PaymentStatus,
    PrepayResult,
    RefundResult,
)


class DemoPayment(PaymentProvider):
    def __init__(self, config) -> None:
        self.config = config
        self._statuses: dict[str, PaymentStatus] = {}

    async def create_prepay(self, *, order_id: str, amount: float,
                            payment_method: str = "alipay",
                            subject: str = "",
                            **kwargs: Any) -> PrepayResult:
        pre_pay_id = f"prepay_{secrets.token_hex(6)}"
        self._statuses[order_id] = PaymentStatus(
            order_id=order_id, status="pending", amount=amount,
            payment_method=payment_method,
        )
        return PrepayResult(
            success=True, order_id=order_id, pre_pay_id=pre_pay_id,
            pay_url=f"https://demo.pay/{order_id}",
            sdk_params={"order_id": order_id, "amount": amount},
        )

    async def handle_callback(self, *, body: bytes, headers: dict[str, str],
                              provider: str = "alipay") -> CallbackResult:
        return CallbackResult(success=True, error="Demo callback — not for production")

    async def query_status(self, order_id: str) -> PaymentStatus:
        return self._statuses.get(
            order_id,
            PaymentStatus(order_id=order_id, status="pending"),
        )

    async def refund(self, *, order_id: str, amount: float,
                     reason: str = "") -> RefundResult:
        status = self._statuses.get(order_id)
        if status is None:
            return RefundResult(success=False, order_id=order_id,
                                error="Order not found")
        status.status = "refunded"
        return RefundResult(
            success=True, order_id=order_id,
            refund_id=f"rfd_{secrets.token_hex(4)}",
            amount=amount,
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
