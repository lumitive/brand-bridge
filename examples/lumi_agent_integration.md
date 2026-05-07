# Integrating brand-bridge with lumi-agent

[lumi-agent](https://github.com/lumitive/lumi-agent) is the AI orchestration layer that brand-bridge was designed to feed. This guide explains how to migrate a lumi-agent install from its hardcoded `data/menu.py` + `data/mock_merchant.py` to a brand-bridge tenant context.

## Why migrate

`lumi-agent` ships as a single-merchant demo. Its workflow nodes import `data.menu.MENU` directly, which means every install is forked off the demo. brand-bridge replaces that hardcoded source with a per-tenant `TenantRegistry` so:

- A single lumi-agent process can serve many brands.
- Adding a brand stops being a code change to lumi-agent.
- Audit, rate limit, and idempotency get pulled out of lumi-agent's bespoke implementations.

## Migration shape (~150 LoC of changes in lumi-agent)

### 1. Add brand-bridge as a dependency

```toml
# lumi-agent/backend/pyproject.toml
[project]
dependencies = [
    # ...existing...
    "brand-bridge>=0.1",
]
```

### 2. Replace `data/menu.py` imports with a context lookup

Before:
```python
from data.menu import MENU, get_by_sku
product = MENU.get(name)
```

After:
```python
# In a graph node:
async def menu_lookup_node(state, ctx: ToolContext):
    product = await ctx.registry.master_data.get_product(name)
    return {"product": product}
```

### 3. Inject `ToolContext` at the LangGraph entry point

`lumi-agent`'s `workflow/ordering.py` builds the graph as a lazy singleton. Wrap the `invoke` call with a context resolver:

```python
# lumi-agent/backend/app/api/chat.py
from brand_bridge.core.context import ToolContext
from brand_bridge.registry import TenantRegistry, load_tenant

async def chat_endpoint(req: ChatRequest):
    config = load_tenant(req.tenant_id)        # X-Tenant-Id header in production
    registry = TenantRegistry.from_config(config)
    ctx = ToolContext(
        tenant_id=config.tenant_id, user_id=req.user_id,
        config=config, registry=registry,
    )
    state = {"input": req.message, "tenant_ctx": ctx}
    result = await workflow.ainvoke(state, config={"configurable": {"thread_id": req.session_id}})
    return result
```

Each graph node accesses `ctx = state["tenant_ctx"]` and goes through `ctx.registry.<provider>`.

### 4. Migrate `services/cart_store.py` to multi-tenant

The current cart_store keys carts on `cardholder_id`. Add `tenant_id` to the composite key:

```python
# Schema change:
CREATE TABLE agent_cart (
    tenant_id TEXT NOT NULL,
    cart_id TEXT NOT NULL,
    items JSON,
    updated_at TIMESTAMP,
    PRIMARY KEY (tenant_id, cart_id)
);
```

This is a breaking change for existing carts; migrate them with a one-time `UPDATE agent_cart SET tenant_id = '_demo'` before deploying.

### 5. Replace `services/payment/factory.py`

```python
# Before: global singleton based on env vars
_payment_service = AlipayService(...)

# After: per-tenant
def get_payment_service(ctx: ToolContext) -> PaymentProvider:
    return ctx.registry.payment
```

The `PaymentProvider` interface is intentionally identical to lumi-agent's `PaymentService`, so existing Alipay / WeChat / Stripe implementations port over with rename only.

### 6. Use `@audited_tool` instead of bespoke `audited_tool`

lumi-agent has its own `services/auth/agent_identity.audited_tool`. The brand-bridge version subsumes it:

```python
from brand_bridge.core.audit import audited_tool

@audited_tool(name="cart.checkout", rate_class="L3")
async def checkout(ctx, *, idempotency_key: str):
    return await ctx.registry.pos.place_order(...)
```

Audit entries land in `brand_bridge.core.audit.DEFAULT_AUDIT_LOG`, which lumi-agent can surface via its existing `/api/external/agent_audit` endpoint by reading `DEFAULT_AUDIT_LOG.tail()`.

### 7. Keep `services/mcp_external.py` shape, swap the data source

The 5 MCP namespaces (`merchant.search`, `cart.*`, `session.*`, `payment.*`, `identity.issue`) keep their tool surface; only the implementation changes. `merchant.search` becomes a thin wrapper around `ctx.registry.master_data.list_stores`.

## What you do NOT migrate

- LangGraph workflow itself — stays in lumi-agent. brand-bridge has no opinion on conversation orchestration.
- The Next.js frontend — the merchant control panel, audit ledger, ops copilot UI all stay.
- The browser-use automation — out of scope.
- WhatsApp / H5 channel adapters — keep them in lumi-agent for now. M3 of brand-bridge will offer optional `IMChannelProvider` implementations as alternatives.

## Verification

After the migration:

```bash
# In lumi-agent backend dir
cd lumi-agent/backend
uv sync
uv run pytest tests/ -v          # All existing tests should pass
uv run python ../scripts/d7_dryrun.py    # 12 demo beats remain green
```

If `d7_dryrun.py` shows ALL BEATS GREEN, the migration is safe to ship.

## Rollout plan

1. PR 1 — add brand-bridge dep, build `_demo` tenant equivalent to current hardcoded data, run side-by-side under a feature flag (`USE_BRAND_BRIDGE=true`).
2. PR 2 — port `data/menu.py` consumers (~6 files in `workflow/` and `services/`).
3. PR 3 — multi-tenant cart_store migration with backfill.
4. PR 4 — flip the feature flag default to true; deprecate hardcoded data.
5. PR 5 — delete `data/menu.py` and `data/mock_merchant.py`.

Each PR is independently shippable and revertible. Total estimated work: ~1.5 weeks for one engineer.

## Open questions

- **Does lumi-agent want to own its IM channels, or move them to brand-bridge?** Argument for moving: brand-bridge serves multiple AI hosts, so channel adapters benefit other consumers too. Argument for keeping: lumi-agent's WhatsApp impl is tightly coupled to its LangGraph workflow.
- **Audit log persistence.** lumi-agent has SQLite. brand-bridge defaults to in-memory. Decide which is canonical for combined deployments.
- **JWT scope authority.** lumi-agent mints AgentIdentity JWTs. Should brand-bridge accept those, or mint its own?

These are tracked in `docs/ROADMAP.md` for the M2 milestone.
