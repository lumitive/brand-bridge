# Lumi Platform — MVP Architecture

> One-pager covering all three Lumi repositories: how they fit together, what each is for, and the investor / merchant story they tell.

The diagram source is [`lumi-platform-architecture.drawio`](./lumi-platform-architecture.drawio). Open it in [diagrams.net](https://app.diagrams.net) (free, browser-based) or VS Code with the Draw.io Integration extension. Export PNG/SVG for slide decks.

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
