"""Smoke tests for the FastMCP stdio server factory.

We don't spawn a subprocess + MCP client here — that's an end-to-end concern
left for manual verification in Claude Desktop. These tests verify the
in-process surface: tool registration count, tool names, and that calling
a representative tool through `mcp.call_tool` runs the audited adapter.
"""

from __future__ import annotations

import json
import uuid

import pytest

from brand_bridge.core.audit import DEFAULT_AUDIT_LOG
from brand_bridge.mcp.server import create_server

EXPECTED_TOOLS = {
    # Discovery
    "now_time_info", "list_stores", "get_store",
    "list_categories", "list_products", "get_product", "list_modifiers",
    "list_campaigns", "list_available_coupons",
    # Account
    "my_account", "my_coupons", "my_orders",
    "list_addresses", "store_coupons", "inventory_snapshot",
    # Order flow
    "calculate_price", "place_order", "get_order", "cancel_order",
    # Loyalty
    "claim_coupon", "redeem_points",
    # Address
    "create_address",
}


@pytest.fixture
def server():
    return create_server("_demo")


@pytest.mark.asyncio
async def test_all_tools_registered(server) -> None:
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOLS, (
        f"missing: {EXPECTED_TOOLS - names}, extra: {names - EXPECTED_TOOLS}"
    )


@pytest.mark.asyncio
async def test_now_time_info(server) -> None:
    result = await server.call_tool("now_time_info", {})
    payload = _extract_json(result)
    assert "iso" in payload and "weekday" in payload


@pytest.mark.asyncio
async def test_list_stores_returns_demo_data(server) -> None:
    result = await server.call_tool("list_stores", {})
    stores = _extract_json(result)
    assert isinstance(stores, list)
    assert any(s["store_id"] == "STORE_001" for s in stores)


@pytest.mark.asyncio
async def test_full_order_flow_through_mcp(server) -> None:
    """The two-step calculate_price → place_order flow over the MCP surface,
    proving the confirmation-token round-trip works through serialization."""
    DEFAULT_AUDIT_LOG.clear()

    quote_result = await server.call_tool("calculate_price", {
        "store_id": "STORE_001",
        "items": [{"product_code": "D001", "quantity": 2}],
    })
    quote = _extract_json(quote_result)
    assert quote["confirmation_token"].startswith("cfm_")

    order_result = await server.call_tool("place_order", {
        "store_id": "STORE_001",
        "items": [{"product_code": "D001", "quantity": 2}],
        "pickup_type": "pickup",
        "idempotency_key": str(uuid.uuid4()),
        "confirmation_token": quote["confirmation_token"],
    })
    order = _extract_json(order_result)
    assert order["status"] == "pending"
    assert order["order_id"].startswith("ord_")

    # Both calls should be in the audit log
    audited_names = {e.tool for e in DEFAULT_AUDIT_LOG.tail()}
    assert {"calculate_price", "place_order"}.issubset(audited_names)


@pytest.mark.asyncio
async def test_place_order_rejects_stale_token(server) -> None:
    """A second place_order with the same token must fail — single-use."""
    quote_result = await server.call_tool("calculate_price", {
        "store_id": "STORE_001",
        "items": [{"product_code": "D001", "quantity": 1}],
    })
    quote = _extract_json(quote_result)
    token = quote["confirmation_token"]

    await server.call_tool("place_order", {
        "store_id": "STORE_001",
        "items": [{"product_code": "D001", "quantity": 1}],
        "pickup_type": "pickup",
        "idempotency_key": str(uuid.uuid4()),
        "confirmation_token": token,
    })

    with pytest.raises(Exception) as exc:
        await server.call_tool("place_order", {
            "store_id": "STORE_001",
            "items": [{"product_code": "D001", "quantity": 1}],
            "pickup_type": "pickup",
            "idempotency_key": str(uuid.uuid4()),  # fresh idem, stale token
            "confirmation_token": token,
        })
    assert "confirmation_token" in str(exc.value).lower() or \
        "already used" in str(exc.value).lower() or \
        "expired" in str(exc.value).lower()


def _extract_json(call_result):
    """FastMCP `call_tool` returns either a list of content blocks or a tuple
    (content, structured). Fish out the JSON payload either way. FastMCP also
    wraps non-dict return values in {"result": <value>} for structured output —
    unwrap that single-key envelope so callers see the real payload."""
    if isinstance(call_result, tuple):
        content, structured = call_result
        if structured is not None:
            return _unwrap_result(structured)
        return _unwrap_result(_from_content(content))
    return _unwrap_result(_from_content(call_result))


def _unwrap_result(payload):
    if isinstance(payload, dict) and set(payload.keys()) == {"result"}:
        return payload["result"]
    return payload


def _from_content(content):
    # FastMCP wraps return values in TextContent[].text as JSON or a dict
    # under .data depending on version. Try both.
    if isinstance(content, list) and content:
        first = content[0]
        text = getattr(first, "text", None)
        if text is not None:
            try:
                return json.loads(text)
            except (json.JSONDecodeError, TypeError):
                return text
        data = getattr(first, "data", None)
        if data is not None:
            return data
    return content
