# CI/CD Troubleshooting Guide

**🔧 Quick Reference for Common Issues**

> **Navigation:** [📖 README](../README.md#-cicd-pipeline) | [⚡ Quick Start](CI_CD_QUICKSTART.md) | [📚 Setup Guide](CI_CD_SETUP.md) | [🔄 Rollback](ROLLBACK_PROCEDURES.md)

---

## When to Use This Guide

- ✅ Your CI/CD pipeline is failing
- ✅ You're getting errors in GitHub Actions
- ✅ Deployments aren't working as expected
- ✅ You need quick solutions to common problems

**For emergency rollbacks:** See [ROLLBACK_PROCEDURES.md](ROLLBACK_PROCEDURES.md)

---

Quick reference for common CI/CD issues and solutions.

---

## Build Failures

### Error: Docker build fails with "no space left on device"

**Cause**: Docker build cache is full

**Solution**:
```bash
# Clean up Docker cache locally
docker system prune -a --volumes

# For GitHub Actions, this is handled automatically
# But you can add cleanup step to workflow:
- name: Clean up Docker
  run: docker system prune -af
```

---

### Error: "failed to solve with frontend dockerfile.v0"

**Cause**: Dockerfile syntax error or missing file

**Solution**:
```bash
# Test Dockerfile locally
cd backend
docker build -t test .

# Check for common issues:
# - Missing files referenced in COPY commands
# - Incorrect file paths
# - Invalid instruction syntax

# Validate Dockerfile
docker build --no-cache -t test .
```

---

### Error: "uv: command not found" during build

**Cause**: UV not installed in Docker image

**Solution**:
```dockerfile
# Ensure UV is installed in Dockerfile
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"
```

---

### Error: DockerHub authentication failed

**Cause**: Invalid credentials or expired token

**Solution**:
```bash
# Regenerate DockerHub token
# 1. Go to https://hub.docker.com/settings/security
# 2. Delete old token
# 3. Create new token
# 4. Update GitHub secret

gh secret set DOCKERHUB_TOKEN
# Paste new token

# Test locally
echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin
```

---

## Deployment Failures

### Error: "Unable to connect to the server"

**Cause**: GKE cluster not accessible or credentials invalid

**Solution**:
```bash
# Verify GCP credentials
gcloud auth list

# Get fresh cluster credentials
gcloud container clusters get-credentials $CLUSTER_NAME \
  --zone $ZONE \
  --project $PROJECT_ID

# Test connection
kubectl cluster-info

# If still failing, regenerate service account key
./scripts/setup-gcp-service-account.sh
```

---

### Error: "ImagePullBackOff" in Kubernetes

**Cause**: Kubernetes can't pull Docker image

**Solution**:
```bash
# Check if image exists in DockerHub
docker pull $DOCKERHUB_USERNAME/crm-digital-fte-factory:$TAG

# Check image name in deployment
kubectl get deployment crm-fte-api -n crm-fte -o yaml | grep image:

# Verify image pull secrets (if using private registry)
kubectl get secrets -n crm-fte

# Check pod events
kubectl describe pod POD_NAME -n crm-fte
```

---

### Error: "CrashLoopBackOff" after deployment

**Cause**: Application crashes on startup

**Solution**:
```bash
# Check pod logs
kubectl logs POD_NAME -n crm-fte

# Common causes:
# 1. Missing environment variables
kubectl get configmap crm-fte-config -n crm-fte -o yaml

# 2. Database connection issues
kubectl exec -it POD_NAME -n crm-fte -- env | grep DATABASE_URL

# 3. Missing dependencies
kubectl exec -it POD_NAME -n crm-fte -- uv pip list

# 4. Port conflicts
kubectl get service -n crm-fte
```

---

### Error: Deployment timeout

**Cause**: Pods not becoming ready within timeout

**Solution**:
```bash
# Check pod status
kubectl get pods -n crm-fte

# Check pod events
kubectl describe pod POD_NAME -n crm-fte

# Check readiness probe
kubectl get deployment crm-fte-api -n crm-fte -o yaml | grep -A 10 readinessProbe

# Increase timeout in workflow (if needed)
# In .github/workflows/2-deploy-to-gke.yml:
kubectl rollout status deployment/$DEPLOYMENT_NAME -n crm-fte --timeout=10m
```

---

### Error: "insufficient cpu" or "insufficient memory"

**Cause**: Not enough resources in cluster

**Solution**:
```bash
# Check node resources
kubectl top nodes

# Check pod resource requests
kubectl describe deployment crm-fte-api -n crm-fte | grep -A 5 Requests

# Options:
# 1. Scale up cluster
gcloud container clusters resize $CLUSTER_NAME \
  --num-nodes 5 \
  --zone $ZONE

# 2. Reduce resource requests in k8s/deployment-api.yaml
resources:
  requests:
    cpu: 250m      # Reduce from 500m
    memory: 256Mi  # Reduce from 512Mi
```

---

## Migration Failures

### Error: "relation already exists"

**Cause**: Migration trying to create existing table

**Solution**:
```bash
# Check current migration status
cd backend
uv run alembic current

# Check database tables
psql "$DATABASE_URL" -c "\dt"

# Options:
# 1. Stamp database with current migration
uv run alembic stamp head

# 2. Drop and recreate (DANGEROUS - only in dev)
uv run alembic downgrade base
uv run alembic upgrade head
```

---

### Error: "could not connect to server"

**Cause**: Database not accessible from GitHub Actions

**Solution**:
```bash
# Test connection locally
psql "$PRODUCTION_DATABASE_URL" -c "SELECT version();"

# Check if database allows GitHub Actions IPs
# For Neon: IP allowlist is not needed (allows all by default)
# For other providers: Add GitHub Actions IP ranges

# Verify connection string format
# Should be: postgresql://user:pass@host:5432/db?sslmode=require

# Test with Python
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os

async def test():
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    async with engine.connect() as conn:
        result = await conn.execute('SELECT 1')
        print('✅ Connected')
    await engine.dispose()

asyncio.run(test())
"
```

---

### Error: "alembic.util.exc.CommandError: Can't locate revision"

**Cause**: Migration history mismatch

**Solution**:
```bash
# Check migration files
ls backend/alembic/versions/

# Check database migration version
psql "$DATABASE_URL" -c "SELECT * FROM alembic_version;"

# Resolve:
# 1. If database is ahead, pull latest migrations
git pull origin main

# 2. If database is behind, run migrations
uv run alembic upgrade head

# 3. If completely out of sync, stamp with current
uv run alembic stamp head
```

---

### Error: Migration rollback fails

**Cause**: Downgrade operation not defined or data loss

**Solution**:
```bash
# Check migration file for downgrade() function
cat backend/alembic/versions/REVISION_ID.py

# If downgrade is empty, you may need to:
# 1. Manually write downgrade SQL
# 2. Restore from backup
# 3. Accept data loss and recreate

# Generate downgrade SQL
uv run alembic downgrade -1 --sql > downgrade.sql
cat downgrade.sql  # Review before executing
```

---

## Testing Failures

### Error: Neon branch creation fails

**Cause**: API key invalid or quota exceeded

**Solution**:
```bash
# Test API key
curl -X GET \
  "https://console.neon.tech/api/v2/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $API_KEY"

# Check branch quota
neonctl branches list --project-id $PROJECT_ID

# Delete old test branches
for branch in $(neonctl branches list --project-id $PROJECT_ID --output json | jq -r '.[] | select(.name | startswith("ci-test-")) | .id'); do
  echo "Deleting branch: $branch"
  neonctl branches delete $branch --project-id $PROJECT_ID
done

# Regenerate API key if needed
# Go to: https://console.neon.tech/app/settings/api-keys
```

---

### Error: Tests fail on Neon branch

**Cause**: Schema mismatch or missing test data

**Solution**:
```bash
# Check migration status on branch
export DATABASE_URL="$NEON_BRANCH_CONNECTION_STRING"
uv run alembic current

# Verify tables exist
psql "$DATABASE_URL" -c "\dt"

# Run migrations if needed
uv run alembic upgrade head

# Check test logs
# In GitHub Actions, view the test output for specific failures
```

---

### Error: Redis connection refused

**Cause**: Redis container not started or wrong port

**Solution**:
```bash
# Check if Redis is running
docker ps | grep redis

# Start Redis
docker run -d -p 6379:6379 --name redis redis:7-alpine

# Test connection
redis-cli ping
# Should return: PONG

# In workflow, ensure Redis starts before tests
- name: Start Redis
  run: docker run -d -p 6379:6379 --name redis redis:7-alpine

- name: Wait for Redis
  run: |
    timeout 30 bash -c 'until redis-cli ping; do sleep 1; done'
```

---

### Error: Kafka connection timeout

**Cause**: Kafka not ready or wrong configuration

**Solution**:
```bash
# Check Kafka container
docker ps | grep kafka

# Check Kafka logs
docker logs kafka

# Increase wait time in workflow
- name: Start Kafka
  run: |
    docker run -d -p 9092:9092 --name kafka \
      -e KAFKA_ENABLE_KRAFT=yes \
      ... (other env vars)
    sleep 30  # Increase from 15 to 30

# Test Kafka connection
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

---

## Secret Management Issues

### Error: "secret not found"

**Cause**: Secret not configured in GitHub

**Solution**:
```bash
# List configured secrets
gh secret list

# Add missing secret
gh secret set SECRET_NAME

# Validate all secrets
./scripts/validate-ci-secrets.sh
```

---

### Error: "invalid character in secret"

**Cause**: Secret contains special characters that need escaping

**Solution**:
```bash
# For secrets with special characters, use file input
echo "your-secret-value" | gh secret set SECRET_NAME

# For JSON secrets (like GCP_SA_KEY), ensure proper formatting
cat service-account-key.json | gh secret set GCP_SA_KEY

# Test secret value (be careful not to expose)
gh secret list  # Should show the secret name
```

---

### Error: Secret not available in workflow

**Cause**: Secret not passed to workflow step

**Solution**:
```yaml
# Ensure secret is in env block
- name: Run command
  env:
    DATABASE_URL: ${{ secrets.PRODUCTION_DATABASE_URL }}
    API_KEY: ${{ secrets.NEON_API_KEY }}
  run: |
    echo "Secret is available"
```

---

## Workflow Trigger Issues

### Error: Workflow not triggering on push

**Cause**: Path filters or branch restrictions

**Solution**:
```yaml
# Check workflow trigger configuration
on:
  push:
    branches:
      - main  # Ensure this matches your branch
    paths:
      - 'backend/**'
      - 'frontend/**'
      # Add other relevant paths

# Test by manually triggering
gh workflow run "1. Build and Push Docker Image"
```

---

### Error: Workflow runs but skips jobs

**Cause**: Conditional checks failing

**Solution**:
```yaml
# Check job conditions
jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    # This will skip if previous workflow failed

# Remove condition for testing
jobs:
  deploy:
    # if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
```

---

## Performance Issues

### Error: Workflow takes too long

**Cause**: Inefficient steps or missing caching

**Solution**:
```yaml
# Add caching for dependencies
- name: Cache UV dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-${{ hashFiles('**/pyproject.toml') }}

# Use Docker layer caching
- name: Build and push
  uses: docker/build-push-action@v5
  with:
    cache-from: type=registry,ref=${{ env.DOCKER_IMAGE }}:buildcache
    cache-to: type=registry,ref=${{ env.DOCKER_IMAGE }}:buildcache,mode=max

# Run jobs in parallel where possible
jobs:
  migrate:
    # runs after deploy
  test:
    # runs in parallel with migrate
```

---

### Error: Rate limit exceeded

**Cause**: Too many API calls to external services

**Solution**:
```bash
# For DockerHub rate limits:
# - Use authenticated pulls
# - Implement caching
# - Use GitHub Container Registry instead

# For GitHub API rate limits:
# - Use GITHUB_TOKEN in workflows
# - Reduce frequency of workflow runs

# For Neon API rate limits:
# - Implement exponential backoff
# - Reduce branch creation frequency
# - Clean up old branches
```

---

## Debugging Tips

### Enable Debug Logging

```yaml
# In workflow file, add:
env:
  ACTIONS_STEP_DEBUG: true
  ACTIONS_RUNNER_DEBUG: true
```

### View Workflow Logs

```bash
# List recent runs
gh run list --limit 10

# View specific run
gh run view RUN_ID

# Download logs
gh run download RUN_ID

# Watch run in real-time
gh run watch
```

### Test Workflow Locally

```bash
# Use act to run workflows locally
# Install: https://github.com/nektos/act

# Run workflow
act -j build-and-push

# Run with secrets
act -j build-and-push --secret-file .secrets
```

### SSH into Runner (for debugging)

```yaml
# Add this step to workflow for debugging
- name: Setup tmate session
  uses: mxschmitt/action-tmate@v3
  if: failure()
```

---

## Quick Diagnostic Commands

```bash
# Check all GitHub Actions status
gh run list --limit 20

# Check Kubernetes cluster health
kubectl get nodes
kubectl get pods --all-namespaces
kubectl top nodes

# Check database connectivity
psql "$PRODUCTION_DATABASE_URL" -c "SELECT version();"

# Check Docker image
docker pull $DOCKERHUB_USERNAME/crm-digital-fte-factory:latest
docker inspect $DOCKERHUB_USERNAME/crm-digital-fte-factory:latest

# Check Neon API
curl -X GET \
  "https://console.neon.tech/api/v2/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $API_KEY"

# Validate all secrets
./scripts/validate-ci-secrets.sh

# Check GCP access
gcloud auth list
gcloud projects list
gcloud container clusters list
```

---

## Getting Help

### Internal Resources
- **Documentation**: `docs/CI_CD_SETUP.md`
- **Quickstart**: `docs/CI_CD_QUICKSTART.md`
- **Rollback**: `docs/ROLLBACK_PROCEDURES.md`

### External Resources
- **GitHub Actions**: https://docs.github.com/en/actions
- **GKE**: https://cloud.google.com/kubernetes-engine/docs
- **Neon**: https://neon.tech/docs
- **Docker**: https://docs.docker.com

### Support Channels
- **GitHub Issues**: Create issue with `ci-cd` label
- **Team Chat**: #devops channel
- **On-Call**: See `docs/ROLLBACK_PROCEDURES.md`

---

**Last Updated**: 2026-04-03
