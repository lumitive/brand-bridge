"""brand-bridge CLI entry point.

Subcommands:
    tenant ls                        — list configured tenants
    tenant show <tenant_id>          — print resolved config
    tenant validate <tenant_id>      — load + instantiate all providers
    serve --tenant <id>              — start stdio MCP server (M2)

Planned for M3+:
    tenant init <id> --preset coffee — scaffold new tenant.yaml
    tenant onboard <id> <api_docs>   — invoke /brand-onboard skill
    serve --tenant <id> --http       — Streamable HTTP MCP server
"""

from __future__ import annotations

import sys

import click

from brand_bridge.registry import TenantRegistry, load_tenant
from brand_bridge.registry.tenant import _tenants_root


@click.group()
@click.version_option()
def main() -> None:
    """brand-bridge — turn brand back-office into AI-ready capabilities."""


@main.group()
def tenant() -> None:
    """Tenant management commands."""


@tenant.command("ls")
def tenant_ls() -> None:
    root = _tenants_root()
    if not root.is_dir():
        click.echo(f"No tenants directory at {root}", err=True)
        sys.exit(1)
    for child in sorted(root.iterdir()):
        if (child / "tenant.yaml").is_file():
            try:
                cfg = load_tenant(child.name)
                click.echo(f"{cfg.tenant_id:<24} {cfg.tenant_name}")
            except Exception as e:  # noqa: BLE001
                click.echo(f"{child.name:<24} (load error: {e})")


@tenant.command("show")
@click.argument("tenant_id")
def tenant_show(tenant_id: str) -> None:
    cfg = load_tenant(tenant_id)
    click.echo(f"tenant_id     : {cfg.tenant_id}")
    click.echo(f"tenant_name   : {cfg.tenant_name}")
    click.echo(f"locale        : {cfg.locale}")
    click.echo(f"currency      : {cfg.currency}")
    click.echo(f"features      : {cfg.features}")
    click.echo(f"rate_limits   : {[name for name in cfg.rate_limits]}")


@tenant.command("validate")
@click.argument("tenant_id")
def tenant_validate(tenant_id: str) -> None:
    cfg = load_tenant(tenant_id)
    registry = TenantRegistry.from_config(cfg)
    click.echo(f"OK: {cfg.tenant_name}")
    click.echo(f"  master_data : {type(registry.master_data).__name__}")
    click.echo(f"  pos         : {type(registry.pos).__name__}")
    click.echo(f"  crm         : {type(registry.crm).__name__}")
    click.echo(f"  payment     : {type(registry.payment).__name__}")


@main.command("serve")
@click.option("--tenant", "tenant_id", required=True,
              help="Tenant id (subdir name under tenants/).")
@click.option("--http", "use_http", is_flag=True, default=False,
              help="Serve over Streamable HTTP instead of stdio.")
@click.option("--host", default="127.0.0.1", show_default=True,
              help="HTTP bind host (only with --http).")
@click.option("--port", default=8000, type=int, show_default=True,
              help="HTTP bind port (only with --http).")
def serve(tenant_id: str, use_http: bool, host: str, port: int) -> None:
    """Start the MCP server for a tenant.

    Default is stdio (Claude Desktop / ChatGPT launch this as a subprocess
    and speak MCP over stdin/stdout). With --http the Streamable HTTP
    transport binds on host:port and exposes /mcp for remote AI hosts.
    """
    if use_http:
        from brand_bridge.mcp.http_server import run_http
        click.echo(f"[brand-bridge] HTTP MCP for {tenant_id} on http://{host}:{port}/mcp")
        run_http(tenant_id, host=host, port=port)
    else:
        from brand_bridge.mcp.server import run_stdio
        run_stdio(tenant_id)


if __name__ == "__main__":
    main()
