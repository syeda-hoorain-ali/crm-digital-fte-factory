# Application Requirements Contract

**Feature**: 007-k8s-deployment - Kubernetes Production Deployment
**Date**: 2026-03-31
**Phase**: Phase 1 - Design & Contracts

## Overview

This document defines the contract between the Kubernetes deployment manifests and the application code. The application must satisfy these requirements to run successfully in the Kubernetes environment.

---

## Environment Variables Contract

### Required Environment Variables (from ConfigMap)

The application MUST read and handle the following environment variables:

```bash
# Environment Configuration
ENVIRONMENT=production          # Deployment environment (development, staging, production)
LOG_LEVEL=INFO                 # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

# External Service Endpoints
KAFKA_BOOTSTRAP_SERVERS=kafka.kafka.svc.cluster.local:9092
POSTGRES_HOST=postgres.customer-success-fte.svc.cluster.local
POSTGRES_DB=fte_db

# Channel Configuration
GMAIL_ENABLED=true             # Enable/disable Gmail channel
WHATSAPP_ENABLED=true          # Enable/disable WhatsApp channel
WEBFORM_ENABLED=true           # Enable/disable Web Form channel

# Response Limits (per channel)
MAX_EMAIL_LENGTH=2000          # Maximum email response length (characters)
MAX_WHATSAPP_LENGTH=1600       # Maximum WhatsApp response length (characters)
MAX_WEBFORM_LENGTH=1000        # Maximum web form response length (characters)
```

### Required Environment Variables (from Secret)

The application MUST read and handle the following sensitive environment variables:

```bash
# AI Service
OPENAI_API_KEY=<secret>        # OpenAI API key for agent

# Database
POSTGRES_PASSWORD=<secret>     # PostgreSQL database password

# Gmail API
GMAIL_CREDENTIALS=<json>       # Gmail API credentials (JSON format)

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=<secret>    # Twilio account SID
TWILIO_AUTH_TOKEN=<secret>     # Twilio authentication token
TWILIO_WHATSAPP_NUMBER=<phone> # Twilio WhatsApp number (e.g., +14155238886)

# Security
WEBHOOK_SECRET=<secret>        # HMAC secret for webhook signature verification
```

### Environment Variable Validation

The application MUST:
1. Validate all required environment variables are present at startup
2. Fail fast with clear error messages if required variables are missing
3. Log configuration (excluding secrets) at startup for debugging
4. Support default values for optional configuration

---

## Health Endpoint Contract

### Endpoint Specification

**Path**: `/health`
**Method**: GET
**Port**: 8000 (FastAPI default)

### Response Requirements

The health endpoint MUST:
1. Respond within 1 second (timeout configured in probes)
2. Return HTTP 200 OK when the application is healthy
3. Return HTTP 503 Service Unavailable when the application is unhealthy
4. Check critical dependencies (database, Kafka) before responding

### Response Format

**Healthy Response** (HTTP 200):
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

**Unhealthy Response** (HTTP 503):
```json
{
  "status": "unhealthy",
  "timestamp": "2026-03-31T12:00:00Z",
  "checks": {
    "database": "ok",
    "kafka": "failed"
  },
  "error": "Kafka connection timeout"
}
```

### Health Check Behavior

**Liveness Probe** (determines if pod should be restarted):
- Checks if the application process is running and responsive
- Does NOT check external dependencies (to avoid restart loops)
- Returns 200 if the application can serve requests

**Readiness Probe** (determines if pod should receive traffic):
- Checks if the application is ready to handle requests
- DOES check external dependencies (database, Kafka)
- Returns 200 only if all critical dependencies are available

### Implementation Example

```python
from fastapi import FastAPI, Response
from datetime import datetime
import asyncio

app = FastAPI()

@app.get("/health")
async def health_check():
    """
    Health check endpoint for Kubernetes probes.
    
    Liveness: Returns 200 if application is running
    Readiness: Returns 200 if application + dependencies are ready
    """
    checks = {}
    all_healthy = True
    
    # Check database connection
    try:
        await check_database()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = "failed"
        all_healthy = False
    
    # Check Kafka connection
    try:
        await check_kafka()
        checks["kafka"] = "ok"
    except Exception as e:
        checks["kafka"] = "failed"
        all_healthy = False
    
    status_code = 200 if all_healthy else 503
    
    return Response(
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": checks
        },
        status_code=status_code
    )
```

---

## Graceful Shutdown Contract

### Signal Handling

The application MUST handle SIGTERM signals for graceful shutdown:

1. **Receive SIGTERM**: Kubernetes sends SIGTERM when terminating pod
2. **Stop accepting new requests**: Close HTTP server listener
3. **Complete in-flight requests**: Allow up to 30 seconds for completion
4. **Close connections**: Gracefully close database, Kafka, Redis connections
5. **Exit cleanly**: Exit with code 0 after cleanup

### Shutdown Timeout

Kubernetes waits 30 seconds (default terminationGracePeriodSeconds) before sending SIGKILL. The application MUST complete shutdown within this window.

### Implementation Example

```python
import signal
import asyncio

shutdown_event = asyncio.Event()

def handle_sigterm(signum, frame):
    """Handle SIGTERM signal for graceful shutdown."""
    logger.info("Received SIGTERM, initiating graceful shutdown")
    shutdown_event.set()

signal.signal(signal.SIGTERM, handle_sigterm)

async def shutdown():
    """Graceful shutdown procedure."""
    logger.info("Stopping HTTP server...")
    # Stop accepting new requests
    
    logger.info("Completing in-flight requests...")
    await asyncio.sleep(5)  # Allow time for completion
    
    logger.info("Closing database connections...")
    await db.close()
    
    logger.info("Closing Kafka connections...")
    await kafka_producer.close()
    
    logger.info("Shutdown complete")
```

---

## Filesystem Contract

### Read-Only Root Filesystem

The application MUST support `readOnlyRootFilesystem: true` security context:

1. **No writes to root filesystem**: All writes must go to mounted volumes
2. **Temporary files**: Use `/tmp` (emptyDir volume)
3. **Cache files**: Use `/app/.cache` (emptyDir volume) if needed
4. **Logs**: Write to stdout/stderr (captured by Kubernetes)

### Volume Mounts Required

```yaml
volumeMounts:
  - name: tmp
    mountPath: /tmp
  - name: cache
    mountPath: /app/.cache

volumes:
  - name: tmp
    emptyDir: {}
  - name: cache
    emptyDir: {}
```

### Implementation Considerations

- Configure Python to use `/tmp` for temporary files
- Set cache directories to `/app/.cache`
- Avoid writing to current working directory
- Use environment variables to configure writable paths

---

## User and Permissions Contract

### Non-Root User Requirement

The application MUST run as non-root user (UID 1000):

1. **Dockerfile**: Create user with UID 1000
2. **File ownership**: Ensure application files are readable by UID 1000
3. **Port binding**: Use port 8000 (>1024, no root required)

### Dockerfile Example

```dockerfile
FROM python:3.12-slim

# Create non-root user with UID 1000
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . /app
WORKDIR /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Resource Usage Contract

### Memory Requirements

The application MUST:
- Stay within 1Gi memory limit under normal load
- Request 512Mi memory (guaranteed allocation)
- Implement memory-efficient data structures
- Avoid memory leaks (use proper cleanup)

### CPU Requirements

The application MUST:
- Stay within 500m CPU limit under normal load
- Request 250m CPU (guaranteed allocation)
- Implement efficient algorithms
- Avoid CPU-intensive blocking operations

### Monitoring

The application SHOULD:
- Expose Prometheus metrics at `/metrics` (optional)
- Log resource usage periodically
- Implement request timeouts to prevent resource exhaustion

---

## Startup Contract

### Startup Time

The application MUST:
- Start and pass health checks within 30 seconds
- Initialize all dependencies during startup
- Fail fast if critical dependencies are unavailable

### Startup Sequence

1. Load environment variables
2. Validate configuration
3. Initialize logging
4. Connect to database
5. Connect to Kafka
6. Connect to Redis
7. Start HTTP server
8. Begin accepting requests

---

## Logging Contract

### Log Format

The application MUST:
- Write logs to stdout/stderr (captured by Kubernetes)
- Use structured logging (JSON format recommended)
- Include correlation IDs for request tracing
- Never log secrets or sensitive data

### Log Levels

- **DEBUG**: Detailed diagnostic information (disabled in production)
- **INFO**: General informational messages
- **WARNING**: Warning messages for recoverable issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical failures requiring immediate attention

### Example Log Entry

```json
{
  "timestamp": "2026-03-31T12:00:00Z",
  "level": "INFO",
  "message": "Processing webhook request",
  "correlation_id": "req-123456",
  "channel": "gmail",
  "customer_id": "cust-789"
}
```

---

## Error Handling Contract

### HTTP Error Responses

The application MUST return appropriate HTTP status codes:

- **200 OK**: Successful request
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Unexpected server error
- **503 Service Unavailable**: Service temporarily unavailable

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Missing required field: customer_email",
    "details": {
      "field": "customer_email",
      "reason": "required"
    }
  }
}
```

---

## Security Contract

### HMAC Signature Verification

The application MUST:
- Verify HMAC signatures on all webhook requests
- Use `WEBHOOK_SECRET` environment variable
- Reject requests with invalid signatures (401 Unauthorized)
- Log signature verification failures

### TLS/SSL

The application MUST:
- Support HTTPS connections (handled by Ingress)
- Not terminate TLS (handled by NGINX Ingress Controller)
- Trust cluster-internal certificates for service-to-service communication

---

## Compliance Checklist

Before deploying to Kubernetes, verify the application satisfies:

- [ ] Reads all required environment variables from ConfigMap and Secret
- [ ] Implements `/health` endpoint with <1s response time
- [ ] Handles SIGTERM for graceful shutdown (completes within 30s)
- [ ] Supports read-only root filesystem (writes only to mounted volumes)
- [ ] Runs as non-root user (UID 1000)
- [ ] Stays within resource limits (1Gi memory, 500m CPU)
- [ ] Starts and passes health checks within 30 seconds
- [ ] Writes logs to stdout/stderr in structured format
- [ ] Returns appropriate HTTP status codes
- [ ] Verifies HMAC signatures on webhook requests
- [ ] Never logs secrets or sensitive data

---

## Summary

This contract ensures the application is compatible with the Kubernetes deployment manifests. All requirements are mandatory for successful deployment and operation in the production environment.
