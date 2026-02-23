import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Column, Field
from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime


class KnowledgeBaseEntry(SQLModel, table=True):
    """Represents a knowledge base article with vector embeddings for semantic search"""
    __tablename__: str = "knowledge_base"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str
    content: str
    category: str  # Category of the document (pricing, features, support, etc.)
    embedding: list[float] = Field(sa_column=Column(Vector(384)))  # Vector embedding for semantic search
    relevance_score: Optional[float] = None  # Relevance score for exact text matches
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    )


class SupportTicket(SQLModel, table=True):
    """Represents a customer support request"""
    __tablename__: str = "support_ticket"

    ticket_id: str = Field(default=None, primary_key=True)
    customer_id: str = Field(index=True)
    channel: str  # Communication channel (gmail, whatsapp, web_form)
    query: str  # The original customer query or issue description
    timestamp: datetime  # Timestamp when ticket was created
    escalated: bool = False
    escalation_reason: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    )


class Customer(SQLModel, table=True):
    """Represents a customer in the system"""
    __tablename__: str = "customer"

    customer_id: str = Field(default=None, primary_key=True)
    email: Optional[str] = None  # Customer's email address (may be empty for phone-only customers)
    phone: Optional[str] = None  # Customer's phone number (may be empty for email-only customers)
    plan_type: str  # Subscription plan type (starter, pro, enterprise)
    subscription_status: str  # Current subscription status (active, inactive, suspended)
    last_interaction: Optional[datetime] = None  # Timestamp of last interaction
    # Note: Support tickets are typically referenced separately, not stored as a list in the database
    # The relationship is maintained through foreign keys in the SupportTicket table
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    )


class DocumentationResult(SQLModel, table=True):
    """Represents a knowledge base article retrieved from search"""
    __tablename__: str = "documentation_result"

    id: str = Field(default=None, primary_key=True)
    title: str
    content: str
    category: str  # Category of the document (pricing, features, support, etc.)
    relevance_score: float  # Score representing how relevant the document is to the query
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    )


class EscalationRecord(SQLModel, table=True):
    """Represents an escalation event when a ticket is sent to human agent"""
    __tablename__: str = "escalation_record"

    escalation_id: str = Field(default=None, primary_key=True)
    ticket_id: str = Field(index=True)  # Reference to the ticket being escalated
    reason: str  # Reason for the escalation
    timestamp: datetime  # Time when escalation occurred
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    )
