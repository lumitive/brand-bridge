"""Tenant configuration loader and provider registry.

A tenant is one brand. Its config lives in `tenants/<tenant_id>/tenant.yaml`
and points at provider implementations to instantiate. Unspecified providers
fall back to the demo adapter so a half-configured tenant still boots.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from brand_bridge.core.errors import AdapterError, TenantNotFound
from brand_bridge.core.providers import (
    CRMProvider,
    IMChannelProvider,
    MasterDataProvider,
    PaymentProvider,
    POSProvider,
)


@dataclass
class RateLimit:
    max_calls: int
    window_seconds: int


@dataclass
class TenantConfig:
    tenant_id: str
    tenant_name: str
    locale: str = "en-US"
    currency: str = "USD"
    default_user_id: str = "DEMO_USER"
    instructions: str = ""
    features: dict[str, bool] = field(default_factory=dict)
    rate_limits: dict[str, RateLimit] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def feature(self) -> dict[str, bool]:
        return self.features


def _tenants_root() -> Path:
    override = os.environ.get("BRAND_BRIDGE_TENANTS_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "tenants"


def load_tenant(tenant_id: str) -> TenantConfig:
    """Load a tenant's YAML config from the tenants directory."""
    root = _tenants_root()
    path = root / tenant_id / "tenant.yaml"
    if not path.is_file():
        raise TenantNotFound(f"tenant.yaml not found at {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    rate_limits = {
        name: RateLimit(max_calls=spec["max_calls"], window_seconds=spec["window_seconds"])
        for name, spec in (raw.get("rate_limits") or {}).items()
    }

    return TenantConfig(
        tenant_id=raw.get("tenant_id", tenant_id),
        tenant_name=raw.get("tenant_name", tenant_id),
        locale=raw.get("locale", "en-US"),
        currency=raw.get("currency", "USD"),
        default_user_id=raw.get("default_user_id", "DEMO_USER"),
        instructions=raw.get("instructions", ""),
        features=raw.get("features", {}) or {},
        rate_limits=rate_limits,
        validation=raw.get("validation", {}) or {},
        raw=raw,
    )


def _load_class(module_path: str, class_name: str) -> type:
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise AdapterError(f"failed to import {module_path}: {e}") from e
    try:
        return getattr(module, class_name)
    except AttributeError as e:
        raise AdapterError(f"{module_path} has no attribute {class_name}") from e


def _resolve_provider(spec: dict[str, Any] | None, fallback_module: str,
                      fallback_class: str) -> Any:
    if not spec:
        cls = _load_class(fallback_module, fallback_class)
        return cls
    module = spec.get("module", fallback_module)
    class_name = spec.get("class", fallback_class)
    return _load_class(module, class_name)


@dataclass
class TenantRegistry:
    """Holds the resolved provider instances for one tenant."""
    config: TenantConfig
    master_data: MasterDataProvider
    pos: POSProvider
    crm: CRMProvider
    payment: PaymentProvider
    im_channels: dict[str, IMChannelProvider] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: TenantConfig) -> TenantRegistry:
        providers = config.raw.get("providers") or {}

        md_cls = _resolve_provider(
            providers.get("master_data"),
            "brand_bridge.adapters.demo", "DemoMasterData",
        )
        pos_cls = _resolve_provider(
            providers.get("pos"),
            "brand_bridge.adapters.demo", "DemoPOS",
        )
        crm_cls = _resolve_provider(
            providers.get("crm"),
            "brand_bridge.adapters.demo", "DemoCRM",
        )
        pay_cls = _resolve_provider(
            providers.get("payment"),
            "brand_bridge.adapters.demo", "DemoPayment",
        )

        return cls(
            config=config,
            master_data=md_cls(config),
            pos=pos_cls(config),
            crm=crm_cls(config),
            payment=pay_cls(config),
            im_channels={},  # Populated lazily as channels register
        )
