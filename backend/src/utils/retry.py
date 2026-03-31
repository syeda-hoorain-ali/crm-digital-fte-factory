"""Exponential backoff retry decorator using tenacity."""

import logging
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)

logger = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    retry_exceptions: tuple = (ConnectionError, TimeoutError)
):
    """Decorator for exponential backoff retry logic.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        backoff_multiplier: Backoff multiplier (default: 2.0)
        retry_exceptions: Tuple of exceptions to retry on

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(max_attempts=3, initial_delay=1.0, backoff_multiplier=2.0)
        async def send_email(to: str, body: str):
            # This will retry up to 3 times with delays: 1s, 2s, 4s
            await email_client.send(to, body)
    """
    def decorator(func):
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=backoff_multiplier,
                min=initial_delay,
                max=60  # Cap at 60 seconds
            ),
            retry=retry_if_exception_type(retry_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except RetryError as e:
                logger.error(
                    f"All retry attempts failed for {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "max_attempts": max_attempts,
                        "error": str(e.last_attempt.exception())
                    },
                    exc_info=True
                )
                raise e.last_attempt.exception()

        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=backoff_multiplier,
                min=initial_delay,
                max=60
            ),
            retry=retry_if_exception_type(retry_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except RetryError as e:
                logger.error(
                    f"All retry attempts failed for {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "max_attempts": max_attempts,
                        "error": str(e.last_attempt.exception())
                    },
                    exc_info=True
                )
                raise e.last_attempt.exception()

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
