---
id: 0015
title: Align Gmail Config Two Account Testing
stage: green
date: 2026-03-10
surface: agent
model: qwen3-code-plus
feature: 006-channel-integrations
branch: 006-channel-integrations
user: d
command: none
labels: ["gmail", "e2e-testing", "configuration", "two-account-approach", "scripts"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/scripts/generate_gmail_credentials.py
  - backend/scripts/register_gmail_watch.py
  - backend/scripts/renew_gmail_watch.py
  - backend/src/config.py
  - backend/src/main.py
  - backend/.env.example
  - backend/tests/e2e/README_GMAIL_E2E.md
tests:
  - None (configuration and script updates)
---

## Prompt

User asked: "are the scripts uptodate with this? are environment variables updateodate? is .env.example file also uptodate?"

Context: After updating the Gmail E2E testing README to document the two-account approach (sender account for sending emails, receiver account for receiving webhooks with full Pub/Sub infrastructure), the user wanted to verify that all scripts, configuration files, and environment variables were aligned with this approach.

User also requested: "yes fix it and in th issue 1 we may add another flag for something like type?"

## Response snapshot

Identified and fixed 4 main issues to align with the two-account approach:

**Issue 1: generate_gmail_credentials.py**
- Problem: Script was setting `GMAIL_SUPPORT_ADDRESS` to the same email as the test account
- Fix: Added `--account-type` parameter (choices: `sender` or `receiver`)
  - Sender account: Sets `GMAIL_TEST_CREDENTIALS_PATH` and `GMAIL_TEST_ACCOUNT_EMAIL`
  - Receiver account: Sets `GMAIL_SUPPORT_CREDENTIALS_PATH`, `GMAIL_SUPPORT_ADDRESS`, `GCP_PROJECT_ID`, and `GMAIL_PUBSUB_TOPIC`
- Updated next steps output based on account type

**Issue 2: register_gmail_watch.py**
- Problem: Using `settings.gmail_test_credentials_path` instead of receiver account credentials
- Fix: Now prioritizes `settings.gmail_support_credentials_path` with fallback to `gmail_test_credentials_path` (with warning)

**Issue 3: config.py**
- Problem: Missing `gmail_support_credentials_path` field
- Fix: Added field with description "Path to Gmail API OAuth credentials JSON file (for receiver/support account)"

**Issue 4: .env.example**
- Problem: Missing `GMAIL_SUPPORT_CREDENTIALS_PATH` variable
- Fix: Added variable to Gmail Configuration section with clarifying comments

**Additional fixes:**
- Updated `renew_gmail_watch.py` to use receiver account credentials
- Updated `main.py` Gmail handler initialization to prioritize receiver account credentials
- Updated README commands to include `--account-type` flag

**Usage examples:**

Receiver account (support inbox):
```bash
uv run scripts/generate_gmail_credentials.py generate \
  --client-secret /path/to/receiver-client-secret.json \
  --output gmail-support-credentials.json \
  --account-type receiver
```

Sender account (test account):
```bash
uv run scripts/generate_gmail_credentials.py generate \
  --client-secret /path/to/sender-client-secret.json \
  --output gmail-test-credentials.json \
  --account-type sender
```

## Outcome

- ✅ Impact: All scripts, configuration, and documentation now correctly distinguish between sender account (simple OAuth for sending emails) and receiver account (OAuth + Pub/Sub infrastructure for webhook processing)
- 🧪 Tests: No new tests added (configuration and script updates only)
- 📁 Files: 7 files modified (scripts, config, .env.example, README)
- 🔁 Next prompts: Ready to run Gmail E2E tests with proper two-account setup
- 🧠 Reflection: The two-account approach is now fully implemented across all components. Scripts automatically set the correct environment variables based on account type, preventing the self-sent email issues with Gmail History API.

## Evaluation notes (flywheel)

- Failure modes observed: None - straightforward configuration alignment
- Graders run and results (PASS/FAIL): N/A (configuration changes)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Test the updated scripts with actual Gmail account setup to verify the two-account flow works end-to-end
