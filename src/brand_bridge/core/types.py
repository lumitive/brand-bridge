"""Domain types — the contract every adapter must honor.

Provider methods accept and return these models; the platform layer (MCP tool
serialization, formatters, audit) operates on them. All field maps that don't
fit the canonical shape go into `metadata` so adapters can pass through brand-
specific extras without schema churn.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


# ─── Master data ─────────────────────────────────────────────────────────

class Store(_Base):
    store_id: str
    name: str
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    open_hours: str | None = None
    services: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Category(_Base):
    code: str
    name: str
    sort: int = 0


class Modifier(_Base):
    code: str
    name: str
    extra_price: float = 0.0
    group: str | None = None


class Product(_Base):
    product_code: str
    name: str
    category: str
    base_price: float
    description: str = ""
    customizable: bool = False
    available_sizes: list[str] = Field(default_factory=list)
    available_temps: list[str] = Field(default_factory=list)
    available_milks: list[str] = Field(default_factory=list)
    available_extras: list[str] = Field(default_factory=list)
    calories: int | None = None
    nutrition: dict[str, float] = Field(default_factory=dict)
    image: str | None = None
    is_new: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─── Order flow ──────────────────────────────────────────────────────────

class OrderItem(_Base):
    """Input shape for calculate_price / place_order."""
    product_code: str
    quantity: int = 1
    size: str | None = None
    milk: str | None = None
    temperature: str | None = None
    sweetness: str | None = None
    extras: list[str] = Field(default_factory=list)


class PriceLine(_Base):
    name: str
    size: str | None = None
    unit_price: float
    quantity: int
    line_total: float


class PriceQuote(_Base):
    items: list[PriceLine]
    original_price: float
    discount: float = 0.0
    coupon_name: str | None = None
    delivery_fee: float = 0.0
    packing_fee: float = 0.0
    final_price: float
    confirmation_token: str
    expires_at: datetime | None = None


OrderStatus = Literal["pending", "paid", "preparing", "ready", "completed", "cancelled", "failed"]


class Order(_Base):
    order_id: str
    store_id: str
    store_name: str | None = None
    pickup_type: Literal["pickup", "delivery", "dine_in"]
    items: list[PriceLine]
    final_price: float
    discount: float = 0.0
    status: OrderStatus
    stars_will_earn: int = 0
    pay_url: str | None = None
    message: str | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CancelResult(_Base):
    order_id: str
    success: bool
    refund_amount: float = 0.0
    message: str = ""


class InventoryItem(_Base):
    sku: str
    name: str
    on_hand: int
    days_left: float | None = None
    suggested_order: int | None = None


class InventorySnapshot(_Base):
    store_id: str
    as_of: datetime
    items: list[InventoryItem]


# ─── CRM ──────────────────────────────────────────────────────────────────

class Member(_Base):
    member_id: str
    name: str
    phone: str | None = None
    member_tier: str | None = None
    tier_name: str | None = None
    star_balance: int = 0
    tier_expire_date: str | None = None
    next_tier: str | None = None
    stars_to_next: int = 0
    registration_date: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


CouponStatus = Literal["claimable", "valid", "used", "expired", "cancelled"]


class Coupon(_Base):
    coupon_id: str
    name: str
    description: str = ""
    discount_value: float
    min_order: float = 0.0
    valid_from: str | None = None
    valid_to: str | None = None
    status: CouponStatus
    applicable_products: list[str] = Field(default_factory=list)
    image: str | None = None


class ClaimResult(_Base):
    success: bool
    claimed_count: int = 0
    already_claimed: int = 0
    claimed_coupons: list[Coupon] = Field(default_factory=list)
    message: str = ""


class Campaign(_Base):
    campaign_id: str
    title: str
    description: str = ""
    start_date: str
    end_date: str
    status: Literal["upcoming", "active", "ended"]
    tags: list[str] = Field(default_factory=list)
    image: str | None = None


class PointsAccount(_Base):
    member_id: str
    balance: int
    expiring_soon: int = 0
    expiry_date: str | None = None


class RedeemResult(_Base):
    success: bool
    redeem_id: str = ""
    product_name: str = ""
    stars_cost: int = 0
    stars_remaining: int = 0
    message: str = ""


# ─── Address (delivery) ───────────────────────────────────────────────────

class Address(_Base):
    address_id: str
    city: str
    address: str
    address_detail: str
    contact_name: str
    phone: str          # Platform applies PII masking before formatting
    is_default: bool = False
