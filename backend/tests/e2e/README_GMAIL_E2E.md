# Gmail Real E2E Testing Setup

This guide explains how to set up and run real Gmail E2E tests that send actual emails through Gmail API.

## Overview

The Gmail E2E tests (`test_gmail_real_flow.py`) perform true end-to-end testing by:

1. **Sending real emails** from a test Gmail account to your application's support email address
2. **Waiting for Gmail Pub/Sub notifications** to trigger the webhook
3. **Verifying database records** (customers, conversations, messages, tickets)
4. **Checking Kafka events** (if available)
5. **Cleaning up test data** after completion

## Important: Two Gmail Accounts Required

**You need TWO separate Gmail accounts for E2E testing:**

| Aspect | Sender Account (Test Account) | Receiver Account (Support Account) |
|--------|-------------------------------|-------------------------------------|
| **Purpose** | Simulates a customer sending emails | Your application's support inbox |
| **Represents** | Regular Gmail user (like your customers in production) | Your application's email processing system |
| **OAuth Setup** | Basic OAuth credentials (client ID + secret) | OAuth credentials with push notification permissions |
| **Infrastructure** | ❌ **No Pub/Sub, no watch, no webhook setup required** | ✅ **ALL the complex infrastructure lives here**: Gmail watch, Pub/Sub topic, push subscription, webhook endpoint |
| **Example** | `test-sender@gmail.com` | `support@yourdomain.com` or `your-app-support@gmail.com` |


## Setup Steps

### 1. Google Cloud Project Setup

You need a Google Cloud project with Gmail API and Pub/Sub API enabled:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to **APIs & Services > Library**
4. Search for "Gmail API" and click **Enable**
5. Search for "Cloud Pub/Sub API" and click **Enable**

### 2. Receiver Account Setup (Support Account)

**This is where ALL the complex setup happens.** This account represents your application's support inbox that receives customer emails.

#### Generate OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services > Credentials**
3. Click **Create Credentials > OAuth Client ID**
4. Choose **Desktop app** as application type
5. Download the credentials JSON file (e.g., `receiver-client-secret.json`)
6. Generate credentials with access token:

```bash
cd backend
uv run scripts/generate_gmail_credentials.py generate \
  --client-secret /path/to/receiver-client-secret.json \
  --output gmail-support-credentials.json \
  --account-type receiver
```


This will:
- Open your browser for OAuth consent
- Ask you to **log in with your RECEIVER account** (e.g., `support@yourdomain.com`)
- Request permission to access Gmail and manage push notifications
- Save credentials with access token to `gmail-support-credentials.json`
- Update `.env` with `GMAIL_SUPPORT_CREDENTIALS_PATH` and `GMAIL_SUPPORT_ADDRESS`

---

### 3. Local Development Tunnel

**Why needed:** Gmail Pub/Sub requires a publicly accessible HTTPS endpoint. During local E2E testing, your app runs on localhost which Google's servers cannot reach.

#### Option 1: VS Code Port Forwarding (Recommended)

**Simplest option** - No installation required if you're using VS Code.

1. **Start your FastAPI app**:
   ```bash
   cd backend
   uv run uvicorn src.main:app --reload --port 8000
   ```

2. **Forward the port in VS Code**:
   - Open the **Ports** tab in VS Code terminal panel
   - Click **Forward a Port**
   - Enter port number: `8000`
   - Right-click the forwarded port → **Port Visibility** → **Public**
   - Copy the forwarded address (e.g., `https://abc123-8000.inc1.devtunnels.ms`)

3. **Use the forwarded URL** for Pub/Sub subscription:
   ```
   https://abc123-8000.inc1.devtunnels.ms/webhooks/gmail
   ```

**Note:** The forwarded URL remains active as long as VS Code is running and connected.

<details>
<summary><b>Option 2: ngrok (Alternative)</b></summary>

Use ngrok if you're not using VS Code or need more advanced features.

**Install ngrok:**

1. Download from [ngrok.com](https://ngrok.com/download)
2. Extract and add to PATH, or install via package manager:
   ```bash
   # Windows (chocolatey)
   choco install ngrok

   # macOS
   brew install ngrok/ngrok/ngrok

   # Linux
   snap install ngrok
   ```

3. Sign up for free account at [ngrok.com](https://ngrok.com) and get auth token
4. Configure auth token:
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

**Start ngrok tunnel:**

1. **Start your FastAPI app** (in one terminal):
   ```bash
   cd backend
   uv run uvicorn src.main:app --reload --port 8000
   ```

2. **Start ngrok tunnel** (in another terminal):
   ```bash
   ngrok http 8000
   ```

3. **Copy the HTTPS URL** from ngrok output:
   ```
   Forwarding  https://abc123def456.ngrok-free.app -> http://localhost:8000
   ```

   Your webhook URL will be: `https://abc123def456.ngrok-free.app/webhooks/gmail`

**Important Notes:**
- Free ngrok URLs change every time you restart ngrok
- You'll need to update the Pub/Sub subscription URL each time
- Keep ngrok running while testing
- For stable URLs, use ngrok paid plan with custom subdomain

</details>

### 4. Gmail Pub/Sub Watch Setup (RECEIVER ACCOUNT ONLY)

**⚠️ This entire section is ONLY for the RECEIVER/SUPPORT account.** The sender account doesn't need any of this infrastructure.

Configure Gmail to send push notifications when emails arrive **at the RECEIVER account (support inbox)**:

#### Create Pub/Sub Topic

1. Go to [Cloud Pub/Sub Console](https://console.cloud.google.com/cloudpubsub/topic/list)
2. Click **Create Topic**
3. Topic ID: `gmail-notifications`
4. Click **Create**

#### Grant Gmail Permission

1. In the topic details page, go to **Permissions** tab
2. Click **Add Principal**
3. Principal: `gmail-api-push@system.gserviceaccount.com`
4. Role: **Pub/Sub Publisher**
5. Click **Save**

#### Create Push Subscription

1. In the topic details, scroll down to **Subscriptions** tab
2. Click **Create Subscription**
3. Subscription ID: `gmail-webhook-sub`
4. Delivery type: **Push**
5. Endpoint URL: Use your forwarded URL + `/webhooks/gmail`
   - **VS Code:** `https://abc123-8000.inc1.devtunnels.ms/webhooks/gmail`
   - **ngrok:** `https://abc123def456.ngrok-free.app/webhooks/gmail`
6. Click **Create**

#### Register Gmail Watch (on Receiver Account)

Run the provided script to register the watch **on your RECEIVER/support account**:

```bash
cd backend
# Make sure GMAIL_TEST_CREDENTIALS_PATH points to receiver credentials
export GMAIL_TEST_CREDENTIALS_PATH=gmail-support-credentials.json
uv run scripts/register_gmail_watch.py
```

**Important:** The watch must be registered on the account that RECEIVES emails (support account), not the sender account.

**Note:** Gmail watch expires after 7 days. You need to renew it:

```bash
# Renew watch (run weekly via cron)
cd backend
export GMAIL_TEST_CREDENTIALS_PATH=gmail-support-credentials.json
uv run scripts/renew_gmail_watch.py
```

### 5. Test Account Setup (Sender Account)

**Simple OAuth only** - just get client ID and secret.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services > Library**
3. Search for "Gmail API" and click **Enable**
4. Navigate to **APIs & Services > Credentials**
5. Click **Create Credentials > OAuth Client ID**
6. Choose **Desktop app** as application type
7. Download the credentials JSON file (e.g., `sender-client-secret.json`)
8. Generate credentials with access token:

```bash
cd backend
uv run scripts/generate_gmail_credentials.py generate \
  --client-secret /path/to/sender-client-secret.json \
  --output gmail-test-credentials.json \
  --account-type sender
```

This will:
- Open your browser for OAuth consent
- Ask you to **log in with your TEST account** (e.g., `test-sender@gmail.com`)
- Request permission to send emails via Gmail API
- Save credentials with access token to `gmail-test-credentials.json`
- Update `.env` with `GMAIL_TEST_CREDENTIALS_PATH` and `GMAIL_TEST_ACCOUNT_EMAIL`

**That's it for the test account!** No Pub/Sub, no watch, no webhook setup needed.

## Running the Tests

### Run All Gmail E2E Tests

```bash
# With output visible
uv run pytest tests/e2e/test_gmail_real_flow.py -v -s --no-cov

# Specific test
uv run pytest tests/e2e/test_gmail_real_flow.py::TestGmailRealFlow::test_gmail_inbound_email_processing -v -s --no-cov
```

## References

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Gmail Push Notifications](https://developers.google.com/gmail/api/guides/push)
- [Google Cloud Pub/Sub](https://cloud.google.com/pubsub/docs)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
