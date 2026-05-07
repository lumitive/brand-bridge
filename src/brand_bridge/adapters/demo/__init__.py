"""Demo adapter — in-memory implementation of all five providers.

Boots without configuration. Used as the default fallback so a half-finished
tenant.yaml still produces a working MCP server with realistic-looking data.
The shape of returned objects is the contract every real adapter must match.
"""

from .crm import DemoCRM
from .master_data import DemoMasterData
from .payment import DemoPayment
from .pos import DemoPOS

__all__ = ["DemoCRM", "DemoMasterData", "DemoPayment", "DemoPOS"]
