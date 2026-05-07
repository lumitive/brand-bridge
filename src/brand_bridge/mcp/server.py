"""FastMCP server factory.

`create_server(tenant_id)` returns a configured FastMCP instance with all
tools registered for that tenant. One process per tenant for stdio (Claude
Desktop launches one); HTTP multiplexing comes in a later milestone.

Every tool body is wrapped in `audited(ctx, ...)` which applies the rate
limit configured in `tenant.yaml` for the L0–L3 risk class and writes an
audit entry on entry/exit. Adapter calls happen inside the context manager;
return values are Pydantic models that FastMCP serializes to JSON.

The 21 tools registered below cover:
    Discovery   — now_time_info, list_stores, list_categories, list_products,
                  get_product, list_modifiers, list_campaigns, list_available_coupons
    Account     — my_account, my_coupons, my_orders, list_addresses, store_coupons
    Order flow  — calculate_price, place_order, get_order, cancel_order,
                  list_recent_orders, inventory_snapshot
    Loyalty     — claim_coupon, redeem_points
    Address     — create_address

Production deployments may want to formatters that return markdown rather
than JSON; for now JSON is the default since AI hosts handle either.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

from brand_bridge.core.audit import audited
from brand_bridge.core.context import ToolContext
from brand_bridge.core.types import OrderItem
from brand_bridge.registry import TenantRegistry, load_tenant


def create_server(tenant_id: str) -> FastMCP:
    config = load_tenant(tenant_id)
    registry = TenantRegistry.from_config(config)

    mcp = FastMCP(
        name=f"brand-bridge:{tenant_id}",
        instructions=config.instructions or f"Tools for {config.tenant_name}.",
    )

    def _ctx() -> ToolContext:
        # M2.5 will derive user_id from JWT scope; for now use the tenant's
        # default. Building per-call so a future request-scoped user_id slots
        # in without restructuring.
        return ToolContext(
            tenant_id=config.tenant_id,
            user_id=config.default_user_id,
            config=config, registry=registry,
        )

    # ─── Discovery ────────────────────────────────────────────────

    @mcp.tool()
    async def now_time_info() -> dict[str, str]:
        """Current UTC time and weekday — call this before reasoning about
        promotion validity windows or store hours."""
        now = datetime.now(timezone.utc)
        return {"iso": now.isoformat(), "weekday": now.strftime("%A")}

    @mcp.tool()
    async def list_stores(city: str | None = None,
                          keyword: str | None = None) -> list[dict]:
        """Search stores. Optional city + keyword filters."""
        ctx = _ctx()
        async with audited(ctx, name="list_stores", rate_class="L0"):
            stores = await ctx.registry.master_data.list_stores(
                city=city, keyword=keyword)
            return [s.model_dump() for s in stores]

    @mcp.tool()
    async def get_store(store_id: str) -> dict | None:
        """Fetch one store by id."""
        ctx = _ctx()
        async with audited(ctx, name="get_store", rate_class="L0"):
            store = await ctx.registry.master_data.get_store(store_id)
            return store.model_dump() if store else None

    @mcp.tool()
    async def list_categories(store_id: str) -> list[dict]:
        """Menu categories for a store."""
        ctx = _ctx()
        async with audited(ctx, name="list_categories", rate_class="L0"):
            cats = await ctx.registry.master_data.list_categories(store_id)
            return [c.model_dump() for c in cats]

    @mcp.tool()
    async def list_products(store_id: str,
                            category: str | None = None) -> list[dict]:
        """Menu items for a store. Optionally filter by category code."""
        ctx = _ctx()
        async with audited(ctx, name="list_products", rate_class="L0"):
            products = await ctx.registry.master_data.list_products(
                store_id, category=category)
            return [p.model_dump() for p in products]

    @mcp.tool()
    async def get_product(product_code: str) -> dict | None:
        """Fetch one product with full customization detail."""
        ctx = _ctx()
        async with audited(ctx, name="get_product", rate_class="L0"):
            p = await ctx.registry.master_data.get_product(product_code)
            return p.model_dump() if p else None

    @mcp.tool()
    async def list_modifiers(product_code: str) -> list[dict]:
        """Customization options (size/milk/extras) for a product."""
        ctx = _ctx()
        async with audited(ctx, name="list_modifiers", rate_class="L0"):
            mods = await ctx.registry.master_data.list_modifiers(product_code)
            return [m.model_dump() for m in mods]

    @mcp.tool()
    async def list_campaigns(month: str | None = None) -> list[dict]:
        """Active and upcoming campaigns. Optional month filter (yyyy-MM)."""
        ctx = _ctx()
        async with audited(ctx, name="list_campaigns", rate_class="L0"):
            camps = await ctx.registry.crm.list_campaigns(month=month)
            return [c.model_dump() for c in camps]

    @mcp.tool()
    async def list_available_coupons() -> list[dict]:
        """Public coupon center."""
        ctx = _ctx()
        async with audited(ctx, name="list_available_coupons", rate_class="L0"):
            coupons = await ctx.registry.crm.list_available_coupons()
            return [c.model_dump() for c in coupons]

    # ─── Account (user-scoped reads) ─────────────────────────────

    @mcp.tool()
    async def my_account() -> dict | None:
        """Current user's member profile + tier + points balance."""
        ctx = _ctx()
        async with audited(ctx, name="my_account", rate_class="L1"):
            m = await ctx.registry.crm.get_member(user_id=ctx.user_id)
            return m.model_dump() if m else None

    @mcp.tool()
    async def my_coupons(status: str | None = None) -> list[dict]:
        """Current user's coupon wallet. Status filter: valid/used/expired."""
        ctx = _ctx()
        async with audited(ctx, name="my_coupons", rate_class="L1"):
            cs = await ctx.registry.crm.list_my_coupons(ctx.user_id, status=status)
            return [c.model_dump() for c in cs]

    @mcp.tool()
    async def my_orders(limit: int = 10) -> list[dict]:
        """Current user's recent orders."""
        ctx = _ctx()
        async with audited(ctx, name="my_orders", rate_class="L1"):
            orders = await ctx.registry.pos.list_recent_orders(
                ctx.user_id, limit=limit)
            return [o.model_dump() for o in orders]

    @mcp.tool()
    async def list_addresses() -> list[dict]:
        """Current user's saved delivery addresses (phone numbers masked)."""
        ctx = _ctx()
        async with audited(ctx, name="list_addresses", rate_class="L1"):
            addrs = await ctx.registry.crm.list_addresses(ctx.user_id)
            from brand_bridge.core.audit import mask_phone
            return [{**a.model_dump(), "phone": mask_phone(a.phone)} for a in addrs]

    @mcp.tool()
    async def store_coupons(store_id: str) -> list[dict]:
        """Coupons usable at this store for the current user."""
        ctx = _ctx()
        async with audited(ctx, name="store_coupons", rate_class="L1"):
            cs = await ctx.registry.crm.store_coupons(store_id, ctx.user_id)
            return [c.model_dump() for c in cs]

    @mcp.tool()
    async def inventory_snapshot(store_id: str) -> dict:
        """Stock levels and low-stock alerts for a store."""
        ctx = _ctx()
        async with audited(ctx, name="inventory_snapshot", rate_class="L1"):
            snap = await ctx.registry.pos.inventory_snapshot(store_id)
            return snap.model_dump()

    # ─── Order flow ──────────────────────────────────────────────

    @mcp.tool()
    async def calculate_price(store_id: str, items: list[dict],
                              coupon_code: str | None = None,
                              pickup_type: str = "pickup") -> dict:
        """Step 1 of ordering — returns a price quote with a confirmation_token.
        Pass that token to place_order to commit. Items shape:
        [{"product_code": "D001", "quantity": 1, "size": "tall", ...}]"""
        ctx = _ctx()
        async with audited(ctx, name="calculate_price", rate_class="L1"):
            order_items = [OrderItem.model_validate(i) for i in items]
            quote = await ctx.registry.pos.calculate_price(
                store_id=store_id, items=order_items,
                coupon_code=coupon_code, pickup_type=pickup_type,
            )
            return quote.model_dump()

    @mcp.tool()
    async def place_order(store_id: str, items: list[dict], pickup_type: str,
                          idempotency_key: str, confirmation_token: str,
                          coupon_code: str | None = None,
                          address_id: str | None = None) -> dict:
        """Step 2 of ordering — commits the order. Requires the
        confirmation_token from calculate_price (single-use, 5-min TTL) and
        an idempotency_key (UUID) so retries don't double-charge."""
        ctx = _ctx()
        async with audited(ctx, name="place_order", rate_class="L3"):
            order_items = [OrderItem.model_validate(i) for i in items]
            order = await ctx.registry.pos.place_order(
                tenant_id=ctx.tenant_id, user_id=ctx.user_id,
                store_id=store_id, items=order_items, pickup_type=pickup_type,
                idempotency_key=idempotency_key,
                confirmation_token=confirmation_token,
                coupon_code=coupon_code, address_id=address_id,
            )
            return order.model_dump()

    @mcp.tool()
    async def get_order(order_id: str) -> dict | None:
        """Fetch order status + line items."""
        ctx = _ctx()
        async with audited(ctx, name="get_order", rate_class="L1"):
            o = await ctx.registry.pos.get_order(order_id, ctx.user_id)
            return o.model_dump() if o else None

    @mcp.tool()
    async def cancel_order(order_id: str, reason: str = "") -> dict:
        """Cancel an order. Refund handled by the brand backend."""
        ctx = _ctx()
        async with audited(ctx, name="cancel_order", rate_class="L3"):
            r = await ctx.registry.pos.cancel_order(order_id, ctx.user_id, reason)
            return r.model_dump()

    # ─── Loyalty writes ───────────────────────────────────────────

    @mcp.tool()
    async def claim_coupon(campaign_id: str) -> dict:
        """Claim one coupon by campaign id."""
        ctx = _ctx()
        async with audited(ctx, name="claim_coupon", rate_class="L2"):
            r = await ctx.registry.crm.claim_coupon(ctx.user_id, campaign_id)
            return r.model_dump()

    @mcp.tool()
    async def redeem_points(product_code: str, idempotency_key: str) -> dict:
        """Redeem points for an item. idempotency_key (UUID) prevents
        duplicate redemptions on retry."""
        ctx = _ctx()
        async with audited(ctx, name="redeem_points", rate_class="L3"):
            r = await ctx.registry.crm.redeem_points(
                user_id=ctx.user_id, product_code=product_code,
                idempotency_key=idempotency_key,
            )
            return r.model_dump()

    # ─── Address writes ───────────────────────────────────────────

    @mcp.tool()
    async def create_address(city: str, address: str, address_detail: str,
                             contact_name: str, phone: str) -> dict:
        """Add a new delivery address for the current user."""
        ctx = _ctx()
        async with audited(ctx, name="create_address", rate_class="L2"):
            a = await ctx.registry.crm.create_address(
                user_id=ctx.user_id, city=city, address=address,
                address_detail=address_detail, contact_name=contact_name,
                phone=phone,
            )
            from brand_bridge.core.audit import mask_phone
            return {**a.model_dump(), "phone": mask_phone(a.phone)}

    return mcp


def run_stdio(tenant_id: str) -> None:
    """Entry point for `brand-bridge serve --tenant <id>`."""
    server = create_server(tenant_id)
    server.run()  # FastMCP picks stdio by default
