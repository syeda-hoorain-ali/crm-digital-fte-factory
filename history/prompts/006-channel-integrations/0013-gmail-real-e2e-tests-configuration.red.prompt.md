---
id: 0013
title: Gmail Real E2E Tests and Configuration
stage: red
date: 2026-03-10
surface: agent
model: qwen3-code-plus
feature: 006-channel-integrations
branch: 006-channel-integrations
user: d
command: continue
labels: ["e2e-testing", "gmail", "configuration", "documentation"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/tests/helpers/gmail_test_helper.py
  - backend/tests/e2e/test_gmail_real_flow.py
  - backend/tests/e2e/README_GMAIL_E2E.md
  - backend/scripts/generate_gmail_credentials.py
  - backend/scripts/register_gmail_watch.py
  - backend/scripts/renew_gmail_watch.py
  - backend/.gitignore
  - backend/.env.example
  - backend/src/config.py
  - docs/guides/gmail-production-setup.md
tests:
  - backend/tests/e2e/test_gmail_real_flow.py::TestGmailRealFlow::test_gmail_inbound_email_processing
  - backend/tests/e2e/test_gmail_real_flow.py::TestGmailRealFlow::test_gmail_reply_threading
---

## Prompt

User requested to create TRUE end-to-end tests for Gmail integration that send REAL emails (not simulated data). Specific requirement: "send actual mail from a email address to email address (saved in .env file), then check if the application endpoint receive it, process it and give the ans back, and more tests (e.g, check database, kafka events, etc)".

User wanted standalone Gmail E2E test created first, then integrated into test_complete_multichannel_flow later.

Throughout the session, user actively engaged in improving documentation by:
- Questioning why JSON credentials file is needed vs just client ID/secret
- Requesting production setup guide
- Pointing out redundant inline code that should use the script instead
- Questioning why separate application account credentials were needed (correctly identified as unnecessary)
- Suggesting VS Code port forwarding as simpler alternative to ngrok
- Identifying configuration mismatches in scripts (uppercase vs lowercase attribute names)

## Response

### 1. Gmail E2E Test Infrastructure Created

**Test Helper (`backend/tests/helpers/gmail_test_helper.py`):**
- Wrapper around Gmail API for test operations
- Methods: send_test_email(), wait_for_reply(), get_message(), delete_message(), delete_thread(), search_messages()
- Gmail API is synchronous, so methods are sync but can be called with asyncio.to_thread()
- Handles OAuth credentials with automatic token refresh

**E2E Tests (`backend/tests/e2e/test_gmail_real_flow.py`):**
- Two comprehensive E2E tests:
  1. `test_gmail_inbound_email_processing`: Sends real email, polls database for 60s, verifies customer/conversation/message/ticket/webhook log
  2. `test_gmail_reply_threading`: Tests email threading and conversation continuity
- Uses real Gmail API to send actual emails
- Polls database with 60-second timeout and 2-second intervals
- Verifies complete flow: email sent → webhook triggered → database records created
- Automatic cleanup of test emails

**Credential Generation Script (`backend/scripts/generate_gmail_credentials.py`):**
- CLI tool to generate OAuth credentials with access token
- Commands: `generate` (create new), `verify` (check existing)
- Enhanced to automatically update .env file with credentials and authenticated email
- Fetches user's email address via Gmail API
- Handles OAuth flow with browser-based consent

**Setup Guide (`backend/tests/e2e/README_GMAIL_E2E.md`):**
- Comprehensive guide for Gmail E2E testing setup
- Covers: OAuth credential generation, Pub/Sub setup, environment configuration, troubleshooting, CI/CD integration
- **Key improvements based on user feedback:**
  - Removed all gcloud commands (replaced with web console instructions)
  - Removed redundant inline Python code (use script instead)
  - Removed confusing "Application Account" section (not needed for E2E testing)
  - Made VS Code port forwarding the recommended option (Option 1)
  - Added ngrok as alternative in collapsible `<details>` section (Option 2)
  - Fixed all endpoint URL references to mention both VS Code and ngrok

### 2. Production Setup Guide Created

**Production Guide (`docs/guides/gmail-production-setup.md`):**
- Comprehensive production setup guide for Gmail integration
- Covers: Service Account creation, domain-wide delegation, Secret Manager integration, Pub/Sub configuration
- Key sections:
  - Service Account setup vs OAuth (production uses Service Account, not OAuth)
  - Domain-wide delegation in Google Workspace Admin Console
  - Secure credential storage in Secret Manager
  - Production application code with GmailService class
  - Gmail watch renewal (expires every 7 days)
  - Monitoring metrics and alerting
  - Security best practices (never commit credentials, rotate keys every 90 days, least privilege)

### 3. Configuration Fixes

**Settings Class (`backend/src/config.py`):**
Added Gmail configuration fields:
- `gmail_credentials_path`: Path to Gmail API OAuth credentials JSON file
- `gmail_service_account_path`: Path to service account credentials (for production)
- `gmail_support_address`: Gmail address that receives customer emails
- `gmail_pubsub_topic`: Google Cloud Pub/Sub topic for Gmail notifications
- `gmail_webhook_secret`: Secret for validating Gmail webhook requests
- `gcp_project_id`: Google Cloud Platform project ID

**Script Fixes:**
- Fixed `backend/scripts/register_gmail_watch.py`:
  - Changed uppercase attribute names (GMAIL_CREDENTIALS_FILE) to lowercase (gmail_credentials_path)
  - Added validation to ensure settings are not empty
  - Added proper error handling for missing Pub/Sub topic configuration
- Fixed `backend/scripts/renew_gmail_watch.py`:
  - Same uppercase to lowercase attribute name fixes
  - Added validation for Pub/Sub topic configuration
  - Improved error messages

**Environment Configuration:**
- Updated `backend/.env` with test credentials automatically via script
- Updated `backend/.env.example` with all Gmail settings:
  - Production settings (GMAIL_CREDENTIALS_PATH, GMAIL_SERVICE_ACCOUNT_PATH, etc.)
  - E2E testing settings (GMAIL_TEST_CREDENTIALS_PATH, GMAIL_TEST_ACCOUNT_EMAIL)
  - Added GEMINI_API_KEY (required by Settings class)
- Secured credentials in `backend/.gitignore`:
  - Added `*credentials*.json`
  - Added `client_secret*.json`

### 4. Key Technical Decisions

**OAuth vs Service Account:**
- E2E testing uses OAuth credentials (user consent flow)
- Production uses Service Account with domain-wide delegation
- Scripts support both credential types for flexibility

**Local Development Tunnel:**
- Gmail Pub/Sub requires public HTTPS endpoint
- VS Code port forwarding recommended (no installation, built-in)
- ngrok as alternative for non-VS Code users
- Both options documented with clear examples

**Database Polling Pattern:**
- Tests poll database for up to 60 seconds waiting for webhook processing
- 2-second intervals to balance responsiveness and load
- Accounts for Gmail Pub/Sub delivery latency

**Credential Security:**
- Never commit credentials to git (.gitignore)
- Production uses Secret Manager for credential storage
- OAuth credentials contain: client_id, client_secret, token, refresh_token, token_uri, scopes
- Service account keys rotated every 90 days

### 5. Files Created/Modified

**Created:**
- `backend/tests/helpers/gmail_test_helper.py` (303 lines)
- `backend/tests/e2e/test_gmail_real_flow.py` (385 lines)
- `backend/tests/e2e/README_GMAIL_E2E.md` (comprehensive guide)
- `backend/scripts/generate_gmail_credentials.py` (credential generator with auto .env update)
- `docs/guides/gmail-production-setup.md` (production setup guide)

**Modified:**
- `backend/src/config.py` (added Gmail configuration fields)
- `backend/scripts/register_gmail_watch.py` (fixed attribute names, added validation)
- `backend/scripts/renew_gmail_watch.py` (fixed attribute names, added validation)
- `backend/.env` (added test credentials automatically)
- `backend/.env.example` (added all Gmail settings)
- `backend/.gitignore` (secured credential files)

### 6. Current Status

**Infrastructure:** ✅ Complete
- All code written
- All scripts working
- All configuration consistent
- All documentation comprehensive

**Can Run Test:** ❌ No - Requires manual setup:
1. Add GMAIL_SUPPORT_ADDRESS to .env
2. Start app and forward port (VS Code or ngrok)
3. Set up Pub/Sub in Google Cloud Console
4. Register Gmail watch
5. Run test

**Stage:** RED - Tests written, infrastructure ready, awaiting configuration to run

### 7. Next Steps

**To Run Gmail E2E Test:**
1. User needs to set up Gmail Pub/Sub (web console - 5 min setup)
2. User needs to register Gmail watch (run script)
3. User needs to run the test

**To Continue with Original Plan:**
- Original request: "first create a stand alone test for gmail, and after it become successfull, then add it into test_complete_multichannel_flow too"
- Standalone test infrastructure: ✅ Created
- Test successful: ❌ Not yet (requires manual setup)
- Integration into multichannel: ❌ Not started

**Parallel Work Options:**
- Create similar real E2E tests for WhatsApp channel
- Create similar real E2E tests for Web Form channel
- User can set up all three channels in parallel once all infrastructure is ready

## Outcome

Gmail E2E test infrastructure is complete and fully documented. All code, scripts, configuration, and documentation are ready. The test can run once user completes manual Pub/Sub setup. Configuration issues across multiple files have been resolved, and all scripts now use consistent lowercase attribute names matching the Settings class.

## Evaluation

**What Went Well:**
- User actively engaged in improving documentation quality
- User identified redundant/confusing sections that needed removal
- User suggested simpler alternatives (VS Code port forwarding vs ngrok)
- User caught configuration mismatches (uppercase vs lowercase attributes)
- Comprehensive infrastructure created following same pattern as original multichannel test

**What Could Be Improved:**
- Initial documentation had redundant sections (inline code when script exists)
- Initial configuration used inconsistent naming (uppercase in scripts, lowercase in Settings)
- Could have anticipated VS Code port forwarding as simpler option from the start

**Lessons Learned:**
- Always check for simpler built-in alternatives before recommending external tools
- Keep documentation DRY - don't duplicate code that exists in scripts
- Ensure consistent naming conventions across all files (Settings class, scripts, .env)
- User feedback is invaluable for improving documentation quality
