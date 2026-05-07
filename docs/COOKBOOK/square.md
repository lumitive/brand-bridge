# Cookbook — Square POS

A worked example of integrating Square (US-focused, REST API) as a `MasterDataProvider` + `POSProvider`. Use this as a template for any vendor with a similar resource model (Toast, Clover, 美团, 有赞).

## Prerequisites

- A Square Developer account with a Sandbox application.
- Sandbox access token (`EAAA...`) and a sandbox `location_id`.
- `httpx` (already a brand-bridge dependency).

## tenant.yaml

```yaml
tenant_id: my_square_brand
tenant_name: "My Square Brand"
locale: en-US
currency: USD
default_user_id: SQR_DEMO_USER

providers:
  master_data:
    module: tenants.my_square_brand.master_data
    class: SquareMasterData
  pos:
    module: tenants.my_square_brand.pos
    class: SquarePOS
  # crm/payment fall through to demo until you add them

features:
  campaigns: false
  coupons: false
  stars_mall: false
  delivery: true
  nutrition: false

rate_limits:
  L0: { max_calls: 60, window_seconds: 60 }
  L1: { max_calls: 30, window_seconds: 60 }
  L2: { max_calls: 5,  window_seconds: 3600 }
  L3: { max_calls: 10, window_seconds: 86400 }

square:
  base_url: https://connect.squareupsandbox.com
  token_env: SQUARE_ACCESS_TOKEN
  default_location_env: SQUARE_LOCATION_ID
```

## master_data.py

```python
"""SquareMasterData — wraps Square Catalog + Locations APIs."""

from __future__ import annotations

import os

import httpx

from brand_bridge.core.providers import MasterDataProvider
from brand_bridge.core.types import Category, Modifier, Product, Store


class SquareMasterData(MasterDataProvider):
    def __init__(self, config) -> None:
        sq = config.raw["square"]
        self.client = httpx.AsyncClient(
            base_url=sq["base_url"],
            headers={
                "Authorization": f"Bearer {os.environ[sq['token_env']]}",
                "Square-Version": "2025-01-23",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )

    async def list_stores(self, *, city=None, keyword=None) -> list[Store]:
        r = await self.client.get("/v2/locations")
        r.raise_for_status()
        out: list[Store] = []
        for loc in r.json().get("locations", []):
            addr = loc.get("address", {})
            if city and addr.get("locality") != city:
                continue
            if keyword and keyword.lower() not in loc.get("name", "").lower():
                continue
            out.append(Store(
                store_id=loc["id"],
                name=loc.get("name", ""),
                city=addr.get("locality"),
                address=", ".join(filter(None, [
                    addr.get("address_line_1"), addr.get("address_line_2"),
                ])),
                phone=loc.get("phone_number"),
                services=loc.get("capabilities", []),
                metadata={"timezone": loc.get("timezone")},
            ))
        return out

    async def get_store(self, store_id: str) -> Store | None:
        r = await self.client.get(f"/v2/locations/{store_id}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        loc = r.json()["location"]
        addr = loc.get("address", {})
        return Store(
            store_id=loc["id"], name=loc.get("name", ""),
            city=addr.get("locality"),
            address=addr.get("address_line_1", ""),
            phone=loc.get("phone_number"),
            services=loc.get("capabilities", []),
        )

    async def list_categories(self, store_id: str) -> list[Category]:
        r = await self.client.post("/v2/catalog/search", json={
            "object_types": ["CATEGORY"],
            "include_deleted_objects": False,
        })
        r.raise_for_status()
        out: list[Category] = []
        for i, obj in enumerate(r.json().get("objects", [])):
            data = obj.get("category_data", {})
            out.append(Category(code=obj["id"], name=data.get("name", ""), sort=i))
        return out

    async def list_products(self, store_id: str, *, category=None) -> list[Product]:
        body = {"object_types": ["ITEM"], "include_deleted_objects": False}
        if category:
            body["query"] = {"exact_query": {"attribute_name": "category_id",
                                             "attribute_value": category}}
        r = await self.client.post("/v2/catalog/search", json=body)
        r.raise_for_status()
        return [_to_product(obj) for obj in r.json().get("objects", [])]

    async def get_product(self, product_code: str) -> Product | None:
        r = await self.client.get(f"/v2/catalog/object/{product_code}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return _to_product(r.json()["object"])

    async def list_modifiers(self, product_code: str) -> list[Modifier]:
        # Square modifiers live on the item via modifier_list_info; resolve them.
        r = await self.client.get(f"/v2/catalog/object/{product_code}")
        if r.status_code == 404:
            return []
        r.raise_for_status()
        item = r.json()["object"]
        infos = item.get("item_data", {}).get("modifier_list_info", [])
        out: list[Modifier] = []
        for info in infos:
            mr = await self.client.get(f"/v2/catalog/object/{info['modifier_list_id']}")
            mr.raise_for_status()
            ml = mr.json()["object"]
            for m in ml.get("modifier_list_data", {}).get("modifiers", []):
                md = m.get("modifier_data", {})
                price = md.get("price_money", {}).get("amount", 0) / 100
                out.append(Modifier(
                    code=m["id"], name=md.get("name", ""),
                    extra_price=price,
                    group=ml.get("modifier_list_data", {}).get("name"),
                ))
        return out


def _to_product(obj: dict) -> Product:
    data = obj.get("item_data", {})
    variations = data.get("variations", [])
    base_price = 0.0
    if variations:
        money = variations[0].get("item_variation_data", {}).get("price_money", {})
        base_price = money.get("amount", 0) / 100
    return Product(
        product_code=obj["id"],
        name=data.get("name", ""),
        category=data.get("category_id", ""),
        base_price=base_price,
        description=data.get("description", ""),
        customizable=bool(data.get("modifier_list_info")),
        metadata={"square_raw": data},
    )
```

## pos.py

```python
"""SquarePOS — Orders + Payments APIs.

The platform handles confirmation tokens and idempotency; we forward
idempotency_key as Square's Idempotency-Key header for defense in depth.
"""

from __future__ import annotations

import os
import secrets
import uuid

import httpx

from brand_bridge.core.audit import (
    DEFAULT_IDEMPOTENCY_STORE,
    consume_confirmation_token,
    generate_confirmation_token,
    register_confirmation_token,
)
from brand_bridge.core.errors import UpstreamError
from brand_bridge.core.providers import POSProvider
from brand_bridge.core.types import (
    CancelResult, InventoryItem, InventorySnapshot,
    Order, OrderItem, PriceLine, PriceQuote,
)


class SquarePOS(POSProvider):
    def __init__(self, config) -> None:
        sq = config.raw["square"]
        self.location_id = os.environ.get(sq["default_location_env"], "")
        self.client = httpx.AsyncClient(
            base_url=sq["base_url"],
            headers={
                "Authorization": f"Bearer {os.environ[sq['token_env']]}",
                "Square-Version": "2025-01-23",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )

    async def calculate_price(self, *, store_id, items, coupon_code=None,
                              pickup_type="pickup") -> PriceQuote:
        body = {
            "idempotency_key": str(uuid.uuid4()),  # Square requires one even for calc
            "order": {
                "location_id": store_id or self.location_id,
                "line_items": [{
                    "catalog_object_id": i.product_code,
                    "quantity": str(i.quantity),
                } for i in items],
                "state": "DRAFT",
            },
        }
        r = await self.client.post("/v2/orders/calculate", json=body)
        if r.status_code >= 400:
            raise UpstreamError(f"Square calculate failed: {r.text}")

        order = r.json()["order"]
        lines = []
        for li in order.get("line_items", []):
            unit = li.get("base_price_money", {}).get("amount", 0) / 100
            line_total = li.get("total_money", {}).get("amount", 0) / 100
            lines.append(PriceLine(
                name=li.get("name", ""), size=None,
                unit_price=unit, quantity=int(li["quantity"]),
                line_total=line_total,
            ))
        original = sum(li.line_total for li in lines)
        final = order.get("total_money", {}).get("amount", 0) / 100
        discount = max(0.0, original - final)

        token = generate_confirmation_token()
        register_confirmation_token(token, {
            "store_id": store_id, "items": [i.model_dump() for i in items],
            "final_price": final, "discount": discount,
        })
        return PriceQuote(
            items=lines, original_price=original, discount=discount,
            final_price=final, confirmation_token=token,
        )

    async def place_order(self, *, tenant_id, user_id, store_id, items,
                          pickup_type, idempotency_key, confirmation_token,
                          coupon_code=None, address_id=None) -> Order:
        idem_scope = f"{tenant_id}:place_order"
        body_hash = DEFAULT_IDEMPOTENCY_STORE.hash_body({
            "store_id": store_id, "items": [i.model_dump() for i in items],
            "pickup_type": pickup_type,
        })
        cached = DEFAULT_IDEMPOTENCY_STORE.lookup(idem_scope, idempotency_key, body_hash)
        if cached is not None:
            return cached

        consume_confirmation_token(confirmation_token)

        r = await self.client.post("/v2/orders", json={
            "idempotency_key": idempotency_key,    # forward to Square too
            "order": {
                "location_id": store_id or self.location_id,
                "line_items": [{
                    "catalog_object_id": i.product_code,
                    "quantity": str(i.quantity),
                } for i in items],
                "fulfillments": [{
                    "type": _square_fulfillment(pickup_type),
                    "state": "PROPOSED",
                }],
            },
        })
        if r.status_code >= 400:
            raise UpstreamError(f"Square create failed: {r.text}")

        sq_order = r.json()["order"]
        lines = [PriceLine(
            name=li.get("name", ""), size=None,
            unit_price=li.get("base_price_money", {}).get("amount", 0) / 100,
            quantity=int(li["quantity"]),
            line_total=li.get("total_money", {}).get("amount", 0) / 100,
        ) for li in sq_order.get("line_items", [])]

        order = Order(
            order_id=sq_order["id"],
            store_id=store_id,
            store_name=None,
            pickup_type=pickup_type,
            items=lines,
            final_price=sq_order.get("total_money", {}).get("amount", 0) / 100,
            status="pending",
            pay_url=None,
            metadata={"square_state": sq_order.get("state")},
        )
        DEFAULT_IDEMPOTENCY_STORE.store(idem_scope, idempotency_key, body_hash, order)
        return order

    async def get_order(self, order_id, user_id) -> Order | None:
        r = await self.client.get(f"/v2/orders/{order_id}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        sq_order = r.json()["order"]
        return _to_order(sq_order)

    async def cancel_order(self, order_id, user_id, reason="") -> CancelResult:
        r = await self.client.put(f"/v2/orders/{order_id}", json={
            "order": {"state": "CANCELED", "version": 0},  # version supplied by your store
            "idempotency_key": str(uuid.uuid4()),
        })
        if r.status_code >= 400:
            return CancelResult(order_id=order_id, success=False,
                                message=r.text[:200])
        return CancelResult(order_id=order_id, success=True,
                            message=reason or "cancelled")

    async def list_recent_orders(self, user_id, *, limit=10) -> list[Order]:
        r = await self.client.post("/v2/orders/search", json={
            "location_ids": [self.location_id],
            "limit": limit,
        })
        r.raise_for_status()
        return [_to_order(o) for o in r.json().get("orders", [])]

    async def inventory_snapshot(self, store_id) -> InventorySnapshot:
        # Square Inventory API returns counts per catalog_object_id; aggregate.
        r = await self.client.get(
            "/v2/inventory/counts/batch-retrieve",
            params={"location_ids": store_id or self.location_id},
        )
        # Normalize into our InventoryItem shape.
        # Actual implementation depends on which catalog items you track.
        return InventorySnapshot(
            store_id=store_id, as_of=__import__("datetime").datetime.now(),
            items=[],
        )


def _square_fulfillment(pickup_type: str) -> str:
    return {"pickup": "PICKUP", "delivery": "DELIVERY",
            "dine_in": "PICKUP"}.get(pickup_type, "PICKUP")


def _to_order(sq: dict) -> Order:
    lines = [PriceLine(
        name=li.get("name", ""), size=None,
        unit_price=li.get("base_price_money", {}).get("amount", 0) / 100,
        quantity=int(li.get("quantity", 1)),
        line_total=li.get("total_money", {}).get("amount", 0) / 100,
    ) for li in sq.get("line_items", [])]
    state = sq.get("state", "OPEN")
    status_map = {"OPEN": "pending", "COMPLETED": "completed",
                  "CANCELED": "cancelled"}
    return Order(
        order_id=sq["id"],
        store_id=sq.get("location_id", ""),
        pickup_type="pickup",
        items=lines,
        final_price=sq.get("total_money", {}).get("amount", 0) / 100,
        status=status_map.get(state, "pending"),
    )
```

## Verification

```bash
export SQUARE_ACCESS_TOKEN=EAAA...
export SQUARE_LOCATION_ID=L4Y...
brand-bridge tenant validate my_square_brand
# OK: My Square Brand
#   master_data : SquareMasterData
#   pos         : SquarePOS
#   crm         : DemoCRM
#   payment     : DemoPayment
```

Then connect to Claude Desktop using the `examples/claude_desktop.json` template — substitute `my_square_brand`.

## Known gotchas

1. **Square requires money in `amount` (cents) + `currency`** — divide by 100 going out, multiply going in. Don't lose the currency or you'll mix HKD with USD totals.
2. **Order versioning** — Square's order updates require the latest `version` number. Cache it on `Order.metadata` and pass it on cancel/update.
3. **Catalog vs Item Variations** — Square models prices per variation, not item. We use the first variation's price as `base_price`; brands with size-priced items should expand `Product.metadata["variations"]` and resolve at quote time.
4. **Pagination** — Square endpoints return `cursor` for >100 items. Production code should follow the cursor; the example skips it for brevity.
5. **Sandbox vs Prod** — different `base_url`. Keep them in tenant.yaml; never hardcode.
