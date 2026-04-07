# CI/CD Pipeline Setup Guide

**📚 Comprehensive Setup with Explanations**

> **Navigation:** [📖 README](../README.md#-cicd-pipeline) | [⚡ Quick Start](CI_CD_QUICKSTART.md) | [🔧 Troubleshooting](CI_CD_TROUBLESHOOTING.md) | [🔄 Rollback](ROLLBACK_PROCEDURES.md)

---

## When to Use This Guide

- ✅ First-time CI/CD setup for this project
- ✅ You want to understand how everything works
- ✅ You need detailed explanations and examples
- ✅ You're setting up for a production environment

**Need to get started quickly?** See [CI_CD_QUICKSTART.md](CI_CD_QUICKSTART.md) for 15-minute setup.

---

## Overview

This project uses 4 GitHub Actions workflows for continuous integration and deployment:

### Sequential Workflows
1. **Build and Push Docker Image** → Builds and pushes to DockerHub
2. **Deploy to GKE** → Deploys the new image to Google Kubernetes Engine

### Parallel Workflows (after deployment)
3. **Apply Production Migrations** → Runs Alembic migrations on production database
4. **Test with Neon Branch** → Creates temporary Neon branch, runs migrations, executes all tests

```
┌─────────────────────────────────────────────────────────────┐
│                     Push to main branch                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Build and Push Docker Image                             │
│     - Build backend Docker image                            │
│     - Push to DockerHub with SHA tag                        │
│     - Create deployment artifact                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Deploy to GKE                                           │
│     - Authenticate to GCP                                   │
│     - Update K8s deployments (API + Worker)                 │
│     - Wait for rollout completion                           │
│     - Health check                                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
┌─────────────────────┐  ┌─────────────────────┐
│ 3. Apply Production │  │ 4. Test with Neon   │
│    Migrations       │  │    Branch           │
│                     │  │                     │
│ - Connect to prod   │  │ - Create Neon branch│
│ - Backup revision   │  │ - Run migrations    │
│ - Run migrations    │  │ - Run all tests     │
│ - Verify tables     │  │ - Auto-delete in    │
│ - Rollback on fail  │  │   15 days           │
└─────────────────────┘  └─────────────────────┘
```

---

## Required GitHub Secrets

### DockerHub Secrets
```bash
DOCKERHUB_USERNAME      # Your DockerHub username
DOCKERHUB_TOKEN         # DockerHub access token (not password)
```

**Setup:**
1. Go to https://hub.docker.com/settings/security
2. Create new access token with Read & Write access
3. Add to GitHub: Settings → Secrets → Actions → New repository secret

---

### Google Cloud Platform (GCP) Secrets
```bash
GCP_PROJECT_ID          # Your GCP project ID
GCP_SA_KEY              # Service account JSON key (entire JSON)
GKE_CLUSTER_NAME        # Name of your GKE cluster
GKE_ZONE                # GKE cluster zone (e.g., us-central1-a)
```

**Setup:**

1. **Create Service Account:**
```bash
# Set project
gcloud config set project YOUR_PROJECT_ID

# Create service account
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer"

# Grant necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/container.developer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/container.clusterAdmin"

# Create and download key
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Copy the entire JSON content and add to GitHub secrets as GCP_SA_KEY
cat github-actions-key.json

# Delete local key file (security)
rm github-actions-key.json
```

2. **Get GKE cluster info:**
```bash
# List clusters
gcloud container clusters list

# Get cluster details
gcloud container clusters describe YOUR_CLUSTER_NAME --zone YOUR_ZONE
```

---

### Database Secrets
```bash
PRODUCTION_DATABASE_URL # Production PostgreSQL connection string
                        # Format: postgresql://user:pass@host:5432/dbname?sslmode=require
```

**Setup:**
1. Get connection string from your production database provider
2. Add to GitHub secrets
3. **IMPORTANT:** Ensure the user has migration privileges

---

### Neon Database Secrets
```bash
NEON_API_KEY           # Neon API key
NEON_PROJECT_ID        # Your Neon project ID
NEON_MAIN_BRANCH_ID    # Main branch ID (usually "br-...")
```

**Setup:**

1. **Get Neon API Key:**
   - Go to https://console.neon.tech/app/settings/api-keys
   - Create new API key
   - Copy and add to GitHub secrets

2. **Get Project ID:**
```bash
# Using Neon CLI
neonctl projects list

# Or from Neon console URL:
# https://console.neon.tech/app/projects/YOUR_PROJECT_ID
```

3. **Get Main Branch ID:**
```bash
# Using Neon CLI
neonctl branches list --project-id YOUR_PROJECT_ID

# Or via API
curl -X GET \
  "https://console.neon.tech/api/v2/projects/YOUR_PROJECT_ID/branches" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  | jq '.branches[] | select(.name == "main") | .id'
```

---

## Initial Setup Steps

### 1. Add All Secrets to GitHub

Go to your repository:
```
Settings → Secrets and variables → Actions → New repository secret
```

Add all secrets listed above.

### 2. Create GKE Cluster (if not exists)

```bash
# Create cluster
gcloud container clusters create crm-fte-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10

# Get credentials
gcloud container clusters get-credentials crm-fte-cluster \
  --zone us-central1-a
```

### 3. Deploy Initial Kubernetes Resources

```bash
# Apply namespace and configs
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml

# Create secrets manually (first time only)
kubectl create secret generic crm-fte-secrets \
  --from-literal=database-url="YOUR_DATABASE_URL" \
  --from-literal=redis-url="YOUR_REDIS_URL" \
  --from-literal=kafka-bootstrap-servers="YOUR_KAFKA_SERVERS" \
  --from-literal=webhook-secret="YOUR_WEBHOOK_SECRET" \
  --from-literal=gmail-client-id="YOUR_GMAIL_CLIENT_ID" \
  --from-literal=gmail-client-secret="YOUR_GMAIL_CLIENT_SECRET" \
  --from-literal=twilio-account-sid="YOUR_TWILIO_SID" \
  --from-literal=twilio-auth-token="YOUR_TWILIO_TOKEN" \
  --from-literal=twilio-whatsapp-number="YOUR_TWILIO_NUMBER" \
  -n crm-fte

# Apply remaining resources
kubectl apply -f k8s/
```

### 4. Verify Setup

```bash
# Check namespace
kubectl get namespace crm-fte

# Check deployments
kubectl get deployments -n crm-fte

# Check services
kubectl get services -n crm-fte

# Check pods
kubectl get pods -n crm-fte
```

---

## Triggering Workflows

### Automatic Trigger
Workflows trigger automatically on push to `main` branch when backend/frontend files change.

### Manual Trigger

**Via GitHub UI:**
1. Go to Actions tab
2. Select workflow
3. Click "Run workflow"
4. Choose branch and parameters

**Via GitHub CLI:**
```bash
# Trigger build and push
gh workflow run "1. Build and Push Docker Image"

# Trigger deployment with specific image
gh workflow run "2. Deploy to GKE" \
  -f image_tag="latest"

# Trigger production migration
gh workflow run "3. Apply Production Migrations"

# Trigger Neon branch tests
gh workflow run "4. Test with Neon Branch"
```

---

## Monitoring Workflows

### View Workflow Status
```bash
# List recent workflow runs
gh run list

# View specific run
gh run view RUN_ID

# Watch run in real-time
gh run watch RUN_ID
```

### Check Deployment Status
```bash
# Check K8s deployment status
kubectl rollout status deployment/crm-fte-api -n crm-fte
kubectl rollout status deployment/crm-fte-worker -n crm-fte

# Check pod logs
kubectl logs -f deployment/crm-fte-api -n crm-fte
kubectl logs -f deployment/crm-fte-worker -n crm-fte

# Check HPA status
kubectl get hpa -n crm-fte
```

### Check Migration Status
```bash
# Connect to production database
psql "$PRODUCTION_DATABASE_URL"

# Check current migration
SELECT * FROM alembic_version;

# Check tables
\dt
```

### Check Neon Branches
```bash
# List all branches
neonctl branches list --project-id YOUR_PROJECT_ID

# Delete old test branches manually (if needed)
neonctl branches delete BRANCH_ID --project-id YOUR_PROJECT_ID
```

---

## Rollback Procedures

### Rollback Deployment
```bash
# Rollback to previous version
kubectl rollout undo deployment/crm-fte-api -n crm-fte
kubectl rollout undo deployment/crm-fte-worker -n crm-fte

# Rollback to specific revision
kubectl rollout history deployment/crm-fte-api -n crm-fte
kubectl rollout undo deployment/crm-fte-api --to-revision=2 -n crm-fte
```

### Rollback Migration
```bash
# Connect to backend
cd backend

# Check migration history
uv run alembic history

# Downgrade one revision
uv run alembic downgrade -1

# Downgrade to specific revision
uv run alembic downgrade REVISION_ID
```

---

## Troubleshooting

### Workflow Fails at Build Step

**Issue:** Docker build fails
```bash
# Check Dockerfile syntax
docker build -t test ./backend

# Check dependencies
cd backend && uv sync
```

**Issue:** DockerHub authentication fails
- Verify `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` are correct
- Regenerate DockerHub token if expired

### Workflow Fails at Deploy Step

**Issue:** GKE authentication fails
- Verify `GCP_SA_KEY` is valid JSON
- Check service account has correct roles
- Verify cluster name and zone are correct

**Issue:** Deployment timeout
```bash
# Check pod status
kubectl get pods -n crm-fte

# Check pod logs
kubectl logs POD_NAME -n crm-fte

# Describe pod for events
kubectl describe pod POD_NAME -n crm-fte
```

### Workflow Fails at Migration Step

**Issue:** Database connection fails
- Verify `PRODUCTION_DATABASE_URL` is correct
- Check database firewall allows GitHub Actions IPs
- Test connection manually

**Issue:** Migration fails
```bash
# Check current migration status
uv run alembic current

# Check pending migrations
uv run alembic history

# Test migration locally first
uv run alembic upgrade head --sql > migration.sql
# Review SQL before applying
```

### Workflow Fails at Test Step

**Issue:** Neon branch creation fails
- Verify `NEON_API_KEY` is valid
- Check `NEON_PROJECT_ID` is correct
- Verify API key has branch creation permissions

**Issue:** Tests fail on Neon branch
- Check test logs in GitHub Actions
- Verify Redis and Kafka containers started
- Test locally with same database schema

---

## Security Best Practices

### Secrets Management
- ✅ Never commit secrets to repository
- ✅ Rotate secrets regularly (every 90 days)
- ✅ Use least-privilege service accounts
- ✅ Enable secret scanning in GitHub

### Database Security
- ✅ Use SSL/TLS for database connections (`?sslmode=require`)
- ✅ Restrict database access by IP (allow GitHub Actions IPs)
- ✅ Use read-only users for test branches
- ✅ Enable audit logging for production migrations

### Kubernetes Security
- ✅ Use namespace isolation
- ✅ Enable RBAC
- ✅ Use network policies
- ✅ Scan images for vulnerabilities

---

## Performance Optimization

### Build Optimization
- ✅ Use Docker layer caching
- ✅ Multi-stage builds (already implemented)
- ✅ Minimize image size

### Deployment Optimization
- ✅ Use rolling updates (zero downtime)
- ✅ Configure proper health checks
- ✅ Set resource limits and requests
- ✅ Enable horizontal pod autoscaling

### Test Optimization
- ✅ Run tests in parallel
- ✅ Use test fixtures for faster setup
- ✅ Cache dependencies (UV cache)
- ✅ Auto-delete test branches (15-day TTL)

---

## Cost Optimization

### Neon Branches
- Auto-delete after 15 days (configured)
- Consider reducing TTL for faster cleanup
- Monitor branch count in Neon console

### GKE Resources
- Use preemptible nodes for non-production
- Configure HPA min/max appropriately
- Monitor resource usage with Prometheus

### GitHub Actions
- Free tier: 2,000 minutes/month for private repos
- Optimize workflow triggers (only on relevant file changes)
- Use caching to reduce build times

---

## Maintenance

### Weekly Tasks
- [ ] Review workflow run history
- [ ] Check for failed deployments
- [ ] Monitor Neon branch count
- [ ] Review GKE resource usage

### Monthly Tasks
- [ ] Rotate secrets
- [ ] Update dependencies
- [ ] Review and optimize workflows
- [ ] Clean up old Docker images

### Quarterly Tasks
- [ ] Audit service account permissions
- [ ] Review and update documentation
- [ ] Load test production environment
- [ ] Disaster recovery drill

---

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Google Kubernetes Engine Documentation](https://cloud.google.com/kubernetes-engine/docs)
- [Neon API Documentation](https://neon.tech/docs/reference/api-reference)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

## Support

For issues or questions:
1. Check workflow logs in GitHub Actions
2. Review this documentation
3. Check project issues: https://github.com/YOUR_USERNAME/crm-digital-fte-factory/issues
4. Contact DevOps team

---

**Last Updated:** 2026-04-03
