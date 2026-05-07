# Brand Integration Guide

> From zero to a working AI-accessible brand in 5 days.

## What you're building

Two artifacts:

1. `tenants/<your_brand>/tenant.yaml` — declarative config
2. `tenants/<your_brand>/<provider>.py` — five Python adapter classes

The platform handles auth, scope, rate limiting, audit, idempotency, confirmation tokens, and PII masking. Your job is field mapping.

## Day 1 — tenant.yaml (30 min)

```bash
mkdir -p tenants/my_brand
```

`tenants/my_brand/tenant.yaml`:

```yaml
tenant_id: my_brand
tenant_name: "My Brand"
locale: zh-CN
currency: HKD
default_user_id: "USER_001"

features:
  campaigns: true
  coupons: true
  stars_mall: false
  delivery: true
  nutrition: true

rate_limits:
  L0: { max_calls: 60, window_seconds: 60 }
  L1: { max_calls: 30, window_seconds: 60 }
  L2: { max_calls: 5,  window_seconds: 3600 }
  L3: { max_calls: 10, window_seconds: 86400 }

# providers: omit to use the demo adapter for everything
```

Validate it:

```bash
brand-bridge tenant validate my_brand
# OK: My Brand
#   master_data : DemoMasterData
#   pos         : DemoPOS
#   ...
```

You can already plug this into Claude Desktop and it serves demo data through 24 tools. Now incrementally replace each provider.

## Day 2 — MasterDataProvider (catalog)

Cheapest provider to implement first. Most brands already have a CDN-cached catalog API.

`tenants/my_brand/master_data.py`:

```python
import httpx

from brand_bridge.core.providers import MasterDataProvider
from brand_bridge.core.types import Category, Modifier, Product, Store


class MyBrandMasterData(MasterDataProvider):
    def __init__(self, config) -> None:
        self.config = config
        self.client = httpx.AsyncClient(base_url="https://api.mybrand.com",
                                        timeout=10.0)

    async def list_stores(self, *, city=None, keyword=None) -> list[Store]:
        params = {}
        if city: params["city"] = city
        if keyword: params["q"] = keyword
        r = await self.client.get("/v1/stores", params=params)
        r.raise_for_status()
        return [
            Store(
                store_id=s["id"], name=s["name"],
                city=s.get("city"), address=s.get("addr"),
                phone=s.get("tel"), open_hours=s.get("hours"),
                services=s.get("services", []),
                metadata={"raw": s},  # Pass-through for fields you don't model yet
            )
            for s in r.json()["items"]
        ]

    # ... implement get_store, list_products, list_categories, list_modifiers
```

Wire it in `tenant.yaml`:

```yaml
providers:
  master_data:
    module: tenants.my_brand.master_data
    class: MyBrandMasterData
```

Re-run `brand-bridge tenant validate my_brand` — now `master_data : MyBrandMasterData`.

## Day 3 — POSProvider (the core)

This is where the value is and where most of the work lives.

`tenants/my_brand/pos.py`:

```python
class MyBrandPOS(POSProvider):
    async def calculate_price(self, *, store_id, items, coupon_code=None,
                              pickup_type="pickup") -> PriceQuote:
        r = await self.client.post("/v1/orders/calculate", json={
            "store_id": store_id,
            "items": [i.model_dump() for i in items],
            "coupon_code": coupon_code,
        })
        r.raise_for_status()
        data = r.json()

        # Confirmation token is OUR responsibility, not the brand's
        from brand_bridge.core.audit import generate_confirmation_token

        return PriceQuote(
            items=[PriceLine(**line) for line in data["lines"]],
            original_price=data["subtotal"],
            discount=data.get("discount", 0),
            final_price=data["total"],
            confirmation_token=generate_confirmation_token(),
        )

    async def place_order(self, *, tenant_id, user_id, store_id, items,
                          pickup_type, idempotency_key, confirmation_token,
                          coupon_code=None, address_id=None) -> Order:
        # Confirmation token already verified by platform layer
        r = await self.client.post(
            "/v1/orders",
            headers={"Idempotency-Key": idempotency_key,
                     "X-User-Id": user_id},
            json={
                "store_id": store_id,
                "items": [i.model_dump() for i in items],
                "pickup_type": pickup_type,
                "coupon_code": coupon_code,
                "address_id": address_id,
            },
        )
        r.raise_for_status()
        d = r.json()
        return Order(
            order_id=d["id"],
            store_id=store_id,
            pickup_type=pickup_type,
            items=[PriceLine(**li) for li in d["lines"]],
            final_price=d["total"],
            status=d["status"],
            pay_url=d.get("pay_url"),
        )

    # ... get_order, cancel_order, list_recent_orders, inventory_snapshot
```

**Three things the platform does for you, so don't reimplement them:**

1. **Idempotency dedupe** — same key returns the same Order without calling your backend twice.
2. **Confirmation token** — `place_order` won't even reach your method if the token is missing or expired.
3. **Rate limiting** — burst-protect your backend per tenant.yaml.

## Day 4 — CRM + Payment + IM (incremental)

CRM and IM are usually owned by different teams; you can ship them in separate PRs. Payment commonly already has an abstraction in your stack — wrap it in a 50-line `PaymentProvider` subclass.

If a feature isn't relevant (e.g. no loyalty program), set `features.coupons: false` in tenant.yaml; the platform will short-circuit those tools with "feature not enabled".

## Day 5 — Test, ship

```bash
# 1. Contract tests (use the same suite the demo adapter passes)
uv run pytest tests/contract --tenant my_brand

# 2. Smoke test against the real backend
brand-bridge tenant smoke my_brand

# 3. Connect to Claude Desktop
# Add to claude_desktop_config.json:
{
  "mcpServers": {
    "my-brand": {
      "command": "brand-bridge",
      "args": ["serve", "--tenant", "my_brand"],
      "env": { "MYBRAND_API_TOKEN": "..." }
    }
  }
}
```

Restart Claude Desktop, you should see your brand's tools.

## Going faster — auto-onboard

If you have OpenAPI / Postman / API docs, skip the manual mapping:

```bash
# In Claude Code:
/brand-onboard https://api.mybrand.com/openapi.json
```

This generates `tenant.yaml`, all five `*.py` providers with field mappings inferred, and a contract test scaffold. You then review the mappings and patch the gaps. This typically compresses 5 days of work to **half a day**.

## Common questions

**Q: My API doesn't expose all the fields the contract requires.**
Set the unknown fields to `None` or empty list, and put what you have into `metadata: dict[str, Any]`. Don't fake fields you don't have — AI hosts will surface them and confuse users.

**Q: My backend doesn't support idempotency.**
The platform layer dedupes in memory, so you're protected against AI-host retries within one process. For multi-instance deployments, configure a Redis backend (M2). Keep forwarding `Idempotency-Key` to your backend regardless — defense in depth.

**Q: Can I use sync code in adapters?**
Yes — wrap blocking calls with `asyncio.to_thread`. Most modern HTTP clients (httpx, aiohttp) are async-native, but the contract doesn't force you.

**Q: How do I test against my real backend without hitting production?**
Use a separate tenant.yaml pointing at your staging API: `tenants/my_brand_staging/tenant.yaml`. Run `brand-bridge tenant smoke my_brand_staging` in CI.

## Time budget

| Day | Provider(s) | Output |
|---|---|---|
| 1 | tenant.yaml | Demo data flowing through MCP |
| 2 | MasterData | Real catalog, real stores |
| 3 | POS | Real ordering, idempotency, inventory |
| 4 | CRM + Payment + IM | Loyalty, payment, channels |
| 5 | Tests + ship | Contract tests pass, Claude Desktop wired |

Total: **5 days for the MVP**, vs months for a custom MCP server.
