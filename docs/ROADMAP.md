# Roadmap

Six weeks to v1.0. One milestone per week unless a milestone is flagged risky.

## M0 — Scaffold (week 1) ✓

- Repo structure, Apache 2.0 license, pyproject.toml
- 5 Provider ABCs + Pydantic types
- Demo adapter (in-memory) for all five providers
- TenantConfig YAML loader, TenantRegistry
- CLI: `brand-bridge tenant ls/show/validate`
- Contract test suite — demo tenant passes
- GitHub Actions CI (Python 3.11/3.12/3.13)
- README, ARCHITECTURE, INTEGRATION_GUIDE drafts

**Exit criterion:** `brand-bridge tenant validate _demo` returns OK; `pytest` passes.

## M1 — Audit + idempotency (week 2) ✓

- ✓ `core/audit.py`: rate limit + audit log decorator (`@audited_tool`)
- ✓ Confirmation token primitive (`generate_confirmation_token` + register + consume, 5-min TTL)
- ✓ In-memory `IdempotencyStore` with body-hash safety check
- ✓ PII masking helpers (`mask_phone`, `mask_email`, idempotent)
- ✓ `core/context.py` — `ToolContext` carries (tenant, user, config, registry)
- ✓ DemoPOS refactored to use platform primitives (canonical reference for real adapters)
- ✓ 13 audit tests + integration with existing 7 contract tests; 20 total pass

**Exit criterion:** `place_order` cannot be invoked without a fresh confirmation token; duplicate idempotency keys with same body return cached order; rate limiter throttles correctly.

## M2a — Stdio MCP server (week 3) ✓

- ✓ `mcp/server.py` — `create_server(tenant_id) -> FastMCP` factory
- ✓ 22 tools registered across discovery (9), account (6), order (4),
  loyalty (2), address (1) — every body wrapped with `audited(...)` context
  manager so rate limit + audit are uniform
- ✓ `brand-bridge serve --tenant <id>` CLI subcommand (stdio)
- ✓ 5 in-process MCP tests including full quote→order flow + stale-token
  rejection through the wire serialization
- ✓ `examples/claude_desktop.json` connection profiles already in M1

**Exit criterion:** stdio server starts cleanly, all 22 tools are listed, full
order flow round-trips through `mcp.call_tool` including confirmation-token
single-use enforcement.

## M2b — Streamable HTTP server (week 3 cont'd) ✓

- ✓ `mcp/http_server.py` — `create_http_app(tenant_id)` for embedding,
  `run_http(tenant_id, host, port)` for standalone (uvicorn-backed)
- ✓ CLI: `brand-bridge serve --http --tenant <id> [--port 8000]`
- ✓ E2E smoke test boots uvicorn on a free port, hits /mcp, asserts <500
- One process per tenant for v1 — multi-tenant-in-one-process deferred
  until a customer needs it (Starlette `Mount` lifespan plumbing is fiddly,
  see lumi-agent CLAUDE.md)

**Exit criterion:** `brand-bridge serve --http --tenant _demo` listens on
the chosen port; `/mcp` route mounted (no 5xx); tests cover both the
embedding path and the standalone runner.

## M2c — Auth + persistence (week 4)

- `auth/agent_identity.py` — JWT scope verification (port from lumi-agent)
- Persistent `AuditLog` (SQLite backend behind the existing interface)
- `GET /api/audit?tenant=...` endpoint (operator scope)
- Optional: in-process multi-tenant routing via `X-Tenant-Id` header
  (Starlette parent app with explicit lifespan forwarding)

## M3 — Auto-onboarding (week 4)

- `brand-bridge tenant init <id> --preset <p>` (Python implementation of brand-init)
- `brand-bridge tenant smoke <id>` (12-beat smoke test)
- Industry presets: coffee, tea, restaurant, retail
- Claude Code skills hardened: `brand-init`, `brand-onboard`, `tenant-smoke`

## M4 — Reference adapters (week 5, risky)

Pick one per surface to validate the abstraction with real APIs:

- `adapters/square/` — POS + MasterData (Square Sandbox)
- `adapters/stripe/` — Payment (Stripe Test Mode)
- `adapters/twilio_wa/` — IM (Twilio WhatsApp Sandbox)

**Risk:** real API field mismatches may force ABC tweaks. Reserve a v0.x bump-tolerance window.

## M5 — Public release (week 6)

- PyPI 0.1.0
- GitHub Pages (docs + COOKBOOK)
- Launch blog post + HN/Reddit submission
- Migrate `coffee-mcp` to be a brand-bridge consumer (validates dogfooding)
- Issue templates, contributing guide

## Post-1.0 candidates (priority ordered)

- Web console (audit viewer + tenant switcher) — v1.1
- REST mirror for non-MCP clients — v1.1
- Redis-backed idempotency store + distributed rate limiter — v1.2
- Multi-region tenant routing — v1.2
- Plug-in browser-automation adapter for legacy POSes without API — v1.3

## Non-goals

- Workflow / agent orchestration (use lumi-agent or LangGraph)
- Hosted SaaS (this is the open-source library; hosting is a separate product)
- Frontend SDK (AI hosts already speak MCP)
