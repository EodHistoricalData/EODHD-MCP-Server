# tests/test_metrics.py
"""Tests for app/metrics.py module."""

import pytest
from app.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    request_count,
    request_errors,
    cache_hits,
    get_metrics,
    track_request
)


class TestCounter:
    """Tests for Counter class."""

    def test_increment(self):
        counter = Counter("test_counter", "Test counter")
        counter.inc()
        assert counter.get() == 1
        counter.inc(5)
        assert counter.get() == 6

    def test_with_labels(self):
        counter = Counter("test_counter", "Test counter")
        counter.inc(labels={"method": "GET"})
        counter.inc(labels={"method": "POST"})
        counter.inc(labels={"method": "GET"})
        assert counter.get(labels={"method": "GET"}) == 2
        assert counter.get(labels={"method": "POST"}) == 1

    def test_to_prometheus(self):
        counter = Counter("test_requests", "Test requests")
        counter.inc(5)
        output = counter.to_prometheus()
        assert "# HELP test_requests" in output
        assert "# TYPE test_requests counter" in output
        assert "test_requests 5" in output


class TestGauge:
    """Tests for Gauge class."""

    def test_set(self):
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(42.5)
        assert gauge.get() == 42.5

    def test_inc_dec(self):
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(10)
        gauge.inc(5)
        assert gauge.get() == 15
        gauge.dec(3)
        assert gauge.get() == 12

    def test_with_labels(self):
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(100, labels={"instance": "a"})
        gauge.set(200, labels={"instance": "b"})
        assert gauge.get(labels={"instance": "a"}) == 100
        assert gauge.get(labels={"instance": "b"}) == 200

    def test_to_prometheus(self):
        gauge = Gauge("active_connections", "Active connections")
        gauge.set(42)
        output = gauge.to_prometheus()
        assert "# TYPE active_connections gauge" in output
        assert "active_connections 42" in output


class TestHistogram:
    """Tests for Histogram class."""

    def test_observe(self):
        histogram = Histogram("test_histogram", "Test histogram")
        histogram.observe(0.1)
        histogram.observe(0.5)
        histogram.observe(1.5)
        assert histogram._count == 3
        assert histogram._sum == 2.1

    def test_buckets(self):
        histogram = Histogram("test_histogram", "Test histogram", buckets=(0.1, 0.5, 1.0))
        histogram.observe(0.05)  # <= 0.1
        histogram.observe(0.3)   # <= 0.5
        histogram.observe(0.8)   # <= 1.0
        histogram.observe(1.5)   # > 1.0
        # Each bucket counts observations <= its threshold
        # 0.05 goes into 0.1, 0.5, 1.0 buckets
        # 0.3 goes into 0.5, 1.0 buckets
        # 0.8 goes into 1.0 bucket
        # 1.5 goes into +Inf only
        assert histogram._bucket_counts[0.1] == 1  # only 0.05
        assert histogram._bucket_counts[0.5] == 2  # 0.05 and 0.3
        assert histogram._bucket_counts[1.0] == 3  # 0.05, 0.3, 0.8

    def test_to_prometheus(self):
        histogram = Histogram("request_duration", "Request duration")
        histogram.observe(0.1)
        output = histogram.to_prometheus()
        assert "# TYPE request_duration histogram" in output
        assert "request_duration_count 1" in output
        assert "request_duration_sum 0.1" in output


class TestMetricsRegistry:
    """Tests for MetricsRegistry class."""

    def test_register_and_get(self):
        registry = MetricsRegistry()
        counter = Counter("my_counter", "My counter")
        registry.register(counter)
        assert registry.get("my_counter") == counter

    def test_to_prometheus(self):
        registry = MetricsRegistry()
        counter = Counter("counter1", "Counter 1")
        gauge = Gauge("gauge1", "Gauge 1")
        registry.register(counter)
        registry.register(gauge)
        output = registry.to_prometheus()
        assert "counter1" in output
        assert "gauge1" in output


class TestGlobalMetrics:
    """Tests for global metrics."""

    def test_request_count_exists(self):
        assert request_count is not None
        assert request_count.name == "eodhd_requests_total"

    def test_request_errors_exists(self):
        assert request_errors is not None
        assert request_errors.name == "eodhd_request_errors_total"

    def test_get_metrics(self):
        output = get_metrics()
        assert "eodhd_requests_total" in output
        assert "eodhd_cache_hits_total" in output


class TestTrackRequestDecorator:
    """Tests for @track_request decorator."""

    @pytest.mark.asyncio
    async def test_async_function(self):
        @track_request("test_tool")
        async def my_async_func():
            return "result"

        result = await my_async_func()
        assert result == "result"

    def test_sync_function(self):
        @track_request("test_tool")
        def my_sync_func():
            return "result"

        result = my_sync_func()
        assert result == "result"
