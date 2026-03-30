# Performance Testing Guide: Multi-Channel Customer Intake

**Feature**: 006-channel-integrations
**Date**: 2026-03-31
**Target**: 1,000 concurrent requests without degradation

---

## Performance Requirements

### Target Metrics

- **Throughput**: 1,000 concurrent requests
- **Response Time**: p95 < 500ms, p99 < 1000ms
- **Error Rate**: < 0.1%
- **CPU Usage**: < 80% under load
- **Memory Usage**: < 2GB per service
- **Database Connections**: < 100 concurrent

---

## Load Testing Setup

### Prerequisites

```bash
# Install Locust for load testing
pip install locust

# Install monitoring tools
pip install psutil prometheus-client
```

### Locust Test Script

Create `backend/tests/performance/locustfile.py`:

```python
"""Load testing script for multi-channel customer intake."""

from locust import HttpUser, task, between
import random
import uuid


class WebFormUser(HttpUser):
    """Simulates web form submissions."""

    wait_time = between(1, 3)

    @task(3)
    def submit_support_request(self):
        """Submit a support request via web form."""
        payload = {
            "name": f"Test User {uuid.uuid4().hex[:8]}",
            "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
            "subject": "Performance test submission",
            "category": random.choice(["technical", "billing", "general"]),
            "priority": random.choice(["low", "medium", "high"]),
            "message": "This is a performance test message. " * 10
        }

        with self.client.post(
            "/support/submit",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # Rate limited - expected behavior
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)
    def health_check(self):
        """Check health endpoint."""
        self.client.get("/health")


class GmailWebhookUser(HttpUser):
    """Simulates Gmail webhook requests."""

    wait_time = between(2, 5)

    @task
    def gmail_webhook(self):
        """Simulate Gmail Pub/Sub webhook."""
        import hmac
        import hashlib
        import json

        payload = {
            "message": {
                "data": "test_message_data",
                "messageId": str(uuid.uuid4()),
                "publishTime": "2026-03-31T00:00:00Z"
            }
        }

        payload_bytes = json.dumps(payload).encode()

        # Generate HMAC signature (use actual secret in real tests)
        secret = "test_webhook_secret"
        signature = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        with self.client.post(
            "/webhooks/gmail",
            json=payload,
            headers={"X-Signature": signature},
            catch_response=True
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


class WhatsAppWebhookUser(HttpUser):
    """Simulates WhatsApp webhook requests."""

    wait_time = between(1, 4)

    @task
    def whatsapp_webhook(self):
        """Simulate Twilio WhatsApp webhook."""
        payload = {
            "From": f"whatsapp:+1234567{random.randint(1000, 9999)}",
            "To": "whatsapp:+14155238886",
            "Body": "Performance test message",
            "MessageSid": f"SM{uuid.uuid4().hex[:32]}"
        }

        with self.client.post(
            "/webhooks/whatsapp",
            data=payload,
            catch_response=True
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
```

---

## Running Performance Tests

### 1. Local Performance Test

```bash
cd backend/tests/performance

# Start with 10 users, ramp up to 100
locust -f locustfile.py --host=http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 5m

# View results at http://localhost:8089
```

### 2. Staged Load Test

```bash
# Stage 1: Baseline (100 users)
locust -f locustfile.py --host=http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 5m \
  --html reports/stage1_100users.html

# Stage 2: Target Load (500 users)
locust -f locustfile.py --host=http://localhost:8000 \
  --users 500 --spawn-rate 50 --run-time 10m \
  --html reports/stage2_500users.html

# Stage 3: Peak Load (1000 users)
locust -f locustfile.py --host=http://localhost:8000 \
  --users 1000 --spawn-rate 100 --run-time 15m \
  --html reports/stage3_1000users.html

# Stage 4: Stress Test (2000 users)
locust -f locustfile.py --host=http://localhost:8000 \
  --users 2000 --spawn-rate 100 --run-time 10m \
  --html reports/stage4_2000users.html
```

### 3. Specific Endpoint Tests

```bash
# Test web form endpoint only
locust -f locustfile.py --host=http://localhost:8000 \
  WebFormUser --users 1000 --spawn-rate 100 --run-time 10m

# Test Gmail webhook only
locust -f locustfile.py --host=http://localhost:8000 \
  GmailWebhookUser --users 500 --spawn-rate 50 --run-time 10m

# Test WhatsApp webhook only
locust -f locustfile.py --host=http://localhost:8000 \
  WhatsAppWebhookUser --users 500 --spawn-rate 50 --run-time 10m
```

---

## Monitoring During Tests

### 1. Application Metrics

```bash
# Monitor Prometheus metrics
curl http://localhost:8000/metrics

# Key metrics to watch:
# - http_request_duration_seconds
# - http_requests_total
# - kafka_messages_produced_total
# - redis_operations_total
```

### 2. System Resources

```bash
# Monitor CPU and memory
htop

# Monitor network
iftop

# Monitor disk I/O
iotop
```

### 3. Database Performance

```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check slow queries
SELECT pid, now() - query_start as duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;

-- Check table sizes
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 4. Kafka Performance

```bash
# Check consumer lag
docker exec -it kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group fte-message-processor

# Monitor topic throughput
docker exec -it kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic customer-intake.email.inbound
```

### 5. Redis Performance

```bash
# Monitor Redis stats
redis-cli INFO stats

# Monitor slow commands
redis-cli SLOWLOG GET 10

# Monitor memory usage
redis-cli INFO memory
```

---

## Performance Optimization Checklist

### Application Level

- [ ] Enable connection pooling (database, Redis, Kafka)
- [ ] Implement caching for frequently accessed data
- [ ] Use async/await for I/O operations
- [ ] Batch database operations where possible
- [ ] Optimize database queries (add indexes)
- [ ] Enable gzip compression for API responses
- [ ] Implement request coalescing for duplicate requests

### Database Level

- [ ] Add indexes on frequently queried columns
- [ ] Enable query result caching
- [ ] Optimize connection pool size
- [ ] Use read replicas for read-heavy operations
- [ ] Implement database connection pooling (PgBouncer)
- [ ] Partition large tables by date

### Infrastructure Level

- [ ] Use CDN for static assets
- [ ] Enable HTTP/2
- [ ] Implement load balancing (multiple backend instances)
- [ ] Use Redis cluster for high availability
- [ ] Use Kafka cluster with multiple brokers
- [ ] Enable auto-scaling based on CPU/memory

### Code Optimizations

```python
# Example: Batch database inserts
async def batch_insert_messages(session, messages):
    """Insert multiple messages in one transaction."""
    session.add_all(messages)
    await session.commit()

# Example: Connection pooling
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

# Example: Redis connection pooling
redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50
)
redis_client = redis.Redis(connection_pool=redis_pool)
```

---

## Expected Results

### Baseline Performance (No Load)

- Response time: p50 < 50ms, p95 < 100ms, p99 < 200ms
- Throughput: 100 req/s
- Error rate: 0%
- CPU: < 10%
- Memory: < 500MB

### Target Load (1000 Concurrent Users)

- Response time: p50 < 200ms, p95 < 500ms, p99 < 1000ms
- Throughput: 500-1000 req/s
- Error rate: < 0.1%
- CPU: 60-80%
- Memory: 1-2GB
- Database connections: 50-100

### Stress Test (2000 Concurrent Users)

- Response time: p50 < 500ms, p95 < 1500ms, p99 < 3000ms
- Throughput: 800-1500 req/s
- Error rate: < 1%
- CPU: 80-95%
- Memory: 2-3GB
- Some rate limiting expected (429 responses)

---

## Bottleneck Analysis

### Common Bottlenecks

1. **Database Connection Pool Exhaustion**
   - Symptom: Timeouts, "too many connections" errors
   - Solution: Increase pool size, use PgBouncer

2. **Redis Memory Limit**
   - Symptom: Evictions, slow rate limit checks
   - Solution: Increase Redis memory, use Redis cluster

3. **Kafka Producer Backpressure**
   - Symptom: Slow message publishing, timeouts
   - Solution: Increase batch size, add more brokers

4. **CPU Saturation**
   - Symptom: High response times, request queuing
   - Solution: Scale horizontally, optimize hot paths

5. **Network Bandwidth**
   - Symptom: Slow data transfer, timeouts
   - Solution: Optimize payload sizes, use compression

---

## Performance Testing Report Template

```markdown
# Performance Test Report

**Date**: YYYY-MM-DD
**Test Duration**: X minutes
**Peak Concurrent Users**: X
**Total Requests**: X

## Results Summary

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| p50 Response Time | < 200ms | Xms | ✅/❌ |
| p95 Response Time | < 500ms | Xms | ✅/❌ |
| p99 Response Time | < 1000ms | Xms | ✅/❌ |
| Throughput | 500+ req/s | X req/s | ✅/❌ |
| Error Rate | < 0.1% | X% | ✅/❌ |
| CPU Usage | < 80% | X% | ✅/❌ |
| Memory Usage | < 2GB | XGB | ✅/❌ |

## Bottlenecks Identified

1. [Description of bottleneck]
   - Impact: [High/Medium/Low]
   - Recommendation: [How to fix]

## Recommendations

1. [Action item 1]
2. [Action item 2]

## Next Steps

- [ ] Implement optimizations
- [ ] Re-run tests
- [ ] Update capacity planning
```

---

## Continuous Performance Monitoring

### Production Monitoring

```yaml
# Prometheus alerts for performance degradation
groups:
  - name: performance
    rules:
      - alert: HighResponseTime
        expr: http_request_duration_seconds{quantile="0.95"} > 0.5
        for: 5m
        annotations:
          summary: "High response time detected"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighCPUUsage
        expr: process_cpu_seconds_total > 0.8
        for: 10m
        annotations:
          summary: "High CPU usage detected"
```

### Regular Performance Tests

- Run load tests weekly in staging environment
- Run stress tests before major releases
- Monitor production metrics continuously
- Set up automated performance regression tests

---

## Conclusion

This performance testing guide provides a framework for validating that the multi-channel customer intake system can handle 1,000 concurrent requests without degradation. Regular performance testing and monitoring ensure the system maintains acceptable performance as it scales.

**Next Steps**:
1. Set up Locust in CI/CD pipeline
2. Run baseline performance tests
3. Implement identified optimizations
4. Re-test and validate improvements
5. Document production capacity planning