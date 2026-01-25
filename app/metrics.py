# app/metrics.py
"""
Prometheus-compatible metrics for EODHD MCP Server.
"""

import time
from collections import defaultdict
from functools import wraps
from typing import Callable, Dict, Optional


class Counter:
    """Simple counter metric."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._value = 0
        self._labels: Dict[str, int] = defaultdict(int)

    def inc(self, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment counter."""
        if labels:
            key = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            self._labels[key] += value
        else:
            self._value += value

    def get(self, labels: Optional[Dict[str, str]] = None) -> int:
        """Get counter value."""
        if labels:
            key = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return self._labels.get(key, 0)
        return self._value

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        lines = [f"# HELP {self.name} {self.description}", f"# TYPE {self.name} counter"]
        if self._labels:
            for key, value in self._labels.items():
                lines.append(f"{self.name}{{{key}}} {value}")
        else:
            lines.append(f"{self.name} {self._value}")
        return "\n".join(lines)


class Gauge:
    """Simple gauge metric."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._value = 0.0
        self._labels: Dict[str, float] = defaultdict(float)

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set gauge value."""
        if labels:
            key = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            self._labels[key] = value
        else:
            self._value = value

    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment gauge."""
        if labels:
            key = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            self._labels[key] += value
        else:
            self._value += value

    def dec(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement gauge."""
        self.inc(-value, labels)

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value."""
        if labels:
            key = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return self._labels.get(key, 0.0)
        return self._value

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        lines = [f"# HELP {self.name} {self.description}", f"# TYPE {self.name} gauge"]
        if self._labels:
            for key, value in self._labels.items():
                lines.append(f"{self.name}{{{key}}} {value}")
        else:
            lines.append(f"{self.name} {self._value}")
        return "\n".join(lines)


class Histogram:
    """Simple histogram metric with buckets."""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(self, name: str, description: str = "", buckets: tuple = None):
        self.name = name
        self.description = description
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._count = 0
        self._sum = 0.0
        self._bucket_counts: Dict[float, int] = {b: 0 for b in self.buckets}
        self._bucket_counts[float("inf")] = 0

    def observe(self, value: float) -> None:
        """Record an observation."""
        self._count += 1
        self._sum += value
        for bucket in self.buckets:
            if value <= bucket:
                self._bucket_counts[bucket] += 1
        self._bucket_counts[float("inf")] += 1

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]
        cumulative = 0
        for bucket in self.buckets:
            cumulative += self._bucket_counts[bucket]
            lines.append(f'{self.name}_bucket{{le="{bucket}"}} {cumulative}')
        lines.append(f'{self.name}_bucket{{le="+Inf"}} {self._count}')
        lines.append(f"{self.name}_sum {self._sum}")
        lines.append(f"{self.name}_count {self._count}")
        return "\n".join(lines)


# Global metrics registry
class MetricsRegistry:
    """Central registry for all metrics."""

    def __init__(self):
        self.metrics: Dict[str, object] = {}

    def register(self, metric) -> None:
        """Register a metric."""
        self.metrics[metric.name] = metric

    def get(self, name: str):
        """Get a metric by name."""
        return self.metrics.get(name)

    def to_prometheus(self) -> str:
        """Export all metrics in Prometheus format."""
        return "\n\n".join(m.to_prometheus() for m in self.metrics.values())


# Global registry instance
registry = MetricsRegistry()

# Pre-defined metrics
request_count = Counter("eodhd_requests_total", "Total number of API requests")
request_errors = Counter("eodhd_request_errors_total", "Total number of API request errors")
request_latency = Histogram("eodhd_request_duration_seconds", "API request duration in seconds")
cache_hits = Counter("eodhd_cache_hits_total", "Total number of cache hits")
cache_misses = Counter("eodhd_cache_misses_total", "Total number of cache misses")
active_requests = Gauge("eodhd_active_requests", "Number of currently active requests")

# Register all metrics
for metric in [request_count, request_errors, request_latency, cache_hits, cache_misses, active_requests]:
    registry.register(metric)


def track_request(tool_name: str = "unknown"):
    """Decorator to track request metrics."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            labels = {"tool": tool_name}
            active_requests.inc(labels=labels)
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                request_count.inc(labels=labels)
                return result
            except Exception as e:
                request_errors.inc(labels=labels)
                raise
            finally:
                duration = time.time() - start_time
                request_latency.observe(duration)
                active_requests.dec(labels=labels)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            labels = {"tool": tool_name}
            active_requests.inc(labels=labels)
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                request_count.inc(labels=labels)
                return result
            except Exception as e:
                request_errors.inc(labels=labels)
                raise
            finally:
                duration = time.time() - start_time
                request_latency.observe(duration)
                active_requests.dec(labels=labels)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_metrics() -> str:
    """Get all metrics in Prometheus format."""
    return registry.to_prometheus()
