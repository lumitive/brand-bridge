"""In-memory data set used by all four demo providers."""

from __future__ import annotations

from datetime import datetime, timezone

from brand_bridge.core.types import (
    Address,
    Campaign,
    Category,
    Coupon,
    InventoryItem,
    InventorySnapshot,
    Member,
    Modifier,
    Product,
    Store,
)

STORES: list[Store] = [
    Store(store_id="STORE_001", name="Demo Flagship — Nanjing West Road",
          city="Shanghai", address="No. 1, Nanjing West Road",
          phone="021-1234-5678", open_hours="07:00-22:00",
          services=["pickup", "delivery", "dine_in"]),
    Store(store_id="STORE_002", name="Demo Branch — Lujiazui",
          city="Shanghai", address="Pudong, Century Avenue",
          phone="021-2222-3333", open_hours="08:00-21:00",
          services=["pickup", "delivery"]),
]

CATEGORIES: list[Category] = [
    Category(code="coffee", name="Coffee", sort=1),
    Category(code="tea", name="Tea", sort=2),
    Category(code="bakery", name="Bakery", sort=3),
]

PRODUCTS: list[Product] = [
    Product(product_code="D001", name="Latte", category="coffee",
            base_price=28.0, description="Classic latte",
            customizable=True,
            available_sizes=["tall", "grande", "venti"],
            available_temps=["hot", "iced"],
            available_milks=["whole", "skim", "oat"],
            calories=200),
    Product(product_code="D002", name="Americano", category="coffee",
            base_price=22.0, description="Classic americano",
            customizable=True,
            available_sizes=["tall", "grande", "venti"],
            available_temps=["hot", "iced"],
            calories=10),
    Product(product_code="F001", name="Croissant", category="bakery",
            base_price=18.0, description="Butter croissant",
            calories=280),
]

MEMBERS: dict[str, Member] = {
    "DEMO_USER": Member(
        member_id="DEMO_USER", name="Demo User",
        phone="138****1234",
        member_tier="GOLD", tier_name="Gold",
        star_balance=142, tier_expire_date="2027-01-31",
        next_tier="DIAMOND", stars_to_next=58,
    ),
}

CAMPAIGNS: list[Campaign] = [
    Campaign(campaign_id="CMP_001", title="May Member Day",
             description="Buy one get one on signature lattes",
             start_date="2026-05-15", end_date="2026-05-20",
             status="upcoming", tags=["loyalty", "spring"]),
]

AVAILABLE_COUPONS: list[Coupon] = [
    Coupon(coupon_id="CPN_NEW3", name="$3 off welcome",
           description="$3 off your first order",
           discount_value=3.0, min_order=10.0,
           valid_from="2026-05-01", valid_to="2026-12-31",
           status="claimable"),
]

DEMO_ADDRESSES: dict[str, list[Address]] = {
    "DEMO_USER": [
        Address(address_id="addr_demo_01", city="Shanghai",
                address="No. 1 Nanjing West Road",
                address_detail="Suite 101",
                contact_name="Demo User",
                phone="13800001234",
                is_default=True),
    ],
}


def demo_inventory(store_id: str) -> InventorySnapshot:
    return InventorySnapshot(
        store_id=store_id,
        as_of=datetime.now(timezone.utc),
        items=[
            InventoryItem(sku="ING-OAT-MILK", name="Oat milk",
                          on_hand=18, days_left=1.5, suggested_order=24),
            InventoryItem(sku="ING-ESPRESSO", name="Espresso beans",
                          on_hand=5, days_left=0.8, suggested_order=10),
        ],
    )


def demo_modifiers(product_code: str) -> list[Modifier]:
    return [
        Modifier(code="extra_shot", name="Extra shot", extra_price=4.0, group="extras"),
        Modifier(code="syrup_vanilla", name="Vanilla syrup", extra_price=3.0, group="extras"),
    ]
