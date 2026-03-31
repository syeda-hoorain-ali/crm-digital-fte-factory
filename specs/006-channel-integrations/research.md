# Research: Multi-Channel Customer Intake

**Feature**: 006-channel-integrations
**Date**: 2026-03-04
**Purpose**: Technical research for implementing Gmail, WhatsApp, and Web Form channel integrations

## Research Questions Resolved

### 1. Gmail API Integration with Pub/Sub

**Decision**: Use Gmail Push Notifications via Google Cloud Pub/Sub for real-time email processing

**Rationale**:
- Real-time processing vs polling IMAP (more efficient, lower latency)
- Native support for push notifications in Gmail API
- Scalable architecture that handles high email volumes
- Automatic retry and delivery guarantees from Pub/Sub

**Implementation Pattern**:
- Create Pub/Sub topic in Google Cloud Console
- Grant Gmail API publish permissions
- Set up push subscription pointing to webhook endpoint
- Use `watch()` API to register mailbox (renews every 7 days)
- Parse email using Python `email` library with `policy.default`
- Extract In-Reply-To and References headers for thread detection
- Validate attachments (10MB limit, filter file types)

**Key Libraries**:
- `google-cloud-pubsub` - Pub/Sub client
- `google-api-python-client` - Gmail API
- `google-auth` - OAuth2 credentials
- Python `email` module - Email parsing

**Common Pitfalls**:
- Watch expires after 7 days - implement automatic renewal
- Pub/Sub delivers at-least-once - implement idempotency
- Rate limits: 250 quota units per user per second
- Must handle multipart emails correctly

**Alternatives Considered**:
- IMAP polling - Rejected: Higher latency, less efficient, requires constant polling
- Direct SMTP integration - Rejected: Doesn't support Gmail-specific features like threading

---

### 2. Twilio WhatsApp Integration

**Decision**: Use Twilio WhatsApp Business API with webhook callbacks

**Rationale**:
- Industry-standard WhatsApp Business API provider
- Built-in HMAC signature verification
- Handles message delivery status callbacks
- Supports media messages and templates
- Reliable webhook retry mechanism

**Implementation Pattern**:
- Configure Twilio webhook URL pointing to FastAPI endpoint
- Verify webhook signature using `RequestValidator`
- Handle incoming messages via form data
- Send messages using Twilio REST API
- Split messages exceeding 1600 character limit
- Handle delivery status callbacks (sent, delivered, read, failed)

**Key Libraries**:
- `twilio` - Official Twilio Python SDK
- `twilio.request_validator.RequestValidator` - Signature verification

**Common Pitfalls**:
- 24-hour session window - can't initiate messages after that
- Template messages required for outbound after 24h window
- Media messages count against rate limits differently
- Must handle webhook retries idempotently

**Alternatives Considered**:
- Direct WhatsApp Business API - Rejected: More complex setup, requires Facebook Business verification
- Other providers (MessageBird, Vonage) - Rejected: Twilio has better documentation and Python SDK

---

### 3. HMAC Signature Verification

**Decision**: Implement constant-time HMAC verification using Python's `hmac.compare_digest()`

**Rationale**:
- Industry standard for webhook authentication
- Prevents timing attacks with constant-time comparison
- Supported by all major webhook providers (Gmail Pub/Sub, Twilio)
- Simple to implement and test

**Implementation Pattern**:
- Store webhook secret in environment variable
- Generate HMAC signature using `hmac.new()` with SHA-256
- Compare using `hmac.compare_digest()` (constant-time)
- Implement as FastAPI dependency for reusability
- Log failed verification attempts for security monitoring

**Key Libraries**:
- Python `hmac` module (stdlib)
- Python `hashlib` module (stdlib)

**Security Best Practices**:
- Always use `hmac.compare_digest()` to prevent timing attacks
- Never use `==` comparison for signatures
- Store secrets in environment variables, never in code
- Rotate secrets periodically with versioning support
- Use SHA-256 or stronger algorithms

**Alternatives Considered**:
- API key authentication - Rejected: Less secure, keys can be intercepted
- OAuth 2.0 - Rejected: Overkill for webhooks, adds complexity
- IP whitelisting only - Rejected: Weak security, IPs can change

---

### 4. Kafka Topic Design for Multi-Channel Routing

**Decision**: Use channel-specific topics with unified message schema

**Rationale**:
- Enables channel-specific processing and monitoring
- Unified schema simplifies agent integration
- Supports future channel additions without schema changes
- Allows independent scaling per channel

**Topic Naming Convention**:
```
customer-intake.{channel}.{message-type}

Examples:
- customer-intake.email.inbound
- customer-intake.whatsapp.inbound
- customer-intake.webform.inbound
- customer-intake.all.inbound (unified topic for agent)
```

**Unified Message Schema** (Pydantic model):
```python
class ChannelMessage(BaseModel):
    message_id: str
    channel: Channel  # enum: email, whatsapp, webform
    message_type: MessageType  # enum: inbound, outbound
    customer_id: Optional[str]
    customer_contact: str  # email or phone
    subject: Optional[str]
    body: str
    thread_id: Optional[str]
    parent_message_id: Optional[str]
    attachments: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    timestamp: datetime
```

**Key Libraries**:
- `aiokafka` - Async Kafka client for Python
- `pydantic` - Message schema validation

**Common Pitfalls**:
- Not using partitioning keys (leads to ordering issues)
- Over-partitioning (too many partitions for low throughput)
- Not handling consumer rebalancing
- Forgetting to commit offsets after processing

**Performance Considerations**:
- Use compression (gzip) for large messages
- Batch messages when possible
- Set appropriate retention policies (7 days default)
- Monitor consumer lag

**Alternatives Considered**:
- Single unified topic - Rejected: Harder to monitor per-channel metrics
- RabbitMQ - Rejected: Kafka better for high-throughput message streaming
- Redis Streams - Rejected: Less mature, fewer operational tools

---

### 5. Rate Limiting Implementation

**Decision**: Use Redis with sliding window algorithm for distributed rate limiting

**Rationale**:
- Accurate rate limiting across distributed backend instances
- Persistent state survives service restarts
- Sliding window more accurate than fixed window
- Redis sorted sets provide efficient time-based operations

**Implementation Pattern**:
- Store requests in Redis sorted set with timestamp as score
- Remove entries outside time window
- Count remaining entries to check limit
- Use Redis pipeline for atomic operations
- Return remaining requests in response headers

**Key Libraries**:
- `redis.asyncio` - Async Redis client

**Rate Limit Parameters** (from clarifications):
- 10 messages per minute per customer
- 60-second sliding window
- Return `429 Too Many Requests` with `Retry-After` header

**Common Pitfalls**:
- Not using atomic operations (race conditions)
- Not setting TTL on rate limit keys (memory leak)
- Not handling Redis connection failures gracefully

**Alternatives Considered**:
- Token bucket (in-memory) - Rejected: Not distributed, lost on restart
- Fixed window - Rejected: Less accurate, allows bursts at window boundaries
- Database-based - Rejected: Too slow for high-frequency checks

---

### 6. Exponential Backoff Retry Logic

**Decision**: Use `tenacity` library for declarative retry logic with exponential backoff

**Rationale**:
- Declarative syntax with decorators
- Built-in exponential backoff with configurable parameters
- Supports retry conditions (specific exceptions)
- Includes logging hooks for observability
- Well-tested and maintained library

**Implementation Pattern**:
- Decorate async functions with `@retry`
- Configure: 3 max attempts, 1s initial delay, 2x multiplier
- Retry only on transient errors (ConnectionError, TimeoutError)
- Log retry attempts with `before_sleep_log`
- Combine with circuit breaker for additional resilience

**Key Libraries**:
- `tenacity` - Retry library with exponential backoff

**Retry Parameters** (from clarifications):
- Maximum 3 retry attempts
- Initial delay: 1 second
- Backoff multiplier: 2x (delays: 1s, 2s, 4s)
- Total retry window: ~7 seconds

**Common Pitfalls**:
- Retrying non-idempotent operations
- Not adding jitter (thundering herd problem)
- Infinite retries without max attempts
- Not logging retry attempts

**Performance Considerations**:
- Add jitter: `delay = delay * (0.5 + random.random())`
- Use async sleep to avoid blocking
- Implement timeout per attempt
- Monitor retry metrics (success rate, average attempts)

**Alternatives Considered**:
- Manual retry loops - Rejected: Error-prone, harder to test
- `backoff` library - Rejected: Less feature-rich than tenacity
- No retries - Rejected: Doesn't meet reliability requirements

---

## Technology Stack Summary

### Backend Dependencies
- **FastAPI** - Web framework for webhook endpoints
- **SQLModel** - Database ORM (existing from feature 005)
- **aiokafka** - Kafka client for message routing
- **google-cloud-pubsub** - Gmail Pub/Sub integration
- **google-api-python-client** - Gmail API
- **twilio** - WhatsApp integration
- **redis.asyncio** - Rate limiting
- **tenacity** - Retry logic with exponential backoff
- **pydantic** - Data validation and serialization

### Frontend Dependencies
- **React** - UI framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **shadcn/ui** - UI components
- **zod** - Form validation

### Infrastructure
- **PostgreSQL** (Neon Serverless) - Database (existing)
- **Kafka** - Message streaming
- **Redis** - Rate limiting state
- **Google Cloud Pub/Sub** - Gmail push notifications

---

## Security Considerations

1. **HMAC Signature Verification**: All webhooks verified using constant-time comparison
2. **Rate Limiting**: 10 messages per minute per customer to prevent abuse
3. **Attachment Validation**: 10MB size limit, file type filtering, malware scanning
4. **Secret Management**: All API keys and secrets in environment variables
5. **Input Validation**: Pydantic models for all incoming data
6. **Audit Logging**: All messages logged with timestamps and delivery status

---

## Performance Targets

Based on success criteria from spec:
- **Acknowledgment**: < 2 minutes for all channels
- **Response Time**: < 5 minutes for 90% of requests
- **Throughput**: 1,000 concurrent requests without degradation
- **Reliability**: 98% message delivery success rate
- **Thread Continuity**: 95% email thread linking accuracy

---

## Next Steps

1. **Phase 1**: Create data-model.md with entity definitions
2. **Phase 1**: Generate API contracts (OpenAPI specs)
3. **Phase 1**: Create quickstart.md for local development
4. **Phase 2**: Generate tasks.md with implementation tasks
