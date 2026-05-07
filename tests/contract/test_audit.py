"""Tests for platform-side audit primitives."""

from __future__ import annotations

import asyncio

import pytest

from brand_bridge.core.audit import (
    DEFAULT_AUDIT_LOG,
    DEFAULT_IDEMPOTENCY_STORE,
    DEFAULT_RATE_LIMITER,
    IdempotencyStore,
    RateLimiter,
    audited_tool,
    consume_confirmation_token,
    generate_confirmation_token,
    mask_email,
    mask_phone,
    register_confirmation_token,
)
from brand_bridge.core.context import ToolContext
from brand_bridge.core.errors import (
    ConfirmationTokenError,
    IdempotencyError,
    RateLimitExceeded,
)
from brand_bridge.registry import TenantRegistry, load_tenant


@pytest.fixture
def ctx() -> ToolContext:
    config = load_tenant("_demo")
    registry = TenantRegistry.from_config(config)
    return ToolContext(
        tenant_id=config.tenant_id, user_id=config.default_user_id,
        config=config, registry=registry,
    )


def test_confirmation_token_round_trip() -> None:
    token = generate_confirmation_token()
    assert token.startswith("cfm_")
    register_confirmation_token(token, {"order": 1})
    assert consume_confirmation_token(token) == {"order": 1}


def test_confirmation_token_single_use() -> None:
    token = generate_confirmation_token()
    register_confirmation_token(token, {"order": 1})
    consume_confirmation_token(token)
    with pytest.raises(ConfirmationTokenError):
        consume_confirmation_token(token)


def test_confirmation_token_unknown_raises() -> None:
    with pytest.raises(ConfirmationTokenError):
        consume_confirmation_token("cfm_does_not_exist")


def test_idempotency_returns_cached_response() -> None:
    store = IdempotencyStore()
    body = store.hash_body({"a": 1})
    store.store("scope", "k1", body, {"order_id": "ord_1"})
    assert store.lookup("scope", "k1", body) == {"order_id": "ord_1"}


def test_idempotency_rejects_body_mismatch() -> None:
    store = IdempotencyStore()
    store.store("scope", "k1", store.hash_body({"a": 1}), "X")
    with pytest.raises(IdempotencyError):
        store.lookup("scope", "k1", store.hash_body({"a": 2}))


def test_rate_limiter_allows_under_threshold() -> None:
    limiter = RateLimiter()
    for _ in range(3):
        limiter.check(tenant_id="t1", scope="tool", key="u1",
                      max_calls=3, window_seconds=60)


def test_rate_limiter_blocks_over_threshold() -> None:
    limiter = RateLimiter()
    for _ in range(2):
        limiter.check(tenant_id="t1", scope="tool", key="u1",
                      max_calls=2, window_seconds=60)
    with pytest.raises(RateLimitExceeded):
        limiter.check(tenant_id="t1", scope="tool", key="u1",
                      max_calls=2, window_seconds=60)


def test_mask_phone_basic() -> None:
    assert mask_phone("13800001234") == "138****1234"
    assert mask_phone("+85291234567") == "852****4567"
    assert mask_phone("") == ""
    assert mask_phone("123") == "123"  # too short, return as-is


def test_mask_phone_idempotent() -> None:
    once = mask_phone("13800001234")
    assert mask_phone(once) == once  # already masked, untouched


def test_mask_email_basic() -> None:
    assert mask_email("alice@example.com") == "a***@example.com"
    assert mask_email("a@x.io") == "a***@x.io"
    assert mask_email("") == ""
    assert mask_email("not-an-email") == "not-an-email"


@pytest.mark.asyncio
async def test_audited_tool_writes_audit_entry(ctx: ToolContext) -> None:
    DEFAULT_AUDIT_LOG.clear()

    @audited_tool(name="demo.echo", rate_class="L0")
    async def echo(ctx, *, value: str) -> str:
        return value

    result = await echo(ctx, value="hello")
    assert result == "hello"
    tail = DEFAULT_AUDIT_LOG.tail()
    assert len(tail) == 1
    assert tail[0].tool == "demo.echo"
    assert tail[0].success is True
    assert tail[0].tenant_id == ctx.tenant_id


@pytest.mark.asyncio
async def test_audited_tool_records_errors(ctx: ToolContext) -> None:
    DEFAULT_AUDIT_LOG.clear()

    @audited_tool(name="demo.boom", rate_class="L0")
    async def boom(ctx) -> None:
        raise ValueError("kaboom")

    with pytest.raises(ValueError):
        await boom(ctx)

    tail = DEFAULT_AUDIT_LOG.tail()
    assert tail[0].success is False
    assert "ValueError: kaboom" in tail[0].error


@pytest.mark.asyncio
async def test_audited_tool_enforces_rate_limit(ctx: ToolContext) -> None:
    """Rate spec L0 in _demo is 60/60s — drop it for this test by mutating the
    config in place. The decorator looks up rate_class on ctx.config."""
    from brand_bridge.registry.tenant import RateLimit

    DEFAULT_AUDIT_LOG.clear()
    ctx.config.rate_limits["TIGHT"] = RateLimit(max_calls=2, window_seconds=60)

    @audited_tool(name="demo.tight", rate_class="TIGHT")
    async def tight(ctx) -> int:
        return 42

    await tight(ctx)
    await tight(ctx)
    with pytest.raises(RateLimitExceeded):
        await tight(ctx)

    # All three calls audited, even the throttled one
    tail = DEFAULT_AUDIT_LOG.tail()
    assert len(tail) == 3
    assert sum(1 for e in tail if e.success) == 2
    assert sum(1 for e in tail if not e.success) == 1
