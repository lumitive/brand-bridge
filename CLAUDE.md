# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`brand-bridge` is the integration layer between brand back-office systems (POS / CRM / master data / payment / IM) and AI hosts (Claude Desktop, ChatGPT, Hex, lumi-agent). The unit of integration is a **tenant**: one brand = one `tenants/<id>/tenant.yaml` + 0–5 Provider classes. The platform handles auth, scope, rate limit, audit, idempotency, confirmation tokens, and PII masking; brand engineers only write field mapping.

Pre-1.0 — see `docs/ROADMAP.md` for milestone state. M0 (scaffold) and M1 (audit primitives + docs) are done; M2 (MCP server + JWT) is next.

## Common commands

```bash
uv sync --all-extras --dev                       # install
uv run pytest                                    # 20 tests, ~0.1s
uv run pytest tests/contract/test_audit.py -v    # one file
uv run pytest -k "idempotency"                   # by keyword

uv run ruff check src tests                      # lint
uv run mypy src --ignore-missing-imports         # type check (best-effort, not strict yet)

uv run brand-bridge tenant ls                    # CLI
uv run brand-bridge tenant validate _demo        # load + instantiate all providers
```

`BRAND_BRIDGE_TENANTS_DIR=/path` overrides where `tenants/` is read from — useful in tests and when running from a checkout outside the repo.

## Architecture you can't see from one file

### The platform / adapter split is load-bearing

The whole project rests on this separation:

- **Platform code** (`src/brand_bridge/core/`, `src/brand_bridge/registry/`) is shared and stable. Don't let security or state-tracking logic leak into adapters.
- **Adapter code** (`src/brand_bridge/adapters/`, `tenants/<id>/`) is per-vendor and per-brand. It does field mapping and HTTP calls — nothing else.

When tempted to add "just a bit of auth/dedupe/rate-limit" to an adapter, stop. Add it once in `core/audit.py` and have every adapter inherit it.

### The five Provider ABCs are the contract

`src/brand_bridge/core/providers/` defines `MasterDataProvider`, `POSProvider`, `CRMProvider`, `PaymentProvider`, `IMChannelProvider`. Each method is async, takes typed inputs, returns Pydantic models from `core/types.py`. Real adapters *must* return these exact shapes — `metadata: dict[str, Any]` is the escape hatch for vendor extras.

Method signatures are intentionally minimal. Don't add methods without updating both the ABC and at least the Demo adapter; otherwise tenant resolution can't fall back gracefully.

### Demo-as-default tenant resolution

`registry/tenant.py::TenantRegistry.from_config` resolves each provider with this rule: if `tenant.yaml` doesn't specify `providers.<name>`, fall back to `brand_bridge.adapters.demo.Demo<Name>`. This means a half-finished `tenant.yaml` *still boots* — brands replace one provider at a time without breaking the others. Preserve this fallback when adding new providers.

### Audit primitives are the platform's job, not the adapter's

`core/audit.py` provides: `generate_confirmation_token` / `register` / `consume` (single-use, 5-min TTL), `IdempotencyStore` (body-hash safety check rejects key reuse with different body), `RateLimiter` (sliding window, configured via `tenant.rate_limits.{L0,L1,L2,L3}`), `mask_phone` / `mask_email`, `AuditLog` ring buffer, `@audited_tool` decorator.

The canonical reference for how to use these is `adapters/demo/pos.py` — its `calculate_price` calls `register_confirmation_token`, its `place_order` calls `consume_confirmation_token` + `DEFAULT_IDEMPOTENCY_STORE.lookup/store`. Real adapters (e.g. the Square example in `docs/COOKBOOK/square.md`) follow the same shape.

### `ToolContext` is how tool handlers get tenant state

`core/context.py::ToolContext` carries `(tenant_id, user_id, config, registry)`. The MCP/REST entry layer (M2) builds it once per request and threads it through every handler — handlers never import a global registry. The `@audited_tool` decorator expects `ctx` as the first arg and reads `ctx.config.rate_limits` to enforce limits.

## Adapter conventions (when adding one)

- Live in `src/brand_bridge/adapters/<vendor>/` (reusable across brands) or `tenants/<id>/<provider>.py` (one brand only).
- Async-first. Wrap blocking SDKs with `asyncio.to_thread`.
- Read auth from env vars referenced in `tenant.yaml` (e.g. `square.token_env: SQUARE_ACCESS_TOKEN`); never hardcode.
- 404 → return `None` for `get_*` methods; don't raise. Other upstream errors → raise `UpstreamError` from `core/errors.py`.
- Forward `idempotency_key` to vendor as `Idempotency-Key` header when supported (defense in depth on top of platform dedupe).
- Don't roll your own confirmation token or rate limiter. Use the platform helpers.

## Testing conventions

- `tests/contract/` is for *contract* tests — every adapter (demo and real) must pass the same suite. When adding behavior to a Provider ABC, add the test here, not in unit tests.
- `pytest-asyncio` is in `auto` mode (set in `pyproject.toml`) — no `@pytest.mark.asyncio` decorator needed on individual tests, but it's still added explicitly in this codebase for clarity.
- The `_demo` tenant is the test substrate. Don't pollute it with test-only data; mutate `ctx.config` in-place (see `test_audited_tool_enforces_rate_limit`) instead.

## Code style

- Python 3.11+ syntax (`str | None`, not `Optional[str]`).
- Pydantic v2 for any new domain types in `core/types.py`. All models extend `_Base` which sets `extra="allow"` so vendor extras flow through `metadata`.
- No emojis in source files unless a user explicitly asks.
- Default to no comments. The why goes in the module docstring; identifiers carry the what. See existing modules for the bar.

## Things to NOT do

- Don't add a workflow / agent orchestration layer here. That's lumi-agent's job; brand-bridge exposes data, agents decide what to do (see `docs/ARCHITECTURE.md` "What brand-bridge is *not*").
- Don't reach across the platform/adapter line. Adapters use platform primitives via imports; platform code never knows about specific adapters.
- Don't break the demo fallback in `TenantRegistry.from_config`. A `tenant.yaml` with no `providers:` section MUST still produce a working registry.
- Don't introduce a global mutable registry. Build the `TenantRegistry` per request in the entry layer.
- Don't add comments that restate code, reference issue numbers, or describe history. The PR description and CHANGELOG own those.

## Where the design rationale lives

- `docs/ARCHITECTURE.md` — why five providers, why demo-as-default, what brand-bridge is *not*.
- `docs/SECURITY.md` — threat model + L0–L3 risk classes + confirmation-token sequence.
- `docs/PROVIDER_SPEC.md` — every method, every return type, common parameters.
- `docs/INTEGRATION_GUIDE.md` — 5-day brand-side walkthrough.
- `docs/COOKBOOK/square.md` — the only worked real-vendor example so far; copy from this when adding others.
- `examples/lumi_agent_integration.md` — how brand-bridge slots under lumi-agent (the consumer it was designed for).
- `CHANGELOG.md` — what shipped in M0/M1; consult before referring to "old" behavior.

## When in doubt

Read `docs/ARCHITECTURE.md`, then `src/brand_bridge/core/audit.py`, then `src/brand_bridge/adapters/demo/pos.py`, then `src/brand_bridge/mcp/server.py`. Those four files contain the entire mental model — providers (contract), audit (platform plumbing), demo POS (canonical adapter pattern), MCP server (how tools get exposed to AI hosts).
