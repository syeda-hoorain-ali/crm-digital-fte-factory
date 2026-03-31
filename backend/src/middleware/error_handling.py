"""Comprehensive error handling for webhook endpoints."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from aiokafka.errors import KafkaError
from redis.exceptions import RedisError

from ..database.models import WebhookDeliveryLog, WebhookProcessingStatus

logger = logging.getLogger(__name__)


class WebhookError(Exception):
    """Base exception for webhook processing errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "WEBHOOK_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize webhook error.

        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Application-specific error code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class SignatureVerificationError(WebhookError):
    """Exception for webhook signature verification failures."""

    def __init__(self, message: str = "Invalid webhook signature"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="INVALID_SIGNATURE"
        )


class RateLimitError(WebhookError):
    """Exception for rate limit violations."""

    def __init__(self, retry_after: int, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after}
        )


class PayloadValidationError(WebhookError):
    """Exception for invalid webhook payloads."""

    def __init__(self, message: str, missing_fields: Optional[list] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="INVALID_PAYLOAD",
            details={"missing_fields": missing_fields or []}
        )


class MessageProcessingError(WebhookError):
    """Exception for message processing failures."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        details = {}
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(
            message=message,
            status_code=500,
            error_code="PROCESSING_ERROR",
            details=details
        )


async def handle_webhook_error(
    error: Exception,
    request: Request,
    webhook_log: Optional[WebhookDeliveryLog] = None,
    session = None
) -> JSONResponse:
    """Handle webhook processing errors with proper logging and response.

    Args:
        error: Exception that occurred
        request: FastAPI request object
        webhook_log: Optional webhook delivery log to update
        session: Optional database session for updating log

    Returns:
        JSONResponse with error details
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')

    # Determine error details
    if isinstance(error, WebhookError):
        status_code = error.status_code
        error_code = error.error_code
        message = error.message
        details = error.details
    elif isinstance(error, HTTPException):
        status_code = error.status_code
        error_code = "HTTP_ERROR"
        message = error.detail
        details = {}
    elif isinstance(error, SQLAlchemyError):
        status_code = 500
        error_code = "DATABASE_ERROR"
        message = "Database operation failed"
        details = {"error": str(error)}
    elif isinstance(error, KafkaError):
        status_code = 500
        error_code = "KAFKA_ERROR"
        message = "Message routing failed"
        details = {"error": str(error)}
    elif isinstance(error, RedisError):
        status_code = 500
        error_code = "REDIS_ERROR"
        message = "Cache operation failed"
        details = {"error": str(error)}
    else:
        status_code = 500
        error_code = "INTERNAL_ERROR"
        message = "An unexpected error occurred"
        details = {"error": str(error), "type": type(error).__name__}

    # Log error with correlation ID
    logger.error(
        f"Webhook error: {message}",
        extra={
            'correlation_id': correlation_id,
            'error_code': error_code,
            'status_code': status_code,
            'path': request.url.path,
            'method': request.method,
            'details': details
        },
        exc_info=True
    )

    # Update webhook log if provided
    if webhook_log and session:
        try:
            webhook_log.processing_status = WebhookProcessingStatus.FAILED
            webhook_log.error_message = f"{error_code}: {message}"
            webhook_log.completed_at = datetime.now(timezone.utc)
            session.add(webhook_log)
            await session.commit()
        except Exception as log_error:
            logger.error(
                f"Failed to update webhook log: {log_error}",
                extra={'correlation_id': correlation_id}
            )

    # Build error response
    error_response = {
        "error": {
            "code": error_code,
            "message": message,
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

    # Add details if present
    if details:
        error_response["error"]["details"] = details

    # Add retry_after header for rate limits
    headers = {}
    if isinstance(error, RateLimitError) and "retry_after" in details:
        headers["Retry-After"] = str(details["retry_after"])

    return JSONResponse(
        status_code=status_code,
        content=error_response,
        headers=headers
    )


def validate_webhook_payload(
    payload: dict,
    required_fields: list[str],
    channel: str
) -> None:
    """Validate webhook payload has required fields.

    Args:
        payload: Webhook payload dictionary
        required_fields: List of required field names
        channel: Channel name for error messages

    Raises:
        PayloadValidationError: If validation fails
    """
    missing_fields = [
        field for field in required_fields
        if not payload.get(field)
    ]

    if missing_fields:
        raise PayloadValidationError(
            message=f"Missing required fields in {channel} webhook payload",
            missing_fields=missing_fields
        )


async def with_error_handling(
    func,
    request: Request,
    webhook_log: Optional[WebhookDeliveryLog] = None,
    session = None
):
    """Wrapper to add error handling to webhook functions.

    Args:
        func: Async function to execute
        request: FastAPI request object
        webhook_log: Optional webhook delivery log
        session: Optional database session

    Returns:
        Function result or error response
    """
    try:
        return await func()
    except Exception as e:
        return await handle_webhook_error(e, request, webhook_log, session)


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to wait before trying again
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open

    def record_success(self):
        """Record successful call."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )

    def can_attempt(self) -> bool:
        """Check if call can be attempted.

        Returns:
            True if call should be attempted
        """
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout_seconds:
                    self.state = "half_open"
                    logger.info("Circuit breaker entering half-open state")
                    return True

            return False

        # half_open state - allow one attempt
        return True
