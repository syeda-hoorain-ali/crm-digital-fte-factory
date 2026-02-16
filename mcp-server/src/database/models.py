from sqlmodel import SQLModel, Field
from typing import Optional


class SupportTicket(SQLModel, table=True):
    """Represents a customer support request"""
    ticket_id: str = Field(default=None, primary_key=True)
    customer_id: str = Field(index=True)
    channel: str  # Communication channel (gmail, whatsapp, web_form)
    query: str  # The original customer query or issue description
    timestamp: str  # ISO format timestamp when ticket was created
    escalated: bool = False
    escalation_reason: Optional[str] = None


class Customer(SQLModel, table=True):
    """Represents a customer in the system"""
    customer_id: str = Field(default=None, primary_key=True)
    email: str  # Customer's email address (may be empty for phone-only customers)
    plan_type: str  # Subscription plan type (starter, pro, enterprise)
    subscription_status: str  # Current subscription status (active, inactive, suspended)
    last_interaction: str  # Timestamp of last interaction
    # Note: Support tickets are typically referenced separately, not stored as a list in the database
    # The relationship is maintained through foreign keys in the SupportTicket table


class DocumentationResult(SQLModel, table=True):
    """Represents a knowledge base article retrieved from search"""
    id: str = Field(default=None, primary_key=True)
    title: str
    content: str
    category: str  # Category of the document (pricing, features, support, etc.)
    relevance_score: float  # Score representing how relevant the document is to the query


class EscalationRecord(SQLModel, table=True):
    """Represents an escalation event when a ticket is sent to human agent"""
    escalation_id: str = Field(default=None, primary_key=True)
    ticket_id: str = Field(index=True)  # Reference to the ticket being escalated
    reason: str  # Reason for the escalation
    timestamp: str  # Time when escalation occurred
