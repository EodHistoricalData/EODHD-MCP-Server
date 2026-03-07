# get_user_details.py
import json

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_user_details(
        api_token: str | None = None,
    ) -> str:
        """

        Retrieve EODHD account details for the current API token. Use when the user asks about
        their subscription plan, API usage, rate limits, or account information.

        Returns account holder name, email, subscription type, payment method, API requests
        consumed today, daily rate limit, and invite token. This is account metadata only --
        does not return any financial market data.

        Args:
            api_token (str, optional): Per-call token override. If omitted, the
                                       env var EODHD_API_KEY is used.


        Returns:
            Object with:
            - name (str): account holder name
            - email (str): account email
            - subscriptionType (str): plan name (e.g. "allworld")
            - paymentMethod (str): payment method type
            - apiRequests (int): API calls used in current period
            - apiRequestsDate (str): current billing period date
            - dailyRateLimit (int): daily API call limit
            - extraLimit (int): extra API calls available
            - inviteToken (str): referral invite token
            - inviteTokenClicked (int): invite link click count
            - subscriptionMode (str): subscription billing mode

        Examples:
            "What plan am I on?" → get_user_details()
            "How many API calls have I used today?" → get_user_details()

        
        """
        # Endpoint: /api/user
        # The API returns JSON by default; no fmt parameter needed.
        url = f"{EODHD_API_BASE}/user"

        # If provided, include per-call token; otherwise make_request appends env token
        if api_token:
            url += f"?api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
