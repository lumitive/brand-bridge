"""IMChannelProvider — WhatsApp / WeChat / SMS / Lark / Slack adapters.

Each tenant can register multiple IM channels. The platform routes outbound
messages by `(tenant_id, channel_kind)` and parses inbound webhooks into a
normalized `InboundMessage` regardless of the source vendor.

Rich replies (UI cards, payment links, suggested replies) are downgraded by
each channel into its native envelope.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ChannelKind(StrEnum):
    WHATSAPP = "whatsapp"
    WECHAT = "wechat"
    SMS = "sms"
    LARK = "lark"
    SLACK = "slack"
    H5 = "h5"
    VOICE = "voice"
    MCP_HOST = "mcp_host"


@dataclass
class ChannelCapabilities:
    text: bool = True
    ui_card: bool = False
    payment_link: bool = False
    image: bool = False
    suggested_replies: bool = False


@dataclass
class InboundMessage:
    kind: ChannelKind
    tenant_id: str
    session_id: str
    cardholder_id: str
    body: str
    user_label: str = ""
    agent_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UIResource:
    uri: str           # ui://kind/{id}
    mime_type: str
    text: str
    kind: str = "card"


@dataclass
class PaymentRequest:
    amount_cents: int
    currency: str = "USD"
    intent: str = ""
    cardholder_id: str = ""
    suggested_token_id: str | None = None


@dataclass
class AgentReply:
    text: str
    ui_resources: list[UIResource] = field(default_factory=list)
    payment_request: PaymentRequest | None = None
    suggested_replies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutboundReply:
    body: str
    media_type: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


class IMChannelProvider(ABC):
    """Channel-specific adapter. One implementation per (tenant, channel_kind)."""

    kind: ChannelKind
    capabilities: ChannelCapabilities

    @abstractmethod
    async def parse_inbound(self, payload: dict[str, Any]) -> InboundMessage: ...

    @abstractmethod
    async def format_reply(self, reply: AgentReply | str) -> OutboundReply: ...

    @abstractmethod
    async def send(self, *, to: str, reply: AgentReply) -> dict[str, Any]: ...

    @abstractmethod
    async def verify_webhook(self, payload: bytes, headers: dict[str, str]) -> bool: ...
