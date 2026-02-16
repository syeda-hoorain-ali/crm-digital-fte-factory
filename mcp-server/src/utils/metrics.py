import time
from collections import defaultdict
from typing import Dict, Any, List
from datetime import datetime, timezone


class MetricsCollector:
    """
    Collects metrics about MCP server operations.
    """
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.tool_usage: Dict[str, int] = defaultdict(int)
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        self.start_time = time.time()

    def increment_request(self):
        """Increment the total request counter."""
        self.request_count += 1

    def increment_error(self):
        """Increment the error counter."""
        self.error_count += 1

    def record_tool_usage(self, tool_name: str):
        """Record usage of a specific tool."""
        self.tool_usage[tool_name] += 1

    def record_response_time(self, tool_name: str, duration: float):
        """Record the response time for a specific tool."""
        self.response_times[tool_name].append(duration)

    def get_metrics(self) -> Dict[str, Any]:
        """Get the current metrics."""
        uptime = time.time() - self.start_time

        # Calculate average response times
        avg_response_times = {}
        for tool, times in self.response_times.items():
            if times:
                avg_response_times[tool] = sum(times) / len(times)
            else:
                avg_response_times[tool] = 0.0

        return {
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / max(1, self.request_count),
            "tool_usage": dict(self.tool_usage),
            "average_response_times": avg_response_times,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()


def get_metrics() -> Dict[str, Any]:
    """
    Get the current metrics from the global collector.

    Returns:
        Dictionary containing current metrics
    """
    return metrics_collector.get_metrics()


def reset_metrics():
    """
    Reset all metrics to their initial state. This is primarily for testing purposes.
    """
    metrics_collector.request_count = 0
    metrics_collector.error_count = 0
    metrics_collector.tool_usage.clear()
    metrics_collector.response_times.clear()
    metrics_collector.start_time = time.time()
