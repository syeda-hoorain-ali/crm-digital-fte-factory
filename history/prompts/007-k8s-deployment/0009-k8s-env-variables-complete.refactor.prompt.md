---
id: 0009
title: Complete K8s Environment Variables Configuration
stage: refactor
date: 2026-04-02
surface: agent
model: qwen3-code-plus
feature: 007-k8s-deployment
branch: 007-k8s-deployment
user: Syeda Hoorain Ali
command: continue
labels: ["k8s", "environment-variables", "configuration", "externalization"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - k8s/configmap.yaml
  - k8s/secrets.yaml
  - backend/src/config.py
  - backend/src/main.py
  - backend/src/workers/message_processor.py
  - scripts/deploy-k8s.sh
  - docs/k8s-env-validation.md
  - .env.example (deleted)
tests:
  - Manual verification of ConfigMap variables count (36)
  - Manual verification of Secrets variables count (11)
  - Alignment check between config.py and K8s manifests
---

## Prompt

User requested to add ALL environment variables from backend/.env.example file into K8s deployment, excluding test-only variables. The requirement was that any configuration value should be changeable in production without modifying code.

Initial context:
- Found variable naming mismatches (TWILIO_WHATSAPP_FROM vs TWILIO_APP_NUMBER)
- Only partial environment variables were in K8s manifests
- Root .env.example file existed (not created by me, but user wanted it deleted)

User's explicit requirements:
1. Delete root .env.example file
2. Add ALL environment variables from backend/.env.example to K8s
3. Keep required variables required, optional variables optional
4. Ensure all values can be changed in production without code changes

## Response snapshot

**Analysis Phase:**
- Read backend/src/config.py to identify all configuration fields (47 total)
- Identified which fields should be in ConfigMap (non-sensitive) vs Secrets (sensitive)
- Categorized variables: required vs optional, test-only vs production

**Implementation:**

1. **Fixed Variable Name Mismatches:**
   - Changed config.py: `twilio_whatsapp_from` → `twilio_app_number`
   - Updated k8s/secrets.yaml: `TWILIO_WHATSAPP_NUMBER` → `TWILIO_APP_NUMBER`
   - Updated scripts/deploy-k8s.sh validation to use `TWILIO_APP_NUMBER`
   - Updated code references in main.py and message_processor.py

2. **Expanded ConfigMap (k8s/configmap.yaml) to 36 variables:**
   - Application: ENVIRONMENT, LOG_LEVEL
   - Gemini: GEMINI_BASE_URL
   - Embedding: EMBEDDING_MODEL, EMBEDDING_DIMENSION
   - API: API_HOST, API_PORT, CORS_ORIGINS
   - Agent: AGENT_MODEL, AGENT_MAX_TOKENS, AGENT_TEMPERATURE, AGENT_COST_PER_MILLION_TOKENS
   - Escalation: ESCALATION_EMAIL_LOW, ESCALATION_EMAIL_MEDIUM, ESCALATION_EMAIL_HIGH, ESCALATION_EMAIL_CRITICAL
   - SMTP: SMTP_HOST, SMTP_PORT, SMTP_FROM_EMAIL, SMTP_USE_TLS, ENABLE_EMAIL_NOTIFICATIONS
   - Database Pool: DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_TIMEOUT
   - Knowledge Base: KB_SEARCH_LIMIT, KB_MIN_SIMILARITY
   - Services: KAFKA_BOOTSTRAP_SERVERS, REDIS_URL, KAFKA_TOPIC_PREFIX, RATE_LIMIT_PER_MINUTE
   - Gmail: GMAIL_SUPPORT_ADDRESS, GMAIL_PUBSUB_TOPIC, GCP_PROJECT_ID
   - Observability: ENABLE_DEBUG_LOGGING, ENABLE_METRICS, ENABLE_TRACING

3. **Expanded Secrets (k8s/secrets.yaml) to 11 variables:**
   - Required: DATABASE_URL, GEMINI_API_KEY, GMAIL_SERVICE_ACCOUNT_PATH, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_APP_NUMBER, TWILIO_WEBHOOK_SECRET
   - Optional: GMAIL_SUPPORT_CREDENTIALS_PATH, GMAIL_WEBHOOK_SECRET, SMTP_USERNAME, SMTP_PASSWORD

4. **Updated Deployment Script:**
   - Added GMAIL_SERVICE_ACCOUNT_PATH to required variables
   - Added default handling for optional variables (GMAIL_SUPPORT_CREDENTIALS_PATH, GMAIL_WEBHOOK_SECRET, SMTP_USERNAME, SMTP_PASSWORD)
   - Removed placeholder logic for GMAIL_SERVICE_ACCOUNT_PATH

5. **Excluded Test-Only Variables:**
   - GMAIL_TEST_CREDENTIALS_PATH
   - GMAIL_TEST_ACCOUNT_EMAIL
   - TWILIO_TEST_ACCOUNT_SID
   - TWILIO_TEST_AUTH_TOKEN
   - TWILIO_TEST_FROM_NUMBER

6. **Deleted Root .env.example:**
   - Removed duplicate .env.example from project root
   - Kept backend/.env.example as the authoritative source

7. **Updated Documentation:**
   - Rewrote docs/k8s-env-validation.md with complete reference
   - Added production update commands (kubectl patch examples)
   - Documented all 47 environment variables with their purposes

**Key Design Decision:**
All configuration values are now externalized to K8s ConfigMap/Secrets, enabling production changes via:
```bash
kubectl patch configmap fte-config -n customer-success-fte -p '{"data":{"AGENT_MODEL":"gemini-2.0-flash-exp"}}'
kubectl rollout restart deployment/fte-api -n customer-success-fte
```

## Outcome

- ✅ Impact: Complete environment variable externalization - all 47 config.py fields now in K8s manifests, enabling zero-downtime configuration updates in production
- 🧪 Tests: Manual verification of variable counts (36 ConfigMap + 11 Secrets = 47 total), alignment check between config.py and K8s manifests
- 📁 Files: Modified 7 files (configmap.yaml, secrets.yaml, config.py, main.py, message_processor.py, deploy-k8s.sh, k8s-env-validation.md), deleted 1 file (.env.example)
- 🔁 Next prompts: Test deployment with kubectl apply, verify pods start with all environment variables correctly injected
- 🧠 Reflection: This completes the K8s deployment configuration. All application settings are now externalized, following 12-factor app principles. Production operators can tune any configuration value without developer involvement or image rebuilds.

## Evaluation notes (flywheel)

- Failure modes observed: Initial confusion about which .env.example file to use (root vs backend/), resolved by deleting root and using backend/.env.example as source of truth
- Graders run and results (PASS/FAIL): Manual verification PASS - all config.py fields accounted for in K8s manifests
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Deploy to actual K8s cluster and verify all environment variables are correctly injected into pods via `kubectl exec` commands
