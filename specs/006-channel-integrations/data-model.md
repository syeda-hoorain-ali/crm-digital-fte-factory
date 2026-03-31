# Data Model: Multi-Channel Customer Intake

**Feature**: 006-channel-integrations
**Date**: 2026-03-04
**Purpose**: Entity definitions and data structures for channel integrations

## Overview

This feature extends the existing database schema from feature 005 (custom-agent-transition) to support multi-channel message intake. The core entities (customers, conversations, messages, tickets) already exist. This document defines new entities and extensions needed for channel-specific functionality.

---

## Existing Entities (from feature 005)

These entities are already defined in the database and will be reused:

### Customer
- **Purpose**: Represents a unique customer across all channels
- **Key Fields**: id (UUID), email, phone, name, created_at, metadata (JSONB)
- **Usage**: Cross-channel customer identification

### Customer Identifier
- **Purpose**: Links multiple contact methods to a single customer
- **Key Fields**: id, customer_id (FK), identifier_type (email/phone/whatsapp), identifier_value, verified
- **Usage**: Cross-channel customer matching

### Conversation
- **Purpose**: Represents a support conversation thread
- **Key Fields**: id, customer_id (FK), initial_channel, started_at, ended_at, status, sentiment_score
- **Usage**: Maintains conversation context across messages

### Message
- **Purpose**: Individual message in a conversation
- **Key Fields**: id, conversation_id (FK), channel, direction (inbound/outbound), role, content, created_at, tokens_used, latency_ms, tool_calls (JSONB), channel_message_id, delivery_status
- **Usage**: Stores all messages with channel tracking

### Ticket
- **Purpose**: Support ticket linked to conversation
- **Key Fields**: id, conversation_id (FK), customer_id (FK), source_channel, category, priority, status, created_at, resolved_at
- **Usage**: Ticket tracking and escalation

---

## New Entities

### ChannelConfiguration
**Purpose**: Stores configuration for each communication channel

**Fields**:
- `id`: UUID (primary key)
- `channel`: VARCHAR(50) (unique) - Channel identifier (email, whatsapp, webform)
- `enabled`: BOOLEAN - Whether channel is active
- `config`: JSONB - Channel-specific configuration
  - For email: `{"gmail_credentials_path": "...", "pubsub_topic": "...", "support_address": "..."}`
  - For whatsapp: `{"twilio_account_sid": "...", "twilio_auth_token": "...", "from_number": "..."}`
  - For webform: `{"form_url": "...", "confirmation_template": "..."}`
- `webhook_secret`: VARCHAR(255) - HMAC secret for webhook verification
- `response_template`: TEXT - Default response template for channel
- `max_response_length`: INTEGER - Character limit for responses
- `rate_limit_per_minute`: INTEGER - Rate limit threshold (default: 10)
- `created_at`: TIMESTAMP WITH TIME ZONE
- `updated_at`: TIMESTAMP WITH TIME ZONE

**Relationships**:
- None (configuration table)

**Validation Rules**:
- `channel` must be unique
- `config` must be valid JSON
- `max_response_length` must be positive
- `rate_limit_per_minute` must be between 1 and 100

**State Transitions**:
- `enabled`: true ↔ false (admin action)

---

### MessageAttachment
**Purpose**: Stores metadata for email attachments

**Fields**:
- `id`: UUID (primary key)
- `message_id`: UUID (foreign key → messages.id)
- `filename`: VARCHAR(255) - Original filename
- `content_type`: VARCHAR(100) - MIME type
- `size_bytes`: INTEGER - File size in bytes
- `storage_path`: VARCHAR(500) - Path to stored file (S3/MinIO)
- `checksum`: VARCHAR(64) - SHA-256 checksum for integrity
- `is_malicious`: BOOLEAN - Malware scan result
- `created_at`: TIMESTAMP WITH TIME ZONE

**Relationships**:
- Many-to-one with Message (message_id)

**Validation Rules**:
- `size_bytes` must be ≤ 10MB (10,485,760 bytes)
- `content_type` must be in allowed list (exclude executables)
- `filename` must not contain path traversal characters

---

### RateLimitEntry
**Purpose**: Tracks rate limit state per customer (if not using Redis)

**Fields**:
- `id`: UUID (primary key)
- `customer_id`: UUID (foreign key → customers.id)
- `channel`: VARCHAR(50) - Channel where request occurred
- `request_timestamp`: TIMESTAMP WITH TIME ZONE - When request was made
- `window_start`: TIMESTAMP WITH TIME ZONE - Start of current rate limit window
- `request_count`: INTEGER - Number of requests in current window

**Relationships**:
- Many-to-one with Customer (customer_id)

**Validation Rules**:
- `request_count` must be non-negative
- `window_start` must be ≤ `request_timestamp`

**Indexes**:
- Composite index on (customer_id, window_start) for fast lookups
- TTL index to auto-delete old entries (> 1 hour)

**Note**: This table is optional if Redis is used for rate limiting. Redis is preferred for distributed systems.

---

### WebhookDeliveryLog
**Purpose**: Audit log for webhook deliveries and retries

**Fields**:
- `id`: UUID (primary key)
- `webhook_type`: VARCHAR(50) - Type of webhook (gmail, whatsapp, webform)
- `request_id`: VARCHAR(100) - Unique request identifier
- `received_at`: TIMESTAMP WITH TIME ZONE - When webhook was received
- `signature_valid`: BOOLEAN - HMAC signature verification result
- `payload`: JSONB - Webhook payload (for debugging)
- `processing_status`: VARCHAR(50) - Status (received, processing, completed, failed)
- `error_message`: TEXT - Error details if failed
- `retry_count`: INTEGER - Number of retry attempts
- `completed_at`: TIMESTAMP WITH TIME ZONE - When processing completed

**Relationships**:
- None (audit log)

**Validation Rules**:
- `retry_count` must be between 0 and 3
- `processing_status` must be valid enum value

**State Transitions**:
- received → processing → completed
- received → processing → failed (with retries)

**Retention Policy**:
- Keep for 90 days for audit compliance
- Archive to cold storage after 30 days

---

## Extended Entities

### Message (Extensions)
**New Fields Added**:
- `thread_id`: VARCHAR(255) - Email thread identifier (from In-Reply-To header)
- `parent_message_id`: UUID - Reference to parent message in thread
- `retry_count`: INTEGER - Number of delivery retry attempts
- `retry_after`: TIMESTAMP WITH TIME ZONE - When to retry delivery
- `webhook_signature`: VARCHAR(255) - HMAC signature for verification

**Indexes Added**:
- Index on `thread_id` for email thread lookups
- Index on `parent_message_id` for conversation threading
- Index on `retry_after` for retry queue processing

---

## Unified Channel Message Schema (Kafka)

**Purpose**: Standardized message format for Kafka topics

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class Channel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEBFORM = "webform"

class MessageType(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"

class MessageDirection(str, Enum):
    CUSTOMER_TO_SUPPORT = "customer_to_support"
    SUPPORT_TO_CUSTOMER = "support_to_customer"

class AttachmentMetadata(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    storage_path: Optional[str] = None

class ChannelMessage(BaseModel):
    """Unified message schema for all channels"""

    # Core identifiers
    message_id: str = Field(..., description="Unique message identifier")
    channel: Channel = Field(..., description="Source/destination channel")
    message_type: MessageType = Field(..., description="Inbound or outbound")
    direction: MessageDirection = Field(..., description="Message direction")

    # Customer information
    customer_id: Optional[str] = Field(None, description="Customer UUID if identified")
    customer_contact: str = Field(..., description="Email address or phone number")
    customer_name: Optional[str] = Field(None, description="Customer name if available")

    # Message content
    subject: Optional[str] = Field(None, description="Email subject or message title")
    body: str = Field(..., description="Message content")

    # Threading
    thread_id: Optional[str] = Field(None, description="Conversation thread identifier")
    parent_message_id: Optional[str] = Field(None, description="Parent message in thread")

    # Attachments
    attachments: List[AttachmentMetadata] = Field(default_factory=list)

    # Channel-specific metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Channel-specific data")
    # For email: {"in_reply_to": "...", "references": [...], "gmail_message_id": "..."}
    # For whatsapp: {"message_sid": "...", "profile_name": "...", "wa_id": "..."}
    # For webform: {"ticket_id": "...", "category": "...", "priority": "..."}

    # Timestamps
    timestamp: datetime = Field(..., description="Message timestamp")
    received_at: Optional[datetime] = Field(None, description="When system received message")

    # Delivery tracking
    delivery_status: Optional[str] = Field(None, description="sent, delivered, failed, bounced")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

---

## Entity Relationships Diagram

```
┌─────────────────┐
│    Customer     │
│  (existing)     │
└────────┬────────┘
         │
         │ 1:N
         │
┌────────▼────────────────┐
│  CustomerIdentifier     │
│  (existing)             │
│  - identifier_type      │
│  - identifier_value     │
└─────────────────────────┘

┌─────────────────┐
│    Customer     │
└────────┬────────┘
         │
         │ 1:N
         │
┌────────▼────────────────┐       ┌──────────────────────┐
│   Conversation          │       │  ChannelConfiguration│
│   (existing)            │       │  (new)               │
│   - initial_channel ────┼──────▶│  - channel           │
│   - status              │       │  - enabled           │
└────────┬────────────────┘       │  - config (JSONB)    │
         │                        └──────────────────────┘
         │ 1:N
         │
┌────────▼────────────────┐
│      Message            │
│      (existing +        │
│       extensions)       │
│   - channel             │
│   - thread_id (new)     │
│   - parent_message_id   │
│   - delivery_status     │
└────────┬────────────────┘
         │
         │ 1:N
         │
┌────────▼────────────────┐
│  MessageAttachment      │
│  (new)                  │
│  - filename             │
│  - content_type         │
│  - size_bytes           │
│  - storage_path         │
└─────────────────────────┘

┌─────────────────────────┐
│  WebhookDeliveryLog     │
│  (new - audit)          │
│  - webhook_type         │
│  - signature_valid      │
│  - processing_status    │
└─────────────────────────┘

┌─────────────────────────┐
│  RateLimitEntry         │
│  (new - optional)       │
│  - customer_id          │
│  - request_count        │
│  - window_start         │
└─────────────────────────┘
```

---

## Database Migration Strategy

### Migration 006: Add Channel Integration Support

**Changes**:
1. Create `channel_configurations` table
2. Create `message_attachments` table
3. Create `webhook_delivery_logs` table
4. Create `rate_limit_entries` table (optional)
5. Add columns to `messages` table:
   - `thread_id` VARCHAR(255)
   - `parent_message_id` UUID
   - `retry_count` INTEGER DEFAULT 0
   - `retry_after` TIMESTAMP WITH TIME ZONE
   - `webhook_signature` VARCHAR(255)
6. Create indexes:
   - `idx_messages_thread_id` on messages(thread_id)
   - `idx_messages_parent_id` on messages(parent_message_id)
   - `idx_messages_retry_after` on messages(retry_after)
   - `idx_webhook_logs_type_status` on webhook_delivery_logs(webhook_type, processing_status)
   - `idx_rate_limit_customer_window` on rate_limit_entries(customer_id, window_start)

**Rollback Strategy**:
- Drop new tables
- Remove new columns from messages table
- Drop new indexes

---

## Data Validation Rules

### Cross-Entity Validation
1. **Customer Contact Uniqueness**: Each email/phone must map to exactly one customer
2. **Thread Consistency**: All messages in a thread must reference the same conversation
3. **Attachment Size Limit**: Sum of all attachments per message ≤ 10MB
4. **Rate Limit Enforcement**: Customer cannot exceed 10 messages per minute across all channels
5. **Channel Configuration**: Messages can only be sent through enabled channels

### Data Integrity Constraints
1. **Foreign Key Constraints**: All FKs must reference valid parent records
2. **Enum Validation**: Channel, status, and type fields must use valid enum values
3. **Timestamp Ordering**: `received_at` ≥ `timestamp`, `completed_at` ≥ `received_at`
4. **Retry Limits**: `retry_count` ≤ 3 for all messages

---

## Performance Considerations

### Indexing Strategy
- **Hot Path**: Indexes on customer_id, conversation_id, thread_id for fast lookups
- **Retry Queue**: Index on retry_after for efficient retry processing
- **Audit Queries**: Composite index on (webhook_type, processing_status, received_at)

### Partitioning Strategy
- **Messages Table**: Consider partitioning by created_at (monthly) for large volumes
- **Webhook Logs**: Partition by received_at (weekly) with automatic archival

### Caching Strategy
- **Channel Configurations**: Cache in Redis (rarely changes)
- **Customer Identifiers**: Cache email→customer_id mappings
- **Rate Limit State**: Store in Redis (fast, distributed)

---

## Security Considerations

### Data Protection
- **PII Fields**: Encrypt customer_contact, customer_name at rest
- **Webhook Secrets**: Store encrypted in channel_configurations.config
- **Attachment Storage**: Use signed URLs with expiration for access
- **Audit Logging**: Log all data access for compliance

### Access Control
- **Row-Level Security**: Customers can only access their own data
- **Channel Isolation**: Separate credentials per channel
- **Secret Rotation**: Support for webhook secret versioning