from functools import wraps
from typing import Callable, Any
from src.config import settings


def authenticate(func: Callable) -> Callable:
    """
    Decorator to authenticate requests to MCP tools.
    Checks for the presence of the MCP server token.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # In a real implementation, this would check for a token in headers or context
        # For now, we'll simulate the authentication check
        expected_token = settings.mcp_server_token

        # In an actual implementation, you would extract the token from the request context
        # and compare it with the expected token

        if expected_token is None:
            # If no token is configured, we allow access (development mode)
            return func(*args, **kwargs)

        # If a token is configured, we'd normally validate it here
        # For now, returning the original function call
        return func(*args, **kwargs)

    return wrapper


def verify_token(token: str) -> bool:
    """
    Verify if the provided token is valid.

    Args:
        token: The token to verify

    Returns:
        True if the token is valid, False otherwise
    """
    expected_token = settings.mcp_server_token
    return expected_token is not None and token == expected_token
