"""Contract tests — every adapter (demo or real) must pass these.

Boots the demo tenant, exercises one method per provider, and asserts the
return shape matches the Pydantic models. Real adapters import the same
test module via parameterization (M1) so brands can validate their work
locally before opening a PR.
"""

from __future__ import annotations

import pytest

from brand_bridge.core.types import (
    InventorySnapshot,
    Member,
    Order,
    PointsAccount,
    PriceQuote,
    Product,
    Store,
)
from brand_bridge.registry import TenantRegistry, load_tenant


@pytest.fixture
def registry() -> TenantRegistry:
    config = load_tenant("_demo")
    return TenantRegistry.from_config(config)


@pytest.mark.asyncio
async def test_master_data_round_trip(registry: TenantRegistry) -> None:
    stores = await registry.master_data.list_stores()
    assert len(stores) > 0
    assert all(isinstance(s, Store) for s in stores)

    products = await registry.master_data.list_products(stores[0].store_id)
    assert len(products) > 0
    assert all(isinstance(p, Product) for p in products)

    one = await registry.master_data.get_product(products[0].product_code)
    assert one is not None
    assert one.product_code == products[0].product_code


@pytest.mark.asyncio
async def test_pos_quote_then_order(registry: TenantRegistry) -> None:
    products = await registry.master_data.list_products("STORE_001")
    items = [{"product_code": products[0].product_code, "quantity": 1}]
    from brand_bridge.core.types import OrderItem
    order_items = [OrderItem.model_validate(i) for i in items]

    quote = await registry.pos.calculate_price(
        store_id="STORE_001", items=order_items)
    assert isinstance(quote, PriceQuote)
    assert quote.confirmation_token.startswith("cfm_")

    order = await registry.pos.place_order(
        tenant_id="_demo", user_id="DEMO_USER", store_id="STORE_001",
        items=order_items, pickup_type="pickup",
        idempotency_key="idem_test_1",
        confirmation_token=quote.confirmation_token,
    )
    assert isinstance(order, Order)
    assert order.status == "pending"
    assert order.order_id.startswith("ord_")


@pytest.mark.asyncio
async def test_pos_idempotency(registry: TenantRegistry) -> None:
    from brand_bridge.core.types import OrderItem
    items = [OrderItem(product_code="D001", quantity=1)]

    q1 = await registry.pos.calculate_price(store_id="STORE_001", items=items)
    o1 = await registry.pos.place_order(
        tenant_id="_demo", user_id="DEMO_USER", store_id="STORE_001",
        items=items, pickup_type="pickup",
        idempotency_key="dup_key", confirmation_token=q1.confirmation_token,
    )

    q2 = await registry.pos.calculate_price(store_id="STORE_001", items=items)
    o2 = await registry.pos.place_order(
        tenant_id="_demo", user_id="DEMO_USER", store_id="STORE_001",
        items=items, pickup_type="pickup",
        idempotency_key="dup_key", confirmation_token=q2.confirmation_token,
    )
    assert o1.order_id == o2.order_id


@pytest.mark.asyncio
async def test_pos_inventory(registry: TenantRegistry) -> None:
    snap = await registry.pos.inventory_snapshot("STORE_001")
    assert isinstance(snap, InventorySnapshot)
    assert len(snap.items) > 0


@pytest.mark.asyncio
async def test_crm_member_and_points(registry: TenantRegistry) -> None:
    member = await registry.crm.get_member(user_id="DEMO_USER")
    assert isinstance(member, Member)
    assert member.member_id == "DEMO_USER"

    points = await registry.crm.get_points("DEMO_USER")
    assert isinstance(points, PointsAccount)
    assert points.balance >= 0


@pytest.mark.asyncio
async def test_crm_claim_idempotent(registry: TenantRegistry) -> None:
    first = await registry.crm.claim_coupon("DEMO_USER", "CPN_NEW3")
    assert first.success
    second = await registry.crm.claim_coupon("DEMO_USER", "CPN_NEW3")
    assert second.success and second.already_claimed == 1


@pytest.mark.asyncio
async def test_payment_prepay_then_query(registry: TenantRegistry) -> None:
    prepay = await registry.payment.create_prepay(
        order_id="ord_test", amount=42.0, payment_method="alipay")
    assert prepay.success
    status = await registry.payment.query_status("ord_test")
    assert status.status == "pending"
