# Lumi Platform — MVP Architecture

> One-pager covering all three Lumi repositories: how they fit together, what each is for, and the investor / merchant story they tell.

The diagram source is [`lumi-platform-architecture.drawio`](./lumi-platform-architecture.drawio) — a **two-page** file. Open in [diagrams.net](https://app.diagrams.net) or VS Code Draw.io Integration. Export PNG/SVG for slide decks.

| Page | Audience | What it shows |
|---|---|---|
| **1 · Lumi Platform — MVP** | investors, executives | High-level: 4-tier flow (AI hosts → discovery → platform → brand back-office) with the OSS-moat / SaaS-revenue split |
| **2 · Capability Detail** | engineers, technical merchants | lumi-agent broken into L1–L4 layered capabilities + AgentOps sidebar; brand-bridge as dual-pillar downstream (品牌初始化 + 系统集成); ERP added explicitly |

---

## The picture

```
┌──────────────────────────────────────────────────────────────────────┐
│  AI HOSTS                                                              │
│  Claude Desktop · ChatGPT · Hex Agents · OpenClaw / Custom Agents     │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │  MCP
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│  DISCOVERY    lumi-mcp · public agent landing                         │
│               GitHub Pages · tools.json · llms.txt · mcp.json         │
└──────────────┬──────────────────────────────────────┬────────────────┘
               │                                       │
               ▼                                       ▼
┌──────────────────────────────┐   ┌──────────────────────────────────┐
│  brand-bridge · OSS          │◀─▶│  lumi-agent · hosted SaaS        │
│  Brand integration framework │   │  AI orchestration layer           │
│                              │   │                                   │
│  • 5 Provider ABCs            │   │  • LangGraph workflow              │
│    MasterData/POS/CRM/Pay/IM │   │  • 5 channels (WA/H5/Voice/MCP)  │
│  • MCP server (stdio + HTTP) │   │  • Ops Copilot (KPI/anomaly)     │
│  • Audit primitives           │   │  • Agentic Payment (Mastercard)   │
│  • Auto-onboard               │   │                                   │
│                              │   │                                   │
│  22 tools · Apache 2.0        │   │  18 tools · single-tenant demo    │
│  github.com/lumitive/         │   │  FastAPI + LangGraph + ChromaDB   │
│   brand-bridge                │   │                                   │
└──────────────┬───────────────┘   └────────────────┬─────────────────┘
               │                                     │
               ▼                                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│  BRAND BACK-OFFICE                                                     │
│  POS · Master Data · CRM/Loyalty · Payment · IM                       │
│  (Square · Toast · 美团 · Salesforce · Stripe · Alipay · WhatsApp)   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Capability detail (page 2)

Page 2 zooms into the platform tier and breaks each project into the modules investors and engineers care about.

### lumi-agent · 上半身 (L1–L4 + AgentOps)

```
L1 · 前端交互     A2UI/H5  ·  WhatsApp/WeChat  ·  Voice (ASR/TTS)  ·  MCP host  ·  UI Action / 服务卡
L2 · 会话         Conversation Center  ·  ConversationContext (Patch+Checkpoint)  ·  Auth/RBAC  ·  Memory
L3 · 编排         LangGraph + TaskDef  ·  A2A Orchestrator (DAG)  ·  Skill Framework  ·  Multi-Agent  ·  Sandbox
L4 · 智能         Intent (LLM)  ·  Slot Filling  ·  RAG (Milvus/ChromaDB)  ·  Recommend  ·  Domain Brain

AgentOps         Eval (LLM-as-Judge · Bad Case · suite gate)  ·  Playground (replay-seed · SSE chat)
                 Audit Ledger  ·  RC / Mock Policy / Namespace  ·  Skill Marketplace
```

This is where the AI work happens — and the layer that justifies SaaS pricing. Customers buy lumi-agent because building L1–L4 from scratch takes a full team a year.

### brand-bridge · 下半身 (dual pillar)

**① 品牌初始化 (Brand Onboarding)** — how a brand goes from zero to AI-accessible:

| Capability | What it does |
|---|---|
| `tenant.yaml` + 4 行业预设 | Declarative config; coffee/tea/restaurant/retail templates |
| `/brand-init` skill | Interactive Q&A → 30-second yaml generation, demo data live immediately |
| `/brand-onboard` skill | OpenAPI / Postman / docs URL → `adapter.py` + `tenant.yaml` + integration tests |
| DemoAdapter fallback | Zero-config startup; replace one provider at a time without breaking others |
| Contract tests | Every adapter (demo and real) passes the same suite |
| **5-day brand integration** | Day 1 yaml · Day 2 MasterData · Day 3 POS · Day 4-5 testing & ship |

**② 系统集成 (System Integration)** — how brand-bridge connects to brand internal systems:

| Capability | What it covers |
|---|---|
| 5 Provider ABCs | MasterData (商品/门店/类目) · POS (算价/下单/库存) · CRM (会员/券/积分) · Payment (预支付/回调/退款) · IM (消息收发) |
| 平台原语 | Confirmation Token (single-use, 5min TTL) · Idempotency Store · Rate Limiter (L0–L3) · PII Mask · Audit Log |
| MCP Server | stdio (Claude Desktop) + Streamable HTTP (production) · 22 tools · `@audited_tool` uniformly applies rate limit + audit |
| TenantRegistry | `X-Tenant-Id` routing · per-tenant provider instances · one process per brand (stdio) or many (HTTP) |
| **ERP Provider** *(v2 planned)* | 进销存 · 财务 · 供应链 · 凭证 — Oracle EBS / SAP / 用友 / 金蝶 |

### Brand internal systems (the targets)

The bottom tier of page 2 names the concrete vendors brand-bridge adapts to. Six categories, plus ERP added explicitly per real customer requests:

- **POS** — Square · Toast · 美团 · 有赞
- **ERP** — SAP · Oracle · 用友 · 金蝶
- **Master Data** — PIM · catalog · 价格管理
- **CRM / Loyalty** — Salesforce · 自研会员体系
- **Payment** — Stripe · Alipay · WeChat Pay · 银联
- **IM** — WhatsApp · 企业微信 · 钉钉

---

## What each piece does

### lumi-mcp — public discovery (~300 LOC of static HTML/JSON)

The **front door for AI agents**. A static GitHub Pages site at `lumitive.github.io/lumi-mcp/` that publishes:

| File | Purpose |
|---|---|
| `index.html` | Human-readable landing page |
| `tools.json` | Live MCP tool catalog with full JSON Schema (18 primary tools) |
| `llms.txt` | LLM crawl manifest — the canonical agent entry point |
| `mcp.json` | Paste-ready Claude Desktop / Cursor config snippet |

Why it matters: **agents discover us automatically** without a per-vendor SDK. No marketplace required.

### brand-bridge — open source integration framework (the moat)

What the brand engineers build against. Five **Provider ABCs** — `MasterDataProvider`, `POSProvider`, `CRMProvider`, `PaymentProvider`, `IMChannelProvider` — covering the surface area of any commerce backend. The platform layer ships:

- **MCP server** (stdio + Streamable HTTP) — 22 tools wrapped in audit/idempotency/rate-limit
- **Audit primitives** — confirmation tokens, idempotency store, sliding-window rate limiter, PII masking, audit log
- **Demo-as-default** — half-finished `tenant.yaml` still boots, brands replace one provider at a time
- **Auto-onboard** — Claude Code skills generate `adapter.py` from OpenAPI / docs

Status: **M2b complete, 27 tests green, public on github.com/lumitive/brand-bridge**.

### lumi-agent — hosted AI orchestration (the revenue)

The premium experience for brands who want AI without managing the stack. Built on:

- **LangGraph workflow** with checkpointed conversation state
- **Five channels** — WhatsApp, H5 web, Voice, MCP host, WeChat
- **Ops Copilot** — KPI snapshots, anomaly detection, browser-use restock automation
- **Agentic Payment** — Mastercard A2A surface, scoped JWT tokens, passkey auth

Status: **single-tenant demo running** ("Golden Harbour Seafood"). M2c plans the migration onto brand-bridge so lumi-agent serves N tenants.

---

## How money moves

```
    Brand pays for AI experience
                │
                ▼
        ┌──────────────┐
        │ lumi-agent   │  hosted SaaS — recurring revenue
        └──────┬───────┘
               │ uses (free)
               ▼
        ┌──────────────┐
        │ brand-bridge │  open source — adoption + moat
        └──────────────┘
```

- **brand-bridge** is **free for everyone**. Adoption is the moat: every brand integrated against `BrandAdapter` is one we don't have to chase. Standardization compounds.
- **lumi-agent** is the **paid hosted product**. Brands that don't want to run their own LangGraph + WhatsApp + Mastercard A2A pay us monthly. Our cost basis on the AI side is thin because brand-bridge does the heavy integration lift.

The two products reinforce each other: brand-bridge adoption drives lumi-agent demand (any brand integrated with brand-bridge is one click from lumi-agent's hosted offering); lumi-agent's polish drives brand-bridge contribution (we keep extending the framework based on real customer needs).

---

## Why now

1. **MCP standardization**. Anthropic's Model Context Protocol shipped 2024. Every major AI host (Claude Desktop, ChatGPT, Hex, Cursor) adopted it within 12 months. This is the moment to be the standard plug.
2. **Per-vendor SDK fatigue**. Brands are tired of building bespoke Slack apps, WhatsApp adapters, ChatGPT plugins. One MCP server feeds them all.
3. **Agentic commerce**. Mastercard A2A, Visa Agent Pay, OpenAI's commerce expansion — agent-initiated transactions are an emerging category. Whoever owns the brand-side abstraction wins distribution.

---

## What investors / merchants need to remember

| Question | Answer |
|---|---|
| **Who pays?** | Brands subscribe to lumi-agent (hosted SaaS). brand-bridge is free. |
| **What's the moat?** | brand-bridge adoption — every brand standardized on our 5 ABCs is locked-in via integration cost. |
| **How fast is integration?** | 5 days for the MVP (MasterData + POS), 2-3 weeks for full coverage. Auto-onboard tooling compresses that to half a day. |
| **What about competitors?** | We're not competing with POSes (Square/Toast). We sit *between* them and AI agents. They benefit from our standardization. |
| **Why three repos?** | Separation of concerns. Public discovery (lumi-mcp) is just static. Integration framework (brand-bridge) is OSS for trust. Orchestration (lumi-agent) is proprietary because that's where the unique value is. |

---

## Repo links

| Repo | Visibility | Tech | Status |
|---|---|---|---|
| [lumi-mcp](https://github.com/lumitive/lumi-mcp) | public | static HTML + JSON manifests | live on GitHub Pages |
| [brand-bridge](https://github.com/lumitive/brand-bridge) | public | Python 3.11+ / FastMCP / Pydantic | M2b complete (Apache 2.0) |
| lumi-agent | private | FastAPI + LangGraph + ChromaDB | single-tenant demo |

---

*Last updated: 2026-05-07. Edit [`lumi-platform-architecture.drawio`](./lumi-platform-architecture.drawio) for changes; export PNG/SVG for pitch decks.*
