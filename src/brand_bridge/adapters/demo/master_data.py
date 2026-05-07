"""Demo MasterDataProvider — serves an in-memory catalog."""

from __future__ import annotations

from brand_bridge.core.providers import MasterDataProvider
from brand_bridge.core.types import Category, Modifier, Product, Store

from ._data import CATEGORIES, PRODUCTS, STORES, demo_modifiers


class DemoMasterData(MasterDataProvider):
    def __init__(self, config) -> None:
        self.config = config

    async def list_stores(self, *, city: str | None = None,
                          keyword: str | None = None) -> list[Store]:
        result = STORES
        if city:
            result = [s for s in result if s.city == city]
        if keyword:
            kw = keyword.lower()
            result = [s for s in result if kw in s.name.lower()]
        return result

    async def get_store(self, store_id: str) -> Store | None:
        return next((s for s in STORES if s.store_id == store_id), None)

    async def list_categories(self, store_id: str) -> list[Category]:
        return CATEGORIES

    async def list_products(self, store_id: str, *,
                            category: str | None = None) -> list[Product]:
        if category:
            return [p for p in PRODUCTS if p.category == category]
        return PRODUCTS

    async def get_product(self, product_code: str) -> Product | None:
        return next((p for p in PRODUCTS if p.product_code == product_code), None)

    async def list_modifiers(self, product_code: str) -> list[Modifier]:
        return demo_modifiers(product_code)
