# Data Model: Customer Success Agent Production Migration

**Feature**: 005-custom-agent-transition  
**Date**: 2026-02-25 (Updated to match hackathon schema)  
**Phase**: 1 - Design Artifacts

## Overview

This document defines the database schema for the Customer Success Agent production system. All entities are implemented using SQLModel with PostgreSQL (Neon Serverless) and include pgvector support for semantic search.

**Schema Design**: Based on hackathon reference schema with modifications for multi-channel customer support, conversation tracking, and cross-channel customer unification.

---

## Entity Definitions

### 1. Customer

**Purpose**: Represents a unified customer across all communication channels.

**Fields**:
- `id` (UUID, PK): Primary key using gen_random_uuid()
- `email` (str, unique, indexed): Customer email address (nullable for phone-only customers)
- `phone` (str, indexed): Customer phone number (nullable for email-only customers)
- `name` (str): Customer name (nullable)
- `metadata` (dict, JSONB): Flexible metadata storage (account tier, preferences, etc.)
- `created_at` (datetime): Record creation timestamp
- `updated_at` (datetime): Last update timestamp

**Relationships**:
- One-to-many with CustomerIdentifier (customer can have multiple identifiers)
- One-to-many with Conversation (customer can have multiple conversations)
- One-to-many with Ticket (customer can have multiple tickets)

**Validation Rules**:
- Email must be valid format (RFC 5322) if provided
- Phone must be valid format (E.164 recommended) if provided
- At least one of email or phone must be provided

**Indexes**:
- Primary key on `id`
- Unique index on `email` (where email IS NOT NULL)
- Index on `phone`
- Index on `created_at` for time-based queries

**SQLModel Definition**:
```python
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSONB
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

class Customer(SQLModel, table=True):
    """Customer entity with contact information."""
    __tablename__ = "customers"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    )
    email: str | None = Field(default=None, unique=True, index=True, max_length=255)
    phone: str | None = Field(default=None, index=True, max_length=50)
    name: str | None = Field(default=None, max_length=255)
    metadata: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}"))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

### 2. CustomerIdentifier

**Purpose**: Tracks customer identifiers across different channels for cross-channel matching and unification.

**Fields**:
- `id` (UUID, PK): Primary key using gen_random_uuid()
- `customer_id` (UUID, FK): Foreign key to Customer
- `identifier_type` (str, enum): Type of identifier [email, phone, whatsapp]
- `identifier_value` (str): The actual identifier value
- `verified` (bool): Whether this identifier has been verified
- `created_at` (datetime): Record creation timestamp
- `updated_at` (datetime): Last update timestamp

**Relationships**:
- Many-to-one with Customer (identifier belongs to one customer)

**Validation Rules**:
- Identifier type must be one of: email, phone, whatsapp
- Identifier value must not be empty
- Unique constraint on (identifier_type, identifier_value)

**Indexes**:
- Primary key on `id`
- Foreign key index on `customer_id`
- Unique index on `(identifier_type, identifier_value)`
- Index on `identifier_value` for fast lookups

**SQLModel Definition**:
```python
from enum import Enum

class IdentifierType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    WHATSAPP = "whatsapp"

class CustomerIdentifier(SQLModel, table=True):
    """Customer identifier for cross-channel matching."""
    __tablename__ = "customer_identifiers"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    )
    customer_id: uuid.UUID = Field(foreign_key="customers.id", index=True)
    identifier_type: IdentifierType
    identifier_value: str = Field(min_length=1, max_length=255)
    verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        # Unique constraint on (identifier_type, identifier_value)
        table_args = (
            UniqueConstraint('identifier_type', 'identifier_value', name='uq_identifier_type_value'),
        )
```

---

### 3. Conversation

**Purpose**: Represents a conversation session with a customer, tracking the lifecycle from start to resolution.

**Fields**:
- `id` (UUID, PK): Primary key using gen_random_uuid()
- `customer_id` (UUID, FK): Foreign key to Customer
- `initial_channel` (str, enum): Channel where conversation started [email, whatsapp, web_form, api]
- `started_at` (datetime): Conversation start timestamp
- `ended_at` (datetime): Conversation end timestamp (nullable)
- `status` (str, enum): Conversation status [active, resolved, escalated, closed]
- `sentiment_score` (float): Overall conversation sentiment score
- `resolution_type` (str): Type of resolution (nullable)
- `escalated_to` (str): Who/where conversation was escalated to (nullable)
- `metadata` (dict, JSONB): Flexible metadata storage
- `updated_at` (datetime): Last update timestamp

**Relationships**:
- Many-to-one with Customer (conversation belongs to one customer)
- One-to-many with Message (conversation has multiple messages)
- One-to-many with Ticket (conversation can have multiple tickets)

**Validation Rules**:
- Initial channel must be one of: email, whatsapp, web_form, api
- Status must be one of: active, resolved, escalated, closed
- Sentiment score must be between -1.0 and 1.0 if provided

**Indexes**:
- Primary key on `id`
- Foreign key index on `customer_id`
- Index on `status`
- Index on `initial_channel`
- Composite index on `(customer_id, started_at)` for customer history

**SQLModel Definition**:
```python
class Channel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"
    API = "api"

class ConversationStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"

class Conversation(SQLModel, table=True):
    """Conversation entity tracking customer interaction lifecycle."""
    __tablename__ = "conversations"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    )
    customer_id: uuid.UUID = Field(foreign_key="customers.id", index=True)
    initial_channel: Channel
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = Field(default=None)
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE)
    sentiment_score: float | None = Field(default=None, ge=-1.0, le=1.0)
    resolution_type: str | None = Field(default=None, max_length=50)
    escalated_to: str | None = Field(default=None, max_length=255)
    metadata: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}"))
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

### 4. Message

**Purpose**: Represents a single message in a conversation with full observability tracking. Also serves as storage backend for custom PostgreSQL session implementation.

**Fields**:
- `id` (UUID, PK): Primary key using gen_random_uuid()
- `conversation_id` (UUID, FK): Foreign key to Conversation (also serves as session_id for session isolation)
- `channel` (str, enum): Communication channel [email, whatsapp, web_form, api]
- `direction` (str, enum): Message direction [inbound, outbound]
- `role` (str, enum): Message role [customer, agent, system]
- `content` (str): Message content
- `sentiment_score` (float): Sentiment score for this message (nullable)
- `tokens_used` (int): Number of tokens used (for cost tracking)
- `latency_ms` (int): Processing latency in milliseconds
- `tool_calls` (dict, JSONB): Agent tool calls made during processing
- `channel_message_id` (str): External message ID (Gmail message ID, Twilio SID, etc.)
- `delivery_status` (str, enum): Delivery status [pending, sent, delivered, failed]
- `created_at` (datetime): Message timestamp (also used for session item ordering)
- `updated_at` (datetime): Last update timestamp

**Session Implementation Notes**:
- Message table serves dual purpose: business data storage + session memory backend
- Session operations map to Message CRUD filtered by conversation_id:
  - `get_items()`: Query messages by conversation_id, transform to EasyInputMessageParam (role mapping: customer→user, agent→assistant; phase: agent→"final_answer", user→None; type: "message")
  - `add_items()`: Insert messages from EasyInputMessageParam items (extract content, role; derive business role from SDK role)
  - `pop_item()`: Delete most recent message by conversation_id ordered by created_at DESC
  - `clear_session()`: No-op (pass) to preserve all message data for audit trail. To start fresh conversation, create new Conversation with new conversation_id.
- No additional storage needed - existing fields (content, role, created_at) provide all data for session memory

**Relationships**:
- Many-to-one with Conversation (message belongs to one conversation)

**Validation Rules**:
- Channel must be one of: email, whatsapp, web_form, api
- Direction must be one of: inbound, outbound
- Role must be one of: customer, agent, system
- Sentiment score must be between -1.0 and 1.0 if provided
- Content must not be empty
- Delivery status must be one of: pending, sent, delivered, failed

**Indexes**:
- Primary key on `id`
- Foreign key index on `conversation_id`
- Index on `channel`
- Composite index on `(conversation_id, created_at)` for conversation history

**SQLModel Definition**:
```python
class MessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"

class MessageRole(str, Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    SYSTEM = "system"

class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"

class Message(SQLModel, table=True):
    """Message entity for conversation tracking with observability."""
    __tablename__ = "messages"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    )
    conversation_id: uuid.UUID = Field(foreign_key="conversations.id", index=True)
    channel: Channel
    direction: MessageDirection
    role: MessageRole
    content: str = Field(min_length=1)
    sentiment_score: float | None = Field(default=None, ge=-1.0, le=1.0)
    tokens_used: int | None = Field(default=None)
    latency_ms: int | None = Field(default=None)
    tool_calls: dict = Field(default_factory=list, sa_column=Column(JSONB, nullable=False, server_default="[]"))
    channel_message_id: str | None = Field(default=None, max_length=255)
    delivery_status: DeliveryStatus = Field(default=DeliveryStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

### 5. Ticket

**Purpose**: Represents a customer support ticket linked to a conversation.

**Fields**:
- `id` (UUID, PK): Primary key using gen_random_uuid()
- `conversation_id` (UUID, FK): Foreign key to Conversation
- `customer_id` (UUID, FK): Foreign key to Customer
- `source_channel` (str, enum): Channel where ticket originated [email, whatsapp, web_form, api]
- `category` (str): Ticket category (nullable)
- `priority` (str, enum): Priority level [low, medium, high, critical]
- `status` (str, enum): Ticket status [open, in_progress, resolved, closed]
- `created_at` (datetime): Ticket creation timestamp
- `resolved_at` (datetime): Ticket resolution timestamp (nullable)
- `resolution_notes` (str): Notes about resolution (nullable)
- `updated_at` (datetime): Last update timestamp

**Relationships**:
- Many-to-one with Conversation (ticket belongs to one conversation)
- Many-to-one with Customer (ticket belongs to one customer)

**Validation Rules**:
- Source channel must be one of: email, whatsapp, web_form, api
- Priority must be one of: low, medium, high, critical
- Status must be one of: open, in_progress, resolved, closed

**Indexes**:
- Primary key on `id`
- Foreign key index on `conversation_id`
- Foreign key index on `customer_id`
- Index on `status`
- Index on `source_channel`
- Composite index on `(status, created_at)` for filtering

**SQLModel Definition**:
```python
class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class Ticket(SQLModel, table=True):
    """Support ticket entity."""
    __tablename__ = "tickets"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    )
    conversation_id: uuid.UUID = Field(foreign_key="conversations.id", index=True)
    customer_id: uuid.UUID = Field(foreign_key="customers.id", index=True)
    source_channel: Channel
    category: str | None = Field(default=None, max_length=100)
    priority: Priority = Field(default=Priority.MEDIUM)
    status: TicketStatus = Field(default=TicketStatus.OPEN)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = Field(default=None)
    resolution_notes: str | None = Field(default=None)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

### 6. KnowledgeBase

**Purpose**: Represents a knowledge base article with vector embedding for semantic search.

**Fields**:
- `id` (UUID, PK): Primary key using gen_random_uuid()
- `title` (str): Article title
- `content` (str): Article content (markdown)
- `category` (str): Article category (nullable)
- `embedding` (vector): 384-dimensional vector embedding (FastEmbed all-MiniLM-L6-v2)
- `created_at` (datetime): Article creation timestamp
- `updated_at` (datetime): Last update timestamp

**Relationships**:
- None (standalone entity)

**Validation Rules**:
- Title must not be empty
- Content must not be empty
- Embedding must be 384 dimensions

**Indexes**:
- Primary key on `id`
- Index on `category` for filtering
- HNSW index on `embedding` for vector similarity search

**SQLModel Definition**:
```python
from pgvector.sqlalchemy import Vector

class KnowledgeBase(SQLModel, table=True):
    """Knowledge base article with vector embedding."""
    __tablename__ = "knowledge_base"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    )
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    category: str | None = Field(default=None, max_length=100, index=True)
    embedding: list[float] = Field(sa_column=Column(Vector(384)))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

### 7. ChannelConfig

**Purpose**: Stores channel-specific configuration for multi-channel support.

**Fields**:
- `id` (UUID, PK): Primary key using gen_random_uuid()
- `channel` (str, enum, unique): Channel name [email, whatsapp, web_form, api]
- `enabled` (bool): Whether channel is enabled
- `config` (dict, JSONB): Channel-specific configuration (API keys, webhook URLs, etc.)
- `response_template` (str): Default response template for channel (nullable)
- `max_response_length` (int): Maximum response length for channel (nullable)
- `created_at` (datetime): Record creation timestamp
- `updated_at` (datetime): Last update timestamp

**Relationships**:
- None (standalone configuration entity)

**Validation Rules**:
- Channel must be one of: email, whatsapp, web_form, api
- Channel must be unique
- Config must be valid JSON

**Indexes**:
- Primary key on `id`
- Unique index on `channel`

**SQLModel Definition**:
```python
class ChannelConfig(SQLModel, table=True):
    """Channel configuration entity."""
    __tablename__ = "channel_configs"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    )
    channel: Channel = Field(unique=True)
    enabled: bool = Field(default=True)
    config: dict = Field(sa_column=Column(JSONB, nullable=False))
    response_template: str | None = Field(default=None)
    max_response_length: int | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

### 8. AgentMetric

**Purpose**: Tracks agent performance metrics for observability and analytics.

**Fields**:
- `id` (UUID, PK): Primary key using gen_random_uuid()
- `metric_name` (str): Name of the metric
- `metric_value` (float): Metric value
- `channel` (str, enum): Channel-specific metric (nullable)
- `dimensions` (dict, JSONB): Additional metric dimensions
- `recorded_at` (datetime): Metric recording timestamp

**Relationships**:
- None (standalone metrics entity)

**Validation Rules**:
- Metric name must not be empty
- Channel must be one of: email, whatsapp, web_form, api (if provided)

**Indexes**:
- Primary key on `id`
- Index on `metric_name`
- Index on `recorded_at` for time-series queries
- Composite index on `(metric_name, recorded_at)` for metric queries

**SQLModel Definition**:
```python
class AgentMetric(SQLModel, table=True):
    """Agent performance metrics entity."""
    __tablename__ = "agent_metrics"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    )
    metric_name: str = Field(min_length=1, max_length=100)
    metric_value: float
    channel: Channel | None = Field(default=None)
    dimensions: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}"))
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## Entity Relationship Diagram

```
┌──────────────────┐
│    Customer      │
│──────────────────│
│ id (UUID, PK)    │◄────┐
│ email            │     │
│ phone            │     │ 1:N
│ name             │     │
│ metadata         │     │
│ created_at       │     │
│ updated_at       │     │
└──────────────────┘     │
         │               │
         │ 1:N           │
         ▼               │
┌──────────────────┐     │
│CustomerIdentifier│     │
│──────────────────│     │
│ id (UUID, PK)    │     │
│ customer_id (FK) │─────┘
│ identifier_type  │
│ identifier_value │
│ verified         │
│ created_at       │
│ updated_at       │
└──────────────────┘

┌──────────────────┐
│   Conversation   │
│──────────────────│
│ id (UUID, PK)    │◄────┐
│ customer_id (FK) │─────┼─── Customer (1:N)
│ initial_channel  │     │
│ started_at       │     │ 1:N
│ ended_at         │     │
│ status           │     │
│ sentiment_score  │     │
│ resolution_type  │     │
│ escalated_to     │     │
│ metadata         │     │
│ updated_at       │     │
└──────────────────┘     │
         │               │
         │ 1:N           │
         ▼               │
┌──────────────────┐     │
│     Message      │     │
│──────────────────│     │
│ id (UUID, PK)    │     │
│ conversation_id  │─────┘
│ channel          │
│ direction        │
│ role             │
│ content          │
│ sentiment_score  │
│ tokens_used      │
│ latency_ms       │
│ tool_calls       │
│ channel_msg_id   │
│ delivery_status  │
│ created_at       │
│ updated_at       │
└──────────────────┘

┌──────────────────┐
│     Ticket       │
│──────────────────│
│ id (UUID, PK)    │
│ conversation_id  │─── Conversation (N:1)
│ customer_id (FK) │─── Customer (N:1)
│ source_channel   │
│ category         │
│ priority         │
│ status           │
│ created_at       │
│ resolved_at      │
│ resolution_notes │
│ updated_at       │
└──────────────────┘

┌──────────────────┐
│  KnowledgeBase   │ (standalone)
│──────────────────│
│ id (UUID, PK)    │
│ title            │
│ content          │
│ category         │
│ embedding (384)  │
│ created_at       │
│ updated_at       │
└──────────────────┘

┌──────────────────┐
│  ChannelConfig   │ (standalone)
│──────────────────│
│ id (UUID, PK)    │
│ channel (unique) │
│ enabled          │
│ config           │
│ response_template│
│ max_resp_length  │
│ created_at       │
│ updated_at       │
└──────────────────┘

┌──────────────────┐
│   AgentMetrics   │ (standalone)
│──────────────────│
│ id (UUID, PK)    │
│ metric_name      │
│ metric_value     │
│ channel          │
│ dimensions       │
│ recorded_at      │
└──────────────────┘
```

---

## Database Constraints

### Foreign Key Constraints
- `customer_identifiers.customer_id` ΓåÆ `customers.id` (ON DELETE CASCADE)
- `conversations.customer_id` ΓåÆ `customers.id` (ON DELETE CASCADE)
- `messages.conversation_id` ΓåÆ `conversations.id` (ON DELETE CASCADE)
- `tickets.conversation_id` ΓåÆ `conversations.id` (ON DELETE CASCADE)
- `tickets.customer_id` ΓåÆ `customers.id` (ON DELETE CASCADE)

### Unique Constraints
- `customers.email` (unique, where email IS NOT NULL)
- `customer_identifiers.(identifier_type, identifier_value)` (unique)
- `channel_configs.channel` (unique)

### Check Constraints
- `messages.sentiment_score` BETWEEN -1.0 AND 1.0
- `conversations.sentiment_score` BETWEEN -1.0 AND 1.0
- All enum fields validated by SQLModel

---

## Migration Strategy

### Initial Migration (Alembic)
```python
# alembic/versions/001_initial_schema.py

def upgrade():
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create tables in dependency order
    op.create_table('customers', ...)
    op.create_table('customer_identifiers', ...)
    op.create_table('conversations', ...)
    op.create_table('messages', ...)
    op.create_table('tickets', ...)
    op.create_table('knowledge_base', ...)
    op.create_table('channel_configs', ...)
    op.create_table('agent_metrics', ...)
    
    # Create vector index for semantic search
    op.execute('''
        CREATE INDEX knowledge_base_embedding_idx
        ON knowledge_base
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    ''')
    
    # Create additional indexes
    op.create_index('idx_customers_email', 'customers', ['email'])
    op.create_index('idx_customer_identifiers_value', 'customer_identifiers', ['identifier_value'])
    op.create_index('idx_conversations_customer', 'conversations', ['customer_id'])
    op.create_index('idx_conversations_status', 'conversations', ['status'])
    op.create_index('idx_conversations_channel', 'conversations', ['initial_channel'])
    op.create_index('idx_messages_conversation', 'messages', ['conversation_id'])
    op.create_index('idx_messages_channel', 'messages', ['channel'])
    op.create_index('idx_tickets_status', 'tickets', ['status'])
    op.create_index('idx_tickets_channel', 'tickets', ['source_channel'])

def downgrade():
    op.drop_table('agent_metrics')
    op.drop_table('channel_configs')
    op.drop_table('knowledge_base')
    op.drop_table('tickets')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('customer_identifiers')
    op.drop_table('customers')
    op.execute('DROP EXTENSION IF EXISTS vector')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
```

---

## Performance Considerations

### Indexes
- All foreign keys have indexes for JOIN performance
- Composite indexes on frequently queried combinations
- HNSW/IVFFlat index on embeddings for fast vector similarity search
- Indexes on enum fields for filtering

### Connection Pooling
- Pool size: 5 connections
- Max overflow: 10 additional connections
- Pool pre-ping: Enabled for stale connection detection
- Pool recycle: 300 seconds (5 minutes)

### Query Optimization
- Use `selectinload()` for eager loading relationships
- Limit result sets with pagination
- Use covering indexes where possible
- Monitor slow queries with `echo=True` in development

---

## Data Integrity

### Cascading Deletes
- Deleting a customer cascades to all identifiers, conversations, tickets, and messages
- Deleting a conversation cascades to all messages and tickets

### Cross-Channel Customer Unification
- CustomerIdentifier table enables linking same customer across channels
- Agent tools use identifier lookups to find unified customer record
- Multiple phone numbers/emails can map to single customer

---
