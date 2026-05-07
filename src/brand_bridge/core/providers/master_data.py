"""MasterDataProvider — stores, products, categories, modifiers.

Read-only surface. Adapters typically wrap a brand's catalog API. Most brands
already expose this as a public CDN-cached endpoint, so this is the cheapest
provider to implement first.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from brand_bridge.core.types import Category, Modifier, Product, Store


class MasterDataProvider(ABC):
    @abstractmethod
    async def list_stores(self, *, city: str | None = None,
                          keyword: str | None = None) -> list[Store]: ...

    @abstractmethod
    async def get_store(self, store_id: str) -> Store | None: ...

    @abstractmethod
    async def list_categories(self, store_id: str) -> list[Category]: ...

    @abstractmethod
    async def list_products(self, store_id: str, *,
                            category: str | None = None) -> list[Product]: ...

    @abstractmethod
    async def get_product(self, product_code: str) -> Product | None: ...

    @abstractmethod
    async def list_modifiers(self, product_code: str) -> list[Modifier]: ...
