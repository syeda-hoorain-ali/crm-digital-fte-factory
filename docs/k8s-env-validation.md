# Kubernetes Environment Variables - Complete Reference

## ✅ Status: All Variables from .env.example Added

All production environment variables from `backend/.env.example` are now included in K8s deployment (test-only variables excluded).

## Environment Variable Mapping

### Required Variables (K8s Secrets)

| K8s Secret | Config.py Field | .env.example | Notes |
|------------|----------------|--------------|-------|
| `DATABASE_URL` | `database_url` | `DATABASE_URL` | PostgreSQL connection string |
| `GEMINI_API_KEY` | `gemini_api_key` | `GEMINI_API_KEY` | Gemini API key for AI agent |
| `GMAIL_SERVICE_ACCOUNT_PATH` | `gmail_service_account_path` | `GMAIL_SERVICE_ACCOUNT_PATH` | Gmail OAuth credentials (JSON as string) |
| `TWILIO_ACCOUNT_SID` | `twilio_account_sid` | `TWILIO_ACCOUNT_SID` | Twilio account identifier |
| `TWILIO_AUTH_TOKEN` | `twilio_auth_token` | `TWILIO_AUTH_TOKEN` | Twilio authentication token |
| `TWILIO_APP_NUMBER` | `twilio_app_number` | `TWILIO_APP_NUMBER` | WhatsApp number (format: whatsapp:+1234567890) |
| `TWILIO_WEBHOOK_SECRET` | N/A | `TWILIO_WEBHOOK_SECRET` | HMAC secret for webhook validation |

### Optional Variables (K8s Secrets)

| K8s Secret | Config.py Field | .env.example | Default |
|------------|----------------|--------------|---------|
| `GMAIL_SUPPORT_CREDENTIALS_PATH` | `gmail_support_credentials_path` | `GMAIL_SUPPORT_CREDENTIALS_PATH` | `""` (empty) |
| `GMAIL_WEBHOOK_SECRET` | `gmail_webhook_secret` | `GMAIL_WEBHOOK_SECRET` | `""` (empty) |

### Configuration Variables (K8s ConfigMap)

| K8s ConfigMap | Config.py Field | .env.example | Production Value |
|---------------|----------------|--------------|------------------|
| `ENVIRONMENT` | `environment` | `ENVIRONMENT` | `production` |
| `LOG_LEVEL` | `log_level` | `LOG_LEVEL` | `INFO` |
| `GEMINI_BASE_URL` | `gemini_base_url` | `GEMINI_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka_bootstrap_servers` | `KAFKA_BOOTSTRAP_SERVERS` | `kafka-client.customer-success-fte.svc.cluster.local:9092` |
| `REDIS_URL` | `redis_url` | `REDIS_URL` | `redis://redis.customer-success-fte.svc.cluster.local:6379` |
| `KAFKA_TOPIC_PREFIX` | N/A | `KAFKA_TOPIC_PREFIX` | `customer-intake` |
| `RATE_LIMIT_PER_MINUTE` | N/A | `RATE_LIMIT_PER_MINUTE` | `10` |

### Optional Configuration Variables (K8s ConfigMap)

| K8s ConfigMap | Config.py Field | .env.example | Default |
|---------------|----------------|--------------|---------|
| `GMAIL_SUPPORT_ADDRESS` | `gmail_support_address` | `GMAIL_SUPPORT_ADDRESS` | `""` (empty) |
| `GMAIL_PUBSUB_TOPIC` | `gmail_pubsub_topic` | `GMAIL_PUBSUB_TOPIC` | `""` (empty) |
| `GCP_PROJECT_ID` | `gcp_project_id` | `GCP_PROJECT_ID` | `""` (empty) |

### Excluded Variables (Test-Only)

These variables from `.env.example` are NOT included in K8s deployment as they are only for E2E testing:

- `GMAIL_TEST_CREDENTIALS_PATH` - Test sender account credentials
- `GMAIL_TEST_ACCOUNT_EMAIL` - Test sender email address
- `TWILIO_TEST_ACCOUNT_SID` - Test Twilio account (duplicate of production)
- `TWILIO_TEST_AUTH_TOKEN` - Test Twilio token (duplicate of production)
- `TWILIO_TEST_FROM_NUMBER` - Test WhatsApp sender number

## Deployment Script Validation

The `scripts/deploy-k8s.sh` script validates these required variables before deployment:

```bash
REQUIRED_VARS=(
    "DATABASE_URL"
    "GEMINI_API_KEY"
    "GMAIL_SERVICE_ACCOUNT_PATH"
    "TWILIO_ACCOUNT_SID"
    "TWILIO_AUTH_TOKEN"
    "TWILIO_APP_NUMBER"
    "TWILIO_WEBHOOK_SECRET"
    "INGRESS_HOSTNAME"
    "CONTAINER_REGISTRY"
    "IMAGE_TAG"
)
```

Optional variables are set with defaults if not provided:
```bash
export GMAIL_SUPPORT_CREDENTIALS_PATH="${GMAIL_SUPPORT_CREDENTIALS_PATH:-}"
export GMAIL_WEBHOOK_SECRET="${GMAIL_WEBHOOK_SECRET:-}"
```

## Deployment Example

### Minimal Deployment (Required Variables Only)

```bash
# Required secrets
export DATABASE_URL="postgresql+asyncpg://user:pass@host/db"
export GEMINI_API_KEY="AIza..."
export GMAIL_SERVICE_ACCOUNT_PATH='{"installed":{"client_id":"...","client_secret":"..."}}'
export TWILIO_ACCOUNT_SID="AC..."
export TWILIO_AUTH_TOKEN="..."
export TWILIO_APP_NUMBER="whatsapp:+1234567890"
export TWILIO_WEBHOOK_SECRET="your-secret-min-32-chars"

# Required deployment config
export INGRESS_HOSTNAME="api.yourdomain.com"
export CONTAINER_REGISTRY="docker.io/yourorg"
export IMAGE_TAG="v1.0.0"

# Deploy
./scripts/deploy-k8s.sh
```

### Full Deployment (With Optional Variables)

```bash
# Required secrets (same as above)
export DATABASE_URL="postgresql+asyncpg://user:pass@host/db"
export GEMINI_API_KEY="AIza..."
export GMAIL_SERVICE_ACCOUNT_PATH='{"installed":{...}}'
export TWILIO_ACCOUNT_SID="AC..."
export TWILIO_AUTH_TOKEN="..."
export TWILIO_APP_NUMBER="whatsapp:+1234567890"
export TWILIO_WEBHOOK_SECRET="your-secret"

# Optional secrets (for Gmail features)
export GMAIL_SUPPORT_CREDENTIALS_PATH='{"installed":{...}}'
export GMAIL_WEBHOOK_SECRET="gmail-webhook-secret"

# Required deployment config
export INGRESS_HOSTNAME="api.yourdomain.com"
export CONTAINER_REGISTRY="docker.io/yourorg"
export IMAGE_TAG="v1.0.0"

# Deploy
./scripts/deploy-k8s.sh
```

## Verification Commands

After deployment, verify environment variables are correctly injected:

```bash
# Check API pod environment
kubectl exec -n customer-success-fte deployment/fte-api -- env | grep -E "GEMINI|TWILIO|GMAIL|KAFKA|REDIS" | sort

# Check Worker pod environment
kubectl exec -n customer-success-fte deployment/fte-message-processor -- env | grep -E "GEMINI|TWILIO|GMAIL|KAFKA|REDIS" | sort

# Check ConfigMap
kubectl get configmap fte-config -n customer-success-fte -o yaml

# Check Secret (base64 encoded)
kubectl get secret fte-secrets -n customer-success-fte -o yaml
```

## Notes

1. **Gmail Credentials Format**: `GMAIL_SERVICE_ACCOUNT_PATH` should contain the full JSON credentials as a string (not a file path) when deployed to K8s. The variable name is kept for compatibility with the codebase.

2. **Optional Variables**: Variables marked as optional can be omitted. The application will use empty string defaults and disable related features gracefully.

3. **Kafka Topics**: Topic names are hardcoded in the application code (customer-intake.email.inbound, customer-intake.whatsapp.inbound, customer-intake.webform.inbound). The `KAFKA_TOPIC_PREFIX` is included for future extensibility.

4. **Rate Limiting**: Currently hardcoded to 10 requests per minute in main.py:124. The ConfigMap value is included for future configurability.

5. **Production vs Development**: The ConfigMap sets `ENVIRONMENT=production` and `LOG_LEVEL=INFO`. Adjust these for staging/development environments.

## Optional Variables (Have Defaults)

These are missing from K8s config but have defaults in config.py:

| Variable | Default in config.py | Required? |
|----------|---------------------|-----------|
| `GEMINI_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai/` | No |
| `GMAIL_SUPPORT_ADDRESS` | `""` | No (but needed for production) |
| `GMAIL_PUBSUB_TOPIC` | `""` | No (but needed for Gmail push notifications) |
| `GMAIL_WEBHOOK_SECRET` | `""` | No (but needed for webhook validation) |
| `GCP_PROJECT_ID` | `""` | No (but needed for Gmail API) |
| `KAFKA_TOPIC_PREFIX` | Not in config.py | No (topics are hardcoded) |
| `RATE_LIMIT_PER_MINUTE` | Hardcoded as 10 in main.py:124 | No |

## Variables Correctly Configured

✅ **ConfigMap (k8s/configmap.yaml):**
- `ENVIRONMENT` → `environment`
- `LOG_LEVEL` → `log_level`
- `KAFKA_BOOTSTRAP_SERVERS` → `kafka_bootstrap_servers`
- `REDIS_URL` → `redis_url`

✅ **Secrets (k8s/secrets.yaml):**
- `DATABASE_URL` → `database_url`
- `GEMINI_API_KEY` → `gemini_api_key`
- `TWILIO_ACCOUNT_SID` → `twilio_account_sid`
- `TWILIO_AUTH_TOKEN` → `twilio_auth_token`
- `TWILIO_WEBHOOK_SECRET` → Not in config.py (used directly in WhatsAppHandler)

## Additional ConfigMap Variables

These are in ConfigMap but not in .env.example:

- `GMAIL_ENABLED` (not in config.py)
- `WHATSAPP_ENABLED` (not in config.py)
- `WEBFORM_ENABLED` (not in config.py)
- `MAX_EMAIL_LENGTH` (not in config.py)
- `MAX_WHATSAPP_LENGTH` (not in config.py)
- `MAX_WEBFORM_LENGTH` (not in config.py)
- `AGENT_MAX_ITERATIONS` (not in config.py)
- `AGENT_TIMEOUT_SECONDS` (not in config.py)

**Status:** These appear to be unused by the application code.

## Recommendations

### Immediate Fixes (Breaking Issues)

1. **Fix Twilio variable name:**
   ```yaml
   # k8s/secrets.yaml
   - TWILIO_WHATSAPP_NUMBER: "${TWILIO_WHATSAPP_NUMBER}"
   + TWILIO_WHATSAPP_FROM: "${TWILIO_WHATSAPP_FROM}"
   ```

2. **Fix Gmail credentials variable name:**
   ```yaml
   # k8s/secrets.yaml
   - GMAIL_CREDENTIALS: "${GMAIL_CREDENTIALS_JSON}"
   + GMAIL_SERVICE_ACCOUNT_PATH: "${GMAIL_CREDENTIALS_JSON}"
   ```

### Optional Additions (For Production)

Add to ConfigMap if needed for Gmail functionality:
```yaml
GMAIL_SUPPORT_ADDRESS: "support@example.com"
GMAIL_WEBHOOK_SECRET: "${GMAIL_WEBHOOK_SECRET}"
GCP_PROJECT_ID: "${GCP_PROJECT_ID}"
```

Add to ConfigMap if needed for Gmail push notifications:
```yaml
GMAIL_PUBSUB_TOPIC: "projects/${GCP_PROJECT_ID}/topics/gmail-notifications"
```

### Cleanup

Remove unused variables from ConfigMap:
- `GMAIL_ENABLED`, `WHATSAPP_ENABLED`, `WEBFORM_ENABLED`
- `MAX_EMAIL_LENGTH`, `MAX_WHATSAPP_LENGTH`, `MAX_WEBFORM_LENGTH`
- `AGENT_MAX_ITERATIONS`, `AGENT_TIMEOUT_SECONDS`

## Testing Checklist

After fixes:
- [ ] Deploy to K8s cluster
- [ ] Check API pod logs for startup errors
- [ ] Check worker pod logs for startup errors
- [ ] Verify Twilio WhatsApp handler initializes correctly
- [ ] Verify Gmail handler initializes correctly (if credentials provided)
- [ ] Test health endpoint: `curl http://localhost:8000/health`