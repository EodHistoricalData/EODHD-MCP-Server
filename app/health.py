# app/health.py
"""
Health check endpoints for EODHD MCP Server.
"""

import asyncio
import time
from typing import Dict, Any
from app.config import EODHD_API_KEY, EODHD_API_BASE
from app.api_client import make_request


class HealthChecker:
    """Health check implementation."""

    def __init__(self):
        self.start_time = time.time()
        self._last_api_check: float = 0
        self._api_healthy: bool = True
        self._api_check_interval: float = 60.0  # Check API every 60 seconds

    @property
    def uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        return time.time() - self.start_time

    def liveness(self) -> Dict[str, Any]:
        """
        Liveness probe - is the server running?
        Returns healthy if the process is alive.
        """
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime_seconds": self.uptime_seconds
        }

    async def readiness(self) -> Dict[str, Any]:
        """
        Readiness probe - is the server ready to accept requests?
        Checks if dependencies are available.
        """
        checks = {
            "api_key_configured": bool(EODHD_API_KEY and EODHD_API_KEY != "demo"),
            "api_reachable": await self._check_api()
        }

        all_healthy = all(checks.values())

        return {
            "status": "ready" if all_healthy else "not_ready",
            "timestamp": time.time(),
            "checks": checks
        }

    async def status(self) -> Dict[str, Any]:
        """
        Detailed status endpoint with all health information.
        """
        readiness = await self.readiness()

        return {
            "status": "healthy" if readiness["status"] == "ready" else "degraded",
            "timestamp": time.time(),
            "uptime_seconds": self.uptime_seconds,
            "version": "2.6.0",
            "checks": {
                "liveness": self.liveness(),
                "readiness": readiness
            },
            "config": {
                "api_base": EODHD_API_BASE,
                "api_key_set": bool(EODHD_API_KEY and EODHD_API_KEY != "demo")
            }
        }

    async def _check_api(self) -> bool:
        """Check if EODHD API is reachable."""
        now = time.time()

        # Use cached result if recent
        if now - self._last_api_check < self._api_check_interval:
            return self._api_healthy

        try:
            # Simple API call to check connectivity
            url = f"{EODHD_API_BASE}/exchanges-list/?fmt=json"
            result = await make_request(url)

            self._api_healthy = result is not None and not (
                isinstance(result, dict) and result.get("error")
            )
        except Exception:
            self._api_healthy = False

        self._last_api_check = now
        return self._api_healthy


# Global health checker instance
health_checker = HealthChecker()


async def get_liveness() -> Dict[str, Any]:
    """Get liveness status."""
    return health_checker.liveness()


async def get_readiness() -> Dict[str, Any]:
    """Get readiness status."""
    return await health_checker.readiness()


async def get_status() -> Dict[str, Any]:
    """Get detailed status."""
    return await health_checker.status()
