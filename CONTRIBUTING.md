# Contributing to brand-bridge

Thanks for your interest. `brand-bridge` is small enough that contribution guidance fits in one page.

## What we want

- **New adapters** for popular POS / CRM / payment / IM vendors. Square, Stripe, Twilio are the M4 reference set; everything else is community-welcome.
- **Field-mapping fixes** in existing adapters — real APIs have edge cases, and the COOKBOOK is incomplete by design.
- **Contract test additions** that cover behaviors a real adapter could get wrong (idempotency under race, confirmation token reuse, rate-limit window edges).
- **Documentation** — especially worked examples and "I tried this and got stuck" notes.

## What we don't want (yet)

- Workflow / agent orchestration features. Use lumi-agent or LangGraph for that.
- Hosted-SaaS code paths.
- Frontend SDK additions — AI hosts already speak MCP.

If you want one of these, open an issue for discussion first.

## Setup

```bash
git clone https://github.com/lumitive/brand-bridge.git
cd brand-bridge
uv sync --all-extras --dev
uv run pytest -v
```

That's the full developer loop. No Docker, no databases.

## Branch + PR flow

1. Fork, branch off `main`. Branch names: `feat/square-pos`, `fix/idem-race`, `docs/cookbook-toast`.
2. Keep PRs small. One adapter per PR; one bug fix per PR.
3. Run `uv run ruff check src tests` and `uv run pytest` before pushing.
4. Open the PR with a description that answers: *what changed, why, how to verify*. The CI matrix (3.11/3.12/3.13) must be green.
5. Address review comments by adding new commits — we squash on merge.

## Adapter PR checklist

If you're adding a new vendor adapter (e.g. `adapters/toast/`):

- [ ] Lives in `src/brand_bridge/adapters/<vendor>/`, not in `tenants/`.
- [ ] Implements at least one of the five Provider ABCs end-to-end.
- [ ] Uses `generate_confirmation_token` / `consume_confirmation_token` for the order flow (don't roll your own).
- [ ] Forwards `idempotency_key` to the vendor as `Idempotency-Key` header (if supported).
- [ ] All return values pass Pydantic validation (the contract tests catch this).
- [ ] Includes at least a smoke test using the vendor's sandbox API; mark expensive tests with `@pytest.mark.slow`.
- [ ] Adds a `docs/COOKBOOK/<vendor>.md` with the auth setup, gotchas, and a minimal `tenant.yaml`.
- [ ] Pins the vendor SDK version (or pure httpx — preferred — with documented headers).

## Style

- Python 3.11+ syntax (`str | None`, not `Optional[str]`).
- Async-first. Wrap blocking SDKs with `asyncio.to_thread` if you must.
- Pydantic v2 for any new domain types.
- Tight docstrings — say *why* the code exists, not what each line does.
- No emojis in source files unless a human user asks for them.
- Default to no comments. Only add a comment when the *why* is non-obvious.

We use `ruff` (configured in `pyproject.toml`) and aim for `mypy --strict` compatibility eventually; for now `mypy --ignore-missing-imports` is the bar.

## Filing issues

- **Bug reports** — include the tenant.yaml (redact secrets), a minimal reproduction, and the traceback. `brand-bridge tenant validate <id>` output is helpful.
- **Feature requests** — describe the user-visible behavior, why existing primitives don't cover it, and one or two API call shapes you'd expect.
- **Adapter requests** — name the vendor, link the public API docs, and (if available) note whether you have a sandbox account to share.

## Code of conduct

Be kind. Assume good faith. Disagree about code, not about people.

## License

By contributing you agree your contributions are licensed under Apache 2.0 (the project license). No CLA required.
