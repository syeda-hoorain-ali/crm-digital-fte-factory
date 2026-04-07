# CI/CD Rollback Procedures

**🔄 Emergency Response Guide**

> **Navigation:** [📖 README](../README.md#-cicd-pipeline) | [⚡ Quick Start](CI_CD_QUICKSTART.md) | [📚 Setup Guide](CI_CD_SETUP.md) | [🔧 Troubleshooting](CI_CD_TROUBLESHOOTING.md)

---

## When to Use This Guide

- 🚨 **Emergency:** Production deployment failed
- 🚨 **Critical Issue:** Need to revert to previous version immediately
- 🚨 **Data Risk:** Migration caused problems
- ✅ **Planning:** Understanding rollback procedures before deployment

**For non-emergency issues:** See [CI_CD_TROUBLESHOOTING.md](CI_CD_TROUBLESHOOTING.md) first.

---

## Overview

This document provides step-by-step procedures for rolling back deployments, migrations, and other CI/CD operations when issues occur in production.

---

## Table of Contents

1. [Rollback Kubernetes Deployment](#rollback-kubernetes-deployment)
2. [Rollback Database Migration](#rollback-database-migration)
3. [Rollback Docker Image](#rollback-docker-image)
4. [Emergency Procedures](#emergency-procedures)
5. [Post-Rollback Actions](#post-rollback-actions)

---

## Rollback Kubernetes Deployment

### Automatic Rollback

The deployment workflow includes automatic rollback on failure. If health checks fail, the deployment automatically reverts to the previous version.

### Manual Rollback

#### Quick Rollback (Last Deployment)

```bash
# Get cluster credentials
gcloud container clusters get-credentials $GKE_CLUSTER_NAME \
  --zone $GKE_ZONE \
  --project $GCP_PROJECT_ID

# Rollback API deployment
kubectl rollout undo deployment/crm-fte-api -n crm-fte

# Rollback Worker deployment
kubectl rollout undo deployment/crm-fte-worker -n crm-fte

# Wait for rollback to complete
kubectl rollout status deployment/crm-fte-api -n crm-fte
kubectl rollout status deployment/crm-fte-worker -n crm-fte

# Verify pods are running
kubectl get pods -n crm-fte
```

#### Rollback to Specific Revision

```bash
# View deployment history
kubectl rollout history deployment/crm-fte-api -n crm-fte

# Output example:
# REVISION  CHANGE-CAUSE
# 1         Deploy abc123: Initial deployment
# 2         Deploy def456: Add new feature
# 3         Deploy ghi789: Fix bug (CURRENT)

# Rollback to specific revision
kubectl rollout undo deployment/crm-fte-api \
  --to-revision=2 \
  -n crm-fte

# Verify rollback
kubectl rollout status deployment/crm-fte-api -n crm-fte
```

#### Rollback via GitHub Actions

```bash
# Trigger deployment with previous image tag
gh workflow run "2. Deploy to GKE" \
  -f image_tag="PREVIOUS_COMMIT_SHA"

# Example:
gh workflow run "2. Deploy to GKE" \
  -f image_tag="abc123def456"
```

### Verification After Rollback

```bash
# Check pod status
kubectl get pods -n crm-fte -l app=crm-fte-api

# Check logs for errors
kubectl logs -f deployment/crm-fte-api -n crm-fte --tail=100

# Test health endpoint
API_URL=$(kubectl get service crm-fte-api-service -n crm-fte \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$API_URL/health

# Check metrics
kubectl top pods -n crm-fte
```

---

## Rollback Database Migration

### Automatic Rollback

The migration workflow includes automatic rollback on failure. If migration fails, it automatically reverts to the backup revision.

### Manual Rollback

#### Rollback One Migration

```bash
# Navigate to backend
cd backend

# Set database URL
export DATABASE_URL="$PRODUCTION_DATABASE_URL"

# Check current migration
uv run alembic current

# View migration history
uv run alembic history

# Rollback one migration
uv run alembic downgrade -1

# Verify rollback
uv run alembic current
```

#### Rollback to Specific Migration

```bash
# View migration history with details
uv run alembic history --verbose

# Rollback to specific revision
uv run alembic downgrade REVISION_ID

# Example:
uv run alembic downgrade 459bcf301ab0

# Verify rollback
uv run alembic current
```

#### Rollback All Migrations (DANGEROUS)

```bash
# ⚠️ WARNING: This will drop all tables!
# Only use in emergency situations

# Downgrade to base (empty database)
uv run alembic downgrade base

# Verify
uv run alembic current
# Output: (empty)
```

### Generate Rollback SQL (Dry Run)

```bash
# Generate SQL for rollback without executing
uv run alembic downgrade -1 --sql > rollback.sql

# Review the SQL
cat rollback.sql

# If safe, execute manually
psql "$PRODUCTION_DATABASE_URL" < rollback.sql
```

### Verification After Migration Rollback

```bash
# Check current migration
uv run alembic current

# Verify critical tables exist
psql "$PRODUCTION_DATABASE_URL" -c "\dt"

# Check table counts
psql "$PRODUCTION_DATABASE_URL" -c "
  SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Test application connectivity
uv run python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os

async def test():
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    async with engine.connect() as conn:
        result = await conn.execute('SELECT COUNT(*) FROM customers')
        count = result.scalar()
        print(f'✅ Database accessible. Customer count: {count}')
    await engine.dispose()

asyncio.run(test())
"
```

---

## Rollback Docker Image

### Redeploy Previous Image

```bash
# Find previous image tag
gh run list --workflow="1. Build and Push Docker Image" --limit 10

# Get commit SHA from previous successful run
PREVIOUS_SHA="abc123def456"

# Trigger deployment with previous image
gh workflow run "2. Deploy to GKE" \
  -f image_tag="$PREVIOUS_SHA"

# Monitor deployment
gh run watch
```

### Pull and Verify Image

```bash
# Pull previous image
docker pull $DOCKERHUB_USERNAME/crm-digital-fte-factory:$PREVIOUS_SHA

# Test image locally
docker run -p 8080:8080 \
  -e DATABASE_URL="$TEST_DATABASE_URL" \
  -e REDIS_URL="redis://localhost:6379" \
  $DOCKERHUB_USERNAME/crm-digital-fte-factory:$PREVIOUS_SHA

# Test health endpoint
curl http://localhost:8080/health
```

---

## Emergency Procedures

### Complete System Rollback

Use this when multiple components need to be rolled back simultaneously.

```bash
#!/bin/bash
# emergency-rollback.sh

set -e

echo "🚨 EMERGENCY ROLLBACK INITIATED"
echo "================================"

# 1. Rollback Kubernetes deployments
echo "Step 1: Rolling back K8s deployments..."
kubectl rollout undo deployment/crm-fte-api -n crm-fte
kubectl rollout undo deployment/crm-fte-worker -n crm-fte

# 2. Wait for rollback
echo "Step 2: Waiting for rollback to complete..."
kubectl rollout status deployment/crm-fte-api -n crm-fte --timeout=5m
kubectl rollout status deployment/crm-fte-worker -n crm-fte --timeout=5m

# 3. Rollback database migration (if needed)
read -p "Rollback database migration? (y/n): " ROLLBACK_DB
if [[ $ROLLBACK_DB =~ ^[Yy]$ ]]; then
    echo "Step 3: Rolling back database migration..."
    cd backend
    uv run alembic downgrade -1
    cd ..
fi

# 4. Verify system health
echo "Step 4: Verifying system health..."
kubectl get pods -n crm-fte
API_URL=$(kubectl get service crm-fte-api-service -n crm-fte \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl -f http://$API_URL/health || echo "⚠️ Health check failed"

echo "✅ Emergency rollback complete"
echo "Next steps:"
echo "  1. Check application logs"
echo "  2. Verify customer-facing functionality"
echo "  3. Investigate root cause"
echo "  4. Create incident report"
```

### Scale Down to Zero (Circuit Breaker)

Use this to stop all traffic while investigating critical issues.

```bash
# Scale down to zero replicas
kubectl scale deployment/crm-fte-api --replicas=0 -n crm-fte
kubectl scale deployment/crm-fte-worker --replicas=0 -n crm-fte

# Verify
kubectl get pods -n crm-fte

# When ready to restore
kubectl scale deployment/crm-fte-api --replicas=3 -n crm-fte
kubectl scale deployment/crm-fte-worker --replicas=3 -n crm-fte
```

### Pause Autoscaling

```bash
# Suspend HPA
kubectl patch hpa crm-fte-api-hpa -n crm-fte \
  -p '{"spec":{"minReplicas":0,"maxReplicas":0}}'

# Resume HPA
kubectl patch hpa crm-fte-api-hpa -n crm-fte \
  -p '{"spec":{"minReplicas":3,"maxReplicas":20}}'
```

---

## Post-Rollback Actions

### 1. Incident Documentation

Create an incident report:

```markdown
# Incident Report: [Date] - [Brief Description]

## Timeline
- **Detection**: [Time] - [How was it detected?]
- **Rollback Initiated**: [Time]
- **Rollback Completed**: [Time]
- **Service Restored**: [Time]

## Impact
- **Duration**: [X minutes/hours]
- **Affected Users**: [Number or percentage]
- **Affected Features**: [List]

## Root Cause
[Detailed explanation of what went wrong]

## Rollback Actions Taken
1. [Action 1]
2. [Action 2]
3. [Action 3]

## Prevention Measures
1. [Measure 1]
2. [Measure 2]
3. [Measure 3]

## Follow-up Tasks
- [ ] Fix root cause
- [ ] Add tests to prevent recurrence
- [ ] Update documentation
- [ ] Review deployment process
```

### 2. Verify System Health

```bash
# Check all pods are healthy
kubectl get pods -n crm-fte

# Check HPA status
kubectl get hpa -n crm-fte

# Check recent events
kubectl get events -n crm-fte --sort-by='.lastTimestamp' | tail -20

# Check application logs
kubectl logs -f deployment/crm-fte-api -n crm-fte --tail=100

# Check metrics
kubectl top pods -n crm-fte
```

### 3. Database Integrity Check

```bash
# Connect to database
psql "$PRODUCTION_DATABASE_URL"

# Check for orphaned records
SELECT 
    c.table_name,
    c.constraint_name,
    c.constraint_type
FROM information_schema.table_constraints c
WHERE c.table_schema = 'public'
    AND c.constraint_type = 'FOREIGN KEY';

# Check for data inconsistencies
SELECT COUNT(*) FROM customers WHERE email IS NULL;
SELECT COUNT(*) FROM conversations WHERE customer_id NOT IN (SELECT id FROM customers);

# Verify indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

### 4. Customer Communication

If customers were affected:

```markdown
Subject: Service Disruption - [Date]

Dear Customers,

We experienced a brief service disruption on [Date] from [Start Time] to [End Time] ([Duration]).

**What happened:**
[Brief, non-technical explanation]

**Impact:**
[What features were affected]

**Resolution:**
The issue has been resolved, and all services are now operating normally.

**Prevention:**
We have implemented additional safeguards to prevent similar issues in the future.

We apologize for any inconvenience this may have caused.

Best regards,
[Your Team]
```

### 5. Update Runbooks

Document lessons learned:

```bash
# Add to runbooks
cat >> docs/runbooks/rollback-procedures.md << EOF

## Incident: [Date] - [Description]

### What Went Wrong
[Description]

### What Worked
- [Action that worked well]

### What Didn't Work
- [Action that didn't work or took too long]

### Improvements Made
- [Improvement 1]
- [Improvement 2]

EOF
```

---

## Rollback Decision Matrix

Use this matrix to decide when to rollback:

| Severity | Impact | Action | Rollback? |
|----------|--------|--------|-----------|
| **Critical** | Service down, data loss risk | Immediate rollback | ✅ Yes |
| **High** | Major feature broken, affecting >50% users | Rollback within 15 min | ✅ Yes |
| **Medium** | Minor feature broken, affecting <50% users | Investigate first, rollback if no quick fix | ⚠️ Maybe |
| **Low** | UI glitch, non-critical bug | Fix forward | ❌ No |

### Critical Triggers (Always Rollback)
- ❌ Health check failures
- ❌ Database connection errors
- ❌ Authentication/authorization failures
- ❌ Data corruption detected
- ❌ Memory leaks causing OOM
- ❌ Infinite loops or CPU spikes

### Fix Forward Triggers (Don't Rollback)
- ✅ Minor UI bugs
- ✅ Typos in text
- ✅ Non-critical logging issues
- ✅ Performance degradation <10%

---

## Testing Rollback Procedures

### Staging Environment Test

```bash
# 1. Deploy to staging
kubectl config use-context staging
kubectl apply -f k8s/ -n crm-fte-staging

# 2. Simulate failure
kubectl set image deployment/crm-fte-api \
  crm-fte-api=invalid-image:latest \
  -n crm-fte-staging

# 3. Practice rollback
kubectl rollout undo deployment/crm-fte-api -n crm-fte-staging

# 4. Verify
kubectl rollout status deployment/crm-fte-api -n crm-fte-staging
```

### Disaster Recovery Drill

Schedule quarterly drills:

```bash
# Drill checklist
- [ ] Rollback K8s deployment
- [ ] Rollback database migration
- [ ] Verify system health
- [ ] Test customer-facing features
- [ ] Document time taken for each step
- [ ] Identify bottlenecks
- [ ] Update procedures based on findings
```

---

## Contact Information

### On-Call Rotation
- **Primary**: [Name] - [Phone] - [Email]
- **Secondary**: [Name] - [Phone] - [Email]
- **Manager**: [Name] - [Phone] - [Email]

### Escalation Path
1. On-call engineer (0-15 min)
2. Team lead (15-30 min)
3. Engineering manager (30-60 min)
4. CTO (>60 min or data loss risk)

### External Contacts
- **GCP Support**: [Support ticket URL]
- **Neon Support**: support@neon.tech
- **DockerHub Support**: [Support URL]

---

## Appendix: Common Rollback Scenarios

### Scenario 1: New Feature Breaks Existing Functionality

```bash
# Quick rollback
kubectl rollout undo deployment/crm-fte-api -n crm-fte

# Verify
kubectl get pods -n crm-fte
curl http://$API_URL/health
```

### Scenario 2: Database Migration Causes Performance Issues

```bash
# Rollback migration
cd backend
uv run alembic downgrade -1

# Verify
psql "$PRODUCTION_DATABASE_URL" -c "SELECT * FROM alembic_version"
```

### Scenario 3: Memory Leak Detected

```bash
# Scale down affected pods
kubectl scale deployment/crm-fte-api --replicas=1 -n crm-fte

# Rollback to previous version
kubectl rollout undo deployment/crm-fte-api -n crm-fte

# Monitor memory usage
kubectl top pods -n crm-fte -l app=crm-fte-api
```

### Scenario 4: Third-Party API Integration Fails

```bash
# Check if rollback needed or just disable feature
kubectl set env deployment/crm-fte-api \
  FEATURE_FLAG_NEW_INTEGRATION=false \
  -n crm-fte

# If that doesn't work, rollback
kubectl rollout undo deployment/crm-fte-api -n crm-fte
```

---

**Last Updated**: 2026-04-03  
**Review Frequency**: Quarterly  
**Next Review**: 2026-07-03
