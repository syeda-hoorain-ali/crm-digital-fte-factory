"""Unified message schema for Kafka routing."""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class Channel(str, Enum):
    """Communication channels."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEBFORM = "webform"


class MessageType(str, Enum):
    """Message type."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageDirection(str, Enum):
    """Message direction."""
    CUSTOMER_TO_SUPPORT = "customer_to_support"
    SUPPORT_TO_CUSTOMER = "support_to_customer"


class AttachmentMetadata(BaseModel):
    """Attachment metadata."""
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str | None = None


class ChannelMessage(BaseModel):
    """Unified message schema for all channels."""

    # Core identifiers
    message_id: str = Field(..., description="Unique message identifier")
    channel: Channel = Field(..., description="Source/destination channel")
    message_type: MessageType = Field(..., description="Inbound or outbound")
    direction: MessageDirection = Field(..., description="Message direction")

    # Customer information
    customer_id: str | None = Field(None, description="Customer UUID if identified")
    customer_contact: str = Field(..., description="Email address or phone number")
    customer_name: str | None = Field(None, description="Customer name if available")

    # Message content
    subject: str | None = Field(None, description="Email subject or message title")
    body: str = Field(..., description="Message content")

    # Threading
    thread_id: str | None = Field(None, description="Conversation thread identifier")
    parent_message_id: str | None = Field(None, description="Parent message in thread")

    # Attachments
    attachments: list[AttachmentMetadata] = Field(default_factory=list)

    # Channel-specific metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Channel-specific data")

    # Timestamps
    timestamp: datetime = Field(..., description="Message timestamp")
    received_at: datetime | None = Field(None, description="When system received message")

    # Delivery tracking
    delivery_status: str | None = Field(None, description="sent, delivered, failed, bounced")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
