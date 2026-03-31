"""Redis-based rate limiter with sliding window algorithm."""

import time
from typing import Optional
from redis.asyncio import Redis


class RateLimiter:
    """Redis-based rate limiter using sliding window algorithm."""

    def __init__(
        self,
        redis_client: Redis,
        rate_limit: int = 10,
        window_seconds: int = 60
    ):
        """Initialize rate limiter.

        Args:
            redis_client: Async Redis client
            rate_limit: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.redis = redis_client
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds

    def _get_key(self, customer_id: str, channel: str) -> str:
        """Generate Redis key for customer and channel.

        Args:
            customer_id: Customer UUID
            channel: Channel name

        Returns:
            Redis key string
        """
        return f"rate_limit:{customer_id}:{channel}"

    async def check_rate_limit(
        self,
        customer_id: str,
        channel: str
    ) -> tuple[bool, int]:
        """Check if customer has exceeded rate limit.

        Args:
            customer_id: Customer UUID
            channel: Channel name

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        key = self._get_key(customer_id, channel)
        now = time.time()
        window_start = now - self.window_seconds

        # Use Redis pipeline for atomic operations
        async with self.redis.pipeline() as pipe:
            # Remove old entries outside the window
            await pipe.zremrangebyscore(key, 0, window_start)

            # Count entries in current window
            await pipe.zcard(key)

            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]

        # Check if limit exceeded
        is_allowed = current_count < self.rate_limit
        remaining = max(0, self.rate_limit - current_count - 1)

        return is_allowed, remaining

    async def record_request(
        self,
        customer_id: str,
        channel: str
    ) -> None:
        """Record a request in the rate limit window.

        Args:
            customer_id: Customer UUID
            channel: Channel name
        """
        key = self._get_key(customer_id, channel)
        now = time.time()

        # Add current request with timestamp as score
        await self.redis.zadd(key, {str(now): now})

        # Set TTL to window size + buffer
        await self.redis.expire(key, self.window_seconds + 10)

    async def get_retry_after(
        self,
        customer_id: str,
        channel: str
    ) -> Optional[int]:
        """Get seconds until rate limit resets.

        Args:
            customer_id: Customer UUID
            channel: Channel name

        Returns:
            Seconds until oldest request expires, or None if not rate limited
        """
        key = self._get_key(customer_id, channel)

        # Get oldest entry in window
        oldest_entries = await self.redis.zrange(key, 0, 0, withscores=True)

        if not oldest_entries:
            return None

        oldest_timestamp = oldest_entries[0][1]
        now = time.time()
        retry_after = int(oldest_timestamp + self.window_seconds - now)

        return max(1, retry_after)
