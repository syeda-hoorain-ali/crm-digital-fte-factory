# CI/CD Quick Start Guide

**⚡ Fast Track Setup - 15 Minutes**

> **Navigation:** [📖 README](../README.md#-cicd-pipeline) | [📚 Full Setup Guide](CI_CD_SETUP.md) | [🔧 Troubleshooting](CI_CD_TROUBLESHOOTING.md) | [🔄 Rollback](ROLLBACK_PROCEDURES.md)

---

## When to Use This Guide

- ✅ You want to get the pipeline running quickly
- ✅ You're comfortable with command-line tools
- ✅ You'll read detailed docs later if needed

**Need more detail?** See [CI_CD_SETUP.md](CI_CD_SETUP.md) for comprehensive explanations.

---

Get your CI/CD pipeline running in 15 minutes.

## Prerequisites

- GitHub repository with admin access
- DockerHub account
- Google Cloud Platform account with GKE cluster
- Neon PostgreSQL database
- GitHub CLI (`gh`) installed (optional but recommended)
- Google Cloud SDK (`gcloud`) installed

---

## Quick Setup (5 Steps)

### Step 1: Install Required Tools (5 min)

```bash
# Install GitHub CLI (if not installed)
# macOS
brew install gh

# Windows
winget install --id GitHub.cli

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# Authenticate
gh auth login
```

```bash
# Install Google Cloud SDK (if not installed)
# Visit: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
```

---

### Step 2: Set Up DockerHub (2 min)

```bash
# 1. Go to https://hub.docker.com/settings/security
# 2. Click "New Access Token"
# 3. Name it "github-actions"
# 4. Copy the token

# Add to GitHub secrets
gh secret set DOCKERHUB_USERNAME
# Paste your DockerHub username

gh secret set DOCKERHUB_TOKEN
# Paste the access token
```

---

### Step 3: Set Up GCP Service Account (3 min)

```bash
# Run the automated setup script
./scripts/setup-gcp-service-account.sh

# This will:
# - Create a service account
# - Grant necessary permissions
# - Generate a key file
# - Add secrets to GitHub (if gh CLI is available)
```

**Manual alternative:**
```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Create service account
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer"

# Grant roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/container.developer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/container.clusterAdmin"

# Create key
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Add to GitHub
cat key.json | gh secret set GCP_SA_KEY
echo "YOUR_PROJECT_ID" | gh secret set GCP_PROJECT_ID
echo "YOUR_CLUSTER_NAME" | gh secret set GKE_CLUSTER_NAME
echo "YOUR_CLUSTER_ZONE" | gh secret set GKE_ZONE

# Delete key file
rm key.json
```

---

### Step 4: Set Up Neon Database (3 min)

```bash
# Run the automated setup script
./scripts/setup-neon-database.sh

# This will:
# - Get your Neon API key
# - Fetch project and branch IDs
# - Test API access
# - Add secrets to GitHub (if gh CLI is available)
```

**Manual alternative:**
```bash
# Get Neon API key from: https://console.neon.tech/app/settings/api-keys
gh secret set NEON_API_KEY

# Get project ID from: https://console.neon.tech/app/projects
gh secret set NEON_PROJECT_ID

# Get main branch ID (use Neon CLI or API)
gh secret set NEON_MAIN_BRANCH_ID

# Get production database URL
gh secret set PRODUCTION_DATABASE_URL
```

---

### Step 5: Validate Setup (1 min)

```bash
# Validate all secrets are configured
./scripts/validate-ci-secrets.sh

# Expected output:
# ✅ DOCKERHUB_USERNAME
# ✅ DOCKERHUB_TOKEN
# ✅ GCP_PROJECT_ID
# ✅ GCP_SA_KEY
# ✅ GKE_CLUSTER_NAME
# ✅ GKE_ZONE
# ✅ PRODUCTION_DATABASE_URL
# ✅ NEON_API_KEY
# ✅ NEON_PROJECT_ID
# ✅ NEON_MAIN_BRANCH_ID
# 🎉 All required secrets are configured!
```

---

## Test Your Pipeline

### Option 1: Automatic Trigger (Recommended)

```bash
# Make a small change to trigger the pipeline
echo "# CI/CD Pipeline Active" >> README.md

# Commit and push
git add README.md
git commit -m "test: trigger CI/CD pipeline"
git push origin main

# Watch the workflow
gh run watch
```

### Option 2: Manual Trigger

```bash
# Trigger the build workflow
gh workflow run "1. Build and Push Docker Image"

# Watch progress
gh run watch

# Check status
gh run list --workflow="1. Build and Push Docker Image"
```

---

## Verify Deployment

### Check Workflow Status

```bash
# List recent runs
gh run list

# View specific run
gh run view RUN_ID

# View logs
gh run view RUN_ID --log
```

### Check Kubernetes Deployment

```bash
# Get cluster credentials
gcloud container clusters get-credentials YOUR_CLUSTER_NAME \
  --zone YOUR_ZONE

# Check deployments
kubectl get deployments -n crm-fte

# Check pods
kubectl get pods -n crm-fte

# Check services
kubectl get services -n crm-fte

# Check logs
kubectl logs -f deployment/crm-fte-api -n crm-fte
```

### Check Database Migrations

```bash
# Connect to production database
psql "$PRODUCTION_DATABASE_URL"

# Check migration status
SELECT * FROM alembic_version;

# List tables
\dt

# Exit
\q
```

### Check Neon Test Branches

```bash
# List branches (if neonctl is installed)
neonctl branches list --project-id YOUR_PROJECT_ID

# Or via API
curl -X GET \
  "https://console.neon.tech/api/v2/projects/YOUR_PROJECT_ID/branches" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  | jq '.branches[] | {name, id, created_at}'
```

---

## Pipeline Flow

```
Push to main
    ↓
┌─────────────────────────────────┐
│ 1. Build and Push Docker Image │
│    - Build backend image        │
│    - Push to DockerHub          │
│    - Tag with commit SHA        │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│ 2. Deploy to GKE                │
│    - Update K8s deployments     │
│    - Rolling update (zero down) │
│    - Health check               │
└────────────┬────────────────────┘
             ↓
      ┌──────┴──────┐
      ↓             ↓
┌──────────────┐  ┌──────────────────┐
│ 3. Migrations│  │ 4. Neon Testing  │
│    - Backup  │  │    - Create branch│
│    - Migrate │  │    - Run migrations│
│    - Verify  │  │    - Run tests    │
└──────────────┘  └──────────────────┘
```

---

## Common Issues

### Issue: Workflow not triggering

**Solution:**
```bash
# Check workflow file syntax
gh workflow list

# Check if workflows are enabled
# Go to: Settings → Actions → General → Allow all actions

# Manually trigger
gh workflow run "1. Build and Push Docker Image"
```

### Issue: Docker build fails

**Solution:**
```bash
# Test build locally
cd backend
docker build -t test .

# Check Dockerfile syntax
docker build --no-cache -t test .

# Verify dependencies
uv sync
```

### Issue: GKE deployment fails

**Solution:**
```bash
# Verify cluster access
gcloud container clusters get-credentials YOUR_CLUSTER \
  --zone YOUR_ZONE

# Check cluster status
kubectl cluster-info

# Check namespace
kubectl get namespace crm-fte

# Check deployments
kubectl get deployments -n crm-fte

# Check events
kubectl get events -n crm-fte --sort-by='.lastTimestamp'
```

### Issue: Migration fails

**Solution:**
```bash
# Test connection
psql "$PRODUCTION_DATABASE_URL" -c "SELECT version();"

# Check current migration
cd backend
uv run alembic current

# Test migration locally
uv run alembic upgrade head --sql > test.sql
cat test.sql  # Review SQL

# Rollback if needed
uv run alembic downgrade -1
```

### Issue: Neon branch creation fails

**Solution:**
```bash
# Test API access
curl -X GET \
  "https://console.neon.tech/api/v2/projects/YOUR_PROJECT_ID" \
  -H "Authorization: Bearer YOUR_API_KEY"

# Check branch quota
# Go to: https://console.neon.tech/app/projects/YOUR_PROJECT_ID

# List existing branches
neonctl branches list --project-id YOUR_PROJECT_ID

# Delete old test branches
neonctl branches delete BRANCH_ID --project-id YOUR_PROJECT_ID
```

---

## Next Steps

1. **Add Status Badges** to README (see below)
2. **Set up Slack/Discord notifications** for deployment status
3. **Configure branch protection rules** to require CI checks
4. **Add code coverage reporting** with Codecov
5. **Set up staging environment** with separate workflows

---

## Status Badges

Add these to your README.md:

```markdown
## CI/CD Status

[![Build and Push](https://github.com/YOUR_USERNAME/crm-digital-fte-factory/actions/workflows/1-build-and-push-docker.yml/badge.svg)](https://github.com/YOUR_USERNAME/crm-digital-fte-factory/actions/workflows/1-build-and-push-docker.yml)
[![Deploy to GKE](https://github.com/YOUR_USERNAME/crm-digital-fte-factory/actions/workflows/2-deploy-to-gke.yml/badge.svg)](https://github.com/YOUR_USERNAME/crm-digital-fte-factory/actions/workflows/2-deploy-to-gke.yml)
[![Production Migrations](https://github.com/YOUR_USERNAME/crm-digital-fte-factory/actions/workflows/3-apply-production-migrations.yml/badge.svg)](https://github.com/YOUR_USERNAME/crm-digital-fte-factory/actions/workflows/3-apply-production-migrations.yml)
[![Neon Testing](https://github.com/YOUR_USERNAME/crm-digital-fte-factory/actions/workflows/4-test-with-neon-branch.yml/badge.svg)](https://github.com/YOUR_USERNAME/crm-digital-fte-factory/actions/workflows/4-test-with-neon-branch.yml)
```

---

## Support

- **Documentation**: See `docs/CI_CD_SETUP.md` for detailed setup
- **Scripts**: Run `./scripts/validate-ci-secrets.sh` to check configuration
- **GitHub Actions**: https://github.com/YOUR_USERNAME/crm-digital-fte-factory/actions
- **Issues**: https://github.com/YOUR_USERNAME/crm-digital-fte-factory/issues

---

**Estimated Setup Time**: 15 minutes  
**Deployment Time**: ~10 minutes per push  
**Zero Downtime**: ✅ Rolling updates  
**Auto Rollback**: ✅ On failure  
**Test Coverage**: ✅ 440+ tests on every push
