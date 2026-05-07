"""CRMProvider — members, coupons, campaigns, points.

Optional surface. Brands without a loyalty program can stub this with the
DemoCRM and disable the `crm` feature flag in tenant.yaml; the relevant MCP
tools will short-circuit with "not enabled for this brand".
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from brand_bridge.core.types import (
    Address,
    Campaign,
    ClaimResult,
    Coupon,
    Member,
    PointsAccount,
    RedeemResult,
)


class CRMProvider(ABC):
    # ─── Membership ───────────────────────────────────────────────
    @abstractmethod
    async def get_member(self, *, user_id: str | None = None,
                         phone: str | None = None) -> Member | None: ...

    # ─── Coupons & Campaigns ──────────────────────────────────────
    @abstractmethod
    async def list_campaigns(self, *, month: str | None = None) -> list[Campaign]: ...

    @abstractmethod
    async def list_available_coupons(self) -> list[Coupon]: ...

    @abstractmethod
    async def list_my_coupons(self, user_id: str, *,
                              status: str | None = None) -> list[Coupon]: ...

    @abstractmethod
    async def claim_coupon(self, user_id: str, campaign_id: str) -> ClaimResult: ...

    @abstractmethod
    async def claim_all_coupons(self, user_id: str) -> ClaimResult: ...

    @abstractmethod
    async def store_coupons(self, store_id: str, user_id: str) -> list[Coupon]: ...

    # ─── Points ───────────────────────────────────────────────────
    @abstractmethod
    async def get_points(self, user_id: str) -> PointsAccount: ...

    @abstractmethod
    async def redeem_points(self, *, user_id: str, product_code: str,
                            idempotency_key: str) -> RedeemResult: ...

    # ─── Addresses (delivery) ─────────────────────────────────────
    @abstractmethod
    async def list_addresses(self, user_id: str) -> list[Address]: ...

    @abstractmethod
    async def create_address(self, *, user_id: str, city: str, address: str,
                             address_detail: str, contact_name: str,
                             phone: str) -> Address: ...
