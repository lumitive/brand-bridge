"""POSProvider — the transactional core of a brand integration.

`calculate_price` MUST return a quote with a fresh `confirmation_token`.
`place_order` MUST verify the token (the platform layer does this before
your method runs, but the token must be present in the quote you returned).

`idempotency_key` is supplied by the caller (AI host) and the platform
deduplicates internally; you may also forward it to your backend's
Idempotency-Key header for a second layer of safety.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from brand_bridge.core.types import (
    CancelResult,
    InventorySnapshot,
    Order,
    OrderItem,
    PriceQuote,
)


class POSProvider(ABC):
    @abstractmethod
    async def calculate_price(self, *, store_id: str, items: list[OrderItem],
                              coupon_code: str | None = None,
                              pickup_type: Literal["pickup", "delivery", "dine_in"] = "pickup",
                              ) -> PriceQuote: ...

    @abstractmethod
    async def place_order(self, *, tenant_id: str, user_id: str, store_id: str,
                          items: list[OrderItem],
                          pickup_type: Literal["pickup", "delivery", "dine_in"],
                          idempotency_key: str, confirmation_token: str,
                          coupon_code: str | None = None,
                          address_id: str | None = None) -> Order: ...

    @abstractmethod
    async def get_order(self, order_id: str, user_id: str) -> Order | None: ...

    @abstractmethod
    async def cancel_order(self, order_id: str, user_id: str,
                           reason: str = "") -> CancelResult: ...

    @abstractmethod
    async def list_recent_orders(self, user_id: str, *, limit: int = 10) -> list[Order]: ...

    @abstractmethod
    async def inventory_snapshot(self, store_id: str) -> InventorySnapshot: ...
