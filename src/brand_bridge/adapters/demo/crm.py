"""Demo CRMProvider — members, coupons, points, addresses (in-memory)."""

from __future__ import annotations

import secrets
from copy import deepcopy

from brand_bridge.core.providers import CRMProvider
from brand_bridge.core.types import (
    Address,
    Campaign,
    ClaimResult,
    Coupon,
    Member,
    PointsAccount,
    RedeemResult,
)

from ._data import AVAILABLE_COUPONS, CAMPAIGNS, DEMO_ADDRESSES, MEMBERS


class DemoCRM(CRMProvider):
    def __init__(self, config) -> None:
        self.config = config
        self._claimed: dict[str, list[Coupon]] = {}
        self._addresses: dict[str, list[Address]] = deepcopy(DEMO_ADDRESSES)
        self._idem: dict[str, RedeemResult] = {}

    async def get_member(self, *, user_id=None, phone=None) -> Member | None:
        if user_id and user_id in MEMBERS:
            return MEMBERS[user_id]
        if phone:
            return next((m for m in MEMBERS.values() if m.phone == phone), None)
        return None

    async def list_campaigns(self, *, month=None) -> list[Campaign]:
        return CAMPAIGNS

    async def list_available_coupons(self) -> list[Coupon]:
        return AVAILABLE_COUPONS

    async def list_my_coupons(self, user_id, *, status=None) -> list[Coupon]:
        coupons = self._claimed.get(user_id, [])
        if status:
            coupons = [c for c in coupons if c.status == status]
        return coupons

    async def claim_coupon(self, user_id, campaign_id) -> ClaimResult:
        coupon = next((c for c in AVAILABLE_COUPONS if c.coupon_id == campaign_id), None)
        if coupon is None:
            return ClaimResult(success=False, message="Coupon not found")

        already = self._claimed.setdefault(user_id, [])
        if any(c.coupon_id == campaign_id for c in already):
            return ClaimResult(success=True, already_claimed=1, message="Already claimed")

        valid = coupon.model_copy(update={"status": "valid"})
        already.append(valid)
        return ClaimResult(success=True, claimed_count=1, claimed_coupons=[valid])

    async def claim_all_coupons(self, user_id) -> ClaimResult:
        already = self._claimed.setdefault(user_id, [])
        existing_ids = {c.coupon_id for c in already}
        newly = []
        for coupon in AVAILABLE_COUPONS:
            if coupon.coupon_id not in existing_ids:
                valid = coupon.model_copy(update={"status": "valid"})
                already.append(valid)
                newly.append(valid)
        return ClaimResult(
            success=True, claimed_count=len(newly),
            already_claimed=len(AVAILABLE_COUPONS) - len(newly),
            claimed_coupons=newly,
            message=f"Claimed {len(newly)} new coupons",
        )

    async def store_coupons(self, store_id, user_id) -> list[Coupon]:
        return self._claimed.get(user_id, [])

    async def get_points(self, user_id) -> PointsAccount:
        member = MEMBERS.get(user_id)
        balance = member.star_balance if member else 0
        return PointsAccount(member_id=user_id, balance=balance)

    async def redeem_points(self, *, user_id, product_code,
                            idempotency_key) -> RedeemResult:
        if idempotency_key in self._idem:
            return self._idem[idempotency_key]

        member = MEMBERS.get(user_id)
        if member is None:
            result = RedeemResult(success=False, message="Member not found")
        elif member.star_balance < 50:
            result = RedeemResult(success=False, message="Insufficient stars")
        else:
            member.star_balance -= 50
            result = RedeemResult(
                success=True, redeem_id=f"rdm_{secrets.token_hex(4)}",
                product_name="Demo redeemable", stars_cost=50,
                stars_remaining=member.star_balance,
                message="Redemption successful",
            )
        self._idem[idempotency_key] = result
        return result

    async def list_addresses(self, user_id) -> list[Address]:
        return self._addresses.get(user_id, [])

    async def create_address(self, *, user_id, city, address, address_detail,
                             contact_name, phone) -> Address:
        addr = Address(
            address_id=f"addr_{secrets.token_hex(4)}",
            city=city, address=address, address_detail=address_detail,
            contact_name=contact_name, phone=phone, is_default=False,
        )
        self._addresses.setdefault(user_id, []).append(addr)
        return addr
