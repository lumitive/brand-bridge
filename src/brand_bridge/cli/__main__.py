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
from pathlib import Path

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
def serve(tenant_id: str) -> None:
    """Start the stdio MCP server for a tenant. AI hosts (Claude Desktop,
    ChatGPT) launch this as a subprocess and speak MCP over stdin/stdout."""
    from brand_bridge.mcp.server import run_stdio
    run_stdio(tenant_id)


if __name__ == "__main__":
    main()
