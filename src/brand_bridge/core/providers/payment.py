"""PaymentProvider — prepay, callback, query, refund.

Mirrors lumi-agent's PaymentService surface so existing Alipay / WeChatPay /
Stripe implementations can be ported with minimal change. The factory in
brand_bridge.adapters resolves a concrete provider from tenant.yaml's
`payment.kind` (alipay | wechat | stripe | mock).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PrepayResult:
    success: bool
    order_id: str
    pre_pay_id: str = ""
    pay_url: str = ""
    sdk_params: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class CallbackResult:
    success: bool
    order_id: str = ""
    trade_no: str = ""
    amount: float = 0.0
    payment_method: str = ""
    paid_at: str = ""
    error: str = ""


@dataclass
class PaymentStatus:
    order_id: str
    status: str  # pending | paid | failed | refunded
    trade_no: str = ""
    amount: float = 0.0
    payment_method: str = ""
    paid_at: str = ""


@dataclass
class RefundResult:
    success: bool
    order_id: str
    refund_id: str = ""
    amount: float = 0.0
    error: str = ""


class PaymentProvider(ABC):
    @abstractmethod
    async def create_prepay(self, *, order_id: str, amount: float,
                            payment_method: str = "alipay",
                            subject: str = "",
                            **kwargs: Any) -> PrepayResult: ...

    @abstractmethod
    async def handle_callback(self, *, body: bytes, headers: dict[str, str],
                              provider: str = "alipay") -> CallbackResult: ...

    @abstractmethod
    async def query_status(self, order_id: str) -> PaymentStatus: ...

    @abstractmethod
    async def refund(self, *, order_id: str, amount: float,
                     reason: str = "") -> RefundResult: ...
