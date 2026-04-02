# Kubernetes Resource Model

**Feature**: 007-k8s-deployment - Kubernetes Production Deployment
**Date**: 2026-03-31
**Phase**: Phase 1 - Design & Contracts

## Overview

This document defines the Kubernetes resource model for the multi-channel customer success FTE system. It describes the 8 manifest files, their relationships, and how they work together to provide a production-ready deployment.

---

## Resource Hierarchy

```
Namespace: customer-success-fte
├── ConfigMap: fte-config
├── Secret: fte-secrets
├── Deployment: fte-api
│   ├── ReplicaSet (managed by Deployment)
│   └── Pods: fte-api-* (3-20 replicas)
├── Deployment: fte-message-processor
│   ├── ReplicaSet (managed by Deployment)
│   └── Pods: fte-message-processor-* (3-30 replicas)
├── Service: customer-success-fte
│   └── Endpoints (points to fte-api pods)
├── Ingress: customer-success-fte
│   └── Routes traffic to Service
├── HorizontalPodAutoscaler: fte-api-hpa
│   └── Scales fte-api Deployment
└── HorizontalPodAutoscaler: fte-worker-hpa
    └── Scales fte-message-processor Deployment
```

---

## Resource Definitions

### 1. Namespace

**Resource**: `namespace.yaml`
**API Version**: v1
**Kind**: Namespace

**Purpose**: Provides logical isolation for all FTE resources within the Kubernetes cluster.

**Attributes**:
- **name**: `customer-success-fte`
- **labels**: `app: customer-success-fte`

**Relationships**:
- Contains all other resources in this deployment
- Provides scope for resource quotas and network policies (if added later)

**Lifecycle**: Created first, deleted last (cascades deletion to all contained resources)

---

### 2. ConfigMap

**Resource**: `configmap.yaml`
**API Version**: v1
**Kind**: ConfigMap

**Purpose**: Stores non-sensitive configuration data for the application.

**Attributes**:
- **name**: `fte-config`
- **namespace**: `customer-success-fte`
- **data**: Key-value pairs for environment variables

**Configuration Keys**:
```yaml
ENVIRONMENT: "production"
LOG_LEVEL: "INFO"
KAFKA_BOOTSTRAP_SERVERS: "kafka.kafka.svc.cluster.local:9092"
POSTGRES_HOST: "postgres.customer-success-fte.svc.cluster.local"
POSTGRES_DB: "fte_db"
GMAIL_ENABLED: "true"
WHATSAPP_ENABLED: "true"
WEBFORM_ENABLED: "true"
MAX_EMAIL_LENGTH: "2000"
MAX_WHATSAPP_LENGTH: "1600"
MAX_WEBFORM_LENGTH: "1000"
```

**Relationships**:
- Referenced by both Deployment resources via `envFrom.configMapRef`
- Can be updated independently of Deployments (requires pod restart to take effect)

**Lifecycle**: Created before Deployments, can be updated without recreating pods (manual restart required)

---

### 3. Secret

**Resource**: `secrets.yaml`
**API Version**: v1
**Kind**: Secret

**Purpose**: Stores sensitive credentials and API keys securely.

**Attributes**:
- **name**: `fte-secrets`
- **namespace**: `customer-success-fte`
- **type**: Opaque
- **stringData**: Key-value pairs with placeholders for credential injection

**Secret Keys** (with placeholders):
```yaml
OPENAI_API_KEY: "${OPENAI_API_KEY}"
POSTGRES_PASSWORD: "${POSTGRES_PASSWORD}"
GMAIL_CREDENTIALS: "${GMAIL_CREDENTIALS_JSON}"
TWILIO_ACCOUNT_SID: "${TWILIO_ACCOUNT_SID}"
TWILIO_AUTH_TOKEN: "${TWILIO_AUTH_TOKEN}"
TWILIO_WHATSAPP_NUMBER: "${TWILIO_WHATSAPP_NUMBER}"
WEBHOOK_SECRET: "${WEBHOOK_SECRET}"
```

**Relationships**:
- Referenced by both Deployment resources via `envFrom.secretRef`
- Must be created with actual values (placeholders replaced) before Deployments

**Lifecycle**: Created before Deployments, rotation requires pod restart

**Security Notes**:
- Never commit actual secrets to version control
- Use environment variable substitution or secret management tools (e.g., sealed-secrets, external-secrets)
- Base64-encoded by Kubernetes automatically

---

### 4. Deployment (API)

**Resource**: `deployment-api.yaml`
**API Version**: apps/v1
**Kind**: Deployment

**Purpose**: Manages the FastAPI service pods that handle webhook requests and serve the REST API.

**Attributes**:
- **name**: `fte-api`
- **namespace**: `customer-success-fte`
- **replicas**: 3 (initial)
- **selector**: `app: customer-success-fte, component: api`

**Pod Template Specification**:
- **Image**: `your-registry/customer-success-fte:v1.2.3` (semantic version tag)
- **Command**: `["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- **Ports**: 8000 (containerPort)
- **Environment**: Injected from ConfigMap and Secret
- **Resources**:
  - Requests: 512Mi memory, 250m CPU
  - Limits: 1Gi memory, 500m CPU

**Health Checks**:
- **Liveness Probe**: HTTP GET /health (initialDelay=10s, period=10s, timeout=1s, failure=3)
- **Readiness Probe**: HTTP GET /health (initialDelay=10s, period=10s, timeout=1s, failure=3)

**Security Context**:
- runAsUser: 1000
- fsGroup: 1000
- runAsNonRoot: true
- readOnlyRootFilesystem: true
- capabilities: drop ALL

**Rolling Update Strategy**:
- maxSurge: 1
- maxUnavailable: 1

**Relationships**:
- Creates and manages ReplicaSet (automatically)
- ReplicaSet creates and manages Pods
- Pods are selected by Service
- Scaled by HorizontalPodAutoscaler

**Lifecycle**: Created after ConfigMap and Secret, updated via rolling updates

---

### 5. Deployment (Worker)

**Resource**: `deployment-worker.yaml`
**API Version**: apps/v1
**Kind**: Deployment

**Purpose**: Manages Kafka message processor worker pods that consume messages and execute agent workflows.

**Attributes**:
- **name**: `fte-message-processor`
- **namespace**: `customer-success-fte`
- **replicas**: 3 (initial)
- **selector**: `app: customer-success-fte, component: message-processor`

**Pod Template Specification**:
- **Image**: `your-registry/customer-success-fte:v1.2.3` (semantic version tag)
- **Command**: `["python", "-m", "src.workers.message_processor"]`
- **Environment**: Injected from ConfigMap and Secret
- **Resources**:
  - Requests: 512Mi memory, 250m CPU
  - Limits: 1Gi memory, 500m CPU

**Security Context**: Same as API deployment (strict security)

**Rolling Update Strategy**: Same as API deployment (maxSurge: 1, maxUnavailable: 1)

**Relationships**:
- Creates and manages ReplicaSet (automatically)
- ReplicaSet creates and manages Pods
- Scaled by HorizontalPodAutoscaler
- Not exposed via Service (internal workers)

**Lifecycle**: Created after ConfigMap and Secret, updated via rolling updates

**Note**: Workers do not have health checks (no HTTP endpoint), rely on process exit codes

---

### 6. Service

**Resource**: `service.yaml`
**API Version**: v1
**Kind**: Service

**Purpose**: Provides internal load balancing and service discovery for API pods.

**Attributes**:
- **name**: `customer-success-fte`
- **namespace**: `customer-success-fte`
- **type**: ClusterIP (internal only)
- **selector**: `app: customer-success-fte, component: api`
- **ports**: 80 (service port) → 8000 (target port)

**Relationships**:
- Selects API pods based on labels
- Creates Endpoints resource automatically
- Referenced by Ingress as backend service

**Lifecycle**: Created after Deployment, stable (rarely changes)

**Load Balancing**: Round-robin across healthy API pods (based on readiness probe)

---

### 7. Ingress

**Resource**: `ingress.yaml`
**API Version**: networking.k8s.io/v1
**Kind**: Ingress

**Purpose**: Provides external access to the API with TLS termination.

**Attributes**:
- **name**: `customer-success-fte`
- **namespace**: `customer-success-fte`
- **ingressClassName**: nginx
- **annotations**:
  - `cert-manager.io/cluster-issuer: letsencrypt-prod`

**TLS Configuration**:
- **hosts**: `${INGRESS_HOSTNAME}` (placeholder)
- **secretName**: `fte-tls` (created by cert-manager)

**Rules**:
- **host**: `${INGRESS_HOSTNAME}` (placeholder)
- **path**: `/` (pathType: Prefix)
- **backend**: Service `customer-success-fte` on port 80

**Relationships**:
- Routes external traffic to Service
- cert-manager watches Ingress and creates TLS certificate
- NGINX Ingress Controller implements routing rules

**Lifecycle**: Created after Service, hostname must be configured before applying

**Security**: TLS 1.2+ enforced by NGINX Ingress Controller

---

### 8. HorizontalPodAutoscaler (API)

**Resource**: `hpa.yaml`
**API Version**: autoscaling/v2
**Kind**: HorizontalPodAutoscaler

**Purpose**: Automatically scales API deployment based on CPU utilization.

**Attributes**:
- **name**: `fte-api-hpa`
- **namespace**: `customer-success-fte`
- **scaleTargetRef**: Deployment `fte-api`
- **minReplicas**: 3
- **maxReplicas**: 20
- **metrics**: CPU utilization target 70%

**Scaling Behavior**:
- Scales up when average CPU > 70% across all pods
- Scales down when average CPU < 70% for sustained period
- Scaling decisions made every 15 seconds (default)
- Scale-up: Immediate (within 30 seconds)
- Scale-down: Gradual (5-minute stabilization window)

**Relationships**:
- Watches Deployment `fte-api`
- Modifies Deployment replica count
- Requires Metrics Server for CPU metrics

**Lifecycle**: Created after Deployment, continuously monitors and adjusts

---

### 9. HorizontalPodAutoscaler (Worker)

**Resource**: `hpa.yaml`
**API Version**: autoscaling/v2
**Kind**: HorizontalPodAutoscaler

**Purpose**: Automatically scales worker deployment based on CPU utilization.

**Attributes**:
- **name**: `fte-worker-hpa`
- **namespace**: `customer-success-fte`
- **scaleTargetRef**: Deployment `fte-message-processor`
- **minReplicas**: 3
- **maxReplicas**: 30
- **metrics**: CPU utilization target 70%

**Scaling Behavior**: Same as API HPA

**Relationships**:
- Watches Deployment `fte-message-processor`
- Modifies Deployment replica count
- Requires Metrics Server for CPU metrics

**Lifecycle**: Created after Deployment, continuously monitors and adjusts

---

## Resource Dependencies

### Creation Order (Apply Sequence)

1. **Namespace** - Must exist before all other resources
2. **ConfigMap** - Required by Deployments
3. **Secret** - Required by Deployments
4. **Deployment (API)** - Creates pods
5. **Deployment (Worker)** - Creates pods
6. **Service** - Selects API pods
7. **Ingress** - Routes to Service
8. **HorizontalPodAutoscaler (API)** - Scales API deployment
9. **HorizontalPodAutoscaler (Worker)** - Scales worker deployment

### Deletion Order (Cleanup Sequence)

Reverse of creation order to avoid orphaned resources and ensure graceful shutdown.

---

## State Transitions

### Deployment Lifecycle States

1. **Progressing**: Rolling update in progress
2. **Available**: Minimum replicas are available
3. **Complete**: All replicas updated and available
4. **Failed**: Update failed (health checks, image pull errors)

### Pod Lifecycle States

1. **Pending**: Waiting for scheduling
2. **ContainerCreating**: Pulling image, creating container
3. **Running**: Container started, health checks passing
4. **Terminating**: Graceful shutdown in progress
5. **Failed**: Container exited with error
6. **CrashLoopBackOff**: Container repeatedly failing

### Scaling Events

1. **Scale Up**: HPA increases replica count → Deployment creates new pods
2. **Scale Down**: HPA decreases replica count → Deployment terminates excess pods
3. **Manual Scale**: kubectl scale command → Overrides HPA (temporarily)

---

## Data Flow

### Request Flow (External → API)

1. External client → DNS resolution → Cluster load balancer
2. Load balancer → NGINX Ingress Controller
3. Ingress Controller → Service (port 80)
4. Service → API Pod (port 8000)
5. API Pod → Response → Client

### Message Processing Flow (Internal)

1. Kafka → Worker Pod consumes message
2. Worker Pod → Processes message → Calls agent
3. Worker Pod → Writes to database
4. Worker Pod → Publishes result to Kafka

---

## Volume Mounts (for Read-Only Filesystem)

Since pods use `readOnlyRootFilesystem: true`, writable volumes are required for:

1. **Temporary Files**: emptyDir volume mounted at `/tmp`
2. **Application Cache**: emptyDir volume mounted at `/app/.cache` (if needed)
3. **Logs**: stdout/stderr (captured by Kubernetes, no volume needed)

**Note**: These volumes are ephemeral and cleared when pods restart.

---

## Summary

The Kubernetes resource model consists of 8 manifest files that work together to provide:
- **Isolation**: Dedicated namespace
- **Configuration**: Separate ConfigMap and Secret
- **Compute**: Two Deployments (API + workers) with strict security
- **Networking**: Service for internal routing, Ingress for external access
- **Scaling**: Two HPAs for automatic resource adjustment

All resources follow Kubernetes best practices with health checks, resource limits, security contexts, and rolling updates.
