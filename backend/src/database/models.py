"""Database models and enums for the CRM system."""

from enum import Enum
from datetime import datetime, timezone
import uuid

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import DateTime, UniqueConstraint, text, JSON
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector


class IdentifierType(str, Enum):
    """Customer identifier types."""
    EMAIL = "email"
    PHONE = "phone"
    WHATSAPP = "whatsapp"


class Channel(str, Enum):
    """Communication channels."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"
    API = "api"


class ConversationStatus(str, Enum):
    """Conversation status values."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class MessageDirection(str, Enum):
    """Message direction values."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageRole(str, Enum):
    """Message role values."""
    CUSTOMER = "customer"
    AGENT = "agent"
    SYSTEM = "system"


class DeliveryStatus(str, Enum):
    """Message delivery status values."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class WebhookProcessingStatus(str, Enum):
    """Webhook processing status values."""
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Priority(str, Enum):
    """Priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(str, Enum):
    """Ticket status values."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# Database Models

class Customer(SQLModel, table=True):
    """Customer entity with contact information."""
    __tablename__ = "customers"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    email: str | None = Field(default=None, unique=True, index=True, max_length=255)
    phone: str | None = Field(default=None, index=True, max_length=50)
    name: str | None = Field(default=None, max_length=255)
    metadata_: dict = Field(
        default_factory=dict, sa_column=Column(
        "metadata", JSON, nullable=False, server_default=text("'{}'::jsonb"))
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class CustomerIdentifier(SQLModel, table=True):
    """Customer identifier for cross-channel matching."""
    __tablename__ = "customer_identifiers"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    customer_id: uuid.UUID = Field(foreign_key="customers.id", index=True)
    identifier_type: IdentifierType
    identifier_value: str = Field(min_length=1, max_length=255)
    verified: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    class Config:
        table_args = (
            UniqueConstraint('identifier_type', 'identifier_value', name='uq_identifier_type_value'),
        )


class Conversation(SQLModel, table=True):
    """Conversation entity tracking customer interaction lifecycle."""
    __tablename__ = "conversations"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    customer_id: uuid.UUID = Field(foreign_key="customers.id", index=True)
    initial_channel: Channel
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    ended_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE)
    sentiment_score: float | None = Field(default=None, ge=-1.0, le=1.0)
    resolution_type: str | None = Field(default=None, max_length=50)
    escalated_to: str | None = Field(default=None, max_length=255)
    metadata_: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False, server_default=text("'{}'::jsonb"))
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class Message(SQLModel, table=True):
    """Message entity for conversation tracking with observability."""
    __tablename__ = "messages"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    conversation_id: uuid.UUID = Field(foreign_key="conversations.id", index=True)
    channel: Channel
    direction: MessageDirection
    role: MessageRole
    content: str = Field(min_length=1)
    sentiment_score: float | None = Field(default=None, ge=-1.0, le=1.0)
    tokens_used: int | None = Field(default=None)
    latency_ms: int | None = Field(default=None)
    tool_calls: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False, server_default=text("'[]'::jsonb")))
    channel_message_id: str | None = Field(default=None, max_length=255)
    delivery_status: DeliveryStatus = Field(default=DeliveryStatus.PENDING)
    # Channel integration extensions
    thread_id: str | None = Field(default=None, max_length=255, index=True)
    parent_message_id: uuid.UUID | None = Field(default=None, foreign_key="messages.id", index=True)
    retry_count: int = Field(default=0, ge=0, le=3)
    retry_after: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), index=True))
    webhook_signature: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class Ticket(SQLModel, table=True):
    """Support ticket entity."""
    __tablename__ = "tickets"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    conversation_id: uuid.UUID = Field(foreign_key="conversations.id", index=True)
    customer_id: uuid.UUID = Field(foreign_key="customers.id", index=True)
    source_channel: Channel
    category: str | None = Field(default=None, max_length=100)
    priority: Priority = Field(default=Priority.MEDIUM)
    status: TicketStatus = Field(default=TicketStatus.OPEN)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    resolved_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )
    resolution_notes: str | None = Field(default=None)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class KnowledgeBase(SQLModel, table=True):
    """Knowledge base article with vector embedding."""
    __tablename__ = "knowledge_base"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    category: str | None = Field(default=None, max_length=100, index=True)
    embedding: list[float] = Field(sa_column=Column(Vector(384)))
    metadata_: dict = Field(
        default_factory=dict, sa_column=Column(
        "metadata", JSON, nullable=False, server_default=text("'{}'::jsonb"))
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class ChannelConfig(SQLModel, table=True):
    """Channel configuration entity."""
    __tablename__ = "channel_configs"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    channel: Channel = Field(unique=True)
    enabled: bool = Field(default=True)
    config: dict = Field(sa_column=Column(JSON, nullable=False))
    response_template: str | None = Field(default=None)
    max_response_length: int | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class AgentMetric(SQLModel, table=True):
    """Agent performance metrics entity."""
    __tablename__ = "agent_metrics"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    conversation_id: uuid.UUID = Field(foreign_key="conversations.id", index=True)
    channel: Channel | None = Field(default=None)
    tokens_used: int = Field()
    latency_ms: int = Field()
    tool_call_count: int = Field(default=0)
    estimated_cost: float = Field()
    success: bool = Field(default=True)
    error_message: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class ChannelConfiguration(SQLModel, table=True):
    """Channel configuration for multi-channel intake."""
    __tablename__ = "channel_configurations"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    channel: Channel = Field(unique=True, index=True)
    enabled: bool = Field(default=True)
    config: dict = Field(
        default_factory=dict,
        sa_column=Column("config", JSON, nullable=False, server_default=text("'{}'::jsonb"))
    )
    webhook_secret: str | None = Field(default=None, max_length=255)
    response_template: str | None = Field(default=None)
    max_response_length: int | None = Field(default=None, ge=1)
    rate_limit_per_minute: int = Field(default=10, ge=1, le=100)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class MessageAttachment(SQLModel, table=True):
    """Message attachment metadata."""
    __tablename__ = "message_attachments"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    message_id: uuid.UUID = Field(foreign_key="messages.id", index=True)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(ge=0, le=10485760)  # 10MB limit
    storage_path: str | None = Field(default=None, max_length=500)
    checksum: str | None = Field(default=None, max_length=64)
    is_malicious: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class WebhookDeliveryLog(SQLModel, table=True):
    """Webhook delivery audit log."""
    __tablename__ = "webhook_delivery_logs"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    webhook_type: str = Field(min_length=1, max_length=50, index=True)
    request_id: str | None = Field(default=None, max_length=100)
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    signature_valid: bool = Field(default=False)
    payload: dict = Field(
        default_factory=dict,
        sa_column=Column("payload", JSON, nullable=False, server_default=text("'{}'::jsonb"))
    )
    processing_status: WebhookProcessingStatus = Field(default=WebhookProcessingStatus.RECEIVED, index=True)
    error_message: str | None = Field(default=None)
    retry_count: int = Field(default=0, ge=0, le=3)
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))

class RateLimitEntry(SQLModel, table=True):
    """Rate limit tracking per customer."""
    __tablename__ = "rate_limit_entries"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    customer_id: uuid.UUID = Field(foreign_key="customers.id", index=True)
    channel: Channel
    request_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    window_start: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    request_count: int = Field(default=1, ge=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class GmailWatchState(SQLModel, table=True):
    """Tracks Gmail watch state and last processed history ID per email account."""
    __tablename__ = "gmail_watch_states"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    )
    email: str = Field(index=True, unique=True, description="Gmail account email address")
    last_history_id: str = Field(description="Last processed Gmail history ID")
    watch_expiration: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the Gmail watch expires"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=text("CURRENT_TIMESTAMP"))
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


