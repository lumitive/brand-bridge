"""End-to-end smoke test for the Streamable HTTP MCP server.

Boots `run_http` in a background thread, waits for the port to accept
connections, and verifies the /mcp endpoint responds. Doesn't speak the
full MCP protocol — that's covered in stdio tests; this just confirms the
HTTP plumbing wires up.
"""

from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest

from brand_bridge.mcp.http_server import create_http_app, run_http


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(host: str, port: int, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def test_create_http_app_returns_asgi_callable() -> None:
    """Embedding path: caller mounts our app under their own ASGI server."""
    app = create_http_app("_demo")
    assert callable(app)


def test_run_http_serves_mcp_endpoint() -> None:
    port = _free_port()
    thread = threading.Thread(
        target=run_http, args=("_demo",),
        kwargs={"host": "127.0.0.1", "port": port},
        daemon=True,
    )
    thread.start()
    assert _wait_for_port("127.0.0.1", port), \
        f"server didn't start on 127.0.0.1:{port}"

    # /mcp without proper MCP handshake returns 4xx, not 5xx — that proves
    # the route is mounted and the ASGI lifespan came up cleanly.
    # trust_env=False so a local HTTPS_PROXY/SOCKS env doesn't intercept
    # what is plainly a localhost call.
    try:
        with httpx.Client(trust_env=False, timeout=3.0) as client:
            resp = client.get(f"http://127.0.0.1:{port}/mcp")
    except httpx.HTTPError as e:
        pytest.fail(f"HTTP server unreachable: {e}")
    assert resp.status_code < 500, (
        f"unexpected 5xx — server likely failed to bind FastMCP routes "
        f"({resp.status_code}: {resp.text[:200]})"
    )
