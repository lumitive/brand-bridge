"""Reference adapters.

`demo` ships with the platform and is used as a fallback when a tenant.yaml
doesn't specify a concrete provider. Vendor-specific adapters (square, stripe,
twilio_wa, ...) live in sibling packages under this namespace.
"""
