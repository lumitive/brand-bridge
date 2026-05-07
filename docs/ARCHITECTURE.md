# Architecture

## The integration problem

Every brand wants AI ordering, AI customer service, AI ops copilots. Every brand has the same problem: their POS, CRM, and master-data systems weren't built for agents. AI hosts (Claude Desktop, ChatGPT, Hex, lumi-agent) can talk MCP, but the brand's backend speaks Square / Toast / 美团 / 有赞 / proprietary REST.

`brand-bridge` is the missing layer.

## The two-layer design

```
                    ┌────────────────────────────────────┐
   AI hosts  <───>  │   MCP server (stdio + HTTP)        │
                    │   Audit · scope · rate · idempotency│
                    └──────────────┬─────────────────────┘
                                   │
                       ┌───────────▼────────────┐
                       │  Provider ABCs (5)     │   ← stable contract
                       │  + Pydantic types      │
                       └───────────┬────────────┘
                                   │
            ┌──────────┬───────────┼──────────┬───────────┐
            │          │           │          │           │
        MasterData   POS         CRM       Payment      IM
        (Square,    (Square,   (Salesforce,(Stripe,    (Twilio,
         own DB,    Toast,      own loyalty, Alipay,    WeChat,
         CDN)       美团)        engine)     WeChatPay) Lark)
```

**Layer 1 — Platform (we maintain):** MCP server, auth, audit, rate limit, idempotency, confirmation token, PII masking, feature flags, tenant routing.

**Layer 2 — Adapters (brands maintain):** Five Provider classes, one per business surface. Each method is a pure mapping from the platform's typed contract into the brand's existing API.

This separation is why a brand can integrate in **3-5 days** for the MVP (MasterData + POS) instead of building yet another agent stack from scratch.

## Why five providers, not one mega-interface

The five surfaces have *very* different ownership patterns inside a brand:

| Provider | Typical owner inside the brand |
|---|---|
| MasterData | Catalog / merchandising team — usually has a CDN-cached read API |
| POS | Store-ops engineering — hardest, requires write auth |
| CRM | Marketing / loyalty team — separate system, different schema |
| Payment | Finance / payments — already abstracted (PSP integration) |
| IM | Customer support — channel accounts owned by social / CRM team |

Bundling them would force every brand to ship all five at once. Splitting them lets a brand start with two providers, prove the value, and add the rest incrementally.

## Tenant routing

A single `brand-bridge` instance can serve N brands. Routing happens at three points:

1. **Stdio MCP** — one process per tenant. `brand-bridge serve --tenant <id>`.
2. **HTTP MCP** — one process, many tenants. `X-Tenant-Id` header (or JWT scope) selects the registry. Reuses lumi-agent's `audited_tool` pattern.
3. **REST mirror (v1.1+)** — same routing as HTTP MCP.

Each tenant's `TenantRegistry` is built once and cached. Provider instances are per-tenant (so per-brand HTTP clients, credentials, and rate limits stay isolated).

## Demo-as-default

The tenant loader's most important design choice: **a tenant.yaml without `providers:` boots successfully** with the demo adapter. This is the same trick `coffee-mcp` used and it's a force multiplier:

- Brand engineers can write their tenant.yaml in 30 minutes and immediately see Claude Desktop call 24 working tools.
- They can replace one provider at a time (MasterData first, then POS) without breaking the others.
- Integration tests work without any backend mocks — the demo data is the contract.

## How this relates to coffee-mcp and lumi-agent

| | coffee-mcp | lumi-agent | **brand-bridge** |
|---|---|---|---|
| Abstraction | 21 MCP tools (`BrandAdapter` ABC) | LangGraph + 5 channels | 5 business `Provider` ABCs |
| Audience | One brand | One demo merchant | Many brands × many backends |
| Distribution | Per-brand fork | Demo repo | PyPI package |
| State | demoware | demoware | production framework |

`coffee-mcp` proved the YAML + DemoAdapter pattern. `lumi-agent` proved the audit + JWT scope + multi-channel pattern. `brand-bridge` is the production-grade synthesis.

## What `brand-bridge` is *not*

- **Not a workflow engine.** LangGraph belongs in lumi-agent. We expose the data; agents decide what to do.
- **Not a UI.** No control panel in v1.0 — operators use CLI + JSON logs. Web console is a v1.2 candidate.
- **Not opinionated about the backend.** Adapters can call anything: REST, gRPC, GraphQL, internal RPC, CSV exports, Snowflake queries.
- **Not a payment gateway.** `PaymentProvider` is an abstraction over PSPs, not its own ledger.

## Security model (M2)

- **Auth** — AgentIdentity JWT (ported from lumi-agent), scoped to `tenant_id` + tool namespaces.
- **Rate limit** — per-tenant, per-tool-class (L0–L3), configured in tenant.yaml.
- **Audit** — every write tool wraps `audited_tool(...)`; tail at `GET /api/audit`.
- **Idempotency** — L3 tools require `idempotency_key`; in-memory dedupe with optional Redis backend.
- **Confirmation token** — `calculate_price → place_order` two-step pattern; tokens single-use, expire in 5 min.
- **PII masking** — phone numbers in formatter output; raw values stay in adapter responses.

## Roadmap

- **M0** (now) — repo scaffold, 5 Provider ABCs, Pydantic types, demo adapter, contract tests.
- **M1** — tenant.yaml loader hardening, all 24 MCP tool implementations, audit primitives.
- **M2** — stdio + Streamable HTTP MCP server, JWT scope, rate limiter.
- **M3** — `brand-bridge tenant init/onboard/smoke` CLI + Claude Code skills, 4 industry presets.
- **M4** — Reference adapters for Square, Stripe, Twilio WhatsApp.
- **M5** — Public release, GitHub Pages, PyPI 0.1.0.
