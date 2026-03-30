# Deployment Guide: Multi-Channel Customer Intake

**Feature**: 006-channel-integrations
**Date**: 2026-03-31
**Target Environments**: Staging, Production

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Database Migration](#database-migration)
4. [Application Deployment](#application-deployment)
5. [Service Configuration](#service-configuration)
6. [Webhook Configuration](#webhook-configuration)
7. [Monitoring Setup](#monitoring-setup)
8. [Rollback Procedures](#rollback-procedures)
9. [Post-Deployment Verification](#post-deployment-verification)

---

## Prerequisites

### Required Services

- **PostgreSQL**: Neon Serverless or managed PostgreSQL (v14+)
- **Redis**: Managed Redis or Redis cluster (v6+)
- **Kafka**: Managed Kafka or Confluent Cloud
- **Container Registry**: Docker Hub, AWS ECR, or GCP Artifact Registry
- **Hosting**: AWS, GCP, Azure, or similar cloud provider

### Required Credentials

- Gmail API credentials (OAuth 2.0 client ID and secret)
- Twilio account (Account SID and Auth Token)
- Webhook secrets for HMAC verification
- Database connection string
- Redis connection string
- Kafka bootstrap servers and credentials

### Tools

```bash
# Install deployment tools
pip install ansible
npm install -g pm2
docker --version
kubectl --version  # If using Kubernetes
```

---

## Infrastructure Setup

### 1. Database Setup (Neon Serverless)

```bash
# Create Neon project
neon projects create --name crm-digital-fte-production

# Get connection string
neon connection-string --project-id <project-id>

# Set environment variable
export DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"
```

### 2. Redis Setup

**Option A: Managed Redis (AWS ElastiCache)**

```bash
# Create Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id crm-redis-prod \
  --engine redis \
  --cache-node-type cache.t3.medium \
  --num-cache-nodes 1 \
  --engine-version 6.2

# Get endpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id crm-redis-prod \
  --show-cache-node-info
```

**Option B: Redis Cloud**

```bash
# Sign up at redis.com/cloud
# Create database with 1GB memory
# Get connection string: redis://default:password@host:port
```

### 3. Kafka Setup

**Option A: Confluent Cloud**

```bash
# Create Kafka cluster
confluent kafka cluster create crm-kafka-prod \
  --cloud aws \
  --region us-east-1 \
  --type basic

# Create topics
confluent kafka topic create customer-intake.email.inbound \
  --cluster <cluster-id> \
  --partitions 3 \
  --replication-factor 3

confluent kafka topic create customer-intake.whatsapp.inbound \
  --cluster <cluster-id> \
  --partitions 3 \
  --replication-factor 3

confluent kafka topic create customer-intake.webform.inbound \
  --cluster <cluster-id> \
  --partitions 3 \
  --replication-factor 3
```

**Option B: AWS MSK**

```bash
# Create MSK cluster
aws kafka create-cluster \
  --cluster-name crm-kafka-prod \
  --broker-node-group-info file://broker-config.json \
  --kafka-version 2.8.1 \
  --number-of-broker-nodes 3
```

### 4. Container Registry

```bash
# Login to registry
docker login

# Or for AWS ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create repository
aws ecr create-repository --repository-name crm-backend
```

---

## Database Migration

### 1. Backup Current Database

```bash
# Create backup before migration
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Or use Neon backup
neon branches create --project-id <project-id> --name backup-$(date +%Y%m%d)
```

### 2. Run Migrations

```bash
cd backend

# Set production database URL
export DATABASE_URL="postgresql://user:pass@prod-host/db?sslmode=require"

# Run migrations
uv run alembic upgrade head

# Verify migration
uv run alembic current
```

### 3. Seed Initial Data (if needed)

```bash
# Seed knowledge base articles
uv run python scripts/seed_knowledge_base.py

# Create initial channel configurations
uv run python scripts/setup_channels.py
```

---

## Application Deployment

### Option 1: Docker Deployment

#### Build Docker Image

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install UV
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Expose port
EXPOSE 8000

# Run application
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Build and Push

```bash
cd backend

# Build image
docker build -t crm-backend:latest .

# Tag for registry
docker tag crm-backend:latest <registry>/crm-backend:v1.0.0

# Push to registry
docker push <registry>/crm-backend:v1.0.0
```

#### Run Container

```bash
# Run backend container
docker run -d \
  --name crm-backend \
  -p 8000:8000 \
  -e DATABASE_URL=$DATABASE_URL \
  -e REDIS_URL=$REDIS_URL \
  -e KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS \
  -e GMAIL_CLIENT_ID=$GMAIL_CLIENT_ID \
  -e GMAIL_CLIENT_SECRET=$GMAIL_CLIENT_SECRET \
  -e TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID \
  -e TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN \
  -e WEBHOOK_SECRET=$WEBHOOK_SECRET \
  <registry>/crm-backend:v1.0.0
```

### Option 2: Kubernetes Deployment

#### Create Kubernetes Manifests

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crm-backend
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crm-backend
  template:
    metadata:
      labels:
        app: crm-backend
    spec:
      containers:
      - name: backend
        image: <registry>/crm-backend:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: crm-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: crm-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: crm-backend-service
  namespace: production
spec:
  selector:
    app: crm-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

#### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace production

# Create secrets
kubectl create secret generic crm-secrets \
  --from-literal=database-url=$DATABASE_URL \
  --from-literal=redis-url=$REDIS_URL \
  --from-literal=kafka-bootstrap-servers=$KAFKA_BOOTSTRAP_SERVERS \
  --from-literal=gmail-client-id=$GMAIL_CLIENT_ID \
  --from-literal=gmail-client-secret=$GMAIL_CLIENT_SECRET \
  --from-literal=twilio-account-sid=$TWILIO_ACCOUNT_SID \
  --from-literal=twilio-auth-token=$TWILIO_AUTH_TOKEN \
  --from-literal=webhook-secret=$WEBHOOK_SECRET \
  -n production

# Deploy application
kubectl apply -f k8s/deployment.yaml

# Check deployment status
kubectl get pods -n production
kubectl get services -n production
```

### Option 3: Serverless Deployment (AWS Lambda)

```bash
# Install serverless framework
npm install -g serverless

# Create serverless.yml
cat > serverless.yml << EOF
service: crm-backend

provider:
  name: aws
  runtime: python3.12
  region: us-east-1
  environment:
    DATABASE_URL: \${env:DATABASE_URL}
    REDIS_URL: \${env:REDIS_URL}
    KAFKA_BOOTSTRAP_SERVERS: \${env:KAFKA_BOOTSTRAP_SERVERS}

functions:
  api:
    handler: src.main.handler
    events:
      - http:
          path: /{proxy+}
          method: ANY
EOF

# Deploy
serverless deploy --stage production
```

---

## Service Configuration

### 1. Environment Variables

Create `.env.production`:

```bash
# Database
DATABASE_URL=postgresql://user:pass@prod-host/db?sslmode=require
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://default:pass@redis-host:6379
REDIS_MAX_CONNECTIONS=50

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka1:9092,kafka2:9092,kafka3:9092
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
KAFKA_SASL_USERNAME=api-key
KAFKA_SASL_PASSWORD=api-secret

# Gmail
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_PUBSUB_TOPIC=projects/your-project/topics/gmail-push

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_WHATSAPP_NUMBER=+14155238886

# Security
WEBHOOK_SECRET=your-webhook-secret-min-32-chars
JWT_SECRET=your-jwt-secret-min-32-chars
ALLOWED_ORIGINS=https://app.example.com,https://www.example.com

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
CORS_ENABLED=true
RATE_LIMIT_PER_MINUTE=10
MAX_ATTACHMENT_SIZE_MB=10

# Monitoring
PROMETHEUS_ENABLED=true
SENTRY_DSN=https://xxx@sentry.io/xxx
```

### 2. Load Environment Variables

```bash
# Load from file
export $(cat .env.production | xargs)

# Or use secrets manager
aws secretsmanager get-secret-value \
  --secret-id crm-production-secrets \
  --query SecretString \
  --output text | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")|.[]' > .env.production
```

---

## Webhook Configuration

### 1. Gmail Webhook Setup

```bash
# Register Gmail watch
uv run python scripts/register_gmail_watch.py \
  --topic projects/your-project/topics/gmail-push \
  --webhook-url https://api.example.com/webhooks/gmail

# Set up Pub/Sub push subscription
gcloud pubsub subscriptions create gmail-push-prod \
  --topic gmail-push \
  --push-endpoint https://api.example.com/webhooks/gmail \
  --push-auth-service-account gmail-push@your-project.iam.gserviceaccount.com
```

### 2. Twilio Webhook Setup

```bash
# Configure WhatsApp webhook in Twilio Console
# Or use Twilio CLI
twilio api:core:incoming-phone-numbers:update \
  --sid PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  --sms-url https://api.example.com/webhooks/whatsapp \
  --sms-method POST \
  --status-callback https://api.example.com/webhooks/whatsapp/status
```

### 3. Verify Webhook Endpoints

```bash
# Test health endpoint
curl https://api.example.com/health

# Test webhook with signature
curl -X POST https://api.example.com/webhooks/gmail \
  -H "Content-Type: application/json" \
  -H "X-Signature: $(generate_signature)" \
  -d '{"test": "data"}'
```

---

## Monitoring Setup

### 1. Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'crm-backend'
    static_configs:
      - targets: ['api.example.com:8000']
    metrics_path: '/metrics'
```

### 2. Grafana Dashboards

```bash
# Import pre-built dashboard
curl -X POST http://grafana:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d @grafana/crm-dashboard.json
```

### 3. Alerting Rules

```yaml
# alerts.yml
groups:
  - name: crm_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: DatabaseConnectionPoolExhausted
        expr: database_connections_active >= database_connections_max * 0.9
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool near capacity"
```

### 4. Log Aggregation

```bash
# Configure log shipping to ELK/Splunk/CloudWatch
# Example: CloudWatch Logs
aws logs create-log-group --log-group-name /aws/crm/backend

# Configure application to send logs
export LOG_DESTINATION=cloudwatch
export LOG_GROUP=/aws/crm/backend
```

---

## Rollback Procedures

### 1. Application Rollback

**Docker:**
```bash
# Rollback to previous version
docker stop crm-backend
docker rm crm-backend
docker run -d --name crm-backend <registry>/crm-backend:v0.9.0
```

**Kubernetes:**
```bash
# Rollback deployment
kubectl rollout undo deployment/crm-backend -n production

# Rollback to specific revision
kubectl rollout undo deployment/crm-backend --to-revision=2 -n production

# Check rollout status
kubectl rollout status deployment/crm-backend -n production
```

### 2. Database Rollback

```bash
# Rollback one migration
uv run alembic downgrade -1

# Rollback to specific revision
uv run alembic downgrade <revision-id>

# Restore from backup
psql $DATABASE_URL < backup_20260331_120000.sql
```

### 3. Emergency Rollback Checklist

- [ ] Stop new deployments
- [ ] Rollback application to previous version
- [ ] Verify health endpoints
- [ ] Check error rates in monitoring
- [ ] Rollback database migrations if needed
- [ ] Notify team and stakeholders
- [ ] Document incident and root cause

---

## Post-Deployment Verification

### 1. Health Checks

```bash
# Check application health
curl https://api.example.com/health

# Expected response:
# {"status": "healthy", "timestamp": "2026-03-31T00:00:00Z"}
```

### 2. Smoke Tests

```bash
# Test web form submission
curl -X POST https://api.example.com/support/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Deployment verification",
    "category": "technical",
    "message": "Testing production deployment"
  }'

# Verify response includes ticket_id
```

### 3. Integration Tests

```bash
# Run integration tests against production
cd backend
export API_URL=https://api.example.com
uv run pytest tests/integration/ --env=production
```

### 4. Monitoring Verification

```bash
# Check Prometheus metrics
curl https://api.example.com/metrics | grep http_requests_total

# Check logs
kubectl logs -f deployment/crm-backend -n production

# Check Grafana dashboards
open https://grafana.example.com/d/crm-dashboard
```

### 5. Webhook Verification

```bash
# Send test email to support address
# Send test WhatsApp message
# Submit test web form

# Verify messages appear in:
# - Database (messages table)
# - Kafka topics
# - Application logs
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Code reviewed and approved
- [ ] All tests passing (unit, integration, E2E)
- [ ] Security audit completed
- [ ] Performance testing completed
- [ ] Database backup created
- [ ] Deployment plan reviewed
- [ ] Rollback plan prepared
- [ ] Stakeholders notified

### During Deployment

- [ ] Deploy to staging first
- [ ] Run smoke tests in staging
- [ ] Deploy to production
- [ ] Monitor error rates
- [ ] Monitor response times
- [ ] Verify webhooks working
- [ ] Check database connections
- [ ] Verify Kafka messages flowing

### Post-Deployment

- [ ] Run smoke tests
- [ ] Verify all endpoints responding
- [ ] Check monitoring dashboards
- [ ] Review application logs
- [ ] Verify webhook delivery
- [ ] Test rate limiting
- [ ] Document deployment
- [ ] Notify stakeholders of completion

---

## Troubleshooting

### Issue: Application won't start

**Check:**
- Environment variables set correctly
- Database connection string valid
- Redis connection working
- Kafka bootstrap servers reachable

**Solution:**
```bash
# Check logs
docker logs crm-backend
kubectl logs deployment/crm-backend -n production

# Verify connections
psql $DATABASE_URL -c "SELECT 1"
redis-cli -u $REDIS_URL ping
```

### Issue: High error rate after deployment

**Check:**
- Database migration completed
- Environment variables correct
- External services (Gmail, Twilio) configured
- Rate limits not exceeded

**Solution:**
```bash
# Check error logs
kubectl logs deployment/crm-backend -n production | grep ERROR

# Rollback if critical
kubectl rollout undo deployment/crm-backend -n production
```

### Issue: Webhooks not receiving messages

**Check:**
- Webhook URLs configured correctly
- HMAC signatures valid
- Firewall rules allow incoming traffic
- SSL certificates valid

**Solution:**
```bash
# Test webhook endpoint
curl -v https://api.example.com/webhooks/gmail

# Check webhook logs
kubectl logs deployment/crm-backend -n production | grep webhook
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Monitor error rates and response times
- Check database connection pool usage
- Review application logs for errors

**Weekly:**
- Review security alerts
- Check disk space and memory usage
- Verify backup integrity

**Monthly:**
- Rotate webhook secrets
- Update dependencies
- Review and optimize database queries
- Run performance tests

**Quarterly:**
- Security audit
- Disaster recovery drill
- Capacity planning review

---

## Support

For deployment issues:
- Check logs: `kubectl logs deployment/crm-backend -n production`
- Review monitoring: https://grafana.example.com
- Contact DevOps team: devops@example.com
- Escalation: oncall@example.com