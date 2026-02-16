from src.utils.security import authenticate, verify_token
from src.config import settings


def test_verify_token_with_none():
    """Test token verification when no token is set."""
    # Store original value
    original_token = settings.mcp_server_token

    # Set token to None (simulate dev mode)
    settings.mcp_server_token = None

    result = verify_token("any_token")
    assert result is False  # Should return False when no expected token is set

    # Restore original value
    settings.mcp_server_token = original_token


def test_verify_token_matching():
    """Test token verification with matching tokens."""
    # Store original value
    original_token = settings.mcp_server_token

    # Set a token for testing
    test_token = "test_secret_token"
    settings.mcp_server_token = test_token

    # Test with correct token
    result = verify_token(test_token)
    assert result is True  # Should return True when tokens match

    # Restore original value
    settings.mcp_server_token = original_token


def test_verify_token_not_matching():
    """Test token verification with non-matching tokens."""
    # Store original value
    original_token = settings.mcp_server_token

    # Set a token for testing
    test_token = "test_secret_token"
    settings.mcp_server_token = test_token

    # Test with wrong token
    result = verify_token("wrong_token")
    assert result is False  # Should return False when tokens don't match

    # Restore original value
    settings.mcp_server_token = original_token


def test_authenticate_decorator_basic():
    """Test that the authenticate decorator doesn't break function behavior."""
    def sample_function(x, y):
        return x + y

    decorated_func = authenticate(sample_function)
    result = decorated_func(2, 3)
    assert result == 5  # Function should still work normally
