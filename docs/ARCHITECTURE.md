# Architecture Overview

## System Architecture

The CRM Digital FTE Factory uses a **microservices architecture** with separate processes for API and message processing.

```
┌────────────────────────────────────────────────────────────────┐
│                       Kubernetes Cluster                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │   fte-api    │      │ fte-message- │      │   kafka-0    │  │
│  │              │      │  processor   │      │              │  │
│  │ FastAPI HTTP │      │              │      │ Kafka Broker │  │
│  │   Server     │      │    Kafka     │      │              │  │
│  │              │      │   Consumer   │      │              │  │
│  │ Port: 8000   │      │              │      │ Port: 9092   │  │
│  └──────┬───────┘      └──────┬───────┘      └──────┬───────┘  │
│         │                     │                     │          │
│         │                     │                     │          │
│         │                     └─────────────────────┘          │
│         │                                                      │
│         │              ┌──────────────┐                        │
│         │              │    redis     │                        │
│         └──────────────┤              │                        │
│                        │  Cache/Rate  │                        │
│                        │   Limiter    │                        │
│                        │ Port: 6379   │                        │
│                        └──────────────┘                        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
         │                                          │
         │                                          │
         ▼                                          ▼
┌─────────────────┐                        ┌─────────────────┐
│   External DB   │                        │  External APIs  │
│ (Neon Postgres) │                        │ (Gmail, Twilio) │
└─────────────────┘                        └─────────────────┘
```

## Components

### 1. API Server (`fte-api`)

**Purpose:** Handle HTTP requests and produce messages to Kafka

**Responsibilities:**
- Receive webhook requests (Gmail, WhatsApp, Web Form)
- Validate HMAC signatures
- Apply rate limiting
- Produce messages to Kafka topics
- Serve health check endpoint
- Expose Prometheus metrics

**Does NOT:**
- Consume messages from Kafka
- Invoke AI agent
- Send responses to customers

**Deployment:**
- Image: `customer-success-fte:test`
- Command: Default (uvicorn)
- Replicas: 1 (can scale horizontally)
- Resources: 512Mi-1Gi memory, 250m-500m CPU

### 2. Message Processor Worker (`fte-message-processor`)

**Purpose:** Consume messages from Kafka and process them with AI agent

**Responsibilities:**
- Consume from 3 Kafka topics:
  - `customer-intake.email.inbound`
  - `customer-intake.whatsapp.inbound`
  - `customer-intake.webform.inbound`
- Invoke AI agent (OpenAI Agents SDK)
- Send responses via Gmail/WhatsApp handlers
- Maintain conversation history in database

**Does NOT:**
- Handle HTTP requests
- Expose any HTTP endpoints

**Deployment:**
- Image: `customer-success-fte:test`
- Command: `python -m src.workers.message_processor`
- Replicas: 1 (can scale horizontally)
- Resources: 512Mi-1Gi memory, 250m-500m CPU
- Consumer Group: `customer-success-agent-group`

### 3. Kafka (`kafka-0`)

**Purpose:** Message queue for reliable async processing

**Deployment:**
- StatefulSet (persistent storage)
- Image: `apache/kafka-native:3.9.0`
- Replicas: 1
- Services:
  - `kafka`: Headless service for StatefulSet
  - `kafka-client`: ClusterIP for client connections

### 4. Redis (`redis`)

**Purpose:** Cache and rate limiting

**Deployment:**
- Deployment (stateless)
- Image: `redis:7-alpine`
- Replicas: 1

## Message Flow

### Inbound Message Flow

```
1. External System (Gmail/Twilio/Web Form)
   │
   ▼
2. API Server (fte-api)
   │ - Validate HMAC
   │ - Rate limit check
   │ - Identify customer
   │
   ▼
3. Kafka Topic (customer-intake.*.inbound)
   │
   ▼
4. Message Processor Worker (fte-message-processor)
   │ - Consume message
   │ - Load conversation history
   │ - Invoke AI agent
   │
   ▼
5. AI Agent (OpenAI Agents SDK)
   │ - Process message
   │ - Generate response
   │
   ▼
6. Channel Handler (Gmail/WhatsApp)
   │ - Send response
   │
   ▼
7. External System (Gmail/Twilio)
```

## Scaling Strategy

### API Server
- **Scale based on:** HTTP request rate
- **Metric:** CPU utilization, request latency
- **HPA:** Can scale 1-10 replicas

### Message Processor Worker
- **Scale based on:** Kafka consumer lag
- **Metric:** Messages pending in Kafka topics
- **HPA:** Can scale 1-10 replicas
- **Note:** Each replica joins the same consumer group, Kafka automatically rebalances partitions

### Independent Scaling
- API and Worker scale independently
- High HTTP traffic doesn't force more Kafka consumers
- High message volume doesn't force more API servers

## Benefits of Separation

1. **Independent Scaling:** Scale API and worker based on different metrics
2. **Fault Isolation:** API failures don't stop message processing
3. **Resource Allocation:** Give workers more memory if needed for AI agent
4. **Deployment Flexibility:** Update API without restarting consumers (no Kafka rebalancing)
5. **Clear Separation of Concerns:** HTTP handling vs message processing

## Configuration

### Environment Variables

Both API and Worker share the same configuration via ConfigMap and Secrets:

**ConfigMap (`fte-config`):**
- `KAFKA_BOOTSTRAP_SERVERS`
- `REDIS_URL`
- `ENVIRONMENT`
- `LOG_LEVEL`

**Secret (`fte-secrets`):**
- `DATABASE_URL`
- `GEMINI_API_KEY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_WEBHOOK_SECRET`

## Monitoring

### Health Checks

**API Server:**
- Endpoint: `GET /health`
- Checks: Database, Redis, Kafka producer

**Worker:**
- No HTTP endpoint (runs in background)
- Monitor via logs and Kafka consumer lag

### Logs

**API Server:**
```bash
kubectl logs -n customer-success-fte deployment/fte-api
```

**Worker:**
```bash
kubectl logs -n customer-success-fte deployment/fte-message-processor
```

### Metrics

- Prometheus metrics exposed at `/metrics` (API only)
- Kafka consumer lag metrics (via Kafka)

## Deployment

### Manual Deployment

```bash
# 1. Create namespace
kubectl create namespace customer-success-fte

# 2. Create secrets
kubectl create secret generic fte-secrets -n customer-success-fte \
  --from-literal=DATABASE_URL="..." \
  --from-literal=GEMINI_API_KEY="..." \
  --from-literal=TWILIO_ACCOUNT_SID="..." \
  --from-literal=TWILIO_AUTH_TOKEN="..." \
  --from-literal=TWILIO_WEBHOOK_SECRET="..."

# 3. Apply manifests
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/kafka-statefulset.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/deployment-api.yaml
kubectl apply -f k8s/deployment-worker.yaml
kubectl apply -f k8s/service.yaml
```

### Automated Deployment

```bash
# Use deployment script
cd scripts
bash deploy-k8s.sh
```

## Testing

### Test API Health

```bash
kubectl port-forward -n customer-success-fte service/customer-success-fte 8000:80
curl http://localhost:8000/health
```

### Test Message Flow

1. Send test message via API
2. Check Kafka topic has message
3. Check worker logs for processing
4. Verify response sent via channel

### Verify Worker is Consuming

```bash
kubectl logs -n customer-success-fte deployment/fte-message-processor | grep "Kafka consumer started"
```

Expected output:
```
INFO - Kafka consumer started (group: customer-success-agent-group)
INFO - Starting Kafka consume loop...
```

## Troubleshooting

### Worker Not Consuming Messages

1. Check worker logs: `kubectl logs -n customer-success-fte deployment/fte-message-processor`
2. Check Kafka connectivity: Worker should show "Joined group" message
3. Check consumer group: `kubectl exec -n customer-success-fte kafka-0 -- kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group customer-success-agent-group`

### API Not Producing Messages

1. Check API logs: `kubectl logs -n customer-success-fte deployment/fte-api`
2. Check Kafka producer initialization in health endpoint
3. Verify Kafka is running: `kubectl get pods -n customer-success-fte -l app=kafka`

### High Consumer Lag

1. Scale worker replicas: `kubectl scale deployment fte-message-processor -n customer-success-fte --replicas=3`
2. Check worker resource usage: `kubectl top pods -n customer-success-fte`
3. Investigate slow message processing in worker logs
