"""Middleware for correlation ID tracking and structured logging."""

import uuid
import logging
import time
from typing import Callable, Awaitable

from fastapi import Request, Response
from starlette.types import ASGIApp, Scope, Receive, Send, Message

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware:
    """Pure ASGI middleware to add correlation IDs to requests for tracing."""

    def __init__(self, app: ASGIApp):
        """Initialize correlation ID middleware.

        Args:
            app: ASGI application
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process ASGI request and add correlation ID.

        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get or generate correlation ID from headers
        correlation_id = None
        for header_name, header_value in scope.get("headers", []):
            if header_name.lower() == b"x-correlation-id":
                correlation_id = header_value.decode("utf-8")
                break

        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in scope state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["correlation_id"] = correlation_id

        # Track request timing
        start_time = time.time()

        # Log request
        logger.info(
            "Request started",
            extra={
                'correlation_id': correlation_id,
                'method': scope.get("method"),
                'path': scope.get("path"),
                'client': scope.get("client"),
            }
        )

        # Wrap send to add correlation ID header to response
        async def send_with_correlation_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-correlation-id", correlation_id.encode("utf-8")))
                message["headers"] = headers

                # Calculate duration
                duration = time.time() - start_time

                # Log response
                logger.info(
                    "Request completed",
                    extra={
                        'correlation_id': correlation_id,
                        'method': scope.get("method"),
                        'path': scope.get("path"),
                        'status_code': message.get("status"),
                        'duration_seconds': duration
                    }
                )

            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation_id)
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            logger.error(
                "Request failed",
                extra={
                    'correlation_id': correlation_id,
                    'method': scope.get("method"),
                    'path': scope.get("path"),
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'duration_seconds': duration
                },
                exc_info=True
            )

            raise


class StructuredLoggingFilter(logging.Filter):
    """Logging filter to add structured fields to all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add structured fields to log record.

        Args:
            record: Log record to enhance

        Returns:
            True to allow record to be logged
        """
        # Ensure extra dict exists
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = None

        if not hasattr(record, 'service'):
            record.service = 'customer-support-api'

        if not hasattr(record, 'environment'):
            import os
            record.environment = os.getenv('ENVIRONMENT', 'development')

        return True


def configure_structured_logging():
    """Configure structured logging for the application."""
    # Add structured logging filter to root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(StructuredLoggingFilter())

    # Configure JSON formatter for production
    import os
    if os.getenv('ENVIRONMENT') == 'production':
        try:
            import json_log_formatter

            formatter = json_log_formatter.JSONFormatter()

            # Update all handlers
            for handler in root_logger.handlers:
                handler.setFormatter(formatter)

            logger.info("Structured JSON logging configured")
        except ImportError:
            logger.warning("json-log-formatter not installed, using standard logging")


def get_correlation_id(request: Request) -> str:
    """Get correlation ID from request.

    Args:
        request: FastAPI request object

    Returns:
        Correlation ID string
    """
    if hasattr(request.state, 'correlation_id'):
        return request.state.correlation_id
    return 'unknown'


def log_with_correlation(
    logger_instance: logging.Logger,
    level: str,
    message: str,
    correlation_id: str,
    **extra_fields
):
    """Log message with correlation ID and extra fields.

    Args:
        logger_instance: Logger to use
        level: Log level (info, warning, error, etc.)
        message: Log message
        correlation_id: Correlation ID for request tracing
        **extra_fields: Additional structured fields
    """
    extra = {
        'correlation_id': correlation_id,
        **extra_fields
    }

    log_method = getattr(logger_instance, level.lower())
    log_method(message, extra=extra)
