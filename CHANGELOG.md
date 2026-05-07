# Changelog

All notable changes to brand-bridge are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added (M2a — stdio MCP server)
- `mcp/server.py` — `create_server(tenant_id) -> FastMCP` factory registering 22 tools across discovery / account / order flow / loyalty / address.
- `brand-bridge serve --tenant <id>` CLI subcommand for the stdio MCP server.
- `core/audit.py::audited` async context manager — variant of `@audited_tool` for handlers that build `ToolContext` inline (the FastMCP signature pattern).
- `tests/contract/test_mcp_server.py` — 5 in-process tests including full calculate_price → place_order round-trip and stale-token rejection.

### Added (M1 — audit primitives + docs)
- `core/audit.py` — platform primitives: confirmation tokens (single-use, 5-min TTL), idempotency store with body-hash safety, sliding-window rate limiter, PII helpers, audit log ring buffer, `@audited_tool` decorator.
- `core/context.py` — `ToolContext` carrying tenant identity, user, config, and registry through tool handlers.
- `tests/contract/test_audit.py` — 13 tests covering tokens, idempotency, rate limit, PII, and the decorator.
- `docs/SECURITY.md` — threat model, defense-by-layer table, L0–L3 risk classes, confirmation-token sequence diagram.
- `docs/COOKBOOK/square.md` — full worked Square POS adapter (MasterData + POS) with auth, gotchas.
- `CONTRIBUTING.md`, `CHANGELOG.md`.
- `examples/claude_desktop.json`, `examples/lumi_agent_integration.md`.

### Changed
- `adapters/demo/pos.py` now delegates to `generate_confirmation_token` / `consume_confirmation_token` and `DEFAULT_IDEMPOTENCY_STORE` instead of inlining its own token dict and idempotency map. This is the canonical pattern real adapters should copy.

## [0.1.0] — M0 scaffold

### Added
- Initial repository structure under Apache 2.0.
- Five Provider ABCs: `MasterDataProvider`, `POSProvider`, `CRMProvider`, `PaymentProvider`, `IMChannelProvider`.
- Pydantic v2 domain types: `Store`, `Product`, `Category`, `Modifier`, `OrderItem`, `PriceQuote`, `Order`, `Member`, `Coupon`, `Campaign`, `PointsAccount`, `Address`, etc.
- In-memory `DemoAdapter` for all five providers; used as the default fallback so a half-configured `tenant.yaml` still boots.
- `TenantConfig` YAML loader and `TenantRegistry` with provider routing.
- CLI: `brand-bridge tenant ls`, `tenant show`, `tenant validate`.
- Contract test suite (7 tests, demo tenant passes).
- GitHub Actions CI matrix on Python 3.11, 3.12, 3.13.
- Documentation: README, ARCHITECTURE, INTEGRATION_GUIDE, PROVIDER_SPEC, ROADMAP.
- Skill stubs for `/brand-init` and `/brand-onboard` Claude Code skills.

[Unreleased]: https://github.com/lumitive/brand-bridge/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/lumitive/brand-bridge/releases/tag/v0.1.0
