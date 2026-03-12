# Quickstart Guide: Multi-Channel Customer Intake

**Feature**: 006-channel-integrations
**Date**: 2026-03-04
**Purpose**: Local development setup and testing guide

## Prerequisites

- Python 3.12+
- Node.js 18+ (for frontend)
- PostgreSQL (via Neon Serverless or local)
- Redis (for rate limiting)
- Kafka (via Docker or local)
- UV package manager
- Gmail API credentials (for email channel)
- Twilio account (for WhatsApp channel)

---

## Environment Setup

### 1. Clone and Navigate to Project

```bash
git clone https://github.com/syeda-hoorain-ali/crm-digital-fte.git
cd crm-digital-fte
git checkout 006-channel-integrations
```

### 2. Backend Setup

```bash
cd backend

# Install dependencies with UV
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 3. Database Migration

```bash
# Run Alembic migrations
uv run alembic upgrade head
```

### 4. Start Infrastructure Services

```bash
# Start Kafka and Redis with Docker Compose
docker-compose up -d kafka redis

# Verify services are running
docker-compose ps
```

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local

# Edit with API endpoint
echo "VITE_API_URL=http://localhost:8000" > .env.local
```

---

## Running the Application

### Start Backend Server

```bash
cd backend

# Run FastAPI server with hot reload
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at: `http://localhost:8000`

API docs: `http://localhost:8000/docs`

### Start Frontend Development Server

```bash
cd frontend

# Run Vite dev server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

---

## Testing Channels

### 1. Test Web Form Channel

**Using Frontend**:
1. Navigate to `http://localhost:5173/support`
2. Fill out the support form:
   - Name: Test User
   - Email: test@example.com
   - Subject: Test submission
   - Category: Technical
   - Message: This is a test message
3. Submit and verify you receive a ticket ID

**Using cURL**:
```bash
curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Test submission",
    "category": "technical",
    "priority": "medium",
    "message": "This is a test message from cURL"
  }'
```

**Expected Response**:
```json
{
  "ticket_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Thank you for contacting us! Our AI assistant will respond shortly.",
  "estimated_response_time": "Usually within 5 minutes"
}
```

### 2. Test Gmail Channel (Local Development)

**Setup Gmail Push Notifications**:

1. Create Google Cloud Project and enable Gmail API
2. Create OAuth 2.0 credentials
3. Download credentials JSON file
4. Set up Pub/Sub topic:

```bash
# Create Pub/Sub topic
gcloud pubsub topics create gmail-push

# Create push subscription pointing to your webhook
gcloud pubsub subscriptions create gmail-push-sub \
  --topic=gmail-push \
  --push-endpoint=https://your-ngrok-url.ngrok.io/webhooks/gmail
```

5. Use ngrok for local webhook testing:

```bash
# Start ngrok tunnel
ngrok http 8000

# Update Pub/Sub subscription with ngrok URL
gcloud pubsub subscriptions update gmail-push-sub \
  --push-endpoint=https://your-ngrok-url.ngrok.io/webhooks/gmail
```

6. Register Gmail watch:

```bash
# Run watch registration script
uv run python scripts/register_gmail_watch.py
```

**Test Email Processing**:
1. Send email to your support address
2. Check backend logs for webhook receipt
3. Verify message appears in Kafka topic
4. Check database for new message record

### 3. Test WhatsApp Channel

**Setup Twilio Sandbox**:

1. Go to Twilio Console → Messaging → Try it out → Try WhatsApp
2. Follow instructions to join sandbox
3. Configure webhook URL:

```bash
# Use ngrok for local testing
ngrok http 8000

# In Twilio Console, set webhook URL to:
https://your-ngrok-url.ngrok.io/webhooks/whatsapp
```

**Test WhatsApp Messaging**:
1. Send WhatsApp message to Twilio sandbox number
2. Check backend logs for webhook receipt
3. Verify HMAC signature validation passes
4. Check Kafka topic for message
5. Verify AI agent response is sent back

**Using Twilio CLI** (for testing):
```bash
# Install Twilio CLI
npm install -g twilio-cli

# Send test message
twilio api:core:messages:create \
  --from "whatsapp:+14155238886" \
  --to "whatsapp:+1234567890" \
  --body "Test message from Twilio CLI"
```

---

## Testing Rate Limiting

```bash
# Send 11 requests rapidly (should trigger rate limit on 11th)
for i in {1..11}; do
  curl -X POST http://localhost:8000/support/submit \
    -H "Content-Type: application/json" \
    -H "X-Customer-ID: test-customer-123" \
    -d '{
      "name": "Test User",
      "email": "test@example.com",
      "subject": "Rate limit test '$i'",
      "category": "general",
      "message": "Testing rate limiting"
    }'
  echo "\nRequest $i completed"
done
```

**Expected**: First 10 requests succeed, 11th returns `429 Too Many Requests` with `Retry-After` header.

---

## Testing HMAC Signature Verification

### Generate Test Signature

```python
import hmac
import hashlib
import json

# Webhook secret
secret = "your_webhook_secret"

# Request payload
payload = json.dumps({"test": "data"})

# Generate signature
signature = hmac.new(
    secret.encode(),
    payload.encode(),
    hashlib.sha256
).hexdigest()

print(f"X-Signature: {signature}")
```

### Test with cURL

```bash
# Calculate signature
PAYLOAD='{"test":"data"}'
SECRET="your_webhook_secret"
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

# Send request with signature
curl -X POST http://localhost:8000/webhooks/gmail \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

---

## Running Tests

### Backend Tests

```bash
cd backend

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_gmail_handler.py

# Run integration tests only
uv run pytest tests/integration/

# Run with verbose output
uv run pytest -v
```

### Frontend Tests (Manual)

1. Open `http://localhost:5173/support`
2. Test form validation:
   - Submit with empty fields → Should show validation errors
   - Submit with invalid email → Should show email format error
   - Submit with short message → Should show length error
3. Test successful submission:
   - Fill all fields correctly
   - Submit and verify ticket ID is displayed
   - Verify confirmation message appears
4. Test ticket status lookup:
   - Use ticket ID from previous step
   - Navigate to status page
   - Verify conversation history is displayed

---

## Monitoring and Debugging

### View Logs

```bash
# Backend logs (FastAPI)
tail -f logs/app.log

# Kafka consumer logs
docker-compose logs -f kafka

# Redis logs
docker-compose logs -f redis
```

### Check Kafka Topics

```bash
# List topics
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# Consume messages from topic
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic customer-intake.email.inbound \
  --from-beginning
```

### Check Redis Rate Limits

```bash
# Connect to Redis CLI
docker exec -it redis redis-cli

# View rate limit keys
KEYS rate_limit:*

# Check specific customer's rate limit
ZRANGE rate_limit:customer-123 0 -1 WITHSCORES
```

### Database Queries

```bash
# Connect to database
psql $DATABASE_URL

# Check recent messages
SELECT id, channel, direction, content, created_at
FROM messages
ORDER BY created_at DESC
LIMIT 10;

# Check webhook delivery logs
SELECT webhook_type, signature_valid, processing_status, received_at
FROM webhook_delivery_logs
ORDER BY received_at DESC
LIMIT 10;

# Check rate limit entries
SELECT customer_id, channel, request_count, window_start
FROM rate_limit_entries
WHERE window_start > NOW() - INTERVAL '5 minutes';
```

---

## Common Issues and Solutions

### Issue: Gmail webhook not receiving messages

**Solution**:
1. Verify Pub/Sub topic exists: `gcloud pubsub topics list`
2. Check subscription is active: `gcloud pubsub subscriptions list`
3. Verify ngrok tunnel is running: `curl https://your-ngrok-url.ngrok.io/health`
4. Check Gmail watch is active: Run `scripts/check_gmail_watch.py`
5. Re-register watch if expired: `scripts/register_gmail_watch.py`

### Issue: Twilio signature verification fails

**Solution**:
1. Verify `TWILIO_AUTH_TOKEN` in `.env` matches Twilio console
2. Check webhook URL in Twilio console matches ngrok URL exactly
3. Ensure request URL includes protocol (https://)
4. Test signature generation: `scripts/test_twilio_signature.py`

### Issue: Rate limiting not working

**Solution**:
1. Verify Redis is running: `docker-compose ps redis`
2. Check Redis connection: `redis-cli ping`
3. Verify `X-Customer-ID` header is being sent
4. Check rate limit keys in Redis: `redis-cli KEYS rate_limit:*`

### Issue: Kafka messages not being consumed

**Solution**:
1. Verify Kafka is running: `docker-compose ps kafka`
2. Check topic exists: `kafka-topics --list`
3. Verify consumer group is active: `kafka-consumer-groups --list`
4. Check for consumer lag: `kafka-consumer-groups --describe --group fte-message-processor`

### Issue: Database connection fails

**Solution**:
1. Verify `DATABASE_URL` in `.env` is correct
2. Check database is accessible: `psql $DATABASE_URL -c "SELECT 1"`
3. Run migrations: `alembic upgrade head`
4. Check connection pool settings in `src/database/connection.py`

---

## Development Workflow

### 1. Make Code Changes

```bash
# Edit files in src/
nano src/channels/gmail_handler.py

# Backend auto-reloads with uvicorn --reload
# Frontend auto-reloads with Vite
```

### 2. Run Tests

```bash
# Run affected tests
uv run pytest tests/unit/test_gmail_handler.py

# Verify coverage
uv run pytest --cov=src.channels
```

### 3. Test Integration

```bash
# Send test webhook
curl -X POST http://localhost:8000/webhooks/gmail \
  -H "Content-Type: application/json" \
  -H "X-Signature: $(generate_signature)" \
  -d @test_payloads/gmail_webhook.json

# Check Kafka topic
kafka-console-consumer --topic customer-intake.email.inbound
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat(channels): implement Gmail webhook handler"
```

---

## Next Steps

After local development is working:

1. **Deploy to Staging**: Follow deployment guide in `docs/deployment.md`
2. **Configure Production Webhooks**: Update webhook URLs to production endpoints
3. **Set Up Monitoring**: Configure Prometheus metrics and Grafana dashboards
4. **Load Testing**: Run Locust tests to verify performance targets
5. **Security Audit**: Review HMAC implementation and rate limiting

---

## Useful Commands

```bash
# Backend
uv run uvicorn src.main:app --reload          # Start dev server
uv run pytest                                  # Run tests
uv run alembic upgrade head                    # Run migrations
uv run python scripts/seed_data.py             # Seed test data

# Frontend
npm run dev                                    # Start dev server
npm run build                                  # Build for production
npm run preview                                # Preview production build

# Docker
docker-compose up -d                           # Start services
docker-compose down                            # Stop services
docker-compose logs -f                         # View logs

# Database
psql $DATABASE_URL                             # Connect to database
alembic revision --autogenerate -m "message"   # Create migration
alembic current                                # Show current revision

# Kafka
kafka-topics --list                            # List topics
kafka-console-consumer --topic <name>          # Consume messages
kafka-consumer-groups --describe --group <id>  # Check consumer lag
```

---

## Support

For issues or questions:
- Check logs: `tail -f logs/app.log`
- Review API docs: `http://localhost:8000/docs`
- Run health check: `curl http://localhost:8000/health`
- Consult feature spec: `specs/006-channel-integrations/spec.md`