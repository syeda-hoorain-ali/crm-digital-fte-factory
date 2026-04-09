---
id: 0097
title: Complete CI/CD Pipeline Deployment
stage: general
date: 2026-04-09
surface: agent
model: qwen3-code-plus
feature: none
branch: main
user: Syeda Hoorain Ali
command: fix ci/cd deployment workflow
labels: ["ci-cd", "github-actions", "kubernetes", "gke", "deployment", "secrets"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .github/workflows/4-deploy-to-gke.yml
  - .github/workflows/3-apply-production-migrations.yml
  - .github/workflows/2-test-with-neon-branch.yml
  - backend/tests/unit/conftest.py
tests:
  - Complete pipeline: Build → Migrate → Deploy (all passing)
  - Health check verification via kubectl port-forward
  - Deployment verification: API (1/1), Worker (3/3), Redis (1/1)
---

## Prompt

User asked to:
1. Evaluate using scripts/deploy-k8s.sh in deployment workflow
2. Setup GitHub secrets from .env file before pushing
3. Write PHR for the completed work

Context: Fixing CI/CD pipeline issues to get complete Build → Migrate → Deploy flow working. Previous errors included container name mismatches, missing secrets, and health check failures.

## Response snapshot

**Evaluated scripts/deploy-k8s.sh**: Script is designed for local/manual deployments with envsubst and requires many environment variables (GMAIL_SERVICE_ACCOUNT_PATH, TWILIO_*, INGRESS_HOSTNAME, CONTAINER_REGISTRY). For CI/CD, the current approach (apply manifests directly, then update images with kubectl set image) is simpler and more appropriate.

**Setup GitHub Secrets**: Created all required secrets from backend/.env:
- GEMINI_API_KEY
- TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_APP_NUMBER
- GCP_PROJECT_ID
- GMAIL_SERVICE_ACCOUNT_PATH, GMAIL_SUPPORT_CREDENTIALS_PATH (from gmail-support-credentials.json)
- TWILIO_WEBHOOK_SECRET, GMAIL_WEBHOOK_SECRET (generated with openssl rand -hex 32)
- SMTP_USERNAME, SMTP_PASSWORD (empty, optional)
- Skipped PRODUCTION_DATABASE_URL per user request

**Fixed Deployment Workflow Issues**:
1. Container name mismatch: Changed fte-message-processor to fte-worker in kubectl set image command
2. Secrets creation: Replaced template file approach with kubectl create secret from GitHub secrets
3. Health check: Replaced curl (not in container) with kubectl port-forward to service
4. First-time deployment: Added steps to apply k8s manifests before updating images

**Final Pipeline Status**:
- Workflow 1: Build and Push Docker Image - 30s ✅
- Workflow 3: Apply Production Migrations - 33s ✅
- Workflow 4: Deploy to GKE - 2m26s ✅

**Deployment Verification**:
```
NAME                    READY   UP-TO-DATE   AVAILABLE
fte-api                 1/1     1            1
fte-message-processor   3/3     3            3
redis                   1/1     1            1
```

**Health Check Result**:
```json
{
  "status": "healthy",
  "components": {
    "database": {"status": "healthy", "message": "Connected"},
    "redis": {"status": "healthy", "message": "Connected"},
    "kafka": {"status": "healthy", "message": "Producer initialized"}
  }
}
```

## Outcome

- ✅ Impact: Complete CI/CD pipeline working end-to-end (Build → Migrate → Deploy). All services deployed and healthy on GKE. HPA scaling worker to 3 replicas due to 97% CPU usage.
- 🧪 Tests: Pipeline tested with multiple commits. Health checks passing via kubectl port-forward. All deployments ready and available.
- 📁 Files: Modified 4 workflow files (.github/workflows/2-test-with-neon-branch.yml, 3-apply-production-migrations.yml, 4-deploy-to-gke.yml) and backend/tests/unit/conftest.py
- 🔁 Next prompts: Monitor HPA scaling behavior, consider LoadBalancer IP assignment for external access, evaluate Node.js 24 migration for GitHub Actions
- 🧠 Reflection: Key insight was using kubectl port-forward for health checks instead of assuming curl exists in container. Secrets management via kubectl create secret is more CI-friendly than envsubst templates.

## Evaluation notes (flywheel)

- Failure modes observed: Container name mismatch (deployment vs container name), missing curl in minimal container images, secrets template requiring envsubst, first-time deployment with non-existent resources
- Graders run and results (PASS/FAIL): Manual verification - PASS (all workflows green, deployments healthy, health checks passing)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add LoadBalancer type to service.yaml for external IP assignment, or configure Ingress with cert-manager for HTTPS access