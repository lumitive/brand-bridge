"""brand-bridge error hierarchy.

Adapters raise these so the platform layer can map them to MCP errors with
appropriate scopes (auth vs validation vs upstream) without leaking adapter
internals to AI hosts.
"""

from __future__ import annotations


class BrandBridgeError(Exception):
    """Base class — never raise this directly."""


class TenantNotFound(BrandBridgeError):
    pass


class AdapterError(BrandBridgeError):
    """Adapter implementation issue — wiring, missing config, contract violation."""


class UpstreamError(BrandBridgeError):
    """Brand backend returned an error or was unreachable."""


class ValidationError(BrandBridgeError):
    """Input failed brand-side validation (whitelisted sizes/milks/extras, etc.)."""


class ConfirmationTokenError(BrandBridgeError):
    """Confirmation token missing, expired, or doesn't match the price quote."""


class IdempotencyError(BrandBridgeError):
    """Duplicate idempotency key with a different request body."""


class RateLimitExceeded(BrandBridgeError):
    """Too many calls within the configured window."""


class ScopeDenied(BrandBridgeError):
    """Caller's JWT scope doesn't grant access to this tool/tenant."""


class FeatureDisabled(BrandBridgeError):
    """Tenant has the feature flag turned off for this capability."""
