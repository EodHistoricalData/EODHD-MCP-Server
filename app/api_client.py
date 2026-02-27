# app/api_client.py

import httpx
from .config import EODHD_API_KEY

#from fastmcp.server.dependencies import get_http_request


#def _resolve_eodhd_token_from_request() -> str | None:
#    """
#    Try to read ?apikey=... from the incoming MCP HTTP request.
#    Safe to call even outside HTTP context (falls back).
#    """
#    try:
#        req = get_http_request()
#    except RuntimeError:
#        # Not running under HTTP transport (e.g., stdio), or no active request
#        return None
#    except Exception:
#        return None
#
#    apikey = req.query_params.get("apikey")
#    if apikey:
#        return apikey

#    return req.query_params.get("api_key") or req.query_params.get("token")

# app/api_client.py

from fastmcp.server.dependencies import get_http_request

def _resolve_eodhd_token_from_request() -> str | None:
    try:
        req = get_http_request()
    except Exception:
        return None

    # 1) Authorization: Bearer <token>
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        if token:
            return token

    # 2) X-API-Key (optional)
    xkey = req.headers.get("x-api-key") or req.headers.get("X-API-Key")
    if xkey:
        return xkey.strip()

    # 3) Legacy query params
    apikey = req.query_params.get("apikey")
    if apikey:
        return apikey
    return req.query_params.get("api_key") or req.query_params.get("token")




def _ensure_api_token(url: str) -> str:
    """
    Inject api_token into URL query string if missing.
    Tool-provided api_token in the URL always wins.
    """
    if "api_token=" in url:
        return url

    token = _resolve_eodhd_token_from_request() or EODHD_API_KEY
    if not token:
        return url  # best-effort; caller may have other auth patterns

    return url + (f"&api_token={token}" if "?" in url else f"?api_token={token}")


async def make_request(
    url: str,
    method: str = "GET",
    json_body: dict | None = None,
    headers: dict | None = None,
    timeout: float = 30.0,
) -> dict | None:
    """
    Generic HTTP request helper for EODHD APIs.

    - Auto-injects api_token into URL if absent.
    - Supports GET (default) and POST with JSON payload.
    - Returns parsed JSON dict on success, or {"error": "..."} on failure.
    """
    url = _ensure_api_token(url)

    m = (method or "GET").upper()

    # Default headers
    req_headers = {}
    if headers:
        req_headers.update(headers)

    # If sending JSON, ensure content-type
    if json_body is not None and "Content-Type" not in {k.title(): v for k, v in req_headers.items()}:
        # Avoid overwriting if caller set it in any case variant
        if "content-type" not in (k.lower() for k in req_headers.keys()):
            req_headers["Content-Type"] = "application/json"

    async with httpx.AsyncClient() as client:
        try:
            if m == "GET":
                response = await client.get(url, headers=req_headers, timeout=timeout)
            elif m == "POST":
                response = await client.post(url, json=json_body, headers=req_headers, timeout=timeout)
            elif m == "PUT":
                response = await client.put(url, json=json_body, headers=req_headers, timeout=timeout)
            elif m == "DELETE":
                response = await client.delete(url, headers=req_headers, timeout=timeout)
            else:
                return {"error": f"Unsupported HTTP method: {m}"}

            response.raise_for_status()

            # Prefer JSON; if server returns non-JSON (e.g., HTML), return a helpful error object.
            try:
                return response.json()
            except Exception:
                ct = response.headers.get("content-type", "")
                text = response.text
                # Keep the payload small-ish
                if text and len(text) > 2000:
                    text = text[:2000] + "…"
                return {
                    "error": "Response is not valid JSON.",
                    "status_code": response.status_code,
                    "content_type": ct,
                    "text": text,
                }

        except httpx.HTTPStatusError as e:
            # Server returned a non-2xx
            text = e.response.text
            if text and len(text) > 2000:
                text = text[:2000] + "…"
            return {
                "error": str(e),
                "status_code": e.response.status_code,
                "text": text,
            }
        except Exception as e:
            return {"error": str(e)}
