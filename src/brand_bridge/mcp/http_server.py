"""Streamable HTTP MCP server.

Wraps FastMCP's `streamable_http_app()` so a single tenant is served over
HTTP instead of stdio. Production deploys one process (one container) per
tenant; reverse-proxy fan-out by subdomain or path handles fleet-level
multi-tenancy.

Why not Starlette-mount many FastMCPs in one process? Sub-app lifespans
don't propagate through `app.mount()` cleanly — see lumi-agent's CLAUDE.md
for the war story. Until we have a customer that needs in-process multi-
tenancy, the operational simplicity of one-process-per-tenant wins.

For embedding in an existing ASGI app (FastAPI / Starlette), use
`create_http_app(tenant_id)` to get the underlying ASGI callable and mount
it yourself, taking care to forward the FastMCP session-manager lifespan
into your parent app's lifespan context.
"""

from __future__ import annotations

import asyncio
from typing import Any

from .server import create_server


def create_http_app(tenant_id: str) -> Any:
    """Return the Streamable HTTP ASGI app for a tenant. Caller owns the
    lifespan if mounting under a parent ASGI application."""
    return create_server(tenant_id).streamable_http_app()


def run_http(tenant_id: str, *, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the Streamable HTTP server in the foreground. AI hosts connect
    to ``http://<host>:<port>/mcp`` (FastMCP's default mount path)."""
    server = create_server(tenant_id)
    asyncio.run(_serve(server, host=host, port=port))


async def _serve(server: Any, *, host: str, port: int) -> None:
    # Bind via uvicorn so the FastMCP session-manager lifespan runs cleanly.
    import uvicorn

    app = server.streamable_http_app()
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    uv_server = uvicorn.Server(config)
    await uv_server.serve()
