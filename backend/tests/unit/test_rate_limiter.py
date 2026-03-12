"""Unit tests for rate limiter."""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from redis.asyncio import Redis

from src.utils.rate_limiter import RateLimiter


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock(spec=Redis)
    redis.pipeline = MagicMock()
    return redis


@pytest.fixture
def rate_limiter(mock_redis):
    """Create rate limiter with mock Redis."""
    return RateLimiter(mock_redis, rate_limit=10, window_seconds=60)


class TestRateLimiter:
    """Test suite for Redis-based rate limiter."""

    def test_get_key(self, rate_limiter):
        """Test Redis key generation."""
        customer_id = "customer-123"
        channel = "email"

        key = rate_limiter._get_key(customer_id, channel)

        assert key == "rate_limit:customer-123:email"

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, rate_limiter, mock_redis):
        """Test rate limit check when under limit."""
        customer_id = "customer-123"
        channel = "email"

        # Mock pipeline execution
        pipeline_mock = AsyncMock()
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[None, 5])  # 5 requests in window
        pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
        pipeline_mock.__aexit__ = AsyncMock()

        mock_redis.pipeline.return_value = pipeline_mock

        is_allowed, remaining = await rate_limiter.check_rate_limit(customer_id, channel)

        assert is_allowed is True
        assert remaining == 4  # 10 - 5 - 1

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, rate_limiter, mock_redis):
        """Test rate limit check when limit exceeded."""
        customer_id = "customer-123"
        channel = "email"

        # Mock pipeline execution
        pipeline_mock = AsyncMock()
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[None, 10])  # 10 requests (at limit)
        pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
        pipeline_mock.__aexit__ = AsyncMock()

        mock_redis.pipeline.return_value = pipeline_mock

        is_allowed, remaining = await rate_limiter.check_rate_limit(customer_id, channel)

        assert is_allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_at_limit(self, rate_limiter, mock_redis):
        """Test rate limit check when exactly at limit."""
        customer_id = "customer-123"
        channel = "email"

        # Mock pipeline execution
        pipeline_mock = AsyncMock()
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[None, 9])  # 9 requests
        pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
        pipeline_mock.__aexit__ = AsyncMock()

        mock_redis.pipeline.return_value = pipeline_mock

        is_allowed, remaining = await rate_limiter.check_rate_limit(customer_id, channel)

        assert is_allowed is True
        assert remaining == 0  # Last allowed request

    @pytest.mark.asyncio
    async def test_record_request(self, rate_limiter, mock_redis):
        """Test recording a request."""
        customer_id = "customer-123"
        channel = "email"

        await rate_limiter.record_request(customer_id, channel)

        # Verify zadd was called
        mock_redis.zadd.assert_called_once()

        # Verify expire was called
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_retry_after_with_entries(self, rate_limiter, mock_redis):
        """Test getting retry-after time when rate limited."""
        customer_id = "customer-123"
        channel = "email"

        # Mock oldest entry timestamp (50 seconds ago)
        now = time.time()
        oldest_timestamp = now - 50
        mock_redis.zrange.return_value = [(b"entry", oldest_timestamp)]

        retry_after = await rate_limiter.get_retry_after(customer_id, channel)

        # Should be approximately 10 seconds (60 - 50)
        assert retry_after >= 1
        assert retry_after <= 11

    @pytest.mark.asyncio
    async def test_get_retry_after_no_entries(self, rate_limiter, mock_redis):
        """Test getting retry-after time when no entries."""
        customer_id = "customer-123"
        channel = "email"

        mock_redis.zrange.return_value = []

        retry_after = await rate_limiter.get_retry_after(customer_id, channel)

        assert retry_after is None

    @pytest.mark.asyncio
    async def test_sliding_window_behavior(self, rate_limiter, mock_redis):
        """Test sliding window removes old entries."""
        customer_id = "customer-123"
        channel = "email"

        # Mock pipeline execution
        pipeline_mock = AsyncMock()
        pipeline_mock.zremrangebyscore = AsyncMock()
        pipeline_mock.zcard = AsyncMock()
        pipeline_mock.execute = AsyncMock(return_value=[None, 3])
        pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
        pipeline_mock.__aexit__ = AsyncMock()

        mock_redis.pipeline.return_value = pipeline_mock

        await rate_limiter.check_rate_limit(customer_id, channel)

        # Verify zremrangebyscore was called to remove old entries
        pipeline_mock.zremrangebyscore.assert_called_once()

    def test_custom_rate_limit(self, mock_redis):
        """Test rate limiter with custom limits."""
        limiter = RateLimiter(mock_redis, rate_limit=5, window_seconds=30)

        assert limiter.rate_limit == 5
        assert limiter.window_seconds == 30
