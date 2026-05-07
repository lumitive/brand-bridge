"""Provider ABCs — the integration contract every brand implements.

Five providers cover the surface area of a brand:
    MasterDataProvider — stores, products, categories, modifiers
    POSProvider        — pricing, ordering, inventory
    CRMProvider        — members, coupons, campaigns, points
    PaymentProvider    — prepay, callback, query, refund
    IMChannelProvider  — outbound message + inbound webhook normalization

Implementations live in `brand_bridge.adapters.<vendor>` (reference) or
`tenants/<tenant_id>/<provider>.py` (brand-specific).
"""

from .crm import CRMProvider
from .im_channel import IMChannelProvider
from .master_data import MasterDataProvider
from .payment import PaymentProvider
from .pos import POSProvider

__all__ = [
    "CRMProvider",
    "IMChannelProvider",
    "MasterDataProvider",
    "PaymentProvider",
    "POSProvider",
]
