# brand-bridge

> Turn any brand's POS / CRM / master data into AI-ready capabilities — exposed via MCP for Claude Desktop, ChatGPT, Hex, and any agent host.

`brand-bridge` is the integration layer between brand back-office systems and AI agents. Define a brand once in YAML + 5 provider classes, get an MCP server that any AI host can talk to.

## Why

Every brand wants AI ordering, AI customer service, AI ops copilots. Every brand has the same problem: their POS, CRM, master data, payment, and IM systems weren't built for agents. `brand-bridge` is the missing layer.

```
Brand back-office          brand-bridge              AI hosts
──────────────────         ─────────────────         ────────────────
POS (Square / Toast)  →    MasterDataProvider   →    Claude Desktop
CRM (Salesforce)      →    POSProvider          →    ChatGPT
Master data (own DB)  →    CRMProvider          →    Hex Agents
Payment (Stripe)      →    PaymentProvider      →    lumi-agent
IM (WhatsApp / WeChat)→    IMChannelProvider    →    OpenClaw
```

## Quickstart

```bash
pip install brand-bridge
brand-bridge tenant init my_brand --preset coffee
brand-bridge serve --tenant my_brand            # stdio MCP, demo data works out of the box
```

Connect it to Claude Desktop:

```jsonc
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "my-brand": {
      "command": "brand-bridge",
      "args": ["serve", "--tenant", "my_brand"]
    }
  }
}
```

That's it. The brand is now AI-accessible with demo data. Replace the demo adapters with your real backend and you're in production.

## How it works

A brand integration is two things:

1. **`tenant.yaml`** — declarative config (menu options, validation rules, feature flags, rate limits)
2. **5 Provider classes** — `MasterDataProvider`, `POSProvider`, `CRMProvider`, `PaymentProvider`, `IMChannelProvider`

The platform handles auth, scope checks, rate limits, audit logging, idempotency, confirmation tokens, and PII masking. Brand engineers only write the field mapping.

```python
from brand_bridge.core.providers import POSProvider
from brand_bridge.core.types import Order, OrderItem

class MyPOS(POSProvider):
    async def place_order(self, *, tenant_id, user_id, store_id, items,
                          pickup_type, idempotency_key, confirmation_token,
                          coupon_code=None, address_id=None) -> Order:
        # Call your real POS, map the response into Order
        ...
```

## Auto-onboarding

Got an OpenAPI spec or API docs? Use the `brand-onboard` Claude Code skill to generate a working adapter automatically:

```bash
# In Claude Code:
/brand-onboard https://api.mybrand.com/openapi.json
```

It reads the docs, infers field mappings, generates `adapter.py` + `tenant.yaml` + integration tests, and runs them for you.

## Status

`brand-bridge` is in active development. v1.0 milestones:

- [x] M0 — Repo scaffold, 5 Provider ABCs, Pydantic types
- [ ] M1 — Demo adapter, contract tests, tenant.yaml loader
- [ ] M2 — MCP server (stdio + Streamable HTTP), audit + JWT scope
- [ ] M3 — CLI + auto-onboard skills + 4 industry presets
- [ ] M4 — Reference adapters (Square POS, Stripe, Twilio WhatsApp)
- [ ] M5 — Public release, GitHub Pages, PyPI

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design and [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md) for the brand-side walkthrough.

## License

Apache 2.0 — see [LICENSE](LICENSE).

Sponsored by [Lumitive](https://github.com/lumitive).
