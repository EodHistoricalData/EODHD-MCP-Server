#get_user_details.py
import json
from typing import Optional

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_user_details(
        api_token: Optional[str] = None,
    ) -> str:
        """
        User API (GET /api/user)

        Returns account information for the API token holder:
        name, email, subscriptionType, paymentMethod, apiRequests, apiRequestsDate,
        dailyRateLimit, extraLimit, inviteToken, inviteTokenClicked, subscriptionMode.

        Args:
            api_token (str, optional): Per-call token override. If omitted, the
                                       env var EODHD_API_KEY (via make_request) will be used.

        Returns:
            str: JSON string with user details or {"error": "..."} on failure.
        """
        # Endpoint: /api/user
        # The API returns JSON by default; no fmt parameter needed.
        url = f"{EODHD_API_BASE}/user"

        # If provided, include per-call token; otherwise make_request appends env token
        if api_token:
            url += f"?api_token={api_token}"

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
