# Gmail Production Setup Guide

Complete guide for setting up Gmail integration in production using Service Accounts and secure credential management.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Setup Steps](#setup-steps)
- [Security Best Practices](#security-best-practices)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers production-grade Gmail integration for receiving customer emails via Gmail API and Google Cloud Pub/Sub.

**Key Differences from Testing Setup:**

| Aspect | Testing (OAuth) | Production (Service Account) |
|--------|----------------|------------------------------|
| **Authentication** | OAuth 2.0 (user consent) | Service Account with Domain-Wide Delegation |
| **Credential Type** | Access + Refresh tokens | Service account key (JSON) |
| **User Interaction** | Browser-based consent flow | No user interaction needed |
| **Use Case** | E2E tests, development | Production email processing |
| **Security** | User-level access | Server-to-server, domain-wide |
| **Token Management** | Refresh every hour | Long-lived key (rotate every 90 days) |

**Production Architecture:**

```
Customer Email
      ↓
Gmail (support@yourdomain.com)
      ↓
Gmail Push Notification
      ↓
Google Cloud Pub/Sub
      ↓
Push Subscription (Webhook)
      ↓
Your Application (/webhooks/gmail)
      ↓
Process Email → Database → Kafka → Agent
```

---

## Prerequisites

### 1. Google Workspace Account

You need a **Google Workspace** (formerly G Suite) account, not a personal Gmail account.

- Domain: `yourdomain.com`
- Support email: `support@yourdomain.com`
- Admin access to Google Workspace Admin Console

### 2. Google Cloud Project

```bash
# Create project
gcloud projects create your-project-id --name="CRM Digital FTE"

# Set as active project
gcloud config set project your-project-id

# Enable billing (required for Pub/Sub)
gcloud billing accounts list
gcloud billing projects link your-project-id --billing-account=BILLING_ACCOUNT_ID
```

### 3. Enable Required APIs

```bash
# Enable Gmail API
gcloud services enable gmail.googleapis.com

# Enable Pub/Sub API
gcloud services enable pubsub.googleapis.com

# Enable Secret Manager API (for secure credential storage)
gcloud services enable secretmanager.googleapis.com
```

---

## Architecture

### Authentication Flow

```
┌──────────────────────────────────────────────────────────┐
│  Google Cloud Secret Manager                             │
│  ┌────────────────────────────────────────────────────┐  │
│  │  gmail-service-account-key (JSON)                  │  │
│  │  {                                                 │  │
│  │    "type": "service_account",                      │  │
│  │    "project_id": "...",                            │  │
│  │    "private_key_id": "...",                        │  │
│  │    "private_key": "...",                           │  │
│  │    "client_email": "...",                          │  │
│  │    "client_id": "..."                              │  │
│  │  }                                                 │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│  Your Application (FastAPI)                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │  1. Fetch service account key on startup           │  │
│  │  2. Create credentials with domain-wide delegation │  │
│  │  3. Impersonate support@yourdomain.com             │  │
│  │  4. Access Gmail API as that user                  │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│  Gmail API (as support@yourdomain.com)                   │
│  - Read emails                                           │
│  - Send responses                                        │
│  - Manage labels                                         │
│  - Register Pub/Sub watch                                │
└──────────────────────────────────────────────────────────┘
```

---

## Setup Steps

### Step 1: Create Service Account

```bash
# Create service account
gcloud iam service-accounts create gmail-service-account \
  --display-name="Gmail Service Account for CRM" \
  --description="Service account for Gmail API access with domain-wide delegation"

# Get service account email
SERVICE_ACCOUNT_EMAIL=$(gcloud iam service-accounts list \
  --filter="displayName:Gmail Service Account" \
  --format="value(email)")

echo "Service Account Email: $SERVICE_ACCOUNT_EMAIL"
```

### Step 2: Generate Service Account Key

```bash
# Generate key (download JSON)
gcloud iam service-accounts keys create service-account-key.json \
  --iam-account=$SERVICE_ACCOUNT_EMAIL

# IMPORTANT: This file contains sensitive credentials!
# We'll upload it to Secret Manager and then delete the local copy
```

**⚠️ Security Warning:** Never commit `service-account-key.json` to git!

### Step 3: Store Key in Secret Manager

```bash
# Create secret
gcloud secrets create gmail-service-account-key \
  --replication-policy="automatic" \
  --data-file=service-account-key.json

# Grant your application access to the secret
# Replace with your application's service account or compute engine default SA
gcloud secrets add-iam-policy-binding gmail-service-account-key \
  --member="serviceAccount:your-app-service-account@your-project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Delete local key file (it's now safely stored in Secret Manager)
rm service-account-key.json

echo "✓ Service account key stored securely in Secret Manager"
```

### Step 4: Enable Domain-Wide Delegation

This allows the service account to impersonate users in your Google Workspace domain.

#### 4.1: Get Service Account Client ID

```bash
# Get the unique client ID (numeric)
gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL \
  --format="value(oauth2ClientId)"
```

Copy this client ID (e.g., `1234567890123456789`).

#### 4.2: Configure in Google Workspace Admin Console

1. Go to [Google Workspace Admin Console](https://admin.google.com/)
2. Navigate to **Security → Access and data control → API Controls**
3. Click **Manage Domain Wide Delegation**
4. Click **Add new**
5. Enter the **Client ID** from step 4.1
6. Add **OAuth Scopes**:
   ```
   https://www.googleapis.com/auth/gmail.readonly
   https://www.googleapis.com/auth/gmail.send
   https://www.googleapis.com/auth/gmail.modify
   https://www.googleapis.com/auth/gmail.settings.basic
   ```
7. Click **Authorize**

**What this does:** Allows the service account to act as any user in your domain (specifically `support@yourdomain.com`).

### Step 5: Create Pub/Sub Topic and Subscription

```bash
# Create topic for Gmail notifications
gcloud pubsub topics create gmail-notifications

# Grant Gmail permission to publish to this topic
gcloud pubsub topics add-iam-policy-binding gmail-notifications \
  --member=serviceAccount:gmail-api-push@system.gserviceaccount.com \
  --role=roles/pubsub.publisher

# Create push subscription pointing to your webhook endpoint
gcloud pubsub subscriptions create gmail-webhook-subscription \
  --topic=gmail-notifications \
  --push-endpoint=https://your-production-domain.com/webhooks/gmail \
  --push-auth-service-account=$SERVICE_ACCOUNT_EMAIL

echo "✓ Pub/Sub topic and subscription created"
```

**Important:** Replace `https://your-production-domain.com` with your actual production URL.

### Step 6: Application Code Integration

#### 6.1: Install Dependencies

```bash
cd backend
uv add google-cloud-secret-manager google-auth google-api-python-client
```

#### 6.2: Create Gmail Service Module

Create `backend/src/services/gmail_service.py`:

```python
"""Gmail service with secure credential management for production."""

import json
import logging
from typing import Optional
from functools import lru_cache

from google.cloud import secretmanager
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import settings

logger = logging.getLogger(__name__)


class GmailService:
    """Production Gmail service using service account with domain-wide delegation."""

    def __init__(self):
        self.credentials: Optional[service_account.Credentials] = None
        self.service = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Gmail service with credentials from Secret Manager."""
        if self._initialized:
            return

        try:
            # Fetch service account key from Secret Manager
            service_account_info = self._get_service_account_key()

            # Create credentials with domain-wide delegation
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=[
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/gmail.modify',
                ],
                subject=settings.GMAIL_SUPPORT_ADDRESS  # Impersonate this user
            )

            # Build Gmail API service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            self._initialized = True

            logger.info(
                "Gmail service initialized",
                extra={"impersonated_user": settings.GMAIL_SUPPORT_ADDRESS}
            )

        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}", exc_info=True)
            raise

    def _get_service_account_key(self) -> dict:
        """Fetch service account key from Secret Manager.

        Returns:
            Service account key as dictionary

        Raises:
            Exception: If secret cannot be accessed
        """
        try:
            # Create Secret Manager client
            client = secretmanager.SecretManagerServiceClient()

            # Build secret name
            secret_name = f"projects/{settings.GCP_PROJECT_ID}/secrets/gmail-service-account-key/versions/latest"

            # Access secret
            response = client.access_secret_version(request={"name": secret_name})

            # Parse JSON
            service_account_info = json.loads(response.payload.data.decode("UTF-8"))

            logger.info("Service account key retrieved from Secret Manager")
            return service_account_info

        except Exception as e:
            logger.error(f"Failed to retrieve service account key: {e}", exc_info=True)
            raise

    async def get_message(self, message_id: str) -> dict:
        """Fetch email message by ID.

        Args:
            message_id: Gmail message ID

        Returns:
            Message data

        Raises:
            HttpError: If API request fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            logger.info(f"Retrieved message {message_id}")
            return message

        except HttpError as e:
            logger.error(f"Failed to get message {message_id}: {e}", exc_info=True)
            raise

    async def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None
    ) -> dict:
        """Send email message.

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body (plain text)
            thread_id: Gmail thread ID for replies
            in_reply_to: Message-ID header for threading
            references: References header for threading

        Returns:
            Sent message metadata

        Raises:
            HttpError: If send fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            from email.mime.text import MIMEText
            import base64

            # Create MIME message
            message = MIMEText(body)
            message['To'] = to
            message['Subject'] = subject
            message['From'] = settings.GMAIL_SUPPORT_ADDRESS

            # Add threading headers
            if in_reply_to:
                message['In-Reply-To'] = in_reply_to
            if references:
                message['References'] = references

            # Encode message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            # Prepare send request
            send_request = {'raw': raw_message}
            if thread_id:
                send_request['threadId'] = thread_id

            # Send message
            sent_message = self.service.users().messages().send(
                userId='me',
                body=send_request
            ).execute()

            logger.info(
                f"Sent message to {to}",
                extra={
                    "message_id": sent_message['id'],
                    "thread_id": sent_message.get('threadId')
                }
            )

            return sent_message

        except HttpError as e:
            logger.error(f"Failed to send message to {to}: {e}", exc_info=True)
            raise

    async def register_watch(self) -> dict:
        """Register Gmail push notifications via Pub/Sub.

        Returns:
            Watch response with expiration timestamp

        Raises:
            HttpError: If watch registration fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            request_body = {
                'topicName': settings.GMAIL_PUBSUB_TOPIC,
                'labelIds': ['INBOX']
            }

            watch_response = self.service.users().watch(
                userId='me',
                body=request_body
            ).execute()

            logger.info(
                "Gmail watch registered",
                extra={
                    "history_id": watch_response.get('historyId'),
                    "expiration": watch_response.get('expiration')
                }
            )

            return watch_response

        except HttpError as e:
            logger.error(f"Failed to register Gmail watch: {e}", exc_info=True)
            raise


# Singleton instance
@lru_cache(maxsize=1)
def get_gmail_service() -> GmailService:
    """Get singleton Gmail service instance."""
    return GmailService()
```

#### 6.3: Update Configuration

Add to `backend/src/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Gmail Configuration
    GMAIL_SUPPORT_ADDRESS: str
    GMAIL_PUBSUB_TOPIC: str
    GMAIL_WEBHOOK_SECRET: str
    GCP_PROJECT_ID: str

    # Secret Manager
    USE_SECRET_MANAGER: bool = True  # Set to False for local dev

    class Config:
        env_file = ".env"
```

#### 6.4: Initialize on Application Startup

Update `backend/src/main.py`:

```python
from contextlib import asynccontextmanager
from src.services.gmail_service import get_gmail_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application...")

    # Initialize Gmail service
    gmail_service = get_gmail_service()
    await gmail_service.initialize()

    # Register Gmail watch (if not already registered)
    try:
        await gmail_service.register_watch()
    except Exception as e:
        logger.warning(f"Gmail watch registration failed: {e}")
        # Don't fail startup if watch registration fails

    yield

    # Shutdown
    logger.info("Shutting down application...")

app = FastAPI(lifespan=lifespan)
```

### Step 7: Environment Configuration

Update `backend/.env` (production):

```bash
# Gmail Production Configuration
GMAIL_SUPPORT_ADDRESS=support@yourdomain.com
GMAIL_PUBSUB_TOPIC=projects/your-project-id/topics/gmail-notifications
GMAIL_WEBHOOK_SECRET=your-secure-webhook-secret-here
GCP_PROJECT_ID=your-project-id

# Secret Manager
USE_SECRET_MANAGER=true

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/crm_prod

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka-broker:9092
```

### Step 8: Deploy and Verify

```bash
# Deploy application (example using Cloud Run)
gcloud run deploy crm-digital-fte \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GMAIL_SUPPORT_ADDRESS=support@yourdomain.com,GMAIL_PUBSUB_TOPIC=projects/your-project-id/topics/gmail-notifications"

# Get deployed URL
SERVICE_URL=$(gcloud run services describe crm-digital-fte --region us-central1 --format="value(status.url)")

# Update Pub/Sub subscription with actual URL
gcloud pubsub subscriptions update gmail-webhook-subscription \
  --push-endpoint="${SERVICE_URL}/webhooks/gmail"

echo "✓ Application deployed and Pub/Sub configured"
```

---

## Security Best Practices

### 1. Never Commit Credentials

Add to `.gitignore`:

```gitignore
# Service account keys
service-account-key.json
*-service-account*.json

# OAuth credentials
client_secret*.json
*credentials*.json

# Environment files
.env
.env.local
.env.production
```

### 2. Use Secret Manager for All Secrets

```bash
# Store webhook secret
echo -n "your-webhook-secret" | gcloud secrets create gmail-webhook-secret --data-file=-

# Store database credentials
echo -n "postgresql://..." | gcloud secrets create database-url --data-file=-

# Access in application
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
```

### 3. Rotate Service Account Keys

```bash
# Create new key
gcloud iam service-accounts keys create new-key.json \
  --iam-account=$SERVICE_ACCOUNT_EMAIL

# Update secret
gcloud secrets versions add gmail-service-account-key \
  --data-file=new-key.json

# Delete old key (after verifying new key works)
gcloud iam service-accounts keys list \
  --iam-account=$SERVICE_ACCOUNT_EMAIL

gcloud iam service-accounts keys delete OLD_KEY_ID \
  --iam-account=$SERVICE_ACCOUNT_EMAIL

# Clean up local file
rm new-key.json
```

**Rotation Schedule:** Every 90 days (set calendar reminder).

### 4. Principle of Least Privilege

Only grant necessary scopes:

```python
# Minimal scopes for read-only access
scopes = [
    'https://www.googleapis.com/auth/gmail.readonly',
]

# Add send scope only if needed
scopes.append('https://www.googleapis.com/auth/gmail.send')
```

### 5. Enable Audit Logging

```bash
# Enable Cloud Audit Logs for Secret Manager
gcloud logging read "resource.type=secretmanager.googleapis.com" --limit 10

# Set up alerts for secret access
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Secret Access Alert" \
  --condition-display-name="Unusual secret access" \
  --condition-threshold-value=10 \
  --condition-threshold-duration=60s
```

### 6. Webhook Authentication

Verify Pub/Sub push requests:

```python
import base64
import json
from fastapi import HTTPException, Request

async def verify_pubsub_token(request: Request):
    """Verify Pub/Sub push authentication token."""
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")

    token = auth_header.replace("Bearer ", "")

    # Verify JWT token (implement proper JWT verification)
    # See: https://cloud.google.com/pubsub/docs/push#authentication_and_authorization
    # ...

    return True
```

---

## Monitoring & Maintenance

### 1. Gmail Watch Expiration

Gmail watch expires after **7 days**. You must renew it regularly.

#### Create Renewal Script

Create `backend/scripts/renew_gmail_watch.py`:

```python
"""Renew Gmail watch subscription."""

import asyncio
import logging
from src.services.gmail_service import get_gmail_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def renew_watch():
    """Renew Gmail watch subscription."""
    try:
        gmail_service = get_gmail_service()
        await gmail_service.initialize()

        watch_response = await gmail_service.register_watch()

        logger.info(
            "Gmail watch renewed successfully",
            extra={
                "expiration": watch_response.get('expiration'),
                "history_id": watch_response.get('historyId')
            }
        )

        return watch_response

    except Exception as e:
        logger.error(f"Failed to renew Gmail watch: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(renew_watch())
```

#### Set Up Cron Job

```bash
# Add to crontab (run every 6 days)
0 0 */6 * * cd /app/backend && python scripts/renew_gmail_watch.py >> /var/log/gmail-watch-renewal.log 2>&1
```

Or use **Cloud Scheduler**:

```bash
# Create Cloud Scheduler job
gcloud scheduler jobs create http gmail-watch-renewal \
  --schedule="0 0 */6 * *" \
  --uri="https://your-app-domain.com/admin/renew-gmail-watch" \
  --http-method=POST \
  --oidc-service-account-email=$SERVICE_ACCOUNT_EMAIL
```

### 2. Monitoring Metrics

Track these metrics:

```python
from prometheus_client import Counter, Histogram

# Email processing metrics
emails_received = Counter('emails_received_total', 'Total emails received')
emails_processed = Counter('emails_processed_total', 'Total emails processed successfully')
emails_failed = Counter('emails_failed_total', 'Total emails failed to process')
email_processing_time = Histogram('email_processing_seconds', 'Email processing time')

# Gmail API metrics
gmail_api_calls = Counter('gmail_api_calls_total', 'Total Gmail API calls', ['method'])
gmail_api_errors = Counter('gmail_api_errors_total', 'Gmail API errors', ['error_type'])
```

### 3. Alerting

Set up alerts for:

- Gmail watch expiration (< 24 hours remaining)
- High error rate (> 5% of emails failing)
- API quota exceeded
- Secret access anomalies
- Webhook delivery failures

```bash
# Example: Alert on high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Email Processing Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s
```

### 4. Health Check Endpoint

Add to `backend/src/main.py`:

```python
@app.get("/health/gmail")
async def gmail_health_check():
    """Check Gmail service health."""
    try:
        gmail_service = get_gmail_service()

        if not gmail_service._initialized:
            return {"status": "unhealthy", "reason": "Gmail service not initialized"}

        # Try to fetch profile (lightweight API call)
        profile = gmail_service.service.users().getProfile(userId='me').execute()

        return {
            "status": "healthy",
            "email": profile.get('emailAddress'),
            "messages_total": profile.get('messagesTotal'),
            "threads_total": profile.get('threadsTotal')
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "reason": str(e)
        }
```

---

## Troubleshooting

### Issue 1: "Domain-wide delegation not enabled"

**Error:**
```
google.auth.exceptions.RefreshError: unauthorized_client: Client is unauthorized to retrieve access tokens using this method
```

**Solution:**
1. Verify domain-wide delegation is enabled in Google Workspace Admin Console
2. Check that the correct client ID is authorized
3. Ensure all required scopes are listed
4. Wait 10-15 minutes for changes to propagate

### Issue 2: "Secret not found"

**Error:**
```
google.api_core.exceptions.NotFound: 404 Secret [gmail-service-account-key] not found
```

**Solution:**
```bash
# Verify secret exists
gcloud secrets list | grep gmail

# Check IAM permissions
gcloud secrets get-iam-policy gmail-service-account-key

# Grant access if needed
gcloud secrets add-iam-policy-binding gmail-service-account-key \
  --member="serviceAccount:your-app-sa@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Issue 3: "Pub/Sub push endpoint unreachable"

**Error:** Emails arrive but webhook is never called.

**Solution:**
```bash
# Check subscription status
gcloud pubsub subscriptions describe gmail-webhook-subscription

# Test endpoint manually
curl -X POST https://your-app-domain.com/webhooks/gmail \
  -H "Content-Type: application/json" \
  -d '{"message":{"data":"dGVzdA==","messageId":"test"}}'

# Check Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Verify endpoint is publicly accessible (not behind VPN)
```

### Issue 4: "Gmail watch expired"

**Error:** Emails stop being processed after 7 days.

**Solution:**
```bash
# Check watch status (if you stored expiration)
# Watch expires after 7 days

# Renew watch
python backend/scripts/renew_gmail_watch.py

# Set up automated renewal (see Monitoring section)
```

### Issue 5: "Quota exceeded"

**Error:**
```
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded for quota metric 'Read requests' and limit 'Read requests per day'
```

**Solution:**
1. Check quota usage in Google Cloud Console
2. Request quota increase if needed
3. Implement caching to reduce API calls
4. Use batch requests where possible

---

## Cost Estimation

### Google Cloud Costs (Approximate)

| Service | Usage | Cost/Month |
|---------|-------|------------|
| **Gmail API** | 10,000 emails/day | Free (within quota) |
| **Pub/Sub** | 10,000 messages/day | ~$0.40 |
| **Secret Manager** | 5 secrets, 30,000 accesses | ~$0.30 |
| **Cloud Run** | 1M requests, 2GB RAM | ~$10-20 |
| **Cloud Scheduler** | 1 job (watch renewal) | ~$0.10 |
| **Total** | | **~$11-21/month** |

**Gmail API Quotas (Free Tier):**
- 1 billion quota units per day
- Read: 5 units per request
- Send: 100 units per request
- Approximately 200 million reads or 10 million sends per day

---

## Next Steps

1. ✅ Complete all setup steps above
2. ✅ Test with a real email to `support@yourdomain.com`
3. ✅ Verify webhook receives notification
4. ✅ Check database for processed email
5. ✅ Set up monitoring and alerting
6. ✅ Schedule watch renewal cron job
7. ✅ Document runbook for on-call team
8. ✅ Plan key rotation schedule (every 90 days)

---

## References

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [Domain-Wide Delegation](https://developers.google.com/identity/protocols/oauth2/service-account#delegatingauthority)
- [Gmail Push Notifications](https://developers.google.com/gmail/api/guides/push)
- [Google Cloud Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Pub/Sub Push Authentication](https://cloud.google.com/pubsub/docs/push#authentication_and_authorization)

---

## Support

For issues or questions:
- Check troubleshooting section above
- Review Cloud Logging for errors
- Contact DevOps team for infrastructure issues
- Escalate to Google Cloud Support for API/quota issues
