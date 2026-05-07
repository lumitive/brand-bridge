"""ToolContext — what every tool handler receives.

Carries the resolved tenant identity, the caller's user_id, and the registry
of provider instances. Built once per request by the MCP / REST entrypoint
and threaded through all tool handlers; tool code never imports the global
registry directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brand_bridge.registry.tenant import TenantConfig, TenantRegistry


@dataclass
class ToolContext:
    tenant_id: str
    user_id: str
    config: "TenantConfig"
    registry: "TenantRegistry"
