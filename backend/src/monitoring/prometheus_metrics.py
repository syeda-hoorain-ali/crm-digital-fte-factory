"""Prometheus metrics for monitoring webhook and system performance."""

import time
from typing import Optional
from functools import wraps

from prometheus_client import Counter, Histogram, Gauge, Info
import logging

logger = logging.getLogger(__name__)

# System info
system_info = Info('crm_system', 'CRM Digital FTE Factory system information')
system_info.info({
    'version': '1.0.0',
    'service': 'customer-support-api'
})

# Webhook metrics
webhook_requests_total = Counter(
    'webhook_requests_total',
    'Total number of webhook requests received',
    ['channel', 'status']
)

webhook_processing_duration_seconds = Histogram(
    'webhook_processing_duration_seconds',
    'Time spent processing webhook requests',
    ['channel'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

webhook_errors_total = Counter(
    'webhook_errors_total',
    'Total number of webhook processing errors',
    ['channel', 'error_type']
)

# Kafka metrics
kafka_messages_sent_total = Counter(
    'kafka_messages_sent_total',
    'Total number of messages sent to Kafka',
    ['topic', 'status']
)

kafka_send_duration_seconds = Histogram(
    'kafka_send_duration_seconds',
    'Time spent sending messages to Kafka',
    ['topic'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
)

kafka_consumer_lag = Gauge(
    'kafka_consumer_lag',
    'Current Kafka consumer lag',
    ['topic', 'partition', 'consumer_group']
)

# Rate limiting metrics
rate_limit_exceeded_total = Counter(
    'rate_limit_exceeded_total',
    'Total number of rate limit violations',
    ['channel', 'customer_id']
)

# Customer metrics
customers_created_total = Counter(
    'customers_created_total',
    'Total number of new customers created',
    ['channel']
)

conversations_created_total = Counter(
    'conversations_created_total',
    'Total number of conversations created',
    ['channel']
)

cross_channel_matches_total = Counter(
    'cross_channel_matches_total',
    'Total number of cross-channel customer matches',
    ['from_channel', 'to_channel']
)

# Database metrics
database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Time spent executing database queries',
    ['operation'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

database_connections_active = Gauge(
    'database_connections_active',
    'Number of active database connections'
)

# Redis metrics
redis_operations_total = Counter(
    'redis_operations_total',
    'Total number of Redis operations',
    ['operation', 'status']
)

redis_operation_duration_seconds = Histogram(
    'redis_operation_duration_seconds',
    'Time spent on Redis operations',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5]
)

# Health check metrics
health_check_status = Gauge(
    'health_check_status',
    'Health check status (1=healthy, 0=unhealthy)',
    ['component']
)

# Message processing metrics
message_processing_duration_seconds = Histogram(
    'message_processing_duration_seconds',
    'Time spent processing messages end-to-end',
    ['channel'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

attachment_processing_total = Counter(
    'attachment_processing_total',
    'Total number of attachments processed',
    ['channel', 'status']
)

attachment_size_bytes = Histogram(
    'attachment_size_bytes',
    'Size of processed attachments in bytes',
    ['channel'],
    buckets=[1024, 10240, 102400, 1048576, 5242880, 10485760]  # 1KB to 10MB
)


def track_webhook_request(channel: str):
    """Decorator to track webhook request metrics.

    Args:
        channel: Channel name (email, whatsapp, webform)

    Usage:
        @track_webhook_request('email')
        async def gmail_webhook(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'
            error_type = None

            try:
                result = await func(*args, **kwargs)
                webhook_requests_total.labels(channel=channel, status='success').inc()
                return result
            except Exception as e:
                status = 'error'
                error_type = type(e).__name__
                webhook_requests_total.labels(channel=channel, status='error').inc()
                webhook_errors_total.labels(channel=channel, error_type=error_type).inc()
                raise
            finally:
                duration = time.time() - start_time
                webhook_processing_duration_seconds.labels(channel=channel).observe(duration)

                logger.info(
                    f"Webhook request completed",
                    extra={
                        'channel': channel,
                        'status': status,
                        'duration_seconds': duration,
                        'error_type': error_type
                    }
                )

        return wrapper
    return decorator


def track_kafka_send(topic: str):
    """Decorator to track Kafka message send metrics.

    Args:
        topic: Kafka topic name
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'

            try:
                result = await func(*args, **kwargs)
                if result:
                    kafka_messages_sent_total.labels(topic=topic, status='success').inc()
                else:
                    kafka_messages_sent_total.labels(topic=topic, status='failed').inc()
                    status = 'failed'
                return result
            except Exception as e:
                kafka_messages_sent_total.labels(topic=topic, status='error').inc()
                status = 'error'
                raise
            finally:
                duration = time.time() - start_time
                kafka_send_duration_seconds.labels(topic=topic).observe(duration)

        return wrapper
    return decorator


def track_database_query(operation: str):
    """Decorator to track database query metrics.

    Args:
        operation: Operation name (select, insert, update, delete)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                database_query_duration_seconds.labels(operation=operation).observe(duration)

        return wrapper
    return decorator


def record_customer_created(channel: str):
    """Record a new customer creation.

    Args:
        channel: Channel where customer was created
    """
    customers_created_total.labels(channel=channel).inc()


def record_conversation_created(channel: str):
    """Record a new conversation creation.

    Args:
        channel: Channel where conversation was created
    """
    conversations_created_total.labels(channel=channel).inc()


def record_cross_channel_match(from_channel: str, to_channel: str):
    """Record a cross-channel customer match.

    Args:
        from_channel: Original channel
        to_channel: New channel where customer was recognized
    """
    cross_channel_matches_total.labels(
        from_channel=from_channel,
        to_channel=to_channel
    ).inc()


def record_rate_limit_exceeded(channel: str, customer_id: str):
    """Record a rate limit violation.

    Args:
        channel: Channel where rate limit was exceeded
        customer_id: Customer ID (hashed for privacy)
    """
    # Hash customer_id for privacy in metrics
    import hashlib
    hashed_id = hashlib.sha256(customer_id.encode()).hexdigest()[:8]
    rate_limit_exceeded_total.labels(
        channel=channel,
        customer_id=hashed_id
    ).inc()


def record_attachment_processed(channel: str, size_bytes: int, success: bool):
    """Record attachment processing.

    Args:
        channel: Channel where attachment was received
        size_bytes: Size of attachment in bytes
        success: Whether processing was successful
    """
    status = 'success' if success else 'failed'
    attachment_processing_total.labels(channel=channel, status=status).inc()
    if success:
        attachment_size_bytes.labels(channel=channel).observe(size_bytes)


def update_health_status(component: str, is_healthy: bool):
    """Update health check status for a component.

    Args:
        component: Component name (database, redis, kafka)
        is_healthy: Whether component is healthy
    """
    health_check_status.labels(component=component).set(1 if is_healthy else 0)


def update_kafka_lag(topic: str, partition: int, consumer_group: str, lag: int):
    """Update Kafka consumer lag metric.

    Args:
        topic: Kafka topic name
        partition: Partition number
        consumer_group: Consumer group name
        lag: Current lag value
    """
    kafka_consumer_lag.labels(
        topic=topic,
        partition=str(partition),
        consumer_group=consumer_group
    ).set(lag)
