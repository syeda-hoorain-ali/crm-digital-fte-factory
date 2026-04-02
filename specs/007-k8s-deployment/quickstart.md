# Kubernetes Deployment Quickstart Guide

**Feature**: 007-k8s-deployment - Kubernetes Production Deployment
**Date**: 2026-03-31
**Audience**: DevOps Engineers, Platform Operators

## Overview

This guide provides step-by-step instructions for deploying the multi-channel customer success FTE system to a Kubernetes cluster. Follow these instructions to achieve a production-ready deployment with high availability, automatic scaling, and zero-downtime updates.

---

## Prerequisites

### Required Cluster Components

Before deploying, ensure your Kubernetes cluster has:

- [ ] **Kubernetes 1.24+** installed and accessible via kubectl
- [ ] **NGINX Ingress Controller** installed and configured
- [ ] **cert-manager** installed for automatic TLS certificate provisioning
- [ ] **Metrics Server** installed for HorizontalPodAutoscaler CPU metrics
- [ ] Sufficient cluster resources (minimum 6 CPU cores, 12Gi memory available)

### Required External Services

Ensure the following external services are accessible from the cluster:

- [ ] **PostgreSQL Database** (Neon Serverless or equivalent)
- [ ] **Kafka Cluster** (external message queue)
- [ ] **Redis Instance** (external cache/rate limiter)
- [ ] **Container Registry** with built Docker image

### Required Tools

Install the following tools on your local machine:

- [ ] `kubectl` (Kubernetes CLI)
- [ ] `kubeval` (manifest validation, optional but recommended)
- [ ] `envsubst` (environment variable substitution)

### Required Credentials

Gather the following credentials before deployment:

- [ ] Gemini API key
- [ ] PostgreSQL database password
- [ ] Gmail API credentials (JSON format)
- [ ] Twilio account SID, auth token, and WhatsApp number
- [ ] Webhook secret (minimum 32 characters)

---

## Step 1: Prepare Configuration

### 1.1 Set Environment Variables

Create a `.env` file with your configuration (DO NOT commit to version control):

```bash
# .env file (keep this secure!)

# Gemini
export GEMINI_API_KEY="AI..."

# PostgreSQL
export POSTGRES_PASSWORD="your-secure-password"

# Gmail API
export GMAIL_CREDENTIALS_JSON='{"installed":{"client_id":"...","client_secret":"..."}}'

# Twilio
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your-auth-token"
export TWILIO_WHATSAPP_NUMBER="+14155238886"

# Security
export WEBHOOK_SECRET="your-webhook-secret-min-32-chars"

# Ingress
export INGRESS_HOSTNAME="api.yourdomain.com"

# Container Registry
# Examples:
#   Docker Hub: docker.io/your-username
#   GitHub Container Registry: ghcr.io/your-org
#   Google Container Registry: gcr.io/your-project
#   Azure Container Registry: your-registry.azurecr.io
#   AWS ECR: 123456789012.dkr.ecr.us-east-1.amazonaws.com
export CONTAINER_REGISTRY="your-registry"
export IMAGE_TAG="v1.0.0"

# Note: Ensure your Kubernetes cluster has pull access to the registry
# For private registries, create an imagePullSecret:
#   kubectl create secret docker-registry regcred \
#     --docker-server=$CONTAINER_REGISTRY \
#     --docker-username=<your-username> \
#     --docker-password=<your-password> \
#     --docker-email=<your-email> \
#     -n customer-success-fte
```

### 1.2 Load Environment Variables

```bash
source .env
```

### 1.3 Verify Configuration

```bash
echo "Gemini API Key: ${GEMINI_API_KEY:0:10}..."
echo "Ingress Hostname: $INGRESS_HOSTNAME"
echo "Image: $CONTAINER_REGISTRY/customer-success-fte:$IMAGE_TAG"
```

---

## Step 2: Validate Manifests

### 2.1 Validate Syntax (Optional)

```bash
# Validate all manifests against Kubernetes API schemas
kubeval k8s/*.yaml
```

### 2.2 Dry-Run Test

```bash
# Test manifests can be applied without actually creating resources
kubectl apply --dry-run=client -f k8s/
```

Expected output: "created (dry run)" for all resources

---

## Step 3: Configure DNS

### 3.1 Get Ingress Load Balancer IP

```bash
# Get the external IP of your NGINX Ingress Controller
kubectl get svc -n ingress-nginx ingress-nginx-controller
```

### 3.2 Create DNS Record

Create an A record in your DNS provider:

```
Type: A
Name: api.yourdomain.com (or your chosen hostname)
Value: <INGRESS_LOAD_BALANCER_IP>
TTL: 300
```

### 3.3 Verify DNS Resolution

```bash
# Wait for DNS propagation (may take 5-15 minutes)
nslookup $INGRESS_HOSTNAME
```

---

## Step 4: Deploy to Kubernetes

### 4.1 Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

Verify:
```bash
kubectl get namespace customer-success-fte
```

### 4.2 Create ConfigMap

```bash
kubectl apply -f k8s/configmap.yaml
```

Verify:
```bash
kubectl get configmap -n customer-success-fte fte-config
kubectl describe configmap -n customer-success-fte fte-config
```

### 4.3 Create Secret

**Important**: Replace placeholders with actual values using envsubst:

```bash
envsubst < k8s/secrets.yaml | kubectl apply -f -
```

Verify (secrets are base64-encoded):
```bash
kubectl get secret -n customer-success-fte fte-secrets
kubectl describe secret -n customer-success-fte fte-secrets
```

**Security Note**: Never run `kubectl get secret -o yaml` in production logs!

### 4.4 Deploy API Service

```bash
# Replace image tag placeholder
envsubst < k8s/deployment-api.yaml | kubectl apply -f -
```

Verify:
```bash
kubectl get deployment -n customer-success-fte fte-api
kubectl get pods -n customer-success-fte -l component=api
```

Wait for pods to be ready:
```bash
kubectl wait --for=condition=ready pod -l component=api -n customer-success-fte --timeout=120s
```

### 4.5 Deploy Worker Service

```bash
# Replace image tag placeholder
envsubst < k8s/deployment-worker.yaml | kubectl apply -f -
```

Verify:
```bash
kubectl get deployment -n customer-success-fte fte-message-processor
kubectl get pods -n customer-success-fte -l component=message-processor
```

Wait for pods to be ready:
```bash
kubectl wait --for=condition=ready pod -l component=message-processor -n customer-success-fte --timeout=120s
```

### 4.6 Create Service

```bash
kubectl apply -f k8s/service.yaml
```

Verify:
```bash
kubectl get service -n customer-success-fte customer-success-fte
kubectl get endpoints -n customer-success-fte customer-success-fte
```

### 4.7 Create Ingress

```bash
# Replace hostname placeholder
envsubst < k8s/ingress.yaml | kubectl apply -f -
```

Verify:
```bash
kubectl get ingress -n customer-success-fte customer-success-fte
kubectl describe ingress -n customer-success-fte customer-success-fte
```

Wait for TLS certificate (cert-manager):
```bash
kubectl get certificate -n customer-success-fte fte-tls
```

Certificate status should show "Ready: True" (may take 2-5 minutes)

### 4.8 Create HorizontalPodAutoscalers

```bash
kubectl apply -f k8s/hpa.yaml
```

Verify:
```bash
kubectl get hpa -n customer-success-fte
```

---

## Step 5: Verify Deployment

### 5.1 Check All Resources

```bash
kubectl get all -n customer-success-fte
```

Expected output:
- 3 API pods (Running)
- 3 worker pods (Running)
- 2 deployments (Available)
- 1 service
- 2 HPAs

### 5.2 Check Pod Logs

```bash
# API logs
kubectl logs -n customer-success-fte -l component=api --tail=50

# Worker logs
kubectl logs -n customer-success-fte -l component=message-processor --tail=50
```

Look for:
- "Application startup complete"
- No error messages
- Successful database/Kafka connections

### 5.3 Test Health Endpoint (Internal)

```bash
# Port-forward to test health endpoint
kubectl port-forward -n customer-success-fte svc/customer-success-fte 8080:80

# In another terminal
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-03-31T12:00:00Z",
  "checks": {
    "database": "ok",
    "kafka": "ok"
  }
}
```

### 5.4 Test External Access

```bash
# Test HTTPS endpoint (after DNS propagation and certificate issuance)
curl https://$INGRESS_HOSTNAME/health
```

Expected: Same healthy response as above

### 5.5 Verify TLS Certificate

```bash
# Check certificate details
curl -vI https://$INGRESS_HOSTNAME/health 2>&1 | grep -A 10 "SSL certificate"
```

Verify:
- Certificate issued by Let's Encrypt
- Valid dates (not expired)
- Matches your hostname

---

## Step 6: Monitor Deployment

### 6.1 Watch Pod Status

```bash
kubectl get pods -n customer-success-fte -w
```

### 6.2 Monitor Autoscaling

```bash
kubectl get hpa -n customer-success-fte -w
```

### 6.3 Check Events

```bash
kubectl get events -n customer-success-fte --sort-by='.lastTimestamp'
```

---

## Common Issues and Troubleshooting

### Issue: Pods Stuck in Pending

**Symptoms**: Pods show "Pending" status for >2 minutes

**Diagnosis**:
```bash
kubectl describe pod -n customer-success-fte <pod-name>
```

**Common Causes**:
- Insufficient cluster resources (CPU/memory)
- Image pull errors (check registry credentials)
- Node selector/affinity constraints

**Solution**:
- Scale down other workloads or add cluster nodes
- Verify image exists and is accessible
- Check pod events for specific error

### Issue: Pods Failing Health Checks

**Symptoms**: Pods show "Running" but not "Ready", frequent restarts

**Diagnosis**:
```bash
kubectl logs -n customer-success-fte <pod-name>
kubectl describe pod -n customer-success-fte <pod-name>
```

**Common Causes**:
- Database connection failures
- Kafka connection failures
- Missing environment variables
- Application startup errors

**Solution**:
- Verify external services are accessible from cluster
- Check ConfigMap and Secret values
- Review application logs for specific errors

### Issue: Certificate Not Issued

**Symptoms**: Ingress shows no TLS certificate after 5+ minutes

**Diagnosis**:
```bash
kubectl describe certificate -n customer-success-fte fte-tls
kubectl logs -n cert-manager -l app=cert-manager
```

**Common Causes**:
- DNS not propagated yet
- cert-manager not installed or misconfigured
- Let's Encrypt rate limits

**Solution**:
- Wait for DNS propagation (check with `nslookup`)
- Verify cert-manager is running: `kubectl get pods -n cert-manager`
- Check cert-manager logs for errors

### Issue: 503 Service Unavailable

**Symptoms**: External requests return 503 error

**Diagnosis**:
```bash
kubectl get endpoints -n customer-success-fte customer-success-fte
kubectl logs -n customer-success-fte -l component=api
```

**Common Causes**:
- No healthy pods (all failing readiness checks)
- Service selector mismatch
- Ingress misconfiguration

**Solution**:
- Fix pod health issues first (see above)
- Verify service selector matches pod labels
- Check ingress backend configuration

---

## Updating the Deployment

### Rolling Update (Zero-Downtime)

```bash
# Update image tag in deployment
kubectl set image deployment/fte-api -n customer-success-fte \
  fte-api=$CONTAINER_REGISTRY/customer-success-fte:v1.1.0

# Watch rollout progress
kubectl rollout status deployment/fte-api -n customer-success-fte
```

### Rollback to Previous Version

```bash
# Rollback if new version has issues
kubectl rollout undo deployment/fte-api -n customer-success-fte

# Check rollout history
kubectl rollout history deployment/fte-api -n customer-success-fte
```

### Update Configuration

```bash
# Edit ConfigMap
kubectl edit configmap -n customer-success-fte fte-config

# Restart pods to pick up new config
kubectl rollout restart deployment/fte-api -n customer-success-fte
kubectl rollout restart deployment/fte-message-processor -n customer-success-fte
```

---

## Scaling

### Manual Scaling

```bash
# Scale API deployment
kubectl scale deployment/fte-api -n customer-success-fte --replicas=5

# Scale worker deployment
kubectl scale deployment/fte-message-processor -n customer-success-fte --replicas=10
```

**Note**: Manual scaling overrides HPA temporarily. HPA will resume control after scaling stabilizes.

### Adjust Autoscaling Limits

```bash
# Edit HPA to change min/max replicas
kubectl edit hpa -n customer-success-fte fte-api-hpa
```

---

## Cleanup / Uninstall

### Remove All Resources

```bash
# Delete entire namespace (cascades to all resources)
kubectl delete namespace customer-success-fte
```

### Remove Individual Resources

```bash
# Delete in reverse order of creation
kubectl delete hpa -n customer-success-fte --all
kubectl delete ingress -n customer-success-fte --all
kubectl delete service -n customer-success-fte --all
kubectl delete deployment -n customer-success-fte --all
kubectl delete secret -n customer-success-fte --all
kubectl delete configmap -n customer-success-fte --all
kubectl delete namespace customer-success-fte
```

---

## Production Checklist

Before going live, verify:

- [ ] All pods are running and healthy (3 API + 3 workers minimum)
- [ ] Health endpoint returns 200 OK via HTTPS
- [ ] TLS certificate is valid and issued by Let's Encrypt
- [ ] DNS resolves to correct load balancer IP
- [ ] External services (database, Kafka, Redis) are accessible
- [ ] Secrets are properly configured (no placeholder values)
- [ ] Autoscaling is working (test with load)
- [ ] Logs are being collected and monitored
- [ ] Backup and disaster recovery procedures are documented
- [ ] Rollback procedure has been tested
- [ ] On-call team has access to cluster and documentation

---

## Next Steps

After successful deployment:

1. **Set up monitoring**: Configure Prometheus/Grafana for metrics
2. **Set up logging**: Configure ELK/Loki for centralized logs
3. **Set up alerts**: Configure alerting for pod failures, high CPU/memory
4. **Load testing**: Verify system handles expected traffic
5. **Disaster recovery**: Test backup/restore procedures
6. **Documentation**: Update runbooks with production-specific details

---

## Support

For issues or questions:
- Check application logs: `kubectl logs -n customer-success-fte <pod-name>`
- Check Kubernetes events: `kubectl get events -n customer-success-fte`
- Review this guide's troubleshooting section
- Contact platform team for cluster-level issues

---

## Summary

You have successfully deployed the multi-channel customer success FTE system to Kubernetes with:
- ✅ High availability (3+ replicas)
- ✅ Automatic scaling (3-20 API, 3-30 workers)
- ✅ Self-healing (automatic pod restarts)
- ✅ Zero-downtime updates (rolling deployments)
- ✅ Secure configuration (strict security context, TLS)
- ✅ External access (HTTPS with Let's Encrypt)

The system is now ready to handle production traffic!
