"""Demo POSProvider — in-memory orders, deterministic confirmation tokens."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from brand_bridge.core.errors import ConfirmationTokenError
from brand_bridge.core.providers import POSProvider
from brand_bridge.core.types import (
    CancelResult,
    InventorySnapshot,
    Order,
    OrderItem,
    PriceLine,
    PriceQuote,
)

from ._data import PRODUCTS, demo_inventory


class DemoPOS(POSProvider):
    def __init__(self, config) -> None:
        self.config = config
        self._tokens: dict[str, dict] = {}      # confirmation_token -> quote payload
        self._orders: dict[str, Order] = {}     # order_id -> Order
        self._idem: dict[str, str] = {}         # idempotency_key -> order_id

    def _price_lines(self, items: list[OrderItem]) -> tuple[list[PriceLine], float]:
        lines: list[PriceLine] = []
        total = 0.0
        for item in items:
            product = next((p for p in PRODUCTS if p.product_code == item.product_code), None)
            if product is None:
                continue
            unit = product.base_price
            line_total = unit * item.quantity
            total += line_total
            lines.append(PriceLine(
                name=product.name, size=item.size,
                unit_price=unit, quantity=item.quantity, line_total=line_total,
            ))
        return lines, total

    async def calculate_price(self, *, store_id, items, coupon_code=None,
                              pickup_type="pickup") -> PriceQuote:
        lines, original = self._price_lines(items)
        discount = 3.0 if coupon_code else 0.0
        delivery = 5.0 if pickup_type == "delivery" else 0.0
        final = max(0.0, original - discount + delivery)

        token = f"cfm_{secrets.token_hex(8)}"
        quote = PriceQuote(
            items=lines, original_price=original, discount=discount,
            coupon_name=coupon_code, delivery_fee=delivery,
            packing_fee=0.0, final_price=final, confirmation_token=token,
        )
        self._tokens[token] = {
            "store_id": store_id, "items": [i.model_dump() for i in items],
            "final_price": final, "discount": discount,
        }
        return quote

    async def place_order(self, *, tenant_id, user_id, store_id, items,
                          pickup_type, idempotency_key, confirmation_token,
                          coupon_code=None, address_id=None) -> Order:
        if confirmation_token not in self._tokens:
            raise ConfirmationTokenError(
                "confirmation_token is invalid or already consumed")

        if idempotency_key in self._idem:
            return self._orders[self._idem[idempotency_key]]

        quote = self._tokens.pop(confirmation_token)
        lines, _ = self._price_lines(items)

        order_id = f"ord_{secrets.token_hex(6)}"
        order = Order(
            order_id=order_id, store_id=store_id,
            store_name="Demo Flagship",
            pickup_type=pickup_type,
            items=lines, final_price=quote["final_price"],
            discount=quote["discount"], status="pending",
            stars_will_earn=int(quote["final_price"] // 10),
            pay_url=f"https://pay.demo/{order_id}",
            message="Please complete payment within 15 minutes.",
            created_at=datetime.now(timezone.utc),
        )
        self._orders[order_id] = order
        self._idem[idempotency_key] = order_id
        return order

    async def get_order(self, order_id, user_id) -> Order | None:
        return self._orders.get(order_id)

    async def cancel_order(self, order_id, user_id, reason="") -> CancelResult:
        order = self._orders.get(order_id)
        if order is None:
            return CancelResult(order_id=order_id, success=False, message="not found")
        order.status = "cancelled"
        return CancelResult(order_id=order_id, success=True,
                            refund_amount=order.final_price,
                            message=reason or "cancelled")

    async def list_recent_orders(self, user_id, *, limit=10) -> list[Order]:
        return list(self._orders.values())[-limit:]

    async def inventory_snapshot(self, store_id) -> InventorySnapshot:
        return demo_inventory(store_id)
