---
name: brand-init
description: Interactive tenant initializer for brand-bridge. Generates tenant.yaml from an industry preset (coffee/tea/restaurant/retail) via Q&A. Trigger phrases — "init brand", "new tenant", "scaffold brand-bridge tenant", "/brand-init".
---

# brand-init

Walks the operator through creating a new tenant. Output is a working `tenants/<id>/tenant.yaml` that boots with the demo adapter.

## Steps

1. Ask for **brand_id** (snake_case English) and **brand_name** (display).
2. Ask which **preset** fits:
   - `coffee` — Manner / Peet's / Starbucks-style chains
   - `tea` — milk tea, fruit tea (toppings + sweetness levels)
   - `restaurant` — sit-down or QSR (no size/milk; combos)
   - `retail` — non-F&B (catalog only, no customization)
3. Ask which **features** to enable. Default reasonable per preset; ask only what's surprising:
   - `campaigns`, `coupons`, `stars_mall`, `delivery`, `nutrition`, `ops_copilot`, `agentic_payment`
4. Run the generator (M3 will provide a Python helper; for now write yaml directly).
5. Validate with `brand-bridge tenant validate <id>`.

## Implementation note (M3)

Add `src/brand_bridge/cli/tenant_init.py` exposing `brand-bridge tenant init <id> --preset <p> --non-interactive` so this skill is a thin wrapper over deterministic Python.
