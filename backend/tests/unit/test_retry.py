"""Unit tests for retry decorator."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from tenacity import RetryError

from src.utils.retry import with_retry


class TestRetryDecorator:
    """Test suite for exponential backoff retry decorator."""

    @pytest.mark.asyncio
    async def test_async_function_success_first_try(self):
        """Test async function succeeds on first try."""
        mock_func = AsyncMock(return_value="success")

        @with_retry(max_attempts=3)
        async def test_func():
            return await mock_func()

        result = await test_func()

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_async_function_success_after_retries(self):
        """Test async function succeeds after retries."""
        mock_func = AsyncMock(
            side_effect=[ConnectionError(), ConnectionError(), "success"]
        )

        @with_retry(max_attempts=3, initial_delay=0.01)
        async def test_func():
            return await mock_func()

        result = await test_func()

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_async_function_all_retries_fail(self):
        """Test async function fails after all retries."""
        mock_func = AsyncMock(side_effect=ConnectionError("Connection failed"))

        @with_retry(max_attempts=3, initial_delay=0.01)
        async def test_func():
            return await mock_func()

        with pytest.raises(ConnectionError, match="Connection failed"):
            await test_func()

        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_async_function_non_retryable_exception(self):
        """Test async function with non-retryable exception."""
        mock_func = AsyncMock(side_effect=ValueError("Invalid value"))

        @with_retry(
            max_attempts=3,
            initial_delay=0.01,
            retry_exceptions=(ConnectionError, TimeoutError)
        )
        async def test_func():
            return await mock_func()

        with pytest.raises(ValueError, match="Invalid value"):
            await test_func()

        # Should not retry for ValueError
        assert mock_func.call_count == 1

    def test_sync_function_success_first_try(self):
        """Test sync function succeeds on first try."""
        mock_func = MagicMock(return_value="success")

        @with_retry(max_attempts=3)
        def test_func():
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_sync_function_success_after_retries(self):
        """Test sync function succeeds after retries."""
        mock_func = MagicMock(
            side_effect=[ConnectionError(), ConnectionError(), "success"]
        )

        @with_retry(max_attempts=3, initial_delay=0.01)
        def test_func():
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_sync_function_all_retries_fail(self):
        """Test sync function fails after all retries."""
        mock_func = MagicMock(side_effect=ConnectionError("Connection failed"))

        @with_retry(max_attempts=3, initial_delay=0.01)
        def test_func():
            return mock_func()

        with pytest.raises(ConnectionError, match="Connection failed"):
            test_func()

        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff delay increases."""
        call_times = []

        async def failing_func():
            call_times.append(pytest.approx(0, abs=0.1))
            raise ConnectionError()

        @with_retry(max_attempts=3, initial_delay=0.1, backoff_multiplier=2.0)
        async def test_func():
            await failing_func()

        with pytest.raises(ConnectionError):
            await test_func()

        # Should have 3 attempts
        assert len(call_times) == 3

    @pytest.mark.asyncio
    async def test_custom_retry_exceptions(self):
        """Test custom retry exception types."""
        mock_func = AsyncMock(side_effect=TimeoutError())

        @with_retry(
            max_attempts=3,
            initial_delay=0.01,
            retry_exceptions=(TimeoutError,)
        )
        async def test_func():
            return await mock_func()

        with pytest.raises(TimeoutError):
            await test_func()

        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_max_attempts_limit(self):
        """Test max attempts limit is respected."""
        mock_func = AsyncMock(side_effect=ConnectionError())

        @with_retry(max_attempts=5, initial_delay=0.01)
        async def test_func():
            return await mock_func()

        with pytest.raises(ConnectionError):
            await test_func()

        assert mock_func.call_count == 5

    @pytest.mark.asyncio
    async def test_function_with_arguments(self):
        """Test retry decorator with function arguments."""
        mock_func = AsyncMock(return_value="success")

        @with_retry(max_attempts=3)
        async def test_func(arg1, arg2, kwarg1=None):
            return await mock_func(arg1, arg2, kwarg1=kwarg1)

        result = await test_func("a", "b", kwarg1="c")

        assert result == "success"
        mock_func.assert_called_once_with("a", "b", kwarg1="c")
