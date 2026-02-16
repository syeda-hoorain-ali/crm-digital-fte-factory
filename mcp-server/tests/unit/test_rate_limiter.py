import time
from src.utils.rate_limiter import RateLimiter, check_rate_limit


def test_rate_limiter_initial_state():
    """Test that rate limiter starts in an allowed state."""
    limiter = RateLimiter()
    result = limiter.is_allowed("client_1")
    assert result is True  # First request should be allowed


def test_rate_limiter_within_limit():
    """Test that requests are allowed within the rate limit."""
    limiter = RateLimiter()

    # Set limits to a small number for testing
    limiter.limit = 3
    limiter.window = 1  # 1 second window

    # First 3 requests should be allowed
    assert limiter.is_allowed("client_1") is True
    assert limiter.is_allowed("client_1") is True
    assert limiter.is_allowed("client_1") is True

    # 4th request should be denied
    assert limiter.is_allowed("client_1") is False


def test_rate_limiter_different_clients():
    """Test that rate limiting works independently for different clients."""
    limiter = RateLimiter()

    # Set limits to a small number for testing
    limiter.limit = 2
    limiter.window = 1  # 1 second window

    # Client 1 - 2 requests allowed
    assert limiter.is_allowed("client_1") is True
    assert limiter.is_allowed("client_1") is True
    assert limiter.is_allowed("client_1") is False  # 3rd request denied

    # Client 2 - should still be allowed since it's different client
    assert limiter.is_allowed("client_2") is True
    assert limiter.is_allowed("client_2") is True
    assert limiter.is_allowed("client_2") is False  # 3rd request denied


def test_rate_limiter_expiration():
    """Test that requests expire from the rate limiter after the window."""
    limiter = RateLimiter()

    # Set limits for testing
    limiter.limit = 2
    limiter.window = 0.1  # 0.1 second window for testing

    # Use up the limit
    assert limiter.is_allowed("client_1") is True
    assert limiter.is_allowed("client_1") is True
    assert limiter.is_allowed("client_1") is False  # Should be denied

    # Wait for the window to pass
    time.sleep(0.15)  # Sleep longer than window

    # Now should be allowed again
    assert limiter.is_allowed("client_1") is True


def test_global_rate_limiter_instance():
    """Test the global rate limiter instance."""
    # First, check it allows initial requests
    assert check_rate_limit("global_client_1") is True
    assert check_rate_limit("global_client_1") is True

    # Set limits for test
    from src.utils.rate_limiter import rate_limiter
    original_limit = rate_limiter.limit
    original_window = rate_limiter.window

    rate_limiter.limit = 1
    rate_limiter.window = 1

    # Use up the limit
    result1 = check_rate_limit("global_client_2")
    result2 = check_rate_limit("global_client_2")

    # Restore original values
    rate_limiter.limit = original_limit
    rate_limiter.window = original_window

    assert result1 is True  # First should pass
    assert result2 is False  # Second should fail


def test_rate_limiter_timing():
    """Test rate limiting behavior with timing."""
    limiter = RateLimiter()

    # Set a very short window for testing
    limiter.limit = 1
    limiter.window = 0.05  # 50ms window

    # First request should be allowed
    assert limiter.is_allowed("timing_client") is True

    # Second request immediately after should be denied
    assert limiter.is_allowed("timing_client") is False

    # Wait for window to pass
    time.sleep(0.06)  # Sleep longer than window

    # Now should be allowed again
    assert limiter.is_allowed("timing_client") is True
