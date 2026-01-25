# tests/test_health.py
"""Tests for app/health.py module."""

import pytest
from app.health import (
    HealthChecker,
    get_liveness,
    get_readiness,
    get_status
)


class TestHealthChecker:
    """Tests for HealthChecker class."""

    def test_liveness(self):
        checker = HealthChecker()
        result = checker.liveness()
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert "uptime_seconds" in result

    def test_uptime_increases(self):
        import time
        checker = HealthChecker()
        uptime1 = checker.uptime_seconds
        time.sleep(0.1)
        uptime2 = checker.uptime_seconds
        assert uptime2 > uptime1

    @pytest.mark.asyncio
    async def test_readiness(self):
        checker = HealthChecker()
        result = await checker.readiness()
        assert "status" in result
        assert "checks" in result
        assert "api_key_configured" in result["checks"]

    @pytest.mark.asyncio
    async def test_status(self):
        checker = HealthChecker()
        result = await checker.status()
        assert "status" in result
        assert "version" in result
        assert "checks" in result
        assert "config" in result


class TestGlobalHealthFunctions:
    """Tests for global health check functions."""

    @pytest.mark.asyncio
    async def test_get_liveness(self):
        result = await get_liveness()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_get_readiness(self):
        result = await get_readiness()
        assert "status" in result

    @pytest.mark.asyncio
    async def test_get_status(self):
        result = await get_status()
        assert "version" in result
