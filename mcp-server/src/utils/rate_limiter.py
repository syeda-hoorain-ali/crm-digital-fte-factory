import time
from collections import defaultdict, deque
from typing import Dict
from src.config import settings


class RateLimiter:
    """
    Simple rate limiter that tracks requests by IP or client ID.
    """
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.limit: int = settings.rate_limit_requests
        self.window: float = settings.rate_limit_window

    def is_allowed(self, client_id: str) -> bool:
        """
        Check if a client is allowed to make a request.

        Args:
            client_id: The ID of the client making the request

        Returns:
            True if the request is allowed, False otherwise
        """
        now = time.time()
        client_requests = self.requests[client_id]

        # Remove requests that are outside the time window
        while client_requests and now - client_requests[0] > self.window:
            client_requests.popleft()

        # Check if the client has exceeded the rate limit
        if len(client_requests) >= self.limit:
            return False

        # Add the current request
        client_requests.append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit(client_id: str) -> bool:
    """
    Check if a client is within the rate limit.

    Args:
        client_id: The ID of the client

    Returns:
        True if the client is within rate limit, False otherwise
    """
    return rate_limiter.is_allowed(client_id)
