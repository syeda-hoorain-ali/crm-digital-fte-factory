from src.utils.metrics import metrics_collector, get_metrics, reset_metrics


def test_initial_metrics():
    """Test that initial metrics are as expected."""
    reset_metrics()  # Reset metrics before the test
    metrics = get_metrics()

    assert "uptime_seconds" in metrics
    assert "total_requests" in metrics
    assert "total_errors" in metrics
    assert "error_rate" in metrics
    assert "tool_usage" in metrics
    assert "average_response_times" in metrics
    assert "timestamp" in metrics

    assert metrics["total_requests"] == 0
    assert metrics["total_errors"] == 0
    assert metrics["error_rate"] == 0.0


def test_metrics_collection():
    """Test that metrics are properly collected."""
    reset_metrics()  # Reset metrics before the test
    # Increment some metrics manually
    metrics_collector.increment_request()
    metrics_collector.increment_error()
    metrics_collector.record_tool_usage("test_tool")
    metrics_collector.record_response_time("test_tool", 0.1)

    metrics = get_metrics()

    assert metrics["total_requests"] == 1
    assert metrics["total_errors"] == 1
    assert metrics["error_rate"] == 1.0  # 1 error out of 1 request
    assert metrics["tool_usage"]["test_tool"] == 1
    assert abs(metrics["average_response_times"]["test_tool"] - 0.1) < 0.001


def test_multiple_tool_calls():
    """Test metrics collection with multiple tool calls."""
    # Reset metrics collector
    metrics_collector.request_count = 0
    metrics_collector.error_count = 0
    metrics_collector.tool_usage.clear()
    metrics_collector.response_times.clear()

    # Simulate multiple tool calls
    for i in range(5):
        metrics_collector.increment_request()
        metrics_collector.record_tool_usage("search_tool")
        metrics_collector.record_response_time("search_tool", 0.05 + i * 0.01)

    for i in range(3):
        metrics_collector.increment_request()
        metrics_collector.record_tool_usage("create_tool")
        metrics_collector.record_response_time("create_tool", 0.1 + i * 0.02)

    metrics = get_metrics()

    assert metrics["total_requests"] == 8  # 5 + 3
    assert metrics["tool_usage"]["search_tool"] == 5
    assert metrics["tool_usage"]["create_tool"] == 3

    expected_avg_search = sum([0.05 + i * 0.01 for i in range(5)]) / 5
    assert abs(metrics["average_response_times"]["search_tool"] - expected_avg_search) < 0.001

    expected_avg_create = sum([0.1 + i * 0.02 for i in range(3)]) / 3
    assert abs(metrics["average_response_times"]["create_tool"] - expected_avg_create) < 0.001


def test_error_rate_calculation():
    """Test that error rate is calculated correctly."""
    # Reset metrics collector
    metrics_collector.request_count = 0
    metrics_collector.error_count = 0

    # Add some requests and errors
    for _ in range(10):
        metrics_collector.increment_request()

    for _ in range(2):
        metrics_collector.increment_error()

    metrics = get_metrics()
    assert metrics["total_requests"] == 10
    assert metrics["total_errors"] == 2
    assert metrics["error_rate"] == 0.2  # 2 out of 10


def test_metrics_timestamp_format():
    """Test that the timestamp is in proper format."""
    reset_metrics()  # Reset metrics before the test
    metrics = get_metrics()
    timestamp = metrics["timestamp"]

    # Should be a string in ISO format
    assert isinstance(timestamp, str)
    # Basic check that it looks like an ISO format timestamp
    assert "T" in timestamp
    # The timestamp from datetime.utcnow().isoformat() doesn't include Z or +
    # Just verify it's in ISO-like format
    assert "T" in timestamp  # This is the basic requirement
