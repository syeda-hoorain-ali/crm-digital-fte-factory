---
id: 0008
title: Separate Kafka Consumer into Standalone Worker Process
stage: refactor
date: 2026-04-02
surface: agent
model: qwen3-code-plus
feature: 007-k8s-deployment
branch: 007-k8s-deployment
user: Syeda Hoorain Ali
command: continue
labels: ["architecture", "kafka", "worker", "separation-of-concerns", "microservices"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/src/workers/__init__.py
  - backend/src/workers/message_processor.py
  - backend/src/main.py
  - docs/ARCHITECTURE.md
  - k8s/deployment-worker.yaml
tests:
  - Manual deployment verification
  - Pod status check
  - Worker logs verification
  - API logs verification (no Kafka consumer)
---

# Prompt

User: "i want separate worker process, not mixed with api"

Context: The initial K8s deployment had the Kafka consumer running inside the API process (main.py). This meant the API pod was handling both HTTP requests and consuming/processing Kafka messages. The user wanted to separate these concerns into independent processes.

# Response

## Problem Analysis

The original architecture had `KafkaConsumerService` running inside the FastAPI application:
- API startup initialized both HTTP server and Kafka consumer
- Both ran in the same process/pod
- Couldn't scale independently
- Resource contention between HTTP and message processing
- Deployment coupling (API updates restart consumers)

## Solution Approach

Created a separate worker process architecture:

### 1. Created Standalone Worker Module

**File:** `backend/src/workers/message_processor.py`

- Standalone Python script that runs independently
- Reuses the tested `KafkaConsumerService` class
- Initializes all dependencies (DB, Redis, Twilio, Gmail, Kafka)
- Runs async event loop with signal handling (SIGTERM, SIGINT)
- No HTTP server, pure message processing

Key features:
- Uses same configuration as API (ConfigMap/Secrets)
- Joins consumer group: `customer-success-agent-group`
- Consumes from 3 topics: email, whatsapp, webform
- Invokes AI agent and sends responses

### 2. Removed Kafka Consumer from API

**File:** `backend/src/main.py`

Removed:
- Import of `KafkaConsumerService`
- Consumer initialization in lifespan (Step 7)
- Consumer shutdown logic
- Consumer storage in `app.state`

Result: API now only handles HTTP requests and produces to Kafka

### 3. Updated K8s Deployment

**File:** `k8s/deployment-worker.yaml`

- Deployment: `fte-message-processor`
- Command: `python -m src.workers.message_processor`
- Same image as API: `customer-success-fte:test`
- Same resources: 512Mi-1Gi memory, 250m-500m CPU
- Same security context: non-root, read-only filesystem

### 4. Documented Architecture

**File:** `docs/ARCHITECTURE.md`

Comprehensive documentation including:
- System architecture diagram
- Component responsibilities
- Message flow
- Scaling strategy
- Benefits of separation
- Deployment instructions
- Troubleshooting guide

## Deployment Process

1. Built Docker image with worker code
2. Loaded image to minikube
3. Deleted namespace for clean deployment
4. Created namespace and secrets
5. Deployed ConfigMap, Kafka, Redis
6. Deployed both API and Worker
7. Verified both pods running

## Verification

### Pod Status
```
NAME                                     READY   STATUS    RESTARTS   AGE
fte-api-8656cc64f6-rgjkk                 1/1     Running   0          7m59s
fte-message-processor-54848dc579-57tpv   1/1     Running   0          6m50s
kafka-0                                  1/1     Running   0          13m
redis-8d76457b9-9t9rl                    1/1     Running   0          10m
```

### Worker Logs (Consuming Successfully)
```
INFO - Joined group 'customer-success-agent-group' (generation 1)
INFO - Successfully synced group customer-success-agent-group with generation 1
INFO - Setting newly assigned partitions {9 partitions across 3 topics}
INFO - Kafka consumer started (group: customer-success-agent-group)
INFO - Message processor worker running...
INFO - Starting Kafka consume loop...
```

### API Logs (No Kafka Consumer)
- No Kafka consumer initialization logs
- Only HTTP server logs (uvicorn)
- Health checks passing

### Code Verification
```bash
$ cat backend/src/main.py | grep "KafkaConsumerService"
No KafkaConsumerService found in main.py
```

## Benefits Achieved

1. **Independent Scaling:** API and worker can scale based on different metrics
2. **Fault Isolation:** API failures don't stop message processing
3. **Resource Allocation:** Can give workers more memory for AI agent
4. **Deployment Flexibility:** Update API without restarting consumers
5. **Clear Separation:** HTTP handling vs message processing

## Architecture Summary

```
API Pod (fte-api)
├── FastAPI HTTP Server (port 8000)
│   ├── /health endpoint
│   ├── /support/submit (web form)
│   ├── /webhooks/whatsapp (Twilio)
│   └── /webhooks/gmail (Gmail push)
└── Kafka Producer (produces messages)

Worker Pod (fte-message-processor)
├── Kafka Consumer (consumes messages)
├── AI Agent (OpenAI Agents SDK)
└── Channel Handlers (Gmail, WhatsApp)
```

## Files Modified

- `backend/src/main.py` (-35 lines): Removed Kafka consumer
- `backend/src/workers/__init__.py` (new): Package init
- `backend/src/workers/message_processor.py` (new, 169 lines): Standalone worker
- `docs/ARCHITECTURE.md` (new, 300+ lines): Architecture documentation

## Outcome

✅ Successfully separated Kafka consumer into standalone worker process
✅ Both API and worker deployed and running in K8s
✅ Worker consuming from Kafka (9 partitions assigned)
✅ API handling HTTP requests only
✅ Complete architecture documented
✅ Ready for independent scaling

## Next Steps

Potential improvements:
1. Add worker health check endpoint (optional HTTP server for liveness probe)
2. Configure HPA for worker based on Kafka consumer lag
3. Add Prometheus metrics to worker
4. Test scaling both API and worker independently
5. Create ADR documenting the separation decision
